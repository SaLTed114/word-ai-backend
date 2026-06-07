from __future__ import annotations

from dataclasses import dataclass

from app.config import PROJECT_ROOT


SKILLS_DIR = PROJECT_ROOT / "skills"


@dataclass(frozen=True)
class SubAgentSpec:
    name: str
    skill_file: str | None
    short_instruction: str
    allowed_actions: list[str]
    include_history: bool = False
    include_memory: bool = False
    include_document_context: bool = False
    max_context_chars: int = 4000


SUBAGENTS: dict[str, SubAgentSpec] = {
    "proofread": SubAgentSpec(
        name="proofread",
        skill_file="proofread.md",
        short_instruction="Check grammar, spelling, punctuation, and clarity. Preserve meaning. Return minimal edits.",
        allowed_actions=["replace_selection", "replace_range", "add_comment", "comment", "highlight", "ask_user", "none"],
    ),
    "academic_polish": SubAgentSpec(
        name="academic_polish",
        skill_file="academic-polish.md",
        short_instruction="Polish the selected text for formal academic English. Preserve technical meaning.",
        allowed_actions=["replace_selection", "replace_range", "add_comment", "comment", "ask_user", "none"],
    ),
    "summarize": SubAgentSpec(
        name="summarize",
        skill_file="summarize.md",
        short_instruction="Summarize the selected text concisely.",
        allowed_actions=["add_comment", "comment", "ask_user", "none"],
    ),
    "translate_zh": SubAgentSpec(
        name="translate_zh",
        skill_file="translate-zh.md",
        short_instruction="Translate or rewrite between Chinese and English as requested. Preserve meaning and formatting.",
        allowed_actions=["replace_selection", "replace_range", "add_comment", "comment", "ask_user", "none"],
    ),
    "formula": SubAgentSpec(
        name="formula",
        skill_file="formula.md",
        short_instruction="Handle LaTeX, equations, and Word equation friendly output.",
        allowed_actions=[
            "replace_selection",
            "replace_selection_equation",
            "replace_range",
            "insert_equation",
            "add_comment",
            "comment",
            "ask_user",
            "none",
        ],
    ),
}


def resolve_subagent(
    name: str,
    instruction: str | None = None,
    allowed_actions: list[str] | None = None,
) -> SubAgentSpec:
    normalized = normalize_subagent_name(name)
    if normalized in SUBAGENTS:
        preset = SUBAGENTS[normalized]
        if instruction or allowed_actions:
            return SubAgentSpec(
                name=preset.name,
                skill_file=preset.skill_file,
                short_instruction=instruction or preset.short_instruction,
                allowed_actions=allowed_actions or preset.allowed_actions,
                include_history=preset.include_history,
                include_memory=preset.include_memory,
                include_document_context=preset.include_document_context,
                max_context_chars=preset.max_context_chars,
            )
        return preset
    return SubAgentSpec(
        name=normalized or "custom",
        skill_file=None,
        short_instruction=instruction
        or "Handle the assigned writing task using only the current user message and selected text.",
        allowed_actions=allowed_actions
        or ["replace_selection", "replace_range", "add_comment", "comment", "ask_user", "none"],
    )


def load_subagent_skill(name: str) -> str:
    spec = resolve_subagent(name)
    if spec.skill_file is None:
        return ""
    path = SKILLS_DIR / spec.skill_file
    if path.exists():
        return path.read_text(encoding="utf-8").strip()
    return ""


def get_subagent(name: str) -> SubAgentSpec:
    normalized = normalize_subagent_name(name)
    if normalized not in SUBAGENTS:
        known = ", ".join(sorted(SUBAGENTS))
        raise ValueError(f"Unknown subagent '{name}'. Available subagents: {known}.")
    return SUBAGENTS[normalized]


def normalize_subagent_name(name: str) -> str:
    return name.strip().lower().replace("-", "_")
