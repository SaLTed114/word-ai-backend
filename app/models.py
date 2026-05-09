from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


ActionType = Literal["replace_selection", "replace_span", "insert_after", "comment", "none"]
TaskType = Literal["syntax", "word_choice", "style", "agent"]
Severity = Literal["info", "low", "medium", "high"]


class TextContext(BaseModel):
    before: str | None = Field(default=None, description="Text before the selected text.")
    after: str | None = Field(default=None, description="Text after the selected text.")
    document_title: str | None = None
    section_heading: str | None = None


class TextRequest(BaseModel):
    text: str
    context: TextContext = Field(default_factory=TextContext)
    instruction: str | None = None
    style: str | None = None


class TextAction(BaseModel):
    type: ActionType = "none"
    original: str | None = None
    replacement: str | None = None
    reason: str | None = None
    severity: Severity = "info"
    start: int | None = Field(default=None, description="Optional start offset in selected text.")
    end: int | None = Field(default=None, description="Optional end offset in selected text.")


class TaskResponse(BaseModel):
    task: TaskType
    reply: str
    summary: str | None = None
    actions: list[TextAction] = Field(default_factory=list)
    final_text: str | None = None


class AgentMessage(BaseModel):
    role: Literal["user", "assistant", "system"]
    content: str


class AgentChatRequest(BaseModel):
    message: str
    selection: TextRequest | None = None
    history: list[AgentMessage] = Field(default_factory=list)
