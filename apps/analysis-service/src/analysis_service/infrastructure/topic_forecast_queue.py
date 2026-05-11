class TaskiqTopicForecastTaskQueue:
    async def enqueue(self, *, job_id: str) -> None:
        from analysis_service.workers.tasks import generate_topic_forecast_task

        await generate_topic_forecast_task.kiq(job_id=job_id)
