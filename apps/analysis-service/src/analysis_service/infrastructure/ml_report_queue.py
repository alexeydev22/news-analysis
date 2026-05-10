class TaskiqMlReportTaskQueue:
    async def enqueue(self, *, job_id: str) -> None:
        from analysis_service.workers.tasks import generate_ml_report_task

        await generate_ml_report_task.kiq(job_id=job_id)
