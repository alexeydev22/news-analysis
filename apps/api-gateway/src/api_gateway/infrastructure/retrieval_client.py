from collections.abc import Callable
from typing import Any

from api_gateway.application.errors import RetrievalServiceUnavailableError
from economic_news_contracts.retrieval import (
    IndexNewsRequest,
    IndexNewsResponse,
    SearchNewsRequest,
    SearchNewsResponse,
)
from zapros import AsyncClient, AsyncStdNetworkHandler


def _make_zapros_client(timeout_seconds: float) -> AsyncClient:
    return AsyncClient(
        handler=AsyncStdNetworkHandler(total_timeout=timeout_seconds),
    )


class ZaprosRetrievalClient:
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

    async def index(self, request: IndexNewsRequest) -> IndexNewsResponse:
        response = await self._post("/api/v1/index", request.model_dump(mode="json"))
        if response.status >= 400:
            raise RetrievalServiceUnavailableError("retrieval-service is unavailable")
        return IndexNewsResponse.model_validate(response.json)

    async def search(self, request: SearchNewsRequest) -> SearchNewsResponse:
        response = await self._post("/api/v1/search", request.model_dump(mode="json"))
        if response.status >= 400:
            raise RetrievalServiceUnavailableError("retrieval-service is unavailable")
        return SearchNewsResponse.model_validate(response.json)

    async def _post(self, path: str, payload: dict[str, Any]) -> Any:
        url = f"{self._base_url}{path}"
        try:
            if self._client is not None:
                return await self._client.post(url, json=payload)
            async with self._client_factory(self._timeout_seconds) as client:
                return await client.post(url, json=payload)
        except Exception as error:
            raise RetrievalServiceUnavailableError("retrieval-service is unavailable") from error
