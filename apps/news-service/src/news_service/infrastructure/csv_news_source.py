import csv
from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from news_service.domain.errors import NewsSourceUnavailableError, NewsSourceValidationError
from news_service.domain.model import NewsDocument, stable_news_id

type _CsvRow = dict[str | None, str | list[str] | None]

_TITLE_COLUMNS = ("title", "headline", "article_title")
_TEXT_COLUMNS = ("text", "content", "body", "description", "article")
_SOURCE_COLUMNS = ("source", "publisher", "stock_symbol", "ticker", "symbol")
_ID_COLUMNS = ("id", "news_id", "article_id")
_PUBLISHED_COLUMNS = ("published_at", "date", "published")
_CORE_COLUMNS = {
    *_TITLE_COLUMNS,
    *_TEXT_COLUMNS,
    *_SOURCE_COLUMNS,
    *_ID_COLUMNS,
    *_PUBLISHED_COLUMNS,
}


@dataclass(frozen=True, slots=True)
class _CsvColumns:
    title: str
    text: str
    source: str | None
    document_id: str | None
    published_at: str | None


class CsvNewsSource:
    def __init__(self, path: Path | str) -> None:
        self._path = Path(path)

    async def load(self, limit: int | None = None) -> list[NewsDocument]:
        try:
            return self._load_sync(limit)
        except NewsSourceValidationError:
            raise
        except (csv.Error, UnicodeDecodeError) as error:
            raise NewsSourceValidationError("Invalid CSV data") from error
        except OSError as error:
            raise NewsSourceUnavailableError("news source is unavailable") from error

    def _load_sync(self, limit: int | None) -> list[NewsDocument]:
        if limit is not None and limit <= 0:
            return []

        with self._path.open(encoding="utf-8", newline="") as csv_file:
            self._validate_quote_shape(csv_file)
            csv_file.seek(0)
            reader = csv.DictReader(csv_file, strict=True)
            columns = self._resolve_columns(reader.fieldnames or [])

            documents: list[NewsDocument] = []
            for row_number, row in enumerate(reader, start=2):
                documents.append(self._document_from_row(row, row_number, columns))
                if limit is not None and len(documents) >= limit:
                    break

            return documents

    def _validate_quote_shape(self, lines: Iterable[str]) -> None:
        for line in lines:
            in_quotes = False
            at_field_start = True
            after_closing_quote = False
            index = 0

            while index < len(line):
                char = line[index]
                if char == '"':
                    if in_quotes:
                        next_index = index + 1
                        if next_index < len(line) and line[next_index] == '"':
                            index += 2
                            continue
                        in_quotes = False
                        after_closing_quote = True
                        index += 1
                        continue
                    if at_field_start:
                        in_quotes = True
                        at_field_start = False
                        index += 1
                        continue
                    raise csv.Error("Stray quote in unquoted field")

                if in_quotes:
                    index += 1
                    continue

                if after_closing_quote:
                    if char in {",", "\r", "\n"}:
                        after_closing_quote = False
                        at_field_start = char == ","
                        index += 1
                        continue
                    raise csv.Error("Unexpected character after closing quote")

                if char == ",":
                    at_field_start = True
                elif char not in {"\r", "\n"}:
                    at_field_start = False
                index += 1

            if in_quotes:
                raise csv.Error("Unclosed quoted field")

    def _resolve_columns(self, fieldnames: Sequence[str]) -> _CsvColumns:
        column_by_name = {
            fieldname.strip().lower(): fieldname
            for fieldname in fieldnames
            if fieldname and fieldname.strip()
        }
        return _CsvColumns(
            title=self._required_column(column_by_name, _TITLE_COLUMNS, "title"),
            text=self._required_column(column_by_name, _TEXT_COLUMNS, "text"),
            source=self._optional_column(column_by_name, _SOURCE_COLUMNS),
            document_id=self._optional_column(column_by_name, _ID_COLUMNS),
            published_at=self._optional_column(column_by_name, _PUBLISHED_COLUMNS),
        )

    def _document_from_row(
        self,
        row: _CsvRow,
        row_number: int,
        columns: _CsvColumns,
    ) -> NewsDocument:
        self._validate_row_shape(row, row_number)

        title = self._required_value(row, columns.title, row_number)
        text = self._required_value(row, columns.text, row_number)
        source = self._optional_value(row, columns.source) or self._path.stem
        raw_id = self._optional_value(row, columns.document_id)
        document_id = raw_id or stable_news_id(source=source, title=title, text=text)
        published_at = self._parse_published_at(
            self._optional_value(row, columns.published_at),
            row_number,
        )

        try:
            return NewsDocument(
                id=document_id,
                title=title,
                text=text,
                source=source,
                published_at=published_at,
                metadata=self._metadata_from_row(row, row_number),
            )
        except ValueError as error:
            raise NewsSourceValidationError(f"Invalid CSV row {row_number}") from error

    def _validate_row_shape(self, row: _CsvRow, row_number: int) -> None:
        if row.get(None):
            raise NewsSourceValidationError(f"Invalid CSV row {row_number}")

    def _metadata_from_row(self, row: _CsvRow, row_number: int) -> dict[str, object]:
        metadata: dict[str, object] = {"row_number": row_number}
        for column, value in row.items():
            if column is None or not isinstance(value, str):
                continue
            normalized_column = column.strip()
            normalized_value = value.strip()
            if normalized_column.lower() in _CORE_COLUMNS or not normalized_value:
                continue
            metadata.setdefault(normalized_column, normalized_value)
        return metadata

    def _required_column(
        self,
        column_by_name: dict[str, str],
        aliases: tuple[str, ...],
        semantic_name: str,
    ) -> str:
        column = self._optional_column(column_by_name, aliases)
        if column is None:
            raise NewsSourceValidationError(f"Missing required CSV column: {semantic_name}")
        return column

    def _optional_column(
        self,
        column_by_name: dict[str, str],
        aliases: tuple[str, ...],
    ) -> str | None:
        for alias in aliases:
            if alias in column_by_name:
                return column_by_name[alias]
        return None

    def _required_value(self, row: _CsvRow, column: str, row_number: int) -> str:
        value = row.get(column)
        if not isinstance(value, str) or not value.strip():
            raise NewsSourceValidationError(f"Missing required value in row {row_number}: {column}")
        return value.strip()

    def _optional_value(self, row: _CsvRow, column: str | None) -> str | None:
        if column is None:
            return None

        value = row.get(column)
        if not isinstance(value, str) or not value.strip():
            return None
        return value.strip()

    def _parse_published_at(self, value: str | None, row_number: int) -> datetime | None:
        if value is None:
            return None

        if value.endswith("Z"):
            value = f"{value[:-1]}+00:00"

        try:
            return datetime.fromisoformat(value)
        except ValueError as error:
            raise NewsSourceValidationError(f"Invalid published_at in row {row_number}") from error
