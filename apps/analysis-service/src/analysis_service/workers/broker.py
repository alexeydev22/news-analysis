from taskiq_redis import RedisAsyncResultBackend, RedisStreamBroker

from analysis_service.main.settings import AnalysisServiceSettings

settings = AnalysisServiceSettings()

broker = RedisStreamBroker(
    url=str(settings.redis_url),
    queue_name=settings.task_queue_name,
).with_result_backend(
    RedisAsyncResultBackend(
        redis_url=str(settings.redis_url),
        result_ex_time=settings.task_result_ttl_seconds,
    ),
)
