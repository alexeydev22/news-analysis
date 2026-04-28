from economic_news_framework.settings import BaseServiceSettings


class ApiGatewaySettings(BaseServiceSettings):
    service_name: str = "api-gateway"
    version: str = "0.1.0"
