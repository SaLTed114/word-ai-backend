from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

import httpx


DEFAULT_BASE_URL = "http://127.0.0.1:8000"
PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SCENARIO = PROJECT_ROOT / "tests" / "scenarios" / "academic_rewrite.zh-CN.json"

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


class ScenarioTestError(Exception):
    pass


def main() -> int:
    _configure_stdio()
    parser = argparse.ArgumentParser(
        description="Run multi-turn agent scenarios against the backend.",
    )
    parser.add_argument(
        "scenario",
        nargs="?",
        default=str(DEFAULT_SCENARIO),
        help=f"Scenario JSON path. Default: {DEFAULT_SCENARIO}",
    )
    parser.add_argument("--base-url", default=DEFAULT_BASE_URL)
    parser.add_argument(
        "--mock",
        action="store_true",
        help="Run in-process with a fake model client instead of calling a running server.",
    )
    parser.add_argument(
        "--keep-session",
        action="store_true",
        help="Do not delete the scenario session after the test.",
    )
    args = parser.parse_args()

    scenario = load_scenario(Path(args.scenario))
    try:
        if args.mock:
            session_id = run_mock_scenario(scenario, keep_session=args.keep_session)
        else:
            with httpx.Client(base_url=args.base_url.rstrip("/"), timeout=180) as client:
                session_id = run_scenario(client, scenario, keep_session=args.keep_session)
        print("\nScenario test passed.")
        if args.keep_session and not args.mock:
            print(f"Kept session: {session_id}")
        return 0
    except (ScenarioTestError, httpx.HTTPError) as exc:
        print(f"\nScenario test failed: {exc}", file=sys.stderr)
        return 1


def load_scenario(path: Path) -> dict[str, Any]:
    if not path.exists():
        raise ScenarioTestError(f"Scenario file not found: {path}")
    return json.loads(path.read_text(encoding="utf-8"))


def run_mock_scenario(scenario: dict[str, Any], keep_session: bool = False) -> str:
    from fastapi.testclient import TestClient

    from app.main import app
    from app.models import ActionPreview, ActionTarget, TaskResponse, TextAction
    from app.storage import AgentSessionStore

    class FakeAgentClient:
        def __init__(self) -> None:
            self.turn_index = 0

        async def complete_task(self, prompt: str) -> TaskResponse:
            self.turn_index += 1
            if "Session memory:" not in prompt:
                raise ScenarioTestError("Session memory was not injected into the prompt.")
            if "Current document selection:" not in prompt:
                raise ScenarioTestError("Document context was not injected into the prompt.")
            return TaskResponse(
                task="agent",
                reply=f"Mock reply for turn {self.turn_index}. 已根据上下文和记忆处理。",
                summary=f"Mock summary for turn {self.turn_index}.",
                final_text=f"Mock academic rewrite version {self.turn_index}.",
                actions=[
                    TextAction(
                        id=f"mock_action_{self.turn_index}",
                        type="replace_selection",
                        target=ActionTarget(scope="selection"),
                        original=_selected_text(scenario),
                        replacement=f"Mock academic rewrite version {self.turn_index}.",
                        preview=ActionPreview(
                            before=_selected_text(scenario),
                            after=f"Mock academic rewrite version {self.turn_index}.",
                        ),
                        reason="Mock action generated for scenario validation.",
                        risk_level="low",
                        requires_confirmation=True,
                        confidence=0.9,
                    )
                ],
            )

    db_path = PROJECT_ROOT / "data" / "agent_scenario_test.sqlite3"
    db_path.parent.mkdir(parents=True, exist_ok=True)
    db_path.unlink(missing_ok=True)
    try:
        with TestClient(app) as client:
            store = AgentSessionStore(db_path)
            store.initialize()
            app.state.session_store = store
            app.state.ai_client = FakeAgentClient()
            return run_scenario(client, scenario, keep_session=keep_session)
    finally:
        if not keep_session:
            db_path.unlink(missing_ok=True)


def run_scenario(
    client: httpx.Client,
    scenario: dict[str, Any],
    keep_session: bool = False,
) -> str:
    title = scenario.get("title") or "agent-scenario"
    turns = scenario.get("turns") or []
    if not turns:
        raise ScenarioTestError("Scenario must contain at least one turn.")

    print(f"Scenario: {title}")
    health = request_json(client, "GET", "/health")
    print(f"Health: status={health.get('status')} ai_configured={health.get('ai_configured')}")
    if health.get("status") != "ok":
        raise ScenarioTestError("Backend health status is not ok.")
    if not health.get("ai_configured"):
        raise ScenarioTestError("AI client is not configured. Use --mock or configure .env.")

    document_context = scenario.get("document_context")
    if document_context:
        context_result = request_json(client, "POST", "/context/build", document_context)
        print_context_summary(context_result)

    session = request_json(client, "POST", "/agent/sessions", {"title": title})
    session_id = session["id"]
    print(f"Session: {session_id}")

    try:
        memory = scenario.get("memory")
        if memory is not None:
            memory_result = request_json(
                client,
                "PUT",
                f"/agent/sessions/{session_id}/memory",
                memory,
            )
            print_memory_summary(memory_result)

        for index, turn in enumerate(turns, 1):
            user_message = turn.get("user")
            if not user_message:
                raise ScenarioTestError(f"Turn {index} is missing user message.")
            payload: dict[str, Any] = {"message": user_message}
            if document_context:
                payload["document_context"] = document_context

            print(f"\nTurn {index}: {user_message}")
            result = request_json(
                client,
                "POST",
                f"/agent/sessions/{session_id}/messages",
                payload,
            )
            response = result["response"]
            print_response_summary(response)
            validate_turn_response(response, turn.get("expect") or {})

            messages = request_json(client, "GET", f"/agent/sessions/{session_id}/messages")
            print(f"Saved messages: {len(messages)}")
            expected_min_messages = turn.get("expect", {}).get("min_messages")
            if expected_min_messages is not None and len(messages) < expected_min_messages:
                raise ScenarioTestError(
                    f"Turn {index} expected at least {expected_min_messages} messages, "
                    f"got {len(messages)}."
                )

        return session_id
    finally:
        if not keep_session:
            request_json(client, "DELETE", f"/agent/sessions/{session_id}")
            print("\nDeleted scenario session.")


def validate_turn_response(response: dict[str, Any], expect: dict[str, Any]) -> None:
    for key in ("task", "reply", "actions"):
        assert_key(response, key)
    expected_task = expect.get("task")
    if expected_task and response["task"] != expected_task:
        raise ScenarioTestError(f"Expected task={expected_task}, got {response['task']}.")
    if not response.get("reply", "").strip():
        raise ScenarioTestError("Reply is empty.")
    if expect.get("requires_final_text") and not response.get("final_text"):
        raise ScenarioTestError("Expected final_text, got empty value.")

    actions = response.get("actions") or []
    min_actions = expect.get("min_actions")
    if min_actions is not None and len(actions) < min_actions:
        raise ScenarioTestError(f"Expected at least {min_actions} actions, got {len(actions)}.")
    if expect.get("requires_action_schema", True):
        for action in actions:
            for key in ("id", "type", "target", "risk_level", "requires_confirmation"):
                assert_key(action, key)


def request_json(
    client: httpx.Client,
    method: str,
    path: str,
    payload: dict[str, Any] | None = None,
) -> Any:
    response = client.request(method, path, json=payload)
    if response.status_code >= 400:
        raise ScenarioTestError(
            f"{method} {path} returned HTTP {response.status_code}: {response.text}"
        )
    return response.json()


def assert_key(data: dict[str, Any], key: str) -> None:
    if key not in data:
        raise ScenarioTestError(f"Missing expected key: {key}")


def _selected_text(scenario: dict[str, Any]) -> str:
    selection = (scenario.get("document_context") or {}).get("selection") or {}
    return selection.get("text") or ""


def print_context_summary(result: dict[str, Any]) -> None:
    print(
        "Context: "
        f"scope={result.get('active_scope')} "
        f"before={result.get('before_chars')} "
        f"after={result.get('after_chars')}"
    )
    for warning in result.get("warnings") or []:
        print(f"Context warning: {warning}")


def print_memory_summary(memory: dict[str, Any]) -> None:
    print("Memory:")
    print(f"- summary: {memory.get('document_summary') or '(empty)'}")
    print(f"- goals: {len(memory.get('writing_goals') or [])}")
    print(f"- terms: {len(memory.get('key_terms') or [])}")
    print(f"- preferences: {len(memory.get('user_preferences') or [])}")


def print_response_summary(response: dict[str, Any]) -> None:
    print(f"Reply: {response.get('reply')}")
    if response.get("final_text"):
        print(f"Final text: {response['final_text']}")
    actions = response.get("actions") or []
    print(f"Actions: {len(actions)}")
    for index, action in enumerate(actions, 1):
        print(
            f"  {index}. {action.get('type')} "
            f"risk={action.get('risk_level')} "
            f"confirm={action.get('requires_confirmation')}"
        )


def _configure_stdio() -> None:
    for stream in (sys.stdin, sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8", errors="replace")


if __name__ == "__main__":
    raise SystemExit(main())
