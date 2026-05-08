from economic_news_contracts.news import IndexNewsJobStatus

from news_service.application.use_cases import IndexNewsDataset
from news_service.workers.broker import broker
from news_service.workers.events import IndexNewsJobEvent, publish_index_news_event


@broker.task
async def index_news_dataset_task(job_id: str, limit: int) -> dict[str, object]:
    await publish_index_news_event(
        IndexNewsJobEvent(job_id=job_id, status=IndexNewsJobStatus.STARTED),
    )

    from news_service.main.container import create_container

    container = create_container()
    try:
        async with container() as request_container:
            use_case = await request_container.get(IndexNewsDataset)
            result = await use_case.execute(limit=limit)
    except Exception:
        await publish_index_news_event(
            IndexNewsJobEvent(job_id=job_id, status=IndexNewsJobStatus.FAILED),
        )
        raise
    finally:
        await container.close()

    await publish_index_news_event(
        IndexNewsJobEvent(
            job_id=job_id,
            status=IndexNewsJobStatus.SUCCEEDED,
            loaded_count=result.loaded_count,
            indexed_count=result.indexed_count,
            collection_name=result.collection_name,
        ),
    )
    return result.model_dump(mode="json")
