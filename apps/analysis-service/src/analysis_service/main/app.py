from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from dishka.integrations.fastapi import setup_dishka
from economic_news_framework.apps import create_service_app
from fastapi import FastAPI

from analysis_service.main.container import create_container
from analysis_service.main.settings import AnalysisServiceSettings
from analysis_service.presentation.errors import register_error_handlers
from analysis_service.presentation.router import router


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    yield
    await app.state.dishka_container.close()


def create_app(*, use_static_classifier: bool | None = None) -> FastAPI:
    settings = AnalysisServiceSettings()
    if use_static_classifier is not None:
        settings = settings.model_copy(update={"use_static_classifier": use_static_classifier})
    container = create_container(settings)
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
