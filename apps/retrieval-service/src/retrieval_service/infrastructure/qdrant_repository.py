from datetime import datetime
from typing import Any
from uuid import NAMESPACE_URL, uuid5

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


def _point_id(document_id: str) -> str:
    return str(uuid5(NAMESPACE_URL, document_id))


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
        await self._ensure_collection()
        points = [
            PointStruct(id=_point_id(document.id), vector=vector, payload=self._payload(document))
            for document, vector in zip(documents, vectors, strict=True)
        ]
        try:
            await self._client.upsert(collection_name=self._collection_name, points=points)
        except Exception as error:
            raise RetrievalUnavailableError() from error
        return len(points)

    async def search(self, query: SearchQuery, vector: list[float]) -> list[SearchResult]:
        await self._ensure_collection()
        try:
            response = await self._client.query_points(
                collection_name=self._collection_name,
                query=vector,
                limit=query.limit,
                query_filter=self._filter(query),
            )
        except Exception as error:
            raise RetrievalUnavailableError() from error
        return [self._to_result(point) for point in response.points]

    async def _ensure_collection(self) -> None:
        try:
            if await self._client.collection_exists(collection_name=self._collection_name):
                return
            await self._client.create_collection(
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
            "document_id": document.id,
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
            id=str(payload["document_id"]),
            title=str(payload["title"]),
            text=str(payload["text"]),
            source=str(payload["source"]),
            published_at=self._published_at(payload.get("published_at")),
            metadata=payload.get("metadata") or {},
        )
        return SearchResult(document=document, score=float(point.score))
