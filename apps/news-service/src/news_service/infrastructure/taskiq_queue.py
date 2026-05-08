from uuid import uuid4

from news_service.workers.tasks import index_news_dataset_task


class TaskiqNewsIndexTaskQueue:
    async def enqueue(self, limit: int) -> str:
        job_id = str(uuid4())
        await index_news_dataset_task.kiq(job_id=job_id, limit=limit)
        return job_id
