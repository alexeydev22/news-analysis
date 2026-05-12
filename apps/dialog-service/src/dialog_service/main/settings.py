from enum import StrEnum

from economic_news_framework.settings import BaseServiceSettings
from pydantic import AnyHttpUrl, Field, SecretStr, field_validator
from pydantic_settings import SettingsConfigDict


class DialogGeneratorKind(StrEnum):
    TEMPLATE = "template"
    LLM = "llm"
    GROQ = "groq"


class DialogServiceSettings(BaseServiceSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        env_prefix="DIALOG_",
        extra="ignore",
    )

    service_name: str = "dialog-service"
    version: str = "0.1.0"
    generator_kind: DialogGeneratorKind = DialogGeneratorKind.TEMPLATE
    generator_name: str = "template-dialog-generator"
    llm_base_url: AnyHttpUrl = AnyHttpUrl("http://localhost:8080")
    llm_model: str = Field(default="Qwen3-0.6B-Instruct-GGUF", min_length=1)
    llm_timeout_seconds: float = Field(default=30.0, gt=0.0)
    llm_temperature: float = Field(default=0.2, ge=0.0, le=2.0)
    llm_max_tokens: int = Field(default=512, ge=1, le=4096)
    groq_base_url: AnyHttpUrl = AnyHttpUrl("https://api.groq.com/openai")
    groq_model: str = Field(default="qwen/qwen3-32b", min_length=1)
    groq_api_key: SecretStr | None = None

    @field_validator("llm_model", "groq_model")
    @classmethod
    def validate_model_name(cls, value: str) -> str:
        stripped_value = value.strip()
        if not stripped_value:
            msg = "model name must not be blank"
            raise ValueError(msg)
        return stripped_value

    @field_validator("groq_base_url")
    @classmethod
    def normalize_groq_base_url(cls, value: AnyHttpUrl) -> AnyHttpUrl:
        return AnyHttpUrl(f"{str(value).rstrip('/')}/")
