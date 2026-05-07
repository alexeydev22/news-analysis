from collections.abc import Mapping
from dataclasses import dataclass, field
from datetime import datetime
from hashlib import sha256
from types import MappingProxyType
from typing import Any

from news_service.domain.errors import EmptyNewsFieldError


def _required_text(value: str, field_name: str) -> str:
    normalized = value.strip()
    if not normalized:
        raise EmptyNewsFieldError(f"{field_name} must not be empty")
    return normalized


def stable_news_id(*, source: str, title: str, text: str) -> str:
    normalized = "\n".join(
        (
            source.strip().casefold(),
            title.strip().casefold(),
            text.strip(),
        ),
    )
    digest = sha256(normalized.encode("utf-8")).hexdigest()[:16]
    return f"news-{digest}"


@dataclass(frozen=True, slots=True)
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
