from typing import Any

from api_gateway.application.errors import AnalysisServiceUnavailableError
from economic_news_contracts.analysis import AnalyzeNewsRequest, AnalyzeNewsResponse
from zapros import AsyncClient


class ZaprosAnalysisClient:
    def __init__(
        self,
        base_url: str,
        timeout_seconds: float,
        client: Any | None = None,
    ) -> None:
        self._base_url = base_url.rstrip("/")
        self._timeout_seconds = timeout_seconds
        self._client = client

    async def analyze(self, request: AnalyzeNewsRequest) -> AnalyzeNewsResponse:
        response = await self._post(request.model_dump(mode="json"))
        if response.status >= 500:
            raise AnalysisServiceUnavailableError("analysis-service is unavailable")
        return AnalyzeNewsResponse.model_validate(response.json())

    async def _post(self, payload: dict[str, Any]) -> Any:
        url = f"{self._base_url}/api/v1/analyze"
        try:
            if self._client is not None:
                return await self._client.post(url, json=payload)
            async with AsyncClient() as client:
                return await client.post(url, json=payload)
        except Exception as error:
            raise AnalysisServiceUnavailableError("analysis-service is unavailable") from error
