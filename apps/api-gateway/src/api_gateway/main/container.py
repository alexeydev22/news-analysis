from api_gateway.application.ports import AnalysisClient, StaticVersionProvider, VersionProvider
from api_gateway.application.use_cases import AnalyzeNewsUseCase
from api_gateway.infrastructure.analysis_client import ZaprosAnalysisClient
from api_gateway.main.settings import ApiGatewaySettings
from dishka import Provider, Scope, make_async_container, provide
from dishka.integrations.fastapi import FastapiProvider


class ApiGatewayProvider(Provider):
    @provide(scope=Scope.APP)
    def settings(self) -> ApiGatewaySettings:
        return ApiGatewaySettings()

    @provide(scope=Scope.APP)
    def version_provider(self, settings: ApiGatewaySettings) -> VersionProvider:
        return StaticVersionProvider(settings.version)

    @provide(scope=Scope.APP)
    def analysis_client(self, settings: ApiGatewaySettings) -> AnalysisClient:
        return ZaprosAnalysisClient(
            base_url=str(settings.analysis_service_url),
            timeout_seconds=settings.analysis_service_timeout_seconds,
        )

    @provide(scope=Scope.APP)
    def analyze_news_use_case(self, analysis_client: AnalysisClient) -> AnalyzeNewsUseCase:
        return AnalyzeNewsUseCase(analysis_client)


def create_container():
    return make_async_container(ApiGatewayProvider(), FastapiProvider())
