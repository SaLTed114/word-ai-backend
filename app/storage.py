from __future__ import annotations

import json
import sqlite3
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

from app.models import (
    AgentSession,
    AgentSessionMemory,
    AgentSessionMemoryUpdate,
    AgentSessionMessage,
    TaskResponse,
)


DEFAULT_DB_PATH = Path("data") / "word_ai.sqlite3"


class AgentSessionStore:
    def __init__(self, db_path: str | Path = DEFAULT_DB_PATH) -> None:
        self.db_path = Path(db_path)

    def initialize(self) -> None:
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        with self._connect() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS agent_sessions (
                    id TEXT PRIMARY KEY,
                    title TEXT,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS agent_messages (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id TEXT NOT NULL,
                    role TEXT NOT NULL,
                    content TEXT NOT NULL,
                    response_json TEXT,
                    created_at TEXT NOT NULL,
                    FOREIGN KEY (session_id) REFERENCES agent_sessions(id)
                        ON DELETE CASCADE
                )
                """
            )
            conn.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_agent_messages_session_id
                ON agent_messages(session_id, id)
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS agent_session_memory (
                    session_id TEXT PRIMARY KEY,
                    document_summary TEXT,
                    writing_goals_json TEXT NOT NULL DEFAULT '[]',
                    key_terms_json TEXT NOT NULL DEFAULT '[]',
                    user_preferences_json TEXT NOT NULL DEFAULT '[]',
                    updated_at TEXT NOT NULL,
                    FOREIGN KEY (session_id) REFERENCES agent_sessions(id)
                        ON DELETE CASCADE
                )
                """
            )

    def create_session(self, title: str | None = None) -> AgentSession:
        now = _now()
        session_id = uuid4().hex
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO agent_sessions (id, title, created_at, updated_at)
                VALUES (?, ?, ?, ?)
                """,
                (session_id, title, now, now),
            )
        return AgentSession(
            id=session_id,
            title=title,
            created_at=now,
            updated_at=now,
            message_count=0,
        )

    def get_session(self, session_id: str) -> AgentSession | None:
        with self._connect() as conn:
            row = conn.execute(
                """
                SELECT
                    s.id,
                    s.title,
                    s.created_at,
                    s.updated_at,
                    COUNT(m.id) AS message_count
                FROM agent_sessions s
                LEFT JOIN agent_messages m ON m.session_id = s.id
                WHERE s.id = ?
                GROUP BY s.id
                """,
                (session_id,),
            ).fetchone()
        return _session_from_row(row) if row else None

    def list_sessions(self, limit: int = 50) -> list[AgentSession]:
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT
                    s.id,
                    s.title,
                    s.created_at,
                    s.updated_at,
                    COUNT(m.id) AS message_count
                FROM agent_sessions s
                LEFT JOIN agent_messages m ON m.session_id = s.id
                GROUP BY s.id
                ORDER BY s.updated_at DESC
                LIMIT ?
                """,
                (limit,),
            ).fetchall()
        return [_session_from_row(row) for row in rows]

    def delete_session(self, session_id: str) -> bool:
        with self._connect() as conn:
            result = conn.execute(
                "DELETE FROM agent_sessions WHERE id = ?",
                (session_id,),
            )
        return result.rowcount > 0

    def list_messages(self, session_id: str, limit: int = 50) -> list[AgentSessionMessage]:
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT id, session_id, role, content, response_json, created_at
                FROM agent_messages
                WHERE session_id = ?
                ORDER BY id DESC
                LIMIT ?
                """,
                (session_id, limit),
            ).fetchall()
        messages = [_message_from_row(row) for row in rows]
        messages.reverse()
        return messages

    def add_message(
        self,
        session_id: str,
        role: str,
        content: str,
        response: TaskResponse | None = None,
    ) -> AgentSessionMessage:
        now = _now()
        response_json = response.model_dump_json() if response else None
        with self._connect() as conn:
            cursor = conn.execute(
                """
                INSERT INTO agent_messages
                    (session_id, role, content, response_json, created_at)
                VALUES (?, ?, ?, ?, ?)
                """,
                (session_id, role, content, response_json, now),
            )
            conn.execute(
                """
                UPDATE agent_sessions
                SET updated_at = ?
                WHERE id = ?
                """,
                (now, session_id),
            )
        return AgentSessionMessage(
            id=int(cursor.lastrowid),
            session_id=session_id,
            role=role,
            content=content,
            created_at=now,
            response=response,
        )

    def get_memory(self, session_id: str) -> AgentSessionMemory:
        with self._connect() as conn:
            row = conn.execute(
                """
                SELECT
                    session_id,
                    document_summary,
                    writing_goals_json,
                    key_terms_json,
                    user_preferences_json,
                    updated_at
                FROM agent_session_memory
                WHERE session_id = ?
                """,
                (session_id,),
            ).fetchone()
        if row is None:
            return AgentSessionMemory(session_id=session_id)
        return _memory_from_row(row)

    def upsert_memory(
        self,
        session_id: str,
        update: AgentSessionMemoryUpdate,
    ) -> AgentSessionMemory:
        now = _now()
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO agent_session_memory (
                    session_id,
                    document_summary,
                    writing_goals_json,
                    key_terms_json,
                    user_preferences_json,
                    updated_at
                )
                VALUES (?, ?, ?, ?, ?, ?)
                ON CONFLICT(session_id) DO UPDATE SET
                    document_summary = excluded.document_summary,
                    writing_goals_json = excluded.writing_goals_json,
                    key_terms_json = excluded.key_terms_json,
                    user_preferences_json = excluded.user_preferences_json,
                    updated_at = excluded.updated_at
                """,
                (
                    session_id,
                    update.document_summary,
                    json.dumps(update.writing_goals, ensure_ascii=False),
                    json.dumps(update.key_terms, ensure_ascii=False),
                    json.dumps(update.user_preferences, ensure_ascii=False),
                    now,
                ),
            )
            conn.execute(
                """
                UPDATE agent_sessions
                SET updated_at = ?
                WHERE id = ?
                """,
                (now, session_id),
            )
        return AgentSessionMemory(
            session_id=session_id,
            document_summary=update.document_summary,
            writing_goals=update.writing_goals,
            key_terms=update.key_terms,
            user_preferences=update.user_preferences,
            updated_at=now,
        )

    @contextmanager
    def _connect(self) -> Iterator[sqlite3.Connection]:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()


def _now() -> str:
    return datetime.now(UTC).isoformat()


def _session_from_row(row: sqlite3.Row) -> AgentSession:
    return AgentSession(
        id=row["id"],
        title=row["title"],
        created_at=row["created_at"],
        updated_at=row["updated_at"],
        message_count=row["message_count"],
    )


def _message_from_row(row: sqlite3.Row) -> AgentSessionMessage:
    response_json = row["response_json"]
    response = TaskResponse.model_validate(json.loads(response_json)) if response_json else None
    return AgentSessionMessage(
        id=row["id"],
        session_id=row["session_id"],
        role=row["role"],
        content=row["content"],
        created_at=row["created_at"],
        response=response,
    )


def _memory_from_row(row: sqlite3.Row) -> AgentSessionMemory:
    return AgentSessionMemory(
        session_id=row["session_id"],
        document_summary=row["document_summary"],
        writing_goals=json.loads(row["writing_goals_json"]),
        key_terms=json.loads(row["key_terms_json"]),
        user_preferences=json.loads(row["user_preferences_json"]),
        updated_at=row["updated_at"],
    )
