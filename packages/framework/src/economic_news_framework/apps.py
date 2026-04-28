from collections.abc import Iterable

from fastapi import APIRouter, FastAPI

from economic_news_framework.health import build_health_response
from economic_news_framework.logging import configure_logging


def create_service_app(
    *,
    service_name: str,
    routers: Iterable[APIRouter] = (),
    log_level: str = "INFO",
) -> FastAPI:
    configure_logging(log_level)
    app = FastAPI(title=service_name)

    @app.get("/health")
    async def health():
        return build_health_response(service_name)

    for router in routers:
        app.include_router(router)

    return app
