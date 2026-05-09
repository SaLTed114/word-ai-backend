from __future__ import annotations

from app.ai_client import AIClient
from app.models import AgentChatRequest, TaskResponse, TextRequest
from app.prompts import build_agent_prompt, build_task_prompt


async def run_syntax(client: AIClient, request: TextRequest) -> TaskResponse:
    prompt = build_task_prompt("syntax", request)
    return await client.complete_task(prompt)


async def run_word_choice(client: AIClient, request: TextRequest) -> TaskResponse:
    prompt = build_task_prompt("word_choice", request)
    return await client.complete_task(prompt)


async def run_style(client: AIClient, request: TextRequest) -> TaskResponse:
    prompt = build_task_prompt("style", request)
    return await client.complete_task(prompt)


async def run_agent(client: AIClient, request: AgentChatRequest) -> TaskResponse:
    history_text = _format_history(request.history)
    message = request.message
    if history_text:
        message = f"Conversation history:\n{history_text}\n\nLatest user message:\n{message}"
    prompt = build_agent_prompt(message, request.selection)
    return await client.complete_task(prompt)


def _format_history(history) -> str:
    return "\n".join(f"{item.role}: {item.content}" for item in history)
