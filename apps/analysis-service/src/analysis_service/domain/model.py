from collections.abc import Mapping
from dataclasses import dataclass, field
from types import MappingProxyType
from typing import Any

from economic_news_contracts.analysis import AnalysisModelName, ImpactLabel

from analysis_service.domain.errors import EmptyNewsTextError, InvalidPredictionConfidenceError

IMPACT_LABELS_RU = {
    ImpactLabel.POSITIVE: "позитивное",
    ImpactLabel.NEGATIVE: "негативное",
    ImpactLabel.NEUTRAL: "нейтральное",
}


@dataclass(frozen=True)
class NewsText:
    value: str

    @classmethod
    def from_raw(cls, value: str) -> "NewsText":
        normalized = value.strip()
        if not normalized:
            raise EmptyNewsTextError()
        return cls(value=normalized)


@dataclass(frozen=True)
class ImpactPrediction:
    model_name: AnalysisModelName
    impact: ImpactLabel
    confidence: float | None = None
    explanation: str | None = None
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if self.confidence is not None and not 0.0 <= self.confidence <= 1.0:
            raise InvalidPredictionConfidenceError(self.confidence)
        if self.explanation is None:
            object.__setattr__(
                self,
                "explanation",
                f"Модель классифицировала влияние новости как {IMPACT_LABELS_RU[self.impact]}.",
            )
        object.__setattr__(self, "metadata", MappingProxyType(dict(self.metadata)))
