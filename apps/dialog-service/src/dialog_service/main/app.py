from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from dishka.integrations.fastapi import setup_dishka
from economic_news_framework.apps import create_service_app
from fastapi import FastAPI

from dialog_service.main.container import create_container
from dialog_service.main.settings import DialogServiceSettings
from dialog_service.presentation.router import router


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    yield
    await app.state.dishka_container.close()


def create_app(settings: DialogServiceSettings | None = None) -> FastAPI:
    resolved_settings = settings or DialogServiceSettings()
    container = create_container(resolved_settings)
    app = create_service_app(
        service_name=resolved_settings.service_name,
        routers=(router,),
        log_level=resolved_settings.log_level,
    )
    app.router.lifespan_context = lifespan
    setup_dishka(container=container, app=app)
    return app


app = create_app()
