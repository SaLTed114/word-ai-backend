from __future__ import annotations

from pathlib import Path

from app.config import PROJECT_ROOT
from app.models import TextRequest


PROMPT_DIR = PROJECT_ROOT / "prompts"


RESPONSE_CONTRACT = """
Return only valid JSON matching this schema:
{
  "task": "syntax | word_choice | style | agent",
  "reply": "short explanation shown to the user",
  "summary": "one sentence summary, or null",
  "actions": [
    {
      "type": "replace_selection | replace_span | insert_after | comment | none",
      "original": "text being changed, or null",
      "replacement": "replacement text, or null",
      "reason": "why this action is suggested, or null",
      "severity": "info | low | medium | high",
      "start": null,
      "end": null
    }
  ],
  "final_text": "full revised selected text, or null"
}
Do not wrap the JSON in Markdown.
"""


def load_prompt(name: str) -> str:
    path = PROMPT_DIR / f"{name}.md"
    if not path.exists():
        raise FileNotFoundError(f"Prompt not found: {path}")
    return path.read_text(encoding="utf-8").strip()


def format_text_request(request: TextRequest) -> str:
    context = request.context
    return f"""
Selected text:
{request.text}

Before context:
{context.before or ""}

After context:
{context.after or ""}

Document title:
{context.document_title or ""}

Section heading:
{context.section_heading or ""}

User instruction:
{request.instruction or ""}

Target style:
{request.style or ""}
""".strip()


def build_task_prompt(name: str, request: TextRequest) -> str:
    return "\n\n".join(
        [
            load_prompt(name),
            "Input:",
            format_text_request(request),
            RESPONSE_CONTRACT,
        ]
    )


def build_agent_prompt(message: str, request: TextRequest | None = None) -> str:
    parts = [load_prompt("agent"), f"User message:\n{message}"]
    if request is not None:
        parts.extend(["Current document selection:", format_text_request(request)])
    parts.append(RESPONSE_CONTRACT)
    return "\n\n".join(parts)

