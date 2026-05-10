from uuid import uuid4

from economic_news_contracts.analysis import (
    AnalysisModelName,
    EnqueueMlReportJobResponse,
    MlReportJobResponse,
    MlReportJobStatus,
)

from analysis_service.application.ports import MlReportStorage, MlReportTaskQueue, ModelRegistry
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
