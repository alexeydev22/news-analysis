from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import cast

from dialog_service.application.ports import DialogGenerator
from dialog_service.application.use_cases import GenerateDialogAnswer
from dialog_service.domain.errors import DialogGeneratorUnavailableError
from dialog_service.domain.model import DialogGeneration
from dialog_service.main.app import create_app
from dialog_service.presentation.router import router
from dishka import Provider, Scope, make_async_container, provide
from dishka.integrations.fastapi import FastapiProvider, setup_dishka
from economic_news_framework.apps import create_service_app
from fastapi.testclient import TestClient


def test_dialog_service_health_endpoint_uses_production_app_factory() -> None:
    with TestClient(create_app()) as client:
        response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"service": "dialog-service", "status": "ok"}


class SuccessfulGenerator:
    async def generate(self, question, context, impact_summaries, language):
        return DialogGeneration(
            answer=f"Ответ на вопрос: {question.value}",
            used_context_ids=[item.id for item in context],
            model_name="fake-generator",
            metadata={"language": language},
        )


class FailingGenerator:
    async def generate(self, question, context, impact_summaries, language):
        raise DialogGeneratorUnavailableError("generator failed")


class DialogProvider(Provider):
    def __init__(self, generator: object) -> None:
        super().__init__()
        self._generator = generator

    @provide(scope=Scope.APP)
    def generate_dialog_answer(self) -> GenerateDialogAnswer:
        return GenerateDialogAnswer(cast(DialogGenerator, self._generator))


def make_client(generator: object) -> TestClient:
    app = create_service_app(service_name="dialog-service", routers=(router,), log_level="INFO")
    container = make_async_container(DialogProvider(generator), FastapiProvider())
    setup_dishka(container=container, app=app)

    @asynccontextmanager
    async def close_container(_: object) -> AsyncIterator[None]:
        yield
        await container.close()

    app.router.lifespan_context = close_container
    return TestClient(app)


def test_generate_dialog_endpoint_returns_answer() -> None:
    with make_client(SuccessfulGenerator()) as client:
        response = client.post(
            "/api/v1/dialog/generate",
            json={
                "question": "Что значит рост ВВП?",
                "context": [
                    {
                        "id": "news-1",
                        "title": "GDP grows",
                        "text": "GDP grew by 2 percent.",
                        "source": "demo",
                        "score": 0.75,
                    },
                ],
                "impact_summaries": [],
            },
        )

    assert response.status_code == 200
    assert response.json()["answer"] == "Ответ на вопрос: Что значит рост ВВП?"
    assert response.json()["used_context_ids"] == ["news-1"]


def test_generate_dialog_endpoint_maps_generator_error_to_503() -> None:
    with make_client(FailingGenerator()) as client:
        response = client.post("/api/v1/dialog/generate", json={"question": "Что с рынком?"})

    assert response.status_code == 503
    assert response.json() == {"detail": "dialog-service is unavailable"}
