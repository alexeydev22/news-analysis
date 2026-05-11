from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator


class NewsDocumentPayload(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str = Field(min_length=1)
    title: str = Field(min_length=1)
    text: str = Field(min_length=1)
    source: str = Field(min_length=1)
    published_at: datetime | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)

    @field_validator("id", "title", "text", "source")
    @classmethod
    def normalize_required_text(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("Value must not be empty")
        return normalized


class IndexNewsRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    documents: list[NewsDocumentPayload] = Field(min_length=1)


class IndexNewsResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    indexed_count: int = Field(ge=0)
    collection_name: str = Field(min_length=1)


class SearchNewsRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    query: str = Field(min_length=1)
    limit: int = Field(default=5, ge=1, le=20)
    source: str | None = Field(default=None, min_length=1)

    @field_validator("query", "source")
    @classmethod
    def normalize_optional_text(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.strip()
        if not normalized:
            raise ValueError("Value must not be empty")
        return normalized


class SearchNewsResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str = Field(min_length=1)
    score: float = Field(ge=-1.0, le=1.0)
    title: str = Field(min_length=1)
    text: str = Field(min_length=1)
    source: str = Field(min_length=1)
    published_at: datetime | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class SearchNewsResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    results: list[SearchNewsResult]


class IndexedNewsDocument(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str = Field(min_length=1)
    title: str = Field(min_length=1)
    text: str = Field(min_length=1)
    source: str = Field(min_length=1)
    published_at: datetime | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)

    @field_validator("id", "title", "text", "source")
    @classmethod
    def normalize_required_text(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("Value must not be empty")
        return normalized


class ListIndexedDocumentsResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    documents: list[IndexedNewsDocument] = Field(default_factory=list)


class FindNeighborsRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    document_ids: list[str] = Field(min_length=1)
    limit: int = Field(default=5, ge=1, le=20)
    source: str | None = Field(default=None, min_length=1)

    @field_validator("document_ids")
    @classmethod
    def normalize_document_ids(cls, values: list[str]) -> list[str]:
        normalized = [value.strip() for value in values]
        if any(not value for value in normalized):
            raise ValueError("Document ids must not be empty")
        return normalized

    @field_validator("source")
    @classmethod
    def normalize_source(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.strip()
        if not normalized:
            raise ValueError("Value must not be empty")
        return normalized


class NewsNeighbor(IndexedNewsDocument):
    score: float = Field(ge=-1.0, le=1.0)


class NewsNeighborGroup(BaseModel):
    model_config = ConfigDict(extra="forbid")

    document_id: str = Field(min_length=1)
    neighbors: list[NewsNeighbor] = Field(default_factory=list)


class FindNeighborsResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    groups: list[NewsNeighborGroup] = Field(default_factory=list)
