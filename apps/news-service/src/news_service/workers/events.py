from typing import Any

from economic_news_contracts.news import IndexNewsJobStatus
from faststream import FastStream
from faststream.redis import RedisBroker
from pydantic import BaseModel, ConfigDict, Field

from news_service.main.settings import NewsServiceSettings

settings = NewsServiceSettings()
events_broker = RedisBroker(str(settings.redis_url))
app = FastStream(events_broker)


class IndexNewsJobEvent(BaseModel):
    model_config = ConfigDict(extra="forbid")

    job_id: str = Field(min_length=1)
    status: IndexNewsJobStatus
    loaded_count: int | None = Field(default=None, ge=0)
    indexed_count: int | None = Field(default=None, ge=0)
    collection_name: str | None = None
    error: str | None = None


async def publish_index_news_event(
    event: IndexNewsJobEvent,
    *,
    broker: Any = events_broker,
    channel: str | None = None,
) -> None:
    target_channel = channel or settings.index_events_channel
    await broker.publish(event.model_dump(mode="json"), target_channel)
