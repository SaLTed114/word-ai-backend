from __future__ import annotations

import argparse
import json
import os
import sys
from typing import Any

import httpx


DEFAULT_BASE_URL = "http://127.0.0.1:8000"


HELP = """
Commands:
  health              Check backend health
  syntax              Send selected text to /tasks/syntax
  word                Send selected text to /tasks/word-choice
  style               Send selected text to /tasks/style
  agent               Start an agent session chat
  sessions            List recent agent sessions
  messages <id>       Show messages in an agent session
  help                Show this help
  exit                Quit
"""


AGENT_HELP = """
Agent commands:
  /text               Attach or replace selected text for later turns
  /clear-text         Clear attached selected text
  /messages           Show messages in this session
  /new                Start a new session
  /help               Show this help
  /exit               Leave agent mode
"""


class ApiCliError(Exception):
    pass


def main() -> None:
    _configure_stdio()
    parser = argparse.ArgumentParser(
        description="Small HTTP CLI for the Word AI backend.",
    )
    parser.add_argument(
        "--base-url",
        default=os.environ.get("WORD_AI_API_URL", DEFAULT_BASE_URL),
        help=f"Backend base URL. Default: {DEFAULT_BASE_URL}",
    )
    args = parser.parse_args()

    with httpx.Client(base_url=args.base_url.rstrip("/"), timeout=120) as client:
        _run_shell(client, args.base_url.rstrip("/"))


def _configure_stdio() -> None:
    for stream in (sys.stdin, sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8", errors="replace")


def _run_shell(client: httpx.Client, base_url: str) -> None:
    print("Word AI backend HTTP CLI")
    print(f"Backend: {base_url}")
    print("Type 'help' for commands.")

    while True:
        command_line = input("\nword-ai-http> ").strip()
        if not command_line:
            continue
        command, *args = command_line.split()
        command = command.lower()

        try:
            if command in {"exit", "quit", "q"}:
                return
            if command in {"help", "?"}:
                print(HELP.strip())
            elif command == "health":
                _print_json(_request_json(client, "GET", "/health"))
            elif command == "syntax":
                _run_task(client, "/tasks/syntax")
            elif command == "word":
                _run_task(client, "/tasks/word-choice")
            elif command == "style":
                request = _read_text_request()
                request["style"] = input("Target style [polished]: ").strip() or "polished"
                response = _request_json(client, "POST", "/tasks/style", request)
                _print_task_response(response)
            elif command == "agent":
                _run_agent(client)
            elif command == "sessions":
                _print_sessions(_request_json(client, "GET", "/agent/sessions"))
            elif command == "messages":
                if not args:
                    print("Usage: messages <session_id>")
                    continue
                _print_messages(
                    _request_json(client, "GET", f"/agent/sessions/{args[0]}/messages")
                )
            else:
                print(f"Unknown command: {command}")
        except (ApiCliError, httpx.HTTPError) as exc:
            print(f"Error: {exc}", file=sys.stderr)


def _run_task(client: httpx.Client, path: str) -> None:
    request = _read_text_request()
    response = _request_json(client, "POST", path, request)
    _print_task_response(response)


def _run_agent(client: httpx.Client) -> None:
    title = input("Session title [cli]: ").strip() or "cli"
    session = _request_json(client, "POST", "/agent/sessions", {"title": title})
    session_id = session["id"]
    selection: dict[str, Any] | None = None

    print(f"Agent session: {session_id}")
    print("Type /help for agent commands.")

    while True:
        message = input("\nagent> ").strip()
        if not message:
            continue
        if message in {"/exit", "/quit"}:
            return
        if message == "/help":
            print(AGENT_HELP.strip())
            continue
        if message == "/text":
            selection = _read_text_request()
            print("Selected text attached.")
            continue
        if message == "/clear-text":
            selection = None
            print("Selected text cleared.")
            continue
        if message == "/messages":
            _print_messages(
                _request_json(client, "GET", f"/agent/sessions/{session_id}/messages")
            )
            continue
        if message == "/new":
            title = input("Session title [cli]: ").strip() or "cli"
            session = _request_json(client, "POST", "/agent/sessions", {"title": title})
            session_id = session["id"]
            selection = None
            print(f"Agent session: {session_id}")
            continue

        payload: dict[str, Any] = {"message": message}
        if selection is not None:
            payload["selection"] = selection
        turn = _request_json(
            client,
            "POST",
            f"/agent/sessions/{session_id}/messages",
            payload,
        )
        _print_task_response(turn["response"])


def _read_text_request() -> dict[str, Any]:
    print("Enter selected text. Finish with a line containing only EOF.")
    text = _read_multiline()
    before = input("Before context (optional): ").strip() or None
    after = input("After context (optional): ").strip() or None
    instruction = input("Instruction (optional): ").strip() or None
    return {
        "text": text,
        "context": {
            "before": before,
            "after": after,
        },
        "instruction": instruction,
    }


def _read_multiline() -> str:
    lines: list[str] = []
    while True:
        line = input()
        if line == "EOF":
            return "\n".join(lines)
        lines.append(line)


def _request_json(
    client: httpx.Client,
    method: str,
    path: str,
    payload: dict[str, Any] | None = None,
) -> Any:
    response = client.request(method, path, json=payload)
    if response.status_code >= 400:
        detail = _safe_response_json(response)
        raise ApiCliError(
            f"{method} {path} failed with HTTP {response.status_code}: "
            f"{json.dumps(detail, ensure_ascii=False)}"
        )
    return response.json()


def _safe_response_json(response: httpx.Response) -> Any:
    try:
        return response.json()
    except ValueError:
        return response.text


def _print_task_response(response: dict[str, Any]) -> None:
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
            _print_action(index, action)


def _print_action(index: int, action: dict[str, Any]) -> None:
    target = action.get("target") or {}
    preview = action.get("preview") or {}
    risk_level = action.get("risk_level") or action.get("severity") or "info"
    print(f"{index}. [{risk_level}] {action.get('type', 'none')} ({action.get('id', 'no-id')})")
    print(f"   target: {target.get('scope', 'selection')}")
    if target.get("start") is not None or target.get("end") is not None:
        print(f"   range: {target.get('start')}..{target.get('end')}")
    if target.get("anchor_text"):
        print(f"   anchor: {target['anchor_text']}")
    if action.get("requires_confirmation") is not None:
        print(f"   requires confirmation: {action['requires_confirmation']}")
    if action.get("confidence") is not None:
        print(f"   confidence: {action['confidence']}")
    if action.get("original"):
        print(f"   original: {action['original']}")
    if action.get("replacement"):
        print(f"   replacement: {action['replacement']}")
    if preview.get("before"):
        print(f"   preview before: {preview['before']}")
    if preview.get("after"):
        print(f"   preview after: {preview['after']}")
    if action.get("reason"):
        print(f"   reason: {action['reason']}")


def _print_sessions(sessions: list[dict[str, Any]]) -> None:
    if not sessions:
        print("No sessions.")
        return
    for session in sessions:
        print(
            f"{session['id']}  "
            f"messages={session.get('message_count', 0)}  "
            f"title={session.get('title') or ''}"
        )


def _print_messages(messages: list[dict[str, Any]]) -> None:
    if not messages:
        print("No messages.")
        return
    for message in messages:
        print(f"\n[{message['id']}] {message['role']}  {message['created_at']}")
        print(message["content"])
        if message.get("response"):
            _print_task_response(message["response"])


def _print_json(data: Any) -> None:
    print(json.dumps(data, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
