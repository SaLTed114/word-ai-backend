from __future__ import annotations

import json

from app.ai_client import AIClient
from app.config import PROJECT_ROOT
from app.models import AgentMessage, AgentPlan, AgentSessionMemory, SubAgentCall, SubAgentContextMode, TaskResponse, TextRequest
from app.prompts import RESPONSE_CONTRACT, build_agent_prompt, build_task_prompt
from app.subagents import SUBAGENTS, load_subagent_skill, resolve_subagent

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
    history_context_chars: int = 4000,
) -> TaskResponse:
    history = history or []
    memory_text = _format_memory(memory)
    history_text = _truncate_head(_format_history(history), history_context_chars)
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


async def run_subagent_turn(
    client: AIClient,
    name: str,
    message: str,
    selection: TextRequest | None = None,
    history: list[AgentMessage] | None = None,
    memory: AgentSessionMemory | None = None,
    use_full_skill_prompt: bool = True,
    context_mode: SubAgentContextMode = "selection",
    instruction: str | None = None,
    skills: list[str] | None = None,
) -> TaskResponse:
    spec = resolve_subagent(name, instruction=instruction)
    history = history or []
    skills = skills or []
    sections = [
        f"Subagent name: {spec.name}",
        f"Instruction:\n{spec.short_instruction}",
        "Allowed action types:\n" + _format_list(list(spec.allowed_actions)),
    ]

    if skills:
        sections.append("Selected skills:\n" + _format_list(skills))
    if use_full_skill_prompt:
        skill_text = _load_selected_subagent_skills(spec.name, skills, max_chars=spec.max_context_chars)
    else:
        skill_text = ""
    if skill_text:
        sections.append(f"Skill instructions:\n{skill_text}")

    if spec.include_history:
        history_text = _truncate(_format_history(history), spec.max_context_chars)
    else:
        history_text = ""
    if spec.include_memory or context_mode == "selection":
        memory_text = _truncate(_format_memory(memory), 1000)
    else:
        memory_text = ""

    if history_text:
        sections.append(f"Conversation history:\n{history_text}")
    if memory_text:
        sections.append(f"Short memory summary:\n{memory_text}")
    if selection is not None:
        sections.append(
            "Current input:\n"
            + _format_subagent_input(
                selection=selection,
                context_mode=context_mode,
                max_context_chars=spec.max_context_chars,
                include_document_context=spec.include_document_context,
            )
        )
    sections.extend(
        [
            f"User task:\n{message}",
            (
                "Subagent output rules:\n"
                "- Return one TaskResponse for only this subagent's specialty.\n"
                "- Keep task as agent.\n"
                "- Only use allowed action types listed above.\n"
                "- Do not apply edits directly; use actions with requires_confirmation=true for document changes."
            ),
            RESPONSE_CONTRACT,
        ]
    )
    response = await client.complete_task("\n\n".join(sections))
    response.task = "agent"
    response.summary = f"{spec.name}: {response.summary or 'completed'}"
    return response


async def plan_subagents(
    client: AIClient,
    message: str,
    selection: TextRequest | None = None,
    skills: list[str] | None = None,
) -> AgentPlan:
    available_skills = _available_skill_names()
    selected_skill_names = skills or []
    sections = [
        "You are a low-cost subagent planner for a Word writing assistant.",
        (
            "Decide whether specialized subagents are useful for the latest user task. "
            "Return no calls when the main agent can handle the task directly."
        ),
        "Known preset subagents:\n" + _format_list(sorted(SUBAGENTS)),
        "Available skills:\n" + (_format_list(available_skills) if available_skills else "(none)"),
    ]
    if selected_skill_names:
        sections.append("User-selected skills:\n" + _format_list(selected_skill_names))
    if selection is not None:
        sections.append("Selected text preview:\n" + _truncate(selection.text, 1000))
    sections.extend(
        [
            f"User task:\n{message}",
            (
                "Return only JSON matching this schema:\n"
                "{\n"
                '  "calls": [\n'
                '    {"name": "short_subagent_name", "instruction": "focused short instruction", '
                '"reason": "why this subagent is useful", "skills": ["optional-skill-name"]}\n'
                "  ]\n"
                "}\n"
                "Rules:\n"
                "- Use at most 3 calls.\n"
                "- Names may be preset names or custom names.\n"
                "- Only list skills that exist in Available skills.\n"
                "- Prefer zero or one call for simple tasks.\n"
                "- Do not include full skill text."
            ),
        ]
    )
    plan = await client.complete_model("\n\n".join(sections), AgentPlan)
    return AgentPlan(calls=_normalize_plan_calls(plan.calls, available_skills))


def merge_subagent_results(results: list[TaskResponse]) -> TaskResponse:
    replies = [result.reply for result in results if result.reply]
    actions = [action for result in results for action in result.actions]
    final_text = next((result.final_text for result in reversed(results) if result.final_text), None)
    summaries = [result.summary for result in results if result.summary]
    summary = "Merged from subagents"
    if summaries:
        summary = f"{summary}: {'; '.join(summaries)}"
    return TaskResponse(
        task="agent",
        reply="\n\n".join(replies),
        summary=summary,
        actions=actions,
        final_text=final_text,
    )


async def merge_subagent_results_with_llm(
    client: AIClient,
    message: str,
    merged: TaskResponse,
    selection: TextRequest | None = None,
    history: list[AgentMessage] | None = None,
    memory: AgentSessionMemory | None = None,
    history_context_chars: int = 4000,
) -> TaskResponse:
    sections = [
        "You are the main agent merging subagent outputs for a Word writing assistant.",
        (
            "Use the conversation history only for user intent and continuity. "
            "Do not invent edits that were not supported by the subagent outputs unless needed to resolve conflicts."
        ),
    ]
    history_text = _truncate_head(_format_history(history or []), history_context_chars)
    memory_text = _truncate(_format_memory(memory), 1000)
    if history_text:
        sections.append(f"Conversation history:\n{history_text}")
    if memory_text:
        sections.append(f"Session memory:\n{memory_text}")
    if selection is not None:
        sections.append("Selected text:\n" + _truncate(selection.text, 4000))
    sections.extend(
        [
            f"Latest user message:\n{message}",
            "Merged subagent TaskResponse JSON:\n" + merged.model_dump_json(),
            (
                "Merge rules:\n"
                "- Return one TaskResponse.\n"
                "- Keep task as agent.\n"
                "- Preserve all useful actions from the subagent JSON unless they conflict.\n"
                "- Keep requires_confirmation=true for document-changing actions.\n"
                "- Prefer the best final_text from subagents, but you may reconcile conflicting final_text values.\n"
                "- Keep subagent_calls if present."
            ),
            RESPONSE_CONTRACT,
        ]
    )
    response = await client.complete_task("\n\n".join(sections))
    response.task = "agent"
    if not response.subagent_calls:
        response.subagent_calls = merged.subagent_calls
    return response


def _normalize_plan_calls(calls: list[SubAgentCall], available_skills: list[str]) -> list[SubAgentCall]:
    available = set(available_skills)
    normalized: list[SubAgentCall] = []
    for call in calls[:3]:
        name = call.name.strip()
        instruction = call.instruction.strip()
        if not name or not instruction:
            continue
        normalized.append(
            SubAgentCall(
                name=name,
                instruction=instruction,
                reason=call.reason,
                skills=[skill for skill in call.skills if skill in available],
            )
        )
    return normalized


def _load_selected_subagent_skills(subagent_name: str, skill_names: list[str], max_chars: int) -> str:
    parts: list[str] = []
    if not skill_names:
        preset_skill = load_subagent_skill(subagent_name)
        if preset_skill:
            parts.append(preset_skill)
    for skill_name in skill_names:
        path = SKILLS_DIR / f"{skill_name}.md"
        if path.exists():
            parts.append(f"# {skill_name}\n{path.read_text(encoding='utf-8').strip()}")
    return _truncate("\n\n".join(parts), max_chars)


def _available_skill_names() -> list[str]:
    if not SKILLS_DIR.exists():
        return []
    return sorted(path.stem for path in SKILLS_DIR.glob("*.md"))


def _format_subagent_input(
    *,
    selection: TextRequest,
    context_mode: SubAgentContextMode,
    max_context_chars: int,
    include_document_context: bool,
) -> str:
    parts = [f"Selected text:\n{_truncate(selection.text, max_context_chars)}"]
    if context_mode == "minimal":
        return "\n\n".join(parts)

    context = selection.context
    meta: list[str] = []
    if context.document_title:
        meta.append(f"Document title: {context.document_title}")
    if context.section_heading:
        meta.append(f"Section heading: {context.section_heading}")
    if context.active_scope:
        meta.append(f"Active scope: {context.active_scope}")
    if selection.instruction:
        meta.append(f"User instruction on selection: {selection.instruction}")
    if selection.style:
        meta.append(f"Target style: {selection.style}")
    if meta:
        parts.append("Context summary:\n" + "\n".join(meta))

    if context_mode == "document" or include_document_context:
        budget = max(max_context_chars - len(selection.text), 0)
        side_budget = max(budget // 2, 0)
    else:
        side_budget = min(500, max_context_chars)

    if side_budget > 0 and context.before:
        parts.append(f"Before context:\n{_truncate(context.before, side_budget)}")
    if side_budget > 0 and context.after:
        parts.append(f"After context:\n{_truncate(context.after, side_budget)}")
    return "\n\n".join(parts)


def _truncate(value: str | None, limit: int) -> str:
    text = value or ""
    if limit <= 0 or len(text) <= limit:
        return text
    return text[:limit].rstrip() + "\n...[truncated]"


def _truncate_head(value: str | None, limit: int) -> str:
    text = value or ""
    if limit <= 0:
        return ""
    if len(text) <= limit:
        return text
    return "[truncated]...\n" + text[-limit:].lstrip()


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
