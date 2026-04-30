from economic_news_framework.settings import BaseServiceSettings
from pydantic import AnyHttpUrl
from pydantic_settings import SettingsConfigDict


class ApiGatewaySettings(BaseServiceSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        env_prefix="API_GATEWAY_",
        extra="ignore",
    )

    service_name: str = "api-gateway"
    version: str = "0.1.0"
    analysis_service_url: AnyHttpUrl = AnyHttpUrl("http://analysis-service:8000")
    analysis_service_timeout_seconds: float = 3.0
    retrieval_service_url: AnyHttpUrl = AnyHttpUrl("http://retrieval-service:8000")
    retrieval_service_timeout_seconds: float = 3.0
    dialog_service_url: AnyHttpUrl = AnyHttpUrl("http://dialog-service:8000")
    dialog_service_timeout_seconds: float = 5.0
