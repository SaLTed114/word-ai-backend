from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

import httpx


DEFAULT_BASE_URL = "http://127.0.0.1:8000"
PROJECT_ROOT = Path(__file__).resolve().parents[1]

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

DOCUMENT_TEXT = """Title: Draft Methods Section

The proposed pipeline aims to support student writing in biomedical engineering reports.

This method is good and useful. It can help users revise grammar and style, but the current wording is too vague for an academic methods section.

In future work, the system should preserve domain terms and avoid changing the scientific meaning."""

SELECTED_TEXT = "This method is good and useful."

USER_MESSAGE = (
    "请解释选中句子的问题，并给出一个更正式、更适合学术论文方法部分的英文改写。"
)


class AgentFlowTestError(Exception):
    pass


def main() -> int:
    _configure_stdio()
    parser = argparse.ArgumentParser(
        description="Run a fixed end-to-end agent flow against a running backend.",
    )
    parser.add_argument("--base-url", default=DEFAULT_BASE_URL)
    parser.add_argument(
        "--keep-session",
        action="store_true",
        help="Do not delete the test session after the test.",
    )
    parser.add_argument(
        "--mock",
        action="store_true",
        help="Run in-process with a fake model client instead of calling a running server.",
    )
    args = parser.parse_args()

    try:
        if args.mock:
            session_id = run_mock_agent_flow(keep_session=args.keep_session)
        else:
            with httpx.Client(base_url=args.base_url.rstrip("/"), timeout=180) as client:
                session_id = run_agent_flow(client, keep_session=args.keep_session)
        print("\nAgent flow test passed.")
        if args.keep_session and not args.mock:
            print(f"Kept session: {session_id}")
        return 0
    except (AgentFlowTestError, httpx.HTTPError) as exc:
        print(f"\nAgent flow test failed: {exc}", file=sys.stderr)
        return 1


def run_mock_agent_flow(keep_session: bool = False) -> str:
    from fastapi.testclient import TestClient

    from app.main import app
    from app.models import ActionPreview, ActionTarget, TaskResponse, TextAction
    from app.storage import AgentSessionStore

    class FakeAgentClient:
        async def complete_task(self, prompt: str) -> TaskResponse:
            if "Session memory:" not in prompt:
                raise AgentFlowTestError("Session memory was not injected into the prompt.")
            if SELECTED_TEXT not in prompt:
                raise AgentFlowTestError("Selected text was not injected into the prompt.")
            return TaskResponse(
                task="agent",
                reply=(
                    "这句话的问题是 good 和 useful 过于笼统，且不符合方法部分的学术表达。"
                ),
                summary="建议用更具体、更正式的 academic wording 替换笼统评价。",
                final_text="This method is effective and valuable for academic writing support.",
                actions=[
                    TextAction(
                        id="mock_action_1",
                        type="replace_selection",
                        target=ActionTarget(scope="selection"),
                        original=SELECTED_TEXT,
                        replacement=(
                            "This method is effective and valuable for academic writing support."
                        ),
                        preview=ActionPreview(
                            before=SELECTED_TEXT,
                            after=(
                                "This method is effective and valuable for academic writing support."
                            ),
                        ),
                        reason="Replace vague wording with a more specific academic expression.",
                        risk_level="low",
                        requires_confirmation=True,
                        confidence=0.92,
                    )
                ],
            )

    db_path = PROJECT_ROOT / "data" / "agent_flow_test.sqlite3"
    db_path.parent.mkdir(parents=True, exist_ok=True)
    db_path.unlink(missing_ok=True)
    try:
        with TestClient(app) as client:
            store = AgentSessionStore(db_path)
            store.initialize()
            app.state.session_store = store
            app.state.ai_client = FakeAgentClient()
            return run_agent_flow(client, keep_session=keep_session)
    finally:
        if not keep_session:
            db_path.unlink(missing_ok=True)


def run_agent_flow(client: httpx.Client, keep_session: bool = False) -> str:
    print("1. Checking health ...")
    health = request_json(client, "GET", "/health")
    print_json(health)
    if health.get("status") != "ok":
        raise AgentFlowTestError("Backend health status is not ok.")
    if not health.get("ai_configured"):
        raise AgentFlowTestError("AI client is not configured. Check .env and restart API.")

    print("\n2. Previewing context builder ...")
    document_context = build_document_context()
    context_result = request_json(client, "POST", "/context/build", document_context)
    print_context_result(context_result)
    assert_key(context_result, "text_request")
    if context_result["text_request"]["text"] != SELECTED_TEXT:
        raise AgentFlowTestError("Context builder did not preserve selected text.")

    print("\n3. Creating agent session ...")
    session = request_json(client, "POST", "/agent/sessions", {"title": "agent-flow-test"})
    session_id = session["id"]
    print_json(session)

    try:
        print("\n4. Setting session memory ...")
        memory = request_json(
            client,
            "PUT",
            f"/agent/sessions/{session_id}/memory",
            {
                "document_summary": (
                    "A draft methods section for a biomedical engineering writing assistant."
                ),
                "writing_goals": [
                    "Use concise academic English.",
                    "Preserve the scientific meaning.",
                    "Avoid vague evaluative wording.",
                ],
                "key_terms": [
                    "biomedical engineering reports",
                    "grammar and style revision",
                    "academic methods section",
                ],
                "user_preferences": [
                    "Explain issues in Chinese.",
                    "Provide the final rewrite in English.",
                ],
            },
        )
        print_memory(memory)

        print("\n5. Sending agent turn ...")
        turn = request_json(
            client,
            "POST",
            f"/agent/sessions/{session_id}/messages",
            {
                "message": USER_MESSAGE,
                "document_context": document_context,
            },
        )
        response = turn["response"]
        print_task_response(response)
        validate_agent_response(response)

        print("\n6. Reading saved messages ...")
        messages = request_json(client, "GET", f"/agent/sessions/{session_id}/messages")
        print_messages(messages)
        if len(messages) < 2:
            raise AgentFlowTestError("Expected at least one user and one assistant message.")

        return session_id
    finally:
        if not keep_session:
            print("\n7. Cleaning up session ...")
            request_json(client, "DELETE", f"/agent/sessions/{session_id}")
            print("Deleted test session.")


def build_document_context() -> dict[str, Any]:
    return {
        "document_id": "agent-flow-test-doc",
        "title": "Draft Methods Section",
        "section_heading": "Methods",
        "document_text": DOCUMENT_TEXT,
        "selection": {
            "text": SELECTED_TEXT,
        },
        "active_scope": "selection",
        "context_window_chars": 300,
        "instruction": "Keep the final rewrite suitable for an academic methods section.",
    }


def request_json(
    client: httpx.Client,
    method: str,
    path: str,
    payload: dict[str, Any] | None = None,
) -> Any:
    response = client.request(method, path, json=payload)
    if response.status_code >= 400:
        raise AgentFlowTestError(
            f"{method} {path} returned HTTP {response.status_code}: {response.text}"
        )
    return response.json()


def validate_agent_response(response: dict[str, Any]) -> None:
    for key in ("task", "reply", "actions"):
        assert_key(response, key)
    if response["task"] != "agent":
        raise AgentFlowTestError(f"Expected task=agent, got {response['task']!r}.")
    if not response["reply"].strip():
        raise AgentFlowTestError("Agent reply is empty.")

    final_text = response.get("final_text")
    actions = response.get("actions") or []
    if not final_text and not actions:
        raise AgentFlowTestError("Expected final_text or at least one action.")

    for action in actions:
        for key in ("id", "type", "target", "risk_level", "requires_confirmation"):
            assert_key(action, key)


def assert_key(data: dict[str, Any], key: str) -> None:
    if key not in data:
        raise AgentFlowTestError(f"Missing expected key: {key}")


def print_context_result(result: dict[str, Any]) -> None:
    print(
        "Context built: "
        f"scope={result.get('active_scope')}, "
        f"before={result.get('before_chars')} chars, "
        f"after={result.get('after_chars')} chars"
    )
    if result.get("warnings"):
        print("Warnings:")
        for warning in result["warnings"]:
            print(f"- {warning}")
    print("\nSelected text sent to model:")
    print(result["text_request"]["text"])


def print_memory(memory: dict[str, Any]) -> None:
    print(f"session_id: {memory['session_id']}")
    print(f"document_summary: {memory.get('document_summary')}")
    print_list("writing_goals", memory.get("writing_goals") or [])
    print_list("key_terms", memory.get("key_terms") or [])
    print_list("user_preferences", memory.get("user_preferences") or [])


def print_task_response(response: dict[str, Any]) -> None:
    print("\n--- Reply ---")
    print(response.get("reply") or "")
    if response.get("summary"):
        print("\n--- Summary ---")
        print(response["summary"])
    if response.get("final_text"):
        print("\n--- Final Text ---")
        print(response["final_text"])
    actions = response.get("actions") or []
    if actions:
        print("\n--- Actions ---")
        for index, action in enumerate(actions, 1):
            print(
                f"{index}. [{action.get('risk_level')}] "
                f"{action.get('type')} ({action.get('id')})"
            )
            print(f"   target: {(action.get('target') or {}).get('scope')}")
            if action.get("replacement"):
                print(f"   replacement: {action['replacement']}")
            if action.get("reason"):
                print(f"   reason: {action['reason']}")


def print_messages(messages: list[dict[str, Any]]) -> None:
    for message in messages:
        print(f"[{message['id']}] {message['role']}: {message['content']}")


def print_list(title: str, items: list[str]) -> None:
    print(f"{title}:")
    for item in items:
        print(f"- {item}")


def print_json(data: Any) -> None:
    print(json.dumps(data, ensure_ascii=False, indent=2))


def _configure_stdio() -> None:
    for stream in (sys.stdin, sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8", errors="replace")


if __name__ == "__main__":
    raise SystemExit(main())
