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
  context             Preview /context/build from document text and a selection
  agent               Start an agent session chat
  sessions            List recent agent sessions
  messages <id>       Show messages in an agent session
  memory <id>         Show session memory
  set-memory <id>     Replace session memory interactively
  help                Show this help
  exit                Quit
"""


AGENT_HELP = """
Agent commands:
  /context            Attach or replace document context for later turns
  /clear-context      Clear attached document context
  /memory             Show memory for this session
  /set-memory         Replace memory for this session interactively
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
                request = _build_text_request_from_cli(client)
                request["style"] = input("Target style [polished]: ").strip() or "polished"
                response = _request_json(client, "POST", "/tasks/style", request)
                _print_task_response(response)
            elif command == "context":
                _run_context_build(client)
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
            elif command == "memory":
                if not args:
                    print("Usage: memory <session_id>")
                    continue
                _print_memory(
                    _request_json(client, "GET", f"/agent/sessions/{args[0]}/memory")
                )
            elif command == "set-memory":
                if not args:
                    print("Usage: set-memory <session_id>")
                    continue
                memory = _request_json(
                    client,
                    "PUT",
                    f"/agent/sessions/{args[0]}/memory",
                    _read_memory_update(),
                )
                _print_memory(memory)
            else:
                print(f"Unknown command: {command}")
        except (ApiCliError, httpx.HTTPError) as exc:
            print(f"Error: {exc}", file=sys.stderr)


def _run_task(client: httpx.Client, path: str) -> None:
    request = _build_text_request_from_cli(client)
    response = _request_json(client, "POST", path, request)
    _print_task_response(response)


def _run_context_build(client: httpx.Client) -> None:
    request = _read_document_context_request()
    response = _request_json(client, "POST", "/context/build", request)
    _print_context_result(response)


def _run_agent(client: httpx.Client) -> None:
    title = input("Session title [cli]: ").strip() or "cli"
    session = _request_json(client, "POST", "/agent/sessions", {"title": title})
    session_id = session["id"]
    document_context: dict[str, Any] | None = None

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
        if message in {"/context", "/text"}:
            document_context = _read_document_context_request()
            print("Document context attached.")
            continue
        if message in {"/clear-context", "/clear-text"}:
            document_context = None
            print("Document context cleared.")
            continue
        if message == "/messages":
            _print_messages(
                _request_json(client, "GET", f"/agent/sessions/{session_id}/messages")
            )
            continue
        if message == "/memory":
            _print_memory(
                _request_json(client, "GET", f"/agent/sessions/{session_id}/memory")
            )
            continue
        if message == "/set-memory":
            memory = _request_json(
                client,
                "PUT",
                f"/agent/sessions/{session_id}/memory",
                _read_memory_update(),
            )
            _print_memory(memory)
            continue
        if message == "/new":
            title = input("Session title [cli]: ").strip() or "cli"
            session = _request_json(client, "POST", "/agent/sessions", {"title": title})
            session_id = session["id"]
            document_context = None
            print(f"Agent session: {session_id}")
            continue

        payload: dict[str, Any] = {"message": message}
        if document_context is not None:
            payload["document_context"] = document_context
        turn = _request_json(
            client,
            "POST",
            f"/agent/sessions/{session_id}/messages",
            payload,
        )
        _print_task_response(turn["response"])


def _build_text_request_from_cli(client: httpx.Client) -> dict[str, Any]:
    context_request = _read_document_context_request()
    context_result = _request_json(client, "POST", "/context/build", context_request)
    _print_context_summary(context_result)
    return context_result["text_request"]


def _read_document_context_request() -> dict[str, Any]:
    title = input("Document title (optional): ").strip() or None
    print("Enter document text. Finish with a line containing only EOF.")
    print("Tip: paste the full text when available; paste only selected text if not.")
    document_text = _read_multiline()
    active_scope = input("Active scope [selection/paragraph/section/document]: ").strip()
    if active_scope not in {"selection", "paragraph", "section", "document"}:
        active_scope = "selection"

    print("Enter selected text, or leave empty and type EOF to use offsets/full document.")
    selected_text = _read_multiline().strip()
    start_raw = input("Selection start offset (optional, for exact document positions): ").strip()
    end_raw = input("Selection end offset (optional, for exact document positions): ").strip()
    instruction = input("Instruction (optional): ").strip() or None

    selection: dict[str, Any] | None = None
    if selected_text or start_raw or end_raw:
        selection = {
            "text": selected_text or None,
            "start": int(start_raw) if start_raw else None,
            "end": int(end_raw) if end_raw else None,
        }

    return {
        "title": title,
        "document_text": document_text,
        "selection": selection,
        "active_scope": active_scope,
        "instruction": instruction,
    }


def _read_memory_update() -> dict[str, Any]:
    print("Document summary. Finish with a line containing only EOF.")
    document_summary = _read_multiline().strip() or None
    print("Writing goals, one per line. Finish with EOF.")
    writing_goals = _read_multiline_list()
    print("Key terms, one per line. Finish with EOF.")
    key_terms = _read_multiline_list()
    print("User preferences, one per line. Finish with EOF.")
    user_preferences = _read_multiline_list()
    return {
        "document_summary": document_summary,
        "writing_goals": writing_goals,
        "key_terms": key_terms,
        "user_preferences": user_preferences,
    }


def _read_multiline() -> str:
    lines: list[str] = []
    while True:
        line = input()
        if line == "EOF":
            return "\n".join(lines)
        lines.append(line)


def _read_multiline_list() -> list[str]:
    return [line.strip() for line in _read_multiline().splitlines() if line.strip()]


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


def _print_context_result(response: dict[str, Any]) -> None:
    text_request = response["text_request"]
    context = text_request.get("context") or {}

    print("\n--- Context Build ---")
    print(f"active_scope: {response.get('active_scope')}")
    print(f"before_chars: {response.get('before_chars')}")
    print(f"after_chars: {response.get('after_chars')}")
    if response.get("warnings"):
        print("warnings:")
        for warning in response["warnings"]:
            print(f"- {warning}")

    print("\n--- Selected Text Sent To Model ---")
    print(text_request.get("text") or "")

    if context.get("before"):
        print("\n--- Before Context ---")
        print(context["before"])
    if context.get("after"):
        print("\n--- After Context ---")
        print(context["after"])


def _print_context_summary(response: dict[str, Any]) -> None:
    warnings = response.get("warnings") or []
    print(
        "Context built: "
        f"scope={response.get('active_scope')}, "
        f"before={response.get('before_chars')} chars, "
        f"after={response.get('after_chars')} chars"
    )
    for warning in warnings:
        print(f"Warning: {warning}")


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


def _print_memory(memory: dict[str, Any]) -> None:
    print("\n--- Session Memory ---")
    print(f"session_id: {memory['session_id']}")
    if memory.get("updated_at"):
        print(f"updated_at: {memory['updated_at']}")
    print("\nDocument summary:")
    print(memory.get("document_summary") or "(empty)")
    _print_named_list("Writing goals", memory.get("writing_goals") or [])
    _print_named_list("Key terms", memory.get("key_terms") or [])
    _print_named_list("User preferences", memory.get("user_preferences") or [])


def _print_named_list(title: str, items: list[str]) -> None:
    print(f"\n{title}:")
    if not items:
        print("(empty)")
        return
    for item in items:
        print(f"- {item}")


def _print_json(data: Any) -> None:
    print(json.dumps(data, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
