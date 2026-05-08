import pytest
from economic_news_contracts.news import IndexNewsJobStatus
from news_service.workers.events import IndexNewsJobEvent, publish_index_news_event


class FakeBroker:
    def __init__(self) -> None:
        self.message: dict[str, object] | None = None
        self.channel: str | None = None

    async def publish(self, message: dict[str, object], channel: str) -> None:
        self.message = message
        self.channel = channel


@pytest.mark.asyncio
async def test_publish_index_news_event_uses_faststream_broker() -> None:
    broker = FakeBroker()

    await publish_index_news_event(
        IndexNewsJobEvent(
            job_id="job-1",
            status=IndexNewsJobStatus.SUCCEEDED,
            loaded_count=2,
            indexed_count=2,
            collection_name="economic_news",
        ),
        broker=broker,
        channel="custom.channel",
    )

    assert broker.channel == "custom.channel"
    assert broker.message == {
        "job_id": "job-1",
        "status": "succeeded",
        "loaded_count": 2,
        "indexed_count": 2,
        "collection_name": "economic_news",
        "error": None,
    }
