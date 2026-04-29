from typing import Protocol

from economic_news_contracts.analysis import AnalyzeNewsRequest, AnalyzeNewsResponse


class VersionProvider(Protocol):
    def get_version(self) -> str:
        """Return current service version."""


class AnalysisClient(Protocol):
    async def analyze(self, request: AnalyzeNewsRequest) -> AnalyzeNewsResponse:
        """Analyze economic news text through analysis-service."""


class StaticVersionProvider:
    def __init__(self, version: str) -> None:
        self._version = version

    def get_version(self) -> str:
        return self._version
