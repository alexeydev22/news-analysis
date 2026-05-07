from collections.abc import Callable
from typing import Any

from economic_news_contracts.retrieval import (
    IndexNewsRequest,
    IndexNewsResponse,
    NewsDocumentPayload,
)
from zapros import AsyncClient, AsyncStdNetworkHandler

from news_service.domain.errors import RetrievalIndexUnavailableError
from news_service.domain.model import NewsDocument


def _make_zapros_client(timeout_seconds: float) -> AsyncClient:
    return AsyncClient(
        handler=AsyncStdNetworkHandler(total_timeout=timeout_seconds),
    )


class ZaprosRetrievalIndexer:
    def __init__(
        self,
        base_url: str,
        timeout_seconds: float,
        client: Any | None = None,
        client_factory: Callable[[float], Any] | None = None,
    ) -> None:
        self._base_url = base_url.rstrip("/")
        self._timeout_seconds = timeout_seconds
        self._client = client
        self._client_factory = client_factory or _make_zapros_client

    async def index(self, documents: list[NewsDocument]) -> IndexNewsResponse:
        request = IndexNewsRequest(
            documents=[
                NewsDocumentPayload(
                    id=document.id,
                    title=document.title,
                    text=document.text,
                    source=document.source,
                    published_at=document.published_at,
                    metadata=dict(document.metadata),
                )
                for document in documents
            ],
        )
        response = await self._post(request.model_dump(mode="json"))
        if response.status >= 400:
            raise RetrievalIndexUnavailableError("retrieval-service is unavailable")
        try:
            return IndexNewsResponse.model_validate(response.json)
        except Exception as error:
            raise RetrievalIndexUnavailableError("retrieval-service is unavailable") from error

    async def _post(self, payload: dict[str, Any]) -> Any:
        url = f"{self._base_url}/api/v1/index"
        try:
            if self._client is not None:
                return await self._client.post(url, json=payload)
            async with self._client_factory(self._timeout_seconds) as client:
                return await client.post(url, json=payload)
        except RetrievalIndexUnavailableError:
            raise
        except Exception as error:
            raise RetrievalIndexUnavailableError("retrieval-service is unavailable") from error
