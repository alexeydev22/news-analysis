import json
from pathlib import Path

from economic_news_contracts.analysis import MlReportJobResponse

from analysis_service.domain.errors import MlReportJobNotFoundError


class JsonMlReportStorage:
    def __init__(self, *, jobs_dir: Path, latest_report_path: Path) -> None:
        self._jobs_dir = jobs_dir
        self._latest_report_path = latest_report_path

    async def save_job(self, job: MlReportJobResponse) -> None:
        self._jobs_dir.mkdir(parents=True, exist_ok=True)
        self._job_path(job.job_id).write_text(
            job.model_dump_json(),
            encoding="utf-8",
        )

    async def get_job(self, job_id: str) -> MlReportJobResponse:
        job_path = self._job_path(job_id)
        if not job_path.exists():
            raise MlReportJobNotFoundError(job_id)
        return MlReportJobResponse.model_validate_json(
            job_path.read_text(encoding="utf-8"),
        )

    async def save_latest_report(self, report: dict[str, object]) -> None:
        self._latest_report_path.parent.mkdir(parents=True, exist_ok=True)
        self._latest_report_path.write_text(
            json.dumps(report, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    async def get_latest_report(self) -> dict[str, object] | None:
        if not self._latest_report_path.exists():
            return None
        return json.loads(self._latest_report_path.read_text(encoding="utf-8"))

    def _job_path(self, job_id: str) -> Path:
        return self._jobs_dir / f"{job_id}.json"
