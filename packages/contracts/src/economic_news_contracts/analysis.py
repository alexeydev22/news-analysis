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
