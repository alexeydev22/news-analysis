import pytest
from retrieval_service.domain.errors import EmptyDocumentTextError, InvalidSearchLimitError
from retrieval_service.domain.model import NewsDocument, SearchQuery


def test_news_document_trims_fields() -> None:
    document = NewsDocument(
        id=" id-1 ",
        title="  Title  ",
        text="  Body  ",
        source="  source  ",
    )

    assert document.id == "id-1"
    assert document.title == "Title"
    assert document.text == "Body"
    assert document.source == "source"


def test_news_document_rejects_blank_text() -> None:
    with pytest.raises(EmptyDocumentTextError):
        NewsDocument(id="id-1", title="Title", text=" ", source="source")


def test_search_query_trims_query_and_source() -> None:
    query = SearchQuery(query="  inflation  ", limit=3, source="  cbr  ")

    assert query.query == "inflation"
    assert query.limit == 3
    assert query.source == "cbr"


def test_search_query_rejects_invalid_limit() -> None:
    with pytest.raises(InvalidSearchLimitError):
        SearchQuery(query="inflation", limit=0)
