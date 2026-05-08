import pytest
from news_service.infrastructure.taskiq_queue import TaskiqNewsIndexTaskQueue


class FakeTask:
    def __init__(self) -> None:
        self.payload: dict[str, object] | None = None

    async def kiq(self, **payload: object) -> None:
        self.payload = payload


@pytest.mark.asyncio
async def test_taskiq_news_index_task_queue_schedules_task(monkeypatch: pytest.MonkeyPatch) -> None:
    fake_task = FakeTask()
    monkeypatch.setattr(
        "news_service.infrastructure.taskiq_queue.index_news_dataset_task",
        fake_task,
    )

    queue = TaskiqNewsIndexTaskQueue()
    job_id = await queue.enqueue(limit=12)

    assert fake_task.payload == {"job_id": job_id, "limit": 12}
    assert job_id
