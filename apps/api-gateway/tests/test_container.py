import pytest
from api_gateway.application.use_cases import (
    AnalyzeNewsUseCase,
    ChatUseCase,
    IndexNewsUseCase,
    SearchNewsUseCase,
)
from api_gateway.main.container import create_container
from api_gateway.main.settings import ApiGatewaySettings
from dishka import AsyncContainer


@pytest.mark.asyncio
async def test_container_resolves_analyze_news_use_case() -> None:
    container: AsyncContainer = create_container()

    try:
        use_case = await container.get(AnalyzeNewsUseCase)
    finally:
        await container.close()

    assert isinstance(use_case, AnalyzeNewsUseCase)


@pytest.mark.asyncio
async def test_container_resolves_retrieval_use_cases() -> None:
    container: AsyncContainer = create_container()

    try:
        index_use_case = await container.get(IndexNewsUseCase)
        search_use_case = await container.get(SearchNewsUseCase)
    finally:
        await container.close()

    assert isinstance(index_use_case, IndexNewsUseCase)
    assert isinstance(search_use_case, SearchNewsUseCase)


@pytest.mark.asyncio
async def test_container_resolves_chat_use_case() -> None:
    container: AsyncContainer = create_container()

    try:
        use_case = await container.get(ChatUseCase)
    finally:
        await container.close()

    assert isinstance(use_case, ChatUseCase)


def test_api_gateway_settings_include_analysis_service_defaults() -> None:
    settings = ApiGatewaySettings()

    assert str(settings.analysis_service_url) == "http://analysis-service:8000/"
    assert settings.analysis_service_timeout_seconds == 3.0


def test_api_gateway_settings_include_retrieval_service_defaults() -> None:
    settings = ApiGatewaySettings()

    assert str(settings.retrieval_service_url) == "http://retrieval-service:8000/"
    assert settings.retrieval_service_timeout_seconds == 3.0


def test_api_gateway_settings_include_dialog_service_defaults() -> None:
    settings = ApiGatewaySettings()

    assert str(settings.dialog_service_url) == "http://dialog-service:8000/"
    assert settings.dialog_service_timeout_seconds == 5.0


def test_api_gateway_settings_read_prefixed_analysis_service_env(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("API_GATEWAY_ANALYSIS_SERVICE_URL", "http://localhost:9000")
    monkeypatch.setenv("API_GATEWAY_ANALYSIS_SERVICE_TIMEOUT_SECONDS", "4.5")

    settings = ApiGatewaySettings()

    assert str(settings.analysis_service_url) == "http://localhost:9000/"
    assert settings.analysis_service_timeout_seconds == 4.5


def test_api_gateway_settings_read_prefixed_retrieval_service_env(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("API_GATEWAY_RETRIEVAL_SERVICE_URL", "http://localhost:9100")
    monkeypatch.setenv("API_GATEWAY_RETRIEVAL_SERVICE_TIMEOUT_SECONDS", "5.5")

    settings = ApiGatewaySettings()

    assert str(settings.retrieval_service_url) == "http://localhost:9100/"
    assert settings.retrieval_service_timeout_seconds == 5.5


def test_api_gateway_settings_read_prefixed_dialog_service_env(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("API_GATEWAY_DIALOG_SERVICE_URL", "http://localhost:9200")
    monkeypatch.setenv("API_GATEWAY_DIALOG_SERVICE_TIMEOUT_SECONDS", "6.5")

    settings = ApiGatewaySettings()

    assert str(settings.dialog_service_url) == "http://localhost:9200/"
    assert settings.dialog_service_timeout_seconds == 6.5
