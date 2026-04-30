from collections.abc import Mapping
from dataclasses import dataclass, field
from datetime import datetime
from types import MappingProxyType
from typing import Any

from dialog_service.domain.errors import EmptyDialogTextError


def _required_text(value: str, field_name: str) -> str:
    normalized = value.strip()
    if not normalized:
        raise EmptyDialogTextError(field_name)
    return normalized


@dataclass(frozen=True)
class DialogQuestion:
    value: str

    def __post_init__(self) -> None:
        object.__setattr__(self, "value", _required_text(self.value, "question"))


@dataclass(frozen=True)
class DialogContextItem:
    id: str
    title: str
    text: str
    source: str
    score: float
    published_at: datetime | None = None
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        object.__setattr__(self, "id", _required_text(self.id, "id"))
        object.__setattr__(self, "title", _required_text(self.title, "title"))
        object.__setattr__(self, "text", _required_text(self.text, "text"))
        object.__setattr__(self, "source", _required_text(self.source, "source"))
        object.__setattr__(self, "metadata", MappingProxyType(dict(self.metadata)))


@dataclass(frozen=True)
class DialogImpactItem:
    news_id: str
    model_name: str
    impact: str
    confidence: float | None
    explanation: str

    def __post_init__(self) -> None:
        object.__setattr__(self, "news_id", _required_text(self.news_id, "news_id"))
        object.__setattr__(self, "model_name", _required_text(self.model_name, "model_name"))
        object.__setattr__(self, "impact", _required_text(self.impact, "impact"))
        object.__setattr__(self, "explanation", _required_text(self.explanation, "explanation"))


@dataclass(frozen=True)
class DialogGeneration:
    answer: str
    used_context_ids: list[str]
    model_name: str
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        object.__setattr__(self, "answer", _required_text(self.answer, "answer"))
        object.__setattr__(self, "model_name", _required_text(self.model_name, "model_name"))
        object.__setattr__(self, "used_context_ids", list(self.used_context_ids))
        object.__setattr__(self, "metadata", MappingProxyType(dict(self.metadata)))
