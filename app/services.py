from __future__ import annotations

from app.ai_client import AIClient
from app.config import PROJECT_ROOT
from app.models import AgentMessage, AgentSessionMemory, TaskResponse, TextRequest
from app.prompts import build_agent_prompt, build_task_prompt

SKILLS_DIR = PROJECT_ROOT / "skills"


async def run_syntax(client: AIClient, request: TextRequest) -> TaskResponse:
    prompt = build_task_prompt("syntax", request)
    return await client.complete_task(prompt)


async def run_word_choice(client: AIClient, request: TextRequest) -> TaskResponse:
    prompt = build_task_prompt("word_choice", request)
    return await client.complete_task(prompt)


async def run_style(client: AIClient, request: TextRequest) -> TaskResponse:
    prompt = build_task_prompt("style", request)
    return await client.complete_task(prompt)


async def run_formula(client: AIClient, request: TextRequest) -> TaskResponse:
    prompt = build_task_prompt("formula", request)
    response = await client.complete_task(prompt)
    response.task = "formula"
    return response


async def run_agent_turn(
    client: AIClient,
    message: str,
    selection: TextRequest | None = None,
    history: list[AgentMessage] | None = None,
    memory: AgentSessionMemory | None = None,
    skills: list[str] | None = None,
) -> TaskResponse:
    history = history or []
    memory_text = _format_memory(memory)
    history_text = _format_history(history)
    skills_text = _load_skills(skills or [])
    sections: list[str] = []
    if skills_text:
        sections.append(f"Active skill instructions:\n{skills_text}")
    if history_text:
        sections.append(f"Conversation history:\n{history_text}")
    if memory_text:
        sections.append(f"Session memory:\n{memory_text}")
    sections.append(f"Latest user message:\n{message}")
    message = "\n\n".join(sections)
    prompt = build_agent_prompt(message, selection)
    response = await client.complete_task(prompt)
    response.task = "agent"
    return response


def _format_history(history) -> str:
    return "\n".join(f"{item.role}: {item.content}" for item in history)


def _format_memory(memory: AgentSessionMemory | None) -> str:
    if memory is None:
        return ""

    parts: list[str] = []
    if memory.document_summary:
        parts.append(f"Document summary: {memory.document_summary}")
    if memory.writing_goals:
        parts.append("Writing goals:\n" + _format_list(memory.writing_goals))
    if memory.key_terms:
        parts.append("Key terms:\n" + _format_list(memory.key_terms))
    if memory.user_preferences:
        parts.append("User preferences:\n" + _format_list(memory.user_preferences))
    return "\n\n".join(parts)


def _format_list(items: list[str]) -> str:
    return "\n".join(f"- {item}" for item in items)


def _load_skills(names: list[str]) -> str:
    if not names:
        return ""
    parts: list[str] = []
    for name in names:
        path = SKILLS_DIR / f"{name}.md"
        if path.exists():
            parts.append(path.read_text(encoding="utf-8").strip())
    return "\n\n".join(parts)
