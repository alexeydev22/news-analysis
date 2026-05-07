import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, cast

import pytest

sys.path.append(str(Path(__file__).resolve().parents[1] / "src"))

from news_service.domain.errors import EmptyNewsFieldError
from news_service.domain.model import NewsDocument, stable_news_id


def test_news_document_trims_required_fields_and_copies_metadata() -> None:
    published_at = datetime(2026, 5, 7, 9, 30, tzinfo=UTC)
    metadata = {"impact": "positive"}
    document = NewsDocument(
        id=" news-1 ",
        title=" GDP grows ",
        text=" GDP grew by 2 percent. ",
        source=" demo ",
        published_at=published_at,
        metadata=metadata,
    )
    metadata["impact"] = "mutated"

    assert document.id == "news-1"
    assert document.title == "GDP grows"
    assert document.text == "GDP grew by 2 percent."
    assert document.source == "demo"
    assert document.published_at == published_at
    assert document.metadata == {"impact": "positive"}
    with pytest.raises(TypeError):
        cast(dict[str, Any], document.metadata)["impact"] = "mutated"


def test_news_document_rejects_empty_required_fields() -> None:
    with pytest.raises(EmptyNewsFieldError, match="title must not be empty"):
        NewsDocument(id="news-1", title=" ", text="text", source="demo")


def test_stable_news_id_is_deterministic_and_source_sensitive() -> None:
    first = stable_news_id(source="demo", title="GDP grows", text="GDP grew")
    second = stable_news_id(source="demo", title=" GDP grows ", text="GDP grew")
    different = stable_news_id(source="another", title="GDP grows", text="GDP grew")

    assert first == second
    assert first.startswith("news-")
    assert first != different
