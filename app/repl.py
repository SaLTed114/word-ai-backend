from __future__ import annotations

import asyncio
from getpass import getpass

from pydantic import ValidationError

from app.ai_client import AIClient, AIClientError
from app.config import AISettings
from app.models import AgentMessage, TaskResponse, TextRequest
from app.services import run_agent_turn, run_style, run_syntax, run_word_choice


HELP = """
Commands:
  config          Show or update AI configuration
  syntax          Check grammar, spelling, punctuation, and clarity
  word            Check word choice and phrasing
  style           Rewrite selected text into a chosen style
  agent           Chat with the assistant about selected text
  help            Show this help
  exit            Quit
"""


def main() -> None:
    asyncio.run(run_repl())


async def run_repl() -> None:
    settings = AISettings.from_env()
    client: AIClient | None = _make_client(settings)

    print("Word AI backend REPL")
    print("Type 'help' for commands.")

    while True:
        command = input("\nword-ai> ").strip().lower()
        if command in {"exit", "quit", "q"}:
            return
        if command in {"help", "?"}:
            print(HELP)
            continue
        if command == "config":
            settings = _configure(settings)
            client = _make_client(settings)
            continue
        if command in {"syntax", "word", "style", "agent"}:
            if client is None:
                print("AI client is not configured. Run 'config' first.")
                continue
            await _run_command(command, client)
            continue
        if not command:
            continue
        print(f"Unknown command: {command}")


def _make_client(settings: AISettings) -> AIClient | None:
    if not settings.is_ready():
        print("AI config is incomplete. Run 'config' or create a .env file.")
        return None
    try:
        print(f"Using config: {settings.redacted()}")
        return AIClient(settings)
    except AIClientError as exc:
        print(f"Config error: {exc}")
        return None


def _configure(settings: AISettings) -> AISettings:
    print(f"Current config: {settings.redacted()}")
    api_key = getpass("API key (blank to keep current): ").strip() or settings.api_key
    model = input(f"Model [{settings.model}]: ").strip() or settings.model
    base_url = input(f"Base URL [{settings.base_url}]: ").strip() or settings.base_url
    api_endpoint = input(
        f"Direct API endpoint [{settings.api_endpoint or 'none'}]: "
    ).strip()
    if not api_endpoint:
        api_endpoint = settings.api_endpoint
    elif api_endpoint.lower() in {"none", "null", "-"}:
        api_endpoint = None
    proxy_url = input(f"Proxy URL [{settings.proxy_url or 'none'}]: ").strip()
    if not proxy_url:
        proxy_url = settings.proxy_url
    elif proxy_url.lower() in {"none", "null", "-"}:
        proxy_url = None

    trust_env_raw = input(
        f"Trust system proxy env [{settings.trust_env}] (true/false): "
    ).strip()
    trust_env = (
        settings.trust_env
        if not trust_env_raw
        else trust_env_raw.lower() in {"1", "true", "yes"}
    )

    use_json_mode_raw = input(
        f"Use JSON mode [{settings.use_json_mode}] (true/false): "
    ).strip()
    use_json_mode = (
        settings.use_json_mode
        if not use_json_mode_raw
        else use_json_mode_raw.lower() not in {"0", "false", "no"}
    )
    return AISettings(
        api_key=api_key,
        model=model,
        base_url=base_url,
        api_endpoint=api_endpoint,
        proxy_url=proxy_url,
        trust_env=trust_env,
        use_json_mode=use_json_mode,
    )


async def _run_command(command: str, client: AIClient) -> None:
    try:
        if command == "agent":
            await _run_agent(client)
            return

        request = _read_text_request()
        if command == "style":
            request.style = input("Target style: ").strip() or "polished"
            response = await run_style(client, request)
        elif command == "word":
            response = await run_word_choice(client, request)
        else:
            response = await run_syntax(client, request)

        _print_response(response)
    except (AIClientError, ValidationError, FileNotFoundError) as exc:
        print(f"Error: {exc}")


async def _run_agent(client: AIClient) -> None:
    print("Agent mode. Type /exit to leave. Type /text to attach selected text.")
    selection: TextRequest | None = None
    history: list[AgentMessage] = []
    while True:
        message = input("\nagent> ").strip()
        if message in {"/exit", "/quit"}:
            return
        if message == "/text":
            selection = _read_text_request()
            print("Attached selected text for later agent turns.")
            continue
        if not message:
            continue
        try:
            response = await run_agent_turn(
                client=client,
                message=message,
                selection=selection,
                history=history,
            )
            _print_response(response)
            history.append(AgentMessage(role="user", content=message))
            history.append(AgentMessage(role="assistant", content=response.reply))
        except (AIClientError, ValidationError, FileNotFoundError) as exc:
            print(f"Error: {exc}")


def _read_text_request() -> TextRequest:
    print("Enter selected text. Finish with a line containing only EOF.")
    lines: list[str] = []
    while True:
        line = input()
        if line == "EOF":
            break
        lines.append(line)

    before = input("Before context (optional): ").strip() or None
    after = input("After context (optional): ").strip() or None
    instruction = input("Instruction (optional): ").strip() or None
    return TextRequest(
        text="\n".join(lines),
        context={"before": before, "after": after},
        instruction=instruction,
    )


def _print_response(response: TaskResponse) -> None:
    print("\n--- Reply ---")
    print(response.reply)
    if response.summary:
        print(f"\nSummary: {response.summary}")
    if response.final_text:
        print("\n--- Final Text ---")
        print(response.final_text)
    if response.actions:
        print("\n--- Actions ---")
        for index, action in enumerate(response.actions, 1):
            print(f"{index}. [{action.risk_level}] {action.type} ({action.id})")
            print(f"   target: {action.target.scope}")
            if action.target.start is not None or action.target.end is not None:
                print(f"   range: {action.target.start}..{action.target.end}")
            if action.requires_confirmation:
                print("   requires confirmation: true")
            if action.original:
                print(f"   original: {action.original}")
            if action.replacement:
                print(f"   replacement: {action.replacement}")
            if action.preview:
                if action.preview.before:
                    print(f"   preview before: {action.preview.before}")
                if action.preview.after:
                    print(f"   preview after: {action.preview.after}")
            if action.reason:
                print(f"   reason: {action.reason}")


if __name__ == "__main__":
    main()
