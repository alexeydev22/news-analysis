from api_gateway.application.ports import StaticVersionProvider, VersionProvider
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


def create_container():
    return make_async_container(ApiGatewayProvider(), FastapiProvider())
