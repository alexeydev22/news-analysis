import pytest
from api_gateway.application.use_cases import AnalyzeNewsUseCase
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


def test_api_gateway_settings_include_analysis_service_defaults() -> None:
    settings = ApiGatewaySettings()

    assert str(settings.analysis_service_url) == "http://analysis-service:8000/"
    assert settings.analysis_service_timeout_seconds == 3.0
