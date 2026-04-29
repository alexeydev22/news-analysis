from api_gateway.application.ports import (
    AnalysisClient,
    RetrievalClient,
    StaticVersionProvider,
    VersionProvider,
)
from api_gateway.application.use_cases import (
    AnalyzeNewsUseCase,
    IndexNewsUseCase,
    SearchNewsUseCase,
)
from api_gateway.infrastructure.analysis_client import ZaprosAnalysisClient
from api_gateway.infrastructure.retrieval_client import ZaprosRetrievalClient
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
    def retrieval_client(self, settings: ApiGatewaySettings) -> RetrievalClient:
        return ZaprosRetrievalClient(
            base_url=str(settings.retrieval_service_url),
            timeout_seconds=settings.retrieval_service_timeout_seconds,
        )

    @provide(scope=Scope.APP)
    def analyze_news_use_case(self, analysis_client: AnalysisClient) -> AnalyzeNewsUseCase:
        return AnalyzeNewsUseCase(analysis_client)

    @provide(scope=Scope.APP)
    def index_news_use_case(self, retrieval_client: RetrievalClient) -> IndexNewsUseCase:
        return IndexNewsUseCase(retrieval_client)

    @provide(scope=Scope.APP)
    def search_news_use_case(self, retrieval_client: RetrievalClient) -> SearchNewsUseCase:
        return SearchNewsUseCase(retrieval_client)


def create_container():
    return make_async_container(ApiGatewayProvider(), FastapiProvider())
