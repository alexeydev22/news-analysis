from pathlib import Path

import pytest
from dialog_service.application.ports import DialogGenerator
from dialog_service.application.use_cases import GenerateDialogAnswer
from dialog_service.infrastructure.llm_generator import LlmDialogGenerator
from dialog_service.infrastructure.template_generator import TemplateDialogGenerator
from dialog_service.main.container import create_container
from dialog_service.main.settings import DialogGeneratorKind, DialogServiceSettings
from dishka import AsyncContainer
from pydantic import AnyHttpUrl, ValidationError

_DIALOG_ENV_KEYS = (
    "DIALOG_SERVICE_NAME",
    "DIALOG_VERSION",
    "DIALOG_GENERATOR_KIND",
    "DIALOG_GENERATOR_NAME",
    "DIALOG_LLM_BASE_URL",
    "DIALOG_LLM_MODEL",
    "DIALOG_LLM_TIMEOUT_SECONDS",
    "DIALOG_LLM_TEMPERATURE",
    "DIALOG_LLM_MAX_TOKENS",
)


@pytest.fixture
def isolate_dialog_settings(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.chdir(tmp_path)
    for key in _DIALOG_ENV_KEYS:
        monkeypatch.delenv(key, raising=False)


def test_dialog_settings_defaults_and_env_prefix(
    isolate_dialog_settings: None,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("DIALOG_GENERATOR_NAME", "custom-generator")

    settings = DialogServiceSettings()

    assert settings.service_name == "dialog-service"
    assert settings.generator_name == "custom-generator"


def test_dialog_settings_include_llm_defaults(isolate_dialog_settings: None) -> None:
    settings = DialogServiceSettings()

    assert settings.generator_kind == DialogGeneratorKind.TEMPLATE
    assert settings.generator_name == "template-dialog-generator"
    assert str(settings.llm_base_url) == "http://localhost:8080/"
    assert settings.llm_model == "Qwen3-0.6B-Instruct-GGUF"
    assert settings.llm_timeout_seconds == 30.0
    assert settings.llm_temperature == 0.2
    assert settings.llm_max_tokens == 512


def test_dialog_settings_reject_blank_llm_model(isolate_dialog_settings: None) -> None:
    with pytest.raises(ValidationError, match="llm_model must not be blank"):
        DialogServiceSettings(llm_model="   ")


def test_dialog_settings_trim_llm_model(isolate_dialog_settings: None) -> None:
    settings = DialogServiceSettings(llm_model="  qwen3-0.6b  ")

    assert settings.llm_model == "qwen3-0.6b"


def test_dialog_settings_reject_invalid_generator_kind(
    isolate_dialog_settings: None,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("DIALOG_GENERATOR_KIND", "invalid")

    with pytest.raises(ValidationError):
        DialogServiceSettings()


def test_dialog_settings_reject_non_positive_llm_timeout(
    isolate_dialog_settings: None,
) -> None:
    with pytest.raises(ValidationError):
        DialogServiceSettings(llm_timeout_seconds=0)


def test_dialog_settings_reject_llm_temperature_above_max(
    isolate_dialog_settings: None,
) -> None:
    with pytest.raises(ValidationError):
        DialogServiceSettings(llm_temperature=2.1)


def test_dialog_settings_reject_non_positive_llm_max_tokens(
    isolate_dialog_settings: None,
) -> None:
    with pytest.raises(ValidationError):
        DialogServiceSettings(llm_max_tokens=0)


def test_dialog_settings_read_prefixed_llm_env(
    isolate_dialog_settings: None,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("DIALOG_GENERATOR_KIND", "llm")
    monkeypatch.setenv("DIALOG_GENERATOR_NAME", "local-qwen")
    monkeypatch.setenv("DIALOG_LLM_BASE_URL", "http://llm.local:8080")
    monkeypatch.setenv("DIALOG_LLM_MODEL", "qwen3-0.6b")
    monkeypatch.setenv("DIALOG_LLM_TIMEOUT_SECONDS", "45")
    monkeypatch.setenv("DIALOG_LLM_TEMPERATURE", "0.1")
    monkeypatch.setenv("DIALOG_LLM_MAX_TOKENS", "384")

    settings = DialogServiceSettings()

    assert settings.generator_kind == DialogGeneratorKind.LLM
    assert settings.generator_name == "local-qwen"
    assert str(settings.llm_base_url) == "http://llm.local:8080/"
    assert settings.llm_model == "qwen3-0.6b"
    assert settings.llm_timeout_seconds == 45.0
    assert settings.llm_temperature == 0.1
    assert settings.llm_max_tokens == 384


@pytest.mark.asyncio
async def test_container_resolves_generate_dialog_answer() -> None:
    container: AsyncContainer = create_container()

    try:
        use_case = await container.get(GenerateDialogAnswer)
    finally:
        await container.close()

    assert isinstance(use_case, GenerateDialogAnswer)


@pytest.mark.asyncio
async def test_container_resolves_template_generator_for_template_mode(
    isolate_dialog_settings: None,
) -> None:
    settings = DialogServiceSettings(
        generator_kind=DialogGeneratorKind.TEMPLATE,
        generator_name="template-generator",
    )
    container: AsyncContainer = create_container(settings)

    try:
        generator = await container.get(DialogGenerator)
    finally:
        await container.close()

    assert isinstance(generator, TemplateDialogGenerator)


@pytest.mark.asyncio
async def test_container_resolves_llm_generator_for_llm_mode(
    isolate_dialog_settings: None,
) -> None:
    settings = DialogServiceSettings(
        generator_kind=DialogGeneratorKind.LLM,
        llm_base_url=AnyHttpUrl("http://llm.local:8080"),
        llm_model="qwen3-0.6b",
        llm_timeout_seconds=45.0,
        llm_temperature=0.1,
        llm_max_tokens=384,
    )
    container: AsyncContainer = create_container(settings)

    try:
        generator = await container.get(DialogGenerator)
    finally:
        await container.close()

    assert isinstance(generator, LlmDialogGenerator)
