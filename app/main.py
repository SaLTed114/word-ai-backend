from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import ValidationError

from app.ai_client import AIClient, AIClientError
from app.config import AISettings
from app.models import (
    AgentMessage,
    AgentSession,
    AgentSessionCreateRequest,
    AgentSessionMessage,
    AgentSessionTurnRequest,
    AgentSessionTurnResponse,
    TaskResponse,
    TextRequest,
)
from app.services import run_agent_turn, run_style, run_syntax, run_word_choice
from app.storage import AgentSessionStore


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = AISettings.from_env()
    session_store = AgentSessionStore()
    session_store.initialize()
    app.state.settings = settings
    app.state.ai_client = AIClient(settings) if settings.is_ready() else None
    app.state.session_store = session_store
    yield


app = FastAPI(
    title="Word AI Backend",
    description="HTTP API for the Word/WPS AI writing assistant backend prototype.",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


def get_client() -> AIClient:
    client = app.state.ai_client
    if client is None:
        raise HTTPException(
            status_code=503,
            detail="AI client is not configured. Check .env and restart the server.",
        )
    return client


def get_session_store() -> AgentSessionStore:
    return app.state.session_store


@app.get("/health")
async def health() -> dict:
    settings: AISettings = app.state.settings
    return {
        "status": "ok",
        "ai_configured": app.state.ai_client is not None,
        "config": settings.redacted(),
    }


@app.post("/tasks/syntax", response_model=TaskResponse)
async def syntax_task(
    request: TextRequest,
    client: AIClient = Depends(get_client),
) -> TaskResponse:
    return await _handle_task(run_syntax(client, request))


@app.post("/tasks/word-choice", response_model=TaskResponse)
async def word_choice_task(
    request: TextRequest,
    client: AIClient = Depends(get_client),
) -> TaskResponse:
    return await _handle_task(run_word_choice(client, request))


@app.post("/tasks/style", response_model=TaskResponse)
async def style_task(
    request: TextRequest,
    client: AIClient = Depends(get_client),
) -> TaskResponse:
    return await _handle_task(run_style(client, request))


@app.post("/agent/sessions", response_model=AgentSession)
async def create_agent_session(
    request: AgentSessionCreateRequest,
    store: AgentSessionStore = Depends(get_session_store),
) -> AgentSession:
    return store.create_session(title=request.title)


@app.get("/agent/sessions", response_model=list[AgentSession])
async def list_agent_sessions(
    limit: int = 50,
    store: AgentSessionStore = Depends(get_session_store),
) -> list[AgentSession]:
    return store.list_sessions(limit=limit)


@app.get("/agent/sessions/{session_id}", response_model=AgentSession)
async def get_agent_session(
    session_id: str,
    store: AgentSessionStore = Depends(get_session_store),
) -> AgentSession:
    session = store.get_session(session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Agent session not found.")
    return session


@app.delete("/agent/sessions/{session_id}")
async def delete_agent_session(
    session_id: str,
    store: AgentSessionStore = Depends(get_session_store),
) -> dict:
    deleted = store.delete_session(session_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Agent session not found.")
    return {"deleted": True}


@app.get("/agent/sessions/{session_id}/messages", response_model=list[AgentSessionMessage])
async def list_agent_session_messages(
    session_id: str,
    limit: int = 50,
    store: AgentSessionStore = Depends(get_session_store),
) -> list[AgentSessionMessage]:
    _require_session(store, session_id)
    return store.list_messages(session_id=session_id, limit=limit)


@app.post("/agent/sessions/{session_id}/messages", response_model=AgentSessionTurnResponse)
async def create_agent_session_message(
    session_id: str,
    request: AgentSessionTurnRequest,
    client: AIClient = Depends(get_client),
    store: AgentSessionStore = Depends(get_session_store),
) -> AgentSessionTurnResponse:
    _require_session(store, session_id)
    previous_messages = store.list_messages(session_id=session_id, limit=50)
    history = _to_agent_history(previous_messages)
    user_message = store.add_message(
        session_id=session_id,
        role="user",
        content=request.message,
    )
    response = await _handle_task(
        run_agent_turn(
            client=client,
            message=request.message,
            selection=request.selection,
            history=history,
        )
    )
    assistant_message = store.add_message(
        session_id=session_id,
        role="assistant",
        content=response.reply,
        response=response,
    )
    session = store.get_session(session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Agent session not found.")
    return AgentSessionTurnResponse(
        session=session,
        user_message=user_message,
        assistant_message=assistant_message,
        response=response,
    )


async def _handle_task(coro) -> TaskResponse:
    try:
        return await coro
    except AIClientError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    except FileNotFoundError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    except ValidationError as exc:
        raise HTTPException(status_code=502, detail=exc.errors()) from exc


def _require_session(store: AgentSessionStore, session_id: str) -> AgentSession:
    session = store.get_session(session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Agent session not found.")
    return session


def _to_agent_history(messages: list[AgentSessionMessage]) -> list[AgentMessage]:
    return [
        AgentMessage(role=message.role, content=message.content)
        for message in messages
        if message.role in {"user", "assistant", "system"}
    ]
