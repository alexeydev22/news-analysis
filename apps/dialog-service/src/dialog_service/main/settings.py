from economic_news_framework.settings import BaseServiceSettings
from pydantic_settings import SettingsConfigDict


class DialogServiceSettings(BaseServiceSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        env_prefix="DIALOG_",
        extra="ignore",
    )

    service_name: str = "dialog-service"
    version: str = "0.1.0"
    generator_name: str = "template-dialog-generator"
