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
      "id": "short stable id such as action_1",
      "type": "replace_selection | replace_range | insert_before | insert_after | add_comment | highlight | ask_user | none",
      "target": {
        "scope": "selection | range | paragraph | section | document | cursor | none",
        "start": null,
        "end": null,
        "anchor_text": "nearby text used to locate this action, or null",
        "occurrence": null
      },
      "original": "text being changed, or null",
      "replacement": "replacement text, or null",
      "preview": {
        "before": "text before applying this action, or null",
        "after": "text after applying this action, or null"
      },
      "reason": "why this action is suggested, or null",
      "risk_level": "info | low | medium | high",
      "requires_confirmation": true,
      "confidence": 0.0
    }
  ],
  "final_text": "full revised selected text, or null"
}
Rules for actions:
- Use replace_selection for a complete selected-text rewrite.
- Use replace_range only when start/end offsets inside the selected text are known.
- Use add_comment for feedback that should not edit the document text.
- Use ask_user when a clarification is needed before editing.
- Set requires_confirmation to true for all edits that change document text.
- Set risk_level to high for whole-document or meaning-changing edits.
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
