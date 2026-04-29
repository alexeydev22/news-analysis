from dataclasses import dataclass, field
from typing import Any

from economic_news_contracts.analysis import AnalysisModelName, ImpactLabel

from analysis_service.domain.errors import EmptyNewsTextError


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
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if self.explanation is None:
            object.__setattr__(
                self,
                "explanation",
                f"Model classified the news text as {self.impact.value}.",
            )
