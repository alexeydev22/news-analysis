from pathlib import Path

import pytest
from analysis_service.application.use_cases import (
    EnqueueMlReportJob,
    GetLatestMlReport,
    GetMlReportJob,
)
from analysis_service.domain.errors import MlReportJobNotFoundError
from analysis_service.infrastructure.ml_report_storage import JsonMlReportStorage
from economic_news_contracts.analysis import MlReportJobResponse, MlReportJobStatus


class StubMlReportTaskQueue:
    def __init__(self) -> None:
        self.job_id: str | None = None

    async def enqueue(self, *, job_id: str) -> None:
        self.job_id = job_id


@pytest.mark.asyncio
async def test_json_ml_report_storage_round_trips_job_and_latest_report(tmp_path: Path) -> None:
    storage = JsonMlReportStorage(
        jobs_dir=tmp_path / "jobs",
        latest_report_path=tmp_path / "model-report.json",
    )

    await storage.save_job(
        MlReportJobResponse(
            job_id="job-1",
            status=MlReportJobStatus.SUCCEEDED,
            report_path="reports/ml/model-report.json",
        ),
    )
    await storage.save_latest_report({"dataset": {"row_count": 9}})

    assert await storage.get_job("job-1") == MlReportJobResponse(
        job_id="job-1",
        status=MlReportJobStatus.SUCCEEDED,
        report_path="reports/ml/model-report.json",
    )
    assert await storage.get_latest_report() == {"dataset": {"row_count": 9}}


@pytest.mark.asyncio
async def test_json_ml_report_storage_raises_for_missing_job(tmp_path: Path) -> None:
    storage = JsonMlReportStorage(
        jobs_dir=tmp_path / "jobs",
        latest_report_path=tmp_path / "model-report.json",
    )

    with pytest.raises(MlReportJobNotFoundError):
        await storage.get_job("missing-job")


@pytest.mark.asyncio
async def test_enqueue_ml_report_job_persists_queued_status_before_enqueue(tmp_path: Path) -> None:
    storage = JsonMlReportStorage(
        jobs_dir=tmp_path / "jobs",
        latest_report_path=tmp_path / "model-report.json",
    )
    queue = StubMlReportTaskQueue()
    use_case = EnqueueMlReportJob(queue, storage)

    response = await use_case.execute()

    assert response.job_id
    assert queue.job_id == response.job_id
    assert await GetMlReportJob(storage).execute(response.job_id) == MlReportJobResponse(
        job_id=response.job_id,
        status=MlReportJobStatus.QUEUED,
    )


@pytest.mark.asyncio
async def test_get_latest_ml_report_returns_none_when_report_missing(tmp_path: Path) -> None:
    storage = JsonMlReportStorage(
        jobs_dir=tmp_path / "jobs",
        latest_report_path=tmp_path / "model-report.json",
    )

    assert await GetLatestMlReport(storage).execute() is None
