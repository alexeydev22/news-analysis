from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from api_gateway.main.container import create_container
from api_gateway.main.settings import ApiGatewaySettings
from api_gateway.presentation.router import router
from dishka.integrations.fastapi import setup_dishka
from economic_news_framework.apps import create_service_app
from fastapi import FastAPI


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    yield
    await app.state.dishka_container.close()


def create_app() -> FastAPI:
    settings = ApiGatewaySettings()
    container = create_container()
    app = create_service_app(
        service_name=settings.service_name,
        routers=(router,),
        log_level=settings.log_level,
    )
    app.router.lifespan_context = lifespan
    setup_dishka(container=container, app=app)
    return app


app = create_app()
