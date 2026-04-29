from enum import StrEnum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator


class ImpactLabel(StrEnum):
    POSITIVE = "positive"
    NEUTRAL = "neutral"
    NEGATIVE = "negative"


class AnalysisModelName(StrEnum):
    TFIDF_LOGREG = "tfidf-logreg"
    EMBEDDING_LOGREG = "embedding-logreg"
    TINY_TRANSFORMER_CLASSIFIER = "tiny-transformer-classifier"


class AnalyzeNewsRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    text: str = Field(min_length=1)
    analysis_model: AnalysisModelName = AnalysisModelName.TFIDF_LOGREG

    @field_validator("text")
    @classmethod
    def normalize_text(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("News text must not be empty")
        return normalized


class AnalyzeNewsResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    model_name: AnalysisModelName
    impact: ImpactLabel
    confidence: float | None = Field(default=None, ge=0.0, le=1.0)
    explanation: str
    metadata: dict[str, Any] = Field(default_factory=dict)
