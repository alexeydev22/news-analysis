from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

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
        normalized = _normalize_required_text(value, "Language must not be empty")
        if len(normalized) < 2:
            raise ValueError("Language must be at least 2 characters")
        return normalized

    @model_validator(mode="after")
    def validate_impact_summaries_match_context(self) -> "GenerateDialogRequest":
        context_ids = {item.id for item in self.context}
        summary_ids = [summary.news_id for summary in self.impact_summaries]
        if len(summary_ids) != len(set(summary_ids)):
            raise ValueError("Impact summaries must be unique by news_id")
        if not set(summary_ids).issubset(context_ids):
            raise ValueError("Impact summary news_id must exist in context")
        return self


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

    @field_validator("used_context_ids")
    @classmethod
    def normalize_used_context_ids(cls, values: list[str]) -> list[str]:
        return [
            _normalize_required_text(value, "Used context id must not be empty")
            for value in values
        ]
