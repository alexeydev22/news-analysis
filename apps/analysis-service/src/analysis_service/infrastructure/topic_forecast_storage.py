from pathlib import Path

from economic_news_contracts.analysis import TopicForecastJobResponse, TopicForecastResponse

from analysis_service.domain.errors import TopicForecastJobNotFoundError


class JsonTopicForecastStorage:
    def __init__(self, *, jobs_dir: Path, latest_report_path: Path) -> None:
        self._jobs_dir = jobs_dir
        self._latest_report_path = latest_report_path

    async def save_job(self, job: TopicForecastJobResponse) -> None:
        self._jobs_dir.mkdir(parents=True, exist_ok=True)
        self._job_path(job.job_id).write_text(
            job.model_dump_json(),
            encoding="utf-8",
        )

    async def get_job(self, job_id: str) -> TopicForecastJobResponse:
        job_path = self._job_path(job_id)
        if not job_path.exists():
            raise TopicForecastJobNotFoundError(job_id)
        return TopicForecastJobResponse.model_validate_json(
            job_path.read_text(encoding="utf-8"),
        )

    async def save_latest_report(self, report: TopicForecastResponse) -> None:
        self._latest_report_path.parent.mkdir(parents=True, exist_ok=True)
        self._latest_report_path.write_text(
            report.model_dump_json(indent=2),
            encoding="utf-8",
        )

    async def get_latest_report(self) -> TopicForecastResponse | None:
        if not self._latest_report_path.exists():
            return None
        return TopicForecastResponse.model_validate_json(
            self._latest_report_path.read_text(encoding="utf-8"),
        )

    def _job_path(self, job_id: str) -> Path:
        return self._jobs_dir / f"{job_id}.json"
