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


class MlReportJobStatus(StrEnum):
    QUEUED = "queued"
    STARTED = "started"
    SUCCEEDED = "succeeded"
    FAILED = "failed"


class EnqueueMlReportJobRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")


class EnqueueMlReportJobResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    job_id: str = Field(min_length=1)
    status: MlReportJobStatus = MlReportJobStatus.QUEUED


class MlReportJobResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    job_id: str = Field(min_length=1)
    status: MlReportJobStatus
    message: str | None = None
    report_path: str | None = None


class MlConfusionMatrixResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    labels: list[str]
    matrix: list[list[int]]


class MlModelReportItemResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    model_name: str = Field(min_length=1)
    validation_accuracy: float | None = None
    validation_macro_f1: float | None = None
    test_accuracy: float | None = None
    test_macro_f1: float | None = None
    inference_seconds_per_sample: float | None = None
    confusion_matrix: MlConfusionMatrixResponse | None = None


class MlDatasetReportResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    path: str
    row_count: int = Field(ge=0)
    class_distribution: dict[str, int]


class MlReportResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    generated_at: str
    dataset: MlDatasetReportResponse
    models: list[MlModelReportItemResponse]
    best_model: MlModelReportItemResponse | None = None
    top_features: dict[str, dict[str, list[str]]] = Field(default_factory=dict)


class TopicForecastJobStatus(StrEnum):
    QUEUED = "queued"
    STARTED = "started"
    SUCCEEDED = "succeeded"
    FAILED = "failed"


class EnqueueTopicForecastJobResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    job_id: str = Field(min_length=1)
    status: TopicForecastJobStatus = TopicForecastJobStatus.QUEUED


class TopicForecastJobResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    job_id: str = Field(min_length=1)
    status: TopicForecastJobStatus
    message: str | None = None
    report_path: str | None = None


class TopicForecastNewsItemResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str = Field(min_length=1)
    title: str = Field(min_length=1)
    source: str = Field(min_length=1)
    impact: ImpactLabel
    score: float | None = Field(default=None, ge=-1.0, le=1.0)


class TopicForecastItemResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    topic_id: str = Field(min_length=1)
    title: str = Field(min_length=1)
    summary: str = Field(min_length=1)
    overall_impact: ImpactLabel
    confidence: float | None = Field(default=None, ge=0.0, le=1.0)
    positive_count: int = Field(ge=0)
    neutral_count: int = Field(ge=0)
    negative_count: int = Field(ge=0)
    forecast: str = Field(min_length=1)
    arguments: list[str] = Field(default_factory=list)
    risks: list[str] = Field(default_factory=list)
    news: list[TopicForecastNewsItemResponse] = Field(default_factory=list)


class GroqForecastScope(StrEnum):
    TOPIC = "topic"
    NEWS = "news"


class GroqForecastRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    scope: GroqForecastScope
    model_name: str = Field(min_length=1)
    topic: TopicForecastItemResponse
    news_id: str | None = None


class GroqForecastResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    provider: str = Field(min_length=1)
    model_name: str = Field(min_length=1)
    scope: GroqForecastScope
    target_id: str = Field(min_length=1)
    prediction: str = Field(min_length=1)
    disclaimer: str = Field(
        default="Это аналитический сценарий, а не финансовая рекомендация.",
    )
    metadata: dict[str, Any] = Field(default_factory=dict)


class TopicForecastModelReportResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    model_name: AnalysisModelName
    topics: list[TopicForecastItemResponse] = Field(default_factory=list)
    error: str | None = None


class TopicForecastResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    generated_at: str
    topics: list[TopicForecastItemResponse] = Field(default_factory=list)
    model_reports: list[TopicForecastModelReportResponse] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)
