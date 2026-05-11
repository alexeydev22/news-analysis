import asyncio
from collections.abc import Callable
from typing import Any, cast

from economic_news_contracts.retrieval import (
    FindNeighborsRequest,
    FindNeighborsResponse,
    IndexedNewsDocument,
    ListIndexedDocumentsResponse,
    NewsNeighborGroup,
)
from zapros import AsyncClient, AsyncStdNetworkHandler


def _make_zapros_client(timeout_seconds: float) -> AsyncClient:
    return AsyncClient(
        handler=AsyncStdNetworkHandler(),
    )


class HttpTopicForecastRetrievalGateway:
    def __init__(
        self,
        *,
        base_url: str,
        timeout_seconds: float,
        client: Any | None = None,
        client_factory: Callable[[float], Any] | None = None,
    ) -> None:
        self._base_url = base_url.rstrip("/")
        self._timeout_seconds = timeout_seconds
        self._client = client
        self._client_factory = client_factory or _make_zapros_client

    async def list_documents(self, *, limit: int) -> list[IndexedNewsDocument]:
        response = await self._get("/api/v1/documents", params={"limit": [str(limit)]})
        response_json = cast("dict[str, object]", response.json)
        if response.status >= 400:
            raise RuntimeError("retrieval-service is unavailable")
        return ListIndexedDocumentsResponse.model_validate(response_json).documents

    async def find_neighbors(
        self,
        *,
        documents: list[IndexedNewsDocument],
        limit: int,
    ) -> list[NewsNeighborGroup]:
        document_ids = [document.id for document in documents]
        if not document_ids:
            return []
        request = FindNeighborsRequest(document_ids=document_ids, limit=limit)
        response = await self._post(
            "/api/v1/neighbors",
            payload=request.model_dump(mode="json"),
        )
        response_json = cast("dict[str, object]", response.json)
        if response.status >= 400:
            raise RuntimeError("retrieval-service is unavailable")
        return FindNeighborsResponse.model_validate(response_json).groups

    async def _get(self, path: str, *, params: dict[str, list[str]]) -> Any:
        url = f"{self._base_url}{path}"
        async with asyncio.timeout(self._timeout_seconds):
            if self._client is not None:
                return await self._client.get(url, params=params)
            async with self._client_factory(self._timeout_seconds) as client:
                return await client.get(url, params=params)

    async def _post(self, path: str, *, payload: dict[str, Any]) -> Any:
        url = f"{self._base_url}{path}"
        async with asyncio.timeout(self._timeout_seconds):
            if self._client is not None:
                return await self._client.post(url, json=payload)
            async with self._client_factory(self._timeout_seconds) as client:
                return await client.post(url, json=payload)
