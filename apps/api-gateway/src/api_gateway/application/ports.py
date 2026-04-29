from typing import Protocol

from economic_news_contracts.analysis import AnalyzeNewsRequest, AnalyzeNewsResponse
from economic_news_contracts.retrieval import (
    IndexNewsRequest,
    IndexNewsResponse,
    SearchNewsRequest,
    SearchNewsResponse,
)


class VersionProvider(Protocol):
    def get_version(self) -> str:
        """Return current service version."""


class AnalysisClient(Protocol):
    async def analyze(self, request: AnalyzeNewsRequest) -> AnalyzeNewsResponse:
        """Analyze economic news text through analysis-service."""


class RetrievalClient(Protocol):
    async def index(self, request: IndexNewsRequest) -> IndexNewsResponse:
        """Index economic news documents through retrieval-service."""

    async def search(self, request: SearchNewsRequest) -> SearchNewsResponse:
        """Search economic news documents through retrieval-service."""


class StaticVersionProvider:
    def __init__(self, version: str) -> None:
        self._version = version

    def get_version(self) -> str:
        return self._version
