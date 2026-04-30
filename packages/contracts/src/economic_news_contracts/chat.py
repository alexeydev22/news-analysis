from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator

from economic_news_contracts.analysis import AnalysisModelName
from economic_news_contracts.dialog import DialogContextNews, DialogImpactSummary


class ChatRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    question: str = Field(min_length=1)
    analysis_model: AnalysisModelName = AnalysisModelName.TFIDF_LOGREG
    limit: int = Field(default=5, ge=1, le=20)
    source: str | None = Field(default=None, min_length=1)

    @field_validator("question", "source")
    @classmethod
    def normalize_text(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.strip()
        if not normalized:
            raise ValueError("Value must not be empty")
        return normalized


class ChatResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    answer: str = Field(min_length=1)
    sources: list[DialogContextNews] = Field(default_factory=list)
    impact_summaries: list[DialogImpactSummary] = Field(default_factory=list)
    analysis_model: AnalysisModelName
    metadata: dict[str, Any] = Field(default_factory=dict)

    @field_validator("answer")
    @classmethod
    def normalize_answer(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("Answer must not be empty")
        return normalized
