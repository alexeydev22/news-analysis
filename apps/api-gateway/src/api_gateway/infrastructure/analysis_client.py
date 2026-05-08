import asyncio
from collections.abc import Callable
from typing import Any

from api_gateway.application.errors import AnalysisServiceUnavailableError
from economic_news_contracts.analysis import AnalyzeNewsRequest, AnalyzeNewsResponse
from zapros import AsyncClient, AsyncStdNetworkHandler


def _make_zapros_client(timeout_seconds: float) -> AsyncClient:
    return AsyncClient(
        handler=AsyncStdNetworkHandler(),
    )


class ZaprosAnalysisClient:
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

    async def analyze(self, request: AnalyzeNewsRequest) -> AnalyzeNewsResponse:
        response = await self._post(request.model_dump(mode="json"))
        if response.status >= 500:
            raise AnalysisServiceUnavailableError("analysis-service is unavailable")
        return AnalyzeNewsResponse.model_validate(response.json)

    async def _post(self, payload: dict[str, Any]) -> Any:
        url = f"{self._base_url}/api/v1/analyze"
        try:
            async with asyncio.timeout(self._timeout_seconds):
                if self._client is not None:
                    return await self._client.post(url, json=payload)
                async with self._client_factory(self._timeout_seconds) as client:
                    return await client.post(url, json=payload)
        except Exception as error:
            raise AnalysisServiceUnavailableError("analysis-service is unavailable") from error
