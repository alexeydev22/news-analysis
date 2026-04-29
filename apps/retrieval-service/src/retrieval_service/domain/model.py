from collections.abc import Mapping
from dataclasses import dataclass, field
from datetime import datetime
from types import MappingProxyType
from typing import Any

from retrieval_service.domain.errors import EmptyDocumentTextError, InvalidSearchLimitError


def _required_text(value: str, field_name: str) -> str:
    normalized = value.strip()
    if not normalized:
        raise EmptyDocumentTextError(field_name)
    return normalized


@dataclass(frozen=True)
class NewsDocument:
    id: str
    title: str
    text: str
    source: str
    published_at: datetime | None = None
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        object.__setattr__(self, "id", _required_text(self.id, "id"))
        object.__setattr__(self, "title", _required_text(self.title, "title"))
        object.__setattr__(self, "text", _required_text(self.text, "text"))
        object.__setattr__(self, "source", _required_text(self.source, "source"))
        object.__setattr__(self, "metadata", MappingProxyType(dict(self.metadata)))


@dataclass(frozen=True)
class SearchQuery:
    query: str
    limit: int = 5
    source: str | None = None

    def __post_init__(self) -> None:
        if self.limit < 1 or self.limit > 20:
            raise InvalidSearchLimitError(self.limit)
        object.__setattr__(self, "query", _required_text(self.query, "query"))
        if self.source is not None:
            object.__setattr__(self, "source", _required_text(self.source, "source"))


@dataclass(frozen=True)
class SearchResult:
    document: NewsDocument
    score: float
