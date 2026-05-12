from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

from economic_news_contracts.analysis import (
    AnalysisModelName,
    EnqueueMlReportJobResponse,
    EnqueueTopicForecastJobResponse,
    GroqForecastRequest,
    GroqForecastResponse,
    MlReportJobResponse,
    MlReportJobStatus,
    TopicForecastJobResponse,
    TopicForecastJobStatus,
    TopicForecastModelReportResponse,
    TopicForecastResponse,
)
from economic_news_contracts.dialog import DialogImpactSummary
from economic_news_contracts.retrieval import IndexedNewsDocument, NewsNeighborGroup

from analysis_service.application.ports import (
    EconomicForecastGenerator,
    MlReportStorage,
    MlReportTaskQueue,
    ModelRegistry,
    TopicForecastRetrievalGateway,
    TopicForecastStorage,
    TopicForecastTaskQueue,
)
from analysis_service.application.topic_forecast import build_topic_forecast
from analysis_service.domain.model import ImpactPrediction, NewsText


class AnalyzeNewsImpact:
    def __init__(self, registry: ModelRegistry) -> None:
        self._registry = registry

    def execute(self, *, text: str, model_name: AnalysisModelName) -> ImpactPrediction:
        news_text = NewsText.from_raw(text)
        classifier = self._registry.get(model_name)
        return classifier.predict(news_text)


class EnqueueMlReportJob:
    def __init__(self, task_queue: MlReportTaskQueue, storage: MlReportStorage) -> None:
        self._task_queue = task_queue
        self._storage = storage

    async def execute(self) -> EnqueueMlReportJobResponse:
        job_id = str(uuid4())
        await self._storage.save_job(
            MlReportJobResponse(job_id=job_id, status=MlReportJobStatus.QUEUED),
        )
        await self._task_queue.enqueue(job_id=job_id)
        return EnqueueMlReportJobResponse(job_id=job_id)


class GetMlReportJob:
    def __init__(self, storage: MlReportStorage) -> None:
        self._storage = storage

    async def execute(self, job_id: str) -> MlReportJobResponse:
        return await self._storage.get_job(job_id)


class GetLatestMlReport:
    def __init__(self, storage: MlReportStorage) -> None:
        self._storage = storage

    async def execute(self) -> dict[str, object] | None:
        return await self._storage.get_latest_report()


class EnqueueTopicForecastJob:
    def __init__(
        self,
        task_queue: TopicForecastTaskQueue,
        storage: TopicForecastStorage,
    ) -> None:
        self._task_queue = task_queue
        self._storage = storage

    async def execute(self) -> EnqueueTopicForecastJobResponse:
        job_id = str(uuid4())
        await self._storage.save_job(
            TopicForecastJobResponse(job_id=job_id, status=TopicForecastJobStatus.QUEUED),
        )
        await self._task_queue.enqueue(job_id=job_id)
        return EnqueueTopicForecastJobResponse(job_id=job_id)


class GetTopicForecastJob:
    def __init__(self, storage: TopicForecastStorage) -> None:
        self._storage = storage

    async def execute(self, job_id: str) -> TopicForecastJobResponse:
        return await self._storage.get_job(job_id)


class GetLatestTopicForecast:
    def __init__(self, storage: TopicForecastStorage) -> None:
        self._storage = storage

    async def execute(self) -> TopicForecastResponse | None:
        return await self._storage.get_latest_report()


class GenerateGroqTopicForecast:
    def __init__(self, generator: EconomicForecastGenerator) -> None:
        self._generator = generator

    async def execute(self, request: GroqForecastRequest) -> GroqForecastResponse:
        return await self._generator.generate(request)


class GenerateTopicForecastReport:
    def __init__(
        self,
        *,
        retrieval_gateway: TopicForecastRetrievalGateway,
        registry: ModelRegistry,
        storage: TopicForecastStorage,
        analysis_model: AnalysisModelName,
        document_limit: int,
        neighbor_limit: int,
        min_neighbor_score: float,
        max_topic_size: int,
        report_path: Path,
    ) -> None:
        self._retrieval_gateway = retrieval_gateway
        self._registry = registry
        self._storage = storage
        self._analysis_model = analysis_model
        self._document_limit = document_limit
        self._neighbor_limit = neighbor_limit
        self._min_neighbor_score = min_neighbor_score
        self._max_topic_size = max_topic_size
        self._report_path = report_path

    async def execute(self, job_id: str) -> TopicForecastResponse:
        await self._storage.save_job(
            TopicForecastJobResponse(job_id=job_id, status=TopicForecastJobStatus.STARTED),
        )
        try:
            documents = await self._retrieval_gateway.list_documents(limit=self._document_limit)
            neighbor_groups = await self._retrieval_gateway.find_neighbors(
                documents=documents,
                limit=self._neighbor_limit,
            )
            model_reports = [
                self._build_model_report(
                    model_name=model_name,
                    documents=documents,
                    neighbor_groups=neighbor_groups,
                )
                for model_name in self._analysis_models()
            ]
            primary_report = next(
                (model_report for model_report in model_reports if model_report.error is None),
                model_reports[0],
            )
            report = TopicForecastResponse(
                generated_at=datetime.now(UTC).isoformat(),
                topics=primary_report.topics,
                model_reports=model_reports,
                metadata={
                    "document_count": len(documents),
                    "neighbor_group_count": len(neighbor_groups),
                    "analysis_model": self._analysis_model,
                    "analysis_models": [model_name.value for model_name in self._analysis_models()],
                    "model_errors": {
                        model_report.model_name.value: model_report.error
                        for model_report in model_reports
                        if model_report.error is not None
                    },
                    "document_limit": self._document_limit,
                    "neighbor_limit": self._neighbor_limit,
                    "min_neighbor_score": self._min_neighbor_score,
                    "max_topic_size": self._max_topic_size,
                },
            )
        except Exception as error:
            await self._storage.save_job(
                TopicForecastJobResponse(
                    job_id=job_id,
                    status=TopicForecastJobStatus.FAILED,
                    message=str(error),
                ),
            )
            raise

        await self._storage.save_latest_report(report)
        await self._storage.save_job(
            TopicForecastJobResponse(
                job_id=job_id,
                status=TopicForecastJobStatus.SUCCEEDED,
                report_path=str(self._report_path),
            ),
        )
        return report

    def _analysis_models(self) -> list[AnalysisModelName]:
        return [
            self._analysis_model,
            *[model_name for model_name in AnalysisModelName if model_name != self._analysis_model],
        ]

    def _build_model_report(
        self,
        *,
        model_name: AnalysisModelName,
        documents: list[IndexedNewsDocument],
        neighbor_groups: list[NewsNeighborGroup],
    ) -> TopicForecastModelReportResponse:
        try:
            impacts_by_news_id = self._predict_impacts(documents, model_name)
            topics = build_topic_forecast(
                documents=documents,
                neighbor_groups=neighbor_groups,
                impacts_by_news_id=impacts_by_news_id,
                min_neighbor_score=self._min_neighbor_score,
                max_topic_size=self._max_topic_size,
            )
            return TopicForecastModelReportResponse(model_name=model_name, topics=topics)
        except Exception as error:
            return TopicForecastModelReportResponse(
                model_name=model_name,
                topics=[],
                error=str(error),
            )

    def _predict_impacts(
        self,
        documents: list[IndexedNewsDocument],
        model_name: AnalysisModelName,
    ) -> dict[str, DialogImpactSummary]:
        classifier = self._registry.get(model_name)
        impacts_by_news_id: dict[str, DialogImpactSummary] = {}
        for document in documents:
            prediction = classifier.predict(NewsText.from_raw(document.text))
            impacts_by_news_id[document.id] = DialogImpactSummary(
                news_id=document.id,
                model_name=prediction.model_name,
                impact=prediction.impact,
                confidence=prediction.confidence,
                explanation=prediction.explanation or "",
            )
        return impacts_by_news_id
