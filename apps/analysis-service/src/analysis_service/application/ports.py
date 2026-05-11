from typing import Protocol

from economic_news_contracts.analysis import (
    AnalysisModelName,
    MlReportJobResponse,
    TopicForecastJobResponse,
    TopicForecastResponse,
)
from economic_news_contracts.retrieval import IndexedNewsDocument, NewsNeighborGroup

from analysis_service.domain.model import ImpactPrediction, NewsText


class ImpactClassifier(Protocol):
    model_name: AnalysisModelName

    def predict(self, text: NewsText) -> ImpactPrediction:
        """Predict economic impact for a normalized news text."""
        ...


class ModelRegistry(Protocol):
    def get(self, model_name: AnalysisModelName) -> ImpactClassifier:
        """Return classifier by model name or raise ModelUnavailableError."""
        ...


class MlReportStorage(Protocol):
    async def save_job(self, job: MlReportJobResponse) -> None:
        """Persist current ML report job state."""
        ...

    async def get_job(self, job_id: str) -> MlReportJobResponse:
        """Return persisted job state."""
        ...

    async def save_latest_report(self, report: dict[str, object]) -> None:
        """Persist latest generated ML report."""
        ...

    async def get_latest_report(self) -> dict[str, object] | None:
        """Return latest generated ML report if it exists."""
        ...


class MlReportTaskQueue(Protocol):
    async def enqueue(self, *, job_id: str) -> None:
        """Enqueue asynchronous ML report generation."""
        ...


class TopicForecastStorage(Protocol):
    async def save_job(self, job: TopicForecastJobResponse) -> None:
        """Persist current topic forecast job state."""
        ...

    async def get_job(self, job_id: str) -> TopicForecastJobResponse:
        """Return persisted topic forecast job state."""
        ...

    async def save_latest_report(self, report: TopicForecastResponse) -> None:
        """Persist latest generated topic forecast report."""
        ...

    async def get_latest_report(self) -> TopicForecastResponse | None:
        """Return latest generated topic forecast report if it exists."""
        ...


class TopicForecastTaskQueue(Protocol):
    async def enqueue(self, *, job_id: str) -> None:
        """Enqueue asynchronous topic forecast generation."""
        ...


class TopicForecastRetrievalGateway(Protocol):
    async def list_documents(self, *, limit: int) -> list[IndexedNewsDocument]:
        """Return indexed documents from retrieval-service."""
        ...

    async def find_neighbors(
        self,
        *,
        documents: list[IndexedNewsDocument],
        limit: int,
    ) -> list[NewsNeighborGroup]:
        """Return nearest indexed documents for each seed document."""
        ...
