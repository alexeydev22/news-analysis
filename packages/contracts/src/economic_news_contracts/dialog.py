from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator

from economic_news_contracts.analysis import AnalysisModelName, ImpactLabel


def _normalize_required_text(value: str, message: str) -> str:
    normalized = value.strip()
    if not normalized:
        raise ValueError(message)
    return normalized


class DialogContextNews(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str = Field(min_length=1)
    title: str = Field(min_length=1)
    text: str = Field(min_length=1)
    source: str = Field(min_length=1)
    score: float = Field(ge=-1.0, le=1.0)
    published_at: datetime | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)

    @field_validator("id", "title", "text", "source")
    @classmethod
    def normalize_required_fields(cls, value: str) -> str:
        return _normalize_required_text(value, "Value must not be empty")


class DialogImpactSummary(BaseModel):
    model_config = ConfigDict(extra="forbid")

    news_id: str = Field(min_length=1)
    model_name: AnalysisModelName
    impact: ImpactLabel
    confidence: float | None = Field(default=None, ge=0.0, le=1.0)
    explanation: str = Field(min_length=1)

    @field_validator("news_id", "explanation")
    @classmethod
    def normalize_required_fields(cls, value: str) -> str:
        return _normalize_required_text(value, "Value must not be empty")


class GenerateDialogRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    question: str = Field(min_length=1)
    context: list[DialogContextNews] = Field(default_factory=list)
    impact_summaries: list[DialogImpactSummary] = Field(default_factory=list)
    language: str = Field(default="ru", min_length=2)

    @field_validator("question")
    @classmethod
    def normalize_question(cls, value: str) -> str:
        return _normalize_required_text(value, "Question must not be empty")

    @field_validator("language")
    @classmethod
    def normalize_language(cls, value: str) -> str:
        return _normalize_required_text(value, "Language must not be empty")


class GenerateDialogResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    answer: str = Field(min_length=1)
    used_context_ids: list[str] = Field(default_factory=list)
    model_name: str = Field(min_length=1)
    metadata: dict[str, Any] = Field(default_factory=dict)

    @field_validator("answer", "model_name")
    @classmethod
    def normalize_required_fields(cls, value: str) -> str:
        return _normalize_required_text(value, "Value must not be empty")
