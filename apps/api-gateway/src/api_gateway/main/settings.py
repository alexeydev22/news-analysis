from economic_news_framework.settings import BaseServiceSettings
from pydantic import AnyHttpUrl


class ApiGatewaySettings(BaseServiceSettings):
    service_name: str = "api-gateway"
    version: str = "0.1.0"
    analysis_service_url: AnyHttpUrl = AnyHttpUrl("http://analysis-service:8000")
    analysis_service_timeout_seconds: float = 3.0
