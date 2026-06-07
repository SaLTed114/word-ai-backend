from __future__ import annotations

from uuid import uuid4
from typing import Any, Literal

from pydantic import BaseModel, Field


ActionType = Literal[
    "replace_selection",
    "replace_selection_equation",
    "replace_range",
    "replace_span",
    "insert_equation",
    "insert_before",
    "insert_after",
    "add_comment",
    "comment",
    "highlight",
    "ask_user",
    "none",
]
ActionScope = Literal[
    "selection",
    "range",
    "paragraph",
    "section",
    "document",
    "cursor",
    "none",
]
TaskType = Literal["syntax", "word_choice", "style", "formula", "agent"]
RiskLevel = Literal["info", "low", "medium", "high"]
ContextScope = Literal["selection", "paragraph", "section", "document"]
FormulaFormat = Literal["latex", "linear", "omml"]
SubAgentName = Literal["proofread", "academic_polish", "summarize", "translate_zh", "formula"]
SubAgentContextMode = Literal["minimal", "selection", "document"]


class TextContext(BaseModel):
    before: str | None = Field(default=None, description="Text before the selected text.")
    after: str | None = Field(default=None, description="Text after the selected text.")
    document_title: str | None = None
    section_heading: str | None = None
    document_id: str | None = None
    active_scope: ContextScope | None = None


class TextRequest(BaseModel):
    text: str
    context: TextContext = Field(default_factory=TextContext)
    instruction: str | None = None
    style: str | None = None


class ActionTarget(BaseModel):
    scope: ActionScope = Field(
        default="selection",
        description="Where this action should be applied.",
    )
    start: int | None = Field(
        default=None,
        description="Optional start offset inside the selected text or target scope.",
    )
    end: int | None = Field(
        default=None,
        description="Optional end offset inside the selected text or target scope.",
    )
    anchor_text: str | None = Field(
        default=None,
        description="Optional nearby text used by a client to locate the action target.",
    )
    occurrence: int | None = Field(
        default=None,
        description="Optional 1-based occurrence index when anchor_text appears more than once.",
    )


class ActionPreview(BaseModel):
    before: str | None = Field(default=None, description="Text before applying the action.")
    after: str | None = Field(default=None, description="Text after applying the action.")


class TextAction(BaseModel):
    id: str = Field(
        default_factory=lambda: uuid4().hex,
        description="Stable action id for preview, confirmation, and later application.",
    )
    type: ActionType = "none"
    target: ActionTarget = Field(default_factory=ActionTarget)
    original: str | None = None
    replacement: str | None = None
    formula: str | None = Field(
        default=None,
        description="Formula source for equation actions, usually LaTeX.",
    )
    formula_format: FormulaFormat | None = Field(
        default=None,
        description="Format of formula source: latex, linear, or omml.",
    )
    preview: ActionPreview | None = None
    reason: str | None = None
    risk_level: RiskLevel = Field(
        default="info",
        description="Estimated risk if this action is applied automatically.",
    )
    requires_confirmation: bool = Field(
        default=True,
        description="Whether a UI must ask the user before applying this action.",
    )
    confidence: float | None = Field(
        default=None,
        ge=0,
        le=1,
        description="Optional model confidence from 0 to 1.",
    )


class TaskResponse(BaseModel):
    task: TaskType
    reply: str
    summary: str | None = None
    actions: list[TextAction] = Field(default_factory=list)
    final_text: str | None = None
    subagent_calls: list[dict[str, Any]] = Field(default_factory=list)


class AgentMessage(BaseModel):
    role: Literal["user", "assistant", "system"]
    content: str


class AgentSessionCreateRequest(BaseModel):
    title: str | None = Field(default=None, description="Optional human-readable session title.")


class AgentSession(BaseModel):
    id: str
    title: str | None = None
    created_at: str
    updated_at: str
    message_count: int = 0


class AgentSessionMessage(BaseModel):
    id: int
    session_id: str
    role: Literal["user", "assistant", "system"]
    content: str
    created_at: str
    response: TaskResponse | None = None


class AgentSessionMemory(BaseModel):
    session_id: str
    document_summary: str | None = None
    writing_goals: list[str] = Field(default_factory=list)
    key_terms: list[str] = Field(default_factory=list)
    user_preferences: list[str] = Field(default_factory=list)
    updated_at: str | None = None


class AgentSessionMemoryUpdate(BaseModel):
    document_summary: str | None = None
    writing_goals: list[str] = Field(default_factory=list)
    key_terms: list[str] = Field(default_factory=list)
    user_preferences: list[str] = Field(default_factory=list)


class DocumentSelection(BaseModel):
    text: str | None = Field(default=None, description="Selected text, if already known.")
    start: int | None = Field(
        default=None,
        ge=0,
        description="Selection start offset in document_text.",
    )
    end: int | None = Field(
        default=None,
        ge=0,
        description="Selection end offset in document_text.",
    )


class DocumentContextRequest(BaseModel):
    document_id: str | None = None
    title: str | None = None
    section_heading: str | None = None
    document_text: str | None = Field(
        default=None,
        description="Plain text representation of the available document content.",
    )
    selection: DocumentSelection | None = None
    active_scope: ContextScope = Field(
        default="selection",
        description="Scope the user intends to work on.",
    )
    context_window_chars: int = Field(
        default=1200,
        ge=0,
        le=8000,
        description="Maximum characters to keep before and after the active text.",
    )
    instruction: str | None = None
    style: str | None = None


class ContextBuildResult(BaseModel):
    text_request: TextRequest
    active_scope: ContextScope
    selected_text: str
    before_chars: int
    after_chars: int
    warnings: list[str] = Field(default_factory=list)


class SubAgentCall(BaseModel):
    name: str
    instruction: str
    reason: str | None = None
    skills: list[str] = Field(default_factory=list)


class AgentSessionTurnRequest(BaseModel):
    message: str
    selection: TextRequest | None = None
    document_context: DocumentContextRequest | None = None
    skills: list[str] = Field(default_factory=list)
    subagents: list[str] = Field(default_factory=list)
    planned_subagents: list[SubAgentCall] = Field(default_factory=list)
    auto_subagents: bool = False
    use_full_skill_prompt: bool = True
    llm_merge_subagents: bool = True
    history_context_chars: int = Field(default=4000, ge=0, le=20000)
    subagent_context_mode: SubAgentContextMode = "selection"


class SubAgentResult(BaseModel):
    name: str
    response: TaskResponse


class AgentPlan(BaseModel):
    calls: list[SubAgentCall] = Field(default_factory=list)


class AgentSessionTurnResponse(BaseModel):
    session: AgentSession
    user_message: AgentSessionMessage
    assistant_message: AgentSessionMessage
    response: TaskResponse


class AgentSubAgentRunRequest(BaseModel):
    message: str
    subagent: SubAgentCall
    selection: TextRequest | None = None
    document_context: DocumentContextRequest | None = None
    skills: list[str] = Field(default_factory=list)
    use_full_skill_prompt: bool = True
    subagent_context_mode: SubAgentContextMode = "selection"


class AgentSubAgentMergeRequest(BaseModel):
    message: str
    selection: TextRequest | None = None
    document_context: DocumentContextRequest | None = None
    subagent_results: list[SubAgentResult] = Field(default_factory=list)
    subagent_calls: list[SubAgentCall] = Field(default_factory=list)
    llm_merge_subagents: bool = True
    history_context_chars: int = Field(default=4000, ge=0, le=20000)


class AIConfigView(BaseModel):
    api_key: str = ""
    model: str = "gpt-4o-mini"
    base_url: str = "https://api.openai.com/v1"
    api_endpoint: str = ""
    proxy_url: str = ""
    trust_env: bool = False
    use_json_mode: bool = True


class AIConfigUpdate(BaseModel):
    api_key: str = ""
    model: str = "gpt-4o-mini"
    base_url: str = "https://api.openai.com/v1"
    api_endpoint: str = ""
    proxy_url: str = ""
    trust_env: bool = False
    use_json_mode: bool = True


class SkillCreate(BaseModel):
    name: str = Field(
        min_length=1,
        max_length=64,
        pattern=r"^[a-zA-Z0-9_-]+$",
        description="Skill name without extension.",
    )
    content: str = Field(min_length=1, description="Markdown content of the skill.")


class SkillInfo(BaseModel):
    name: str
    size: int


class SkillContent(BaseModel):
    name: str
    content: str
