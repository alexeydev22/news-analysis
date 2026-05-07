from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from dishka.integrations.fastapi import setup_dishka
from economic_news_framework.apps import create_service_app
from fastapi import FastAPI

from news_service.main.container import create_container
from news_service.main.settings import NewsServiceSettings
from news_service.presentation.errors import register_error_handlers
from news_service.presentation.router import router


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    yield
    await app.state.dishka_container.close()


def create_app(*, use_fake_components: bool = False) -> FastAPI:
    settings = NewsServiceSettings()
    container = create_container(settings, use_fake_components=use_fake_components)
    app = create_service_app(
        service_name=settings.service_name,
        routers=(router,),
        log_level=settings.log_level,
    )
    app.router.lifespan_context = lifespan
    setup_dishka(container=container, app=app)
    register_error_handlers(app)
    return app


app = create_app()
