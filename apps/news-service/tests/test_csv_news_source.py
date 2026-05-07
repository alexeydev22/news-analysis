from datetime import UTC, datetime
from pathlib import Path

import pytest
from news_service.domain.errors import NewsSourceUnavailableError, NewsSourceValidationError
from news_service.domain.model import stable_news_id
from news_service.infrastructure.csv_news_source import CsvNewsSource


def write_csv(path: Path, content: str) -> Path:
    path.write_text(content, encoding="utf-8")
    return path


@pytest.mark.asyncio
async def test_csv_news_source_reads_alias_columns_and_metadata(tmp_path: Path) -> None:
    csv_path = write_csv(
        tmp_path / "news.csv",
        "article_id,headline,body,publisher,date,impact\n"
        "a-1,GDP grows,GDP grew by 2 percent,demo,2026-05-07T09:30:00Z,positive\n",
    )
    source = CsvNewsSource(csv_path)

    documents = await source.load()

    assert len(documents) == 1
    assert documents[0].id == "a-1"
    assert documents[0].title == "GDP grows"
    assert documents[0].text == "GDP grew by 2 percent"
    assert documents[0].source == "demo"
    assert documents[0].published_at == datetime(2026, 5, 7, 9, 30, tzinfo=UTC)
    assert documents[0].metadata == {"row_number": 2, "impact": "positive"}


@pytest.mark.asyncio
async def test_csv_news_source_generates_stable_id_when_id_is_missing(tmp_path: Path) -> None:
    csv_path = write_csv(
        tmp_path / "news.csv",
        "title,text,source\nGDP grows,GDP grew,demo\n",
    )
    source = CsvNewsSource(csv_path)

    first = await source.load()
    second = await source.load()

    assert first[0].id == second[0].id
    assert first[0].id == stable_news_id(source="demo", title="GDP grows", text="GDP grew")


@pytest.mark.asyncio
async def test_csv_news_source_applies_limit(tmp_path: Path) -> None:
    csv_path = write_csv(
        tmp_path / "news.csv",
        "title,text,source\nA,Text A,demo\nB,Text B,demo\n",
    )
    source = CsvNewsSource(csv_path)

    documents = await source.load(limit=1)

    assert [document.title for document in documents] == ["A"]


@pytest.mark.asyncio
async def test_csv_news_source_rejects_missing_required_columns(tmp_path: Path) -> None:
    csv_path = write_csv(tmp_path / "news.csv", "title,source\nGDP grows,demo\n")
    source = CsvNewsSource(csv_path)

    with pytest.raises(NewsSourceValidationError, match="Missing required CSV column: text"):
        await source.load()


@pytest.mark.asyncio
async def test_csv_news_source_rejects_empty_required_row_value(tmp_path: Path) -> None:
    csv_path = write_csv(tmp_path / "news.csv", "title,text,source\nGDP grows, ,demo\n")
    source = CsvNewsSource(csv_path)

    with pytest.raises(NewsSourceValidationError, match="row 2"):
        await source.load()


@pytest.mark.asyncio
async def test_csv_news_source_rejects_rows_with_extra_cells(tmp_path: Path) -> None:
    csv_path = write_csv(
        tmp_path / "news.csv",
        "title,text,source\nGDP grows,GDP grew,demo,unexpected\n",
    )
    source = CsvNewsSource(csv_path)

    with pytest.raises(NewsSourceValidationError, match="Invalid CSV row 2"):
        await source.load()


@pytest.mark.asyncio
async def test_csv_news_source_preserves_internal_row_number(tmp_path: Path) -> None:
    csv_path = write_csv(
        tmp_path / "news.csv",
        "title,text,source,row_number\nGDP grows,GDP grew,demo,external\n",
    )
    source = CsvNewsSource(csv_path)

    documents = await source.load()

    assert documents[0].metadata["row_number"] == 2


@pytest.mark.asyncio
async def test_csv_news_source_maps_decode_errors_to_validation_error(tmp_path: Path) -> None:
    csv_path = tmp_path / "news.csv"
    csv_path.write_bytes(b"title,text,source\n\xff,GDP grew,demo\n")
    source = CsvNewsSource(csv_path)

    with pytest.raises(NewsSourceValidationError, match="Invalid CSV data"):
        await source.load()


@pytest.mark.asyncio
async def test_csv_news_source_maps_missing_file_to_unavailable_error(tmp_path: Path) -> None:
    source = CsvNewsSource(tmp_path / "missing.csv")

    with pytest.raises(NewsSourceUnavailableError, match="news source is unavailable"):
        await source.load()


@pytest.mark.asyncio
async def test_csv_news_source_maps_os_error_to_unavailable_error(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    csv_path = write_csv(tmp_path / "news.csv", "title,text,source\nGDP grows,GDP grew,demo\n")
    source = CsvNewsSource(csv_path)

    def raise_os_error(
        self: Path,
        mode: str = "r",
        buffering: int = -1,
        encoding: str | None = None,
        errors: str | None = None,
        newline: str | None = None,
    ) -> None:
        raise OSError("permission denied")

    monkeypatch.setattr(Path, "open", raise_os_error)

    with pytest.raises(NewsSourceUnavailableError, match="news source is unavailable"):
        await source.load()
