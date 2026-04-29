from datetime import datetime
from typing import Any

from qdrant_client.models import (
    Distance,
    FieldCondition,
    Filter,
    MatchValue,
    PointStruct,
    VectorParams,
)

from retrieval_service.domain.errors import RetrievalUnavailableError
from retrieval_service.domain.model import NewsDocument, SearchQuery, SearchResult


class QdrantNewsRepository:
    def __init__(
        self,
        client: Any,
        collection_name: str,
        vector_size: int,
    ) -> None:
        self._client = client
        self._collection_name = collection_name
        self._vector_size = vector_size

    async def upsert(self, documents: list[NewsDocument], vectors: list[list[float]]) -> int:
        self._ensure_collection()
        points = [
            PointStruct(id=document.id, vector=vector, payload=self._payload(document))
            for document, vector in zip(documents, vectors, strict=True)
        ]
        try:
            self._client.upsert(collection_name=self._collection_name, points=points)
        except Exception as error:
            raise RetrievalUnavailableError() from error
        return len(points)

    async def search(self, query: SearchQuery, vector: list[float]) -> list[SearchResult]:
        self._ensure_collection()
        try:
            response = self._client.query_points(
                collection_name=self._collection_name,
                query=vector,
                limit=query.limit,
                query_filter=self._filter(query),
            )
        except Exception as error:
            raise RetrievalUnavailableError() from error
        return [self._to_result(point) for point in response.points]

    def _ensure_collection(self) -> None:
        try:
            if self._client.collection_exists(collection_name=self._collection_name):
                return
            self._client.create_collection(
                collection_name=self._collection_name,
                vectors_config=VectorParams(size=self._vector_size, distance=Distance.COSINE),
            )
        except Exception as error:
            raise RetrievalUnavailableError() from error

    def _filter(self, query: SearchQuery) -> Filter | None:
        if query.source is None:
            return None
        return Filter(
            must=[FieldCondition(key="source", match=MatchValue(value=query.source))],
        )

    def _payload(self, document: NewsDocument) -> dict[str, Any]:
        return {
            "title": document.title,
            "text": document.text,
            "source": document.source,
            "published_at": document.published_at.isoformat() if document.published_at else None,
            "metadata": dict(document.metadata),
        }

    def _published_at(self, value: Any) -> datetime | None:
        if value is None or isinstance(value, datetime):
            return value
        return datetime.fromisoformat(str(value))

    def _to_result(self, point: Any) -> SearchResult:
        payload = point.payload or {}
        document = NewsDocument(
            id=str(point.id),
            title=str(payload["title"]),
            text=str(payload["text"]),
            source=str(payload["source"]),
            published_at=self._published_at(payload.get("published_at")),
            metadata=payload.get("metadata") or {},
        )
        return SearchResult(document=document, score=float(point.score))
