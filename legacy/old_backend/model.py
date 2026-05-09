import uuid
from typing import Any, Dict, Optional

from pydantic import BaseModel, Field

from dataclasses import dataclass


@dataclass
class AIConfig:
    model: str = "gpt-3.5-turbo"
    api_key: str = ""
    base_url: str = "https://api.openai.com/v1/chat/completions"
    temperature: float = 0.7
    max_tokens: int = 1000
    top_p: float = 1.0
    frequency_penalty: float = 0.0
    presence_penalty: float = 0.0
    stop: Optional[list[str]] = None


@dataclass
class SyntaxCheckRequest:
    text: str = Field(..., description="Text to be checked for syntax errors")


@dataclass
class WordCheckRequest:
    text: str = Field(..., description="Text to be checked for word errors")


@dataclass
class StyleAdjustmentRequest:
    text: str = Field(..., description="Text to be adjusted for style")
    target_style: str = Field(
        ..., description="Target style for the text adjustment (e.g., formal, casual)"
    )


class CorrectionItem(BaseModel):
    original: str = Field(..., description="Original text before correction")
    corrected: str = Field(..., description="Corrected text after grammar check")
    reason: str = Field(
        ..., description="Reason for the correction (e.g., grammar rule violated)"
    )


class CorrectionResponse(BaseModel):
    corrections: list[CorrectionItem] = Field(
        ..., description="List of corrections made to the original text"
    )
    message: str = "Corrections applied successfully."


class StyleAdjustmentResponse(BaseModel):
    result: str = Field(
        ..., description="The adjusted text after applying the style change"
    )
    reasons: list[str] = Field(
        ..., description="List of reasons for the style adjustments made"
    )
