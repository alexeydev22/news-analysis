from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator


class NewsDocumentResponse(BaseModel):
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


class PreviewNewsResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    documents: list[NewsDocumentResponse]
    total_count: int = Field(ge=0)


class IndexNewsDatasetRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    limit: int = Field(default=100, ge=1, le=1000)


class IndexNewsDatasetResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    loaded_count: int = Field(ge=0)
    indexed_count: int = Field(ge=0)
    collection_name: str = Field(min_length=1)

    @field_validator("collection_name")
    @classmethod
    def normalize_collection_name(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("Value must not be empty")
        return normalized
