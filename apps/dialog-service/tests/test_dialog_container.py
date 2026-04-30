import pytest
from dialog_service.application.use_cases import GenerateDialogAnswer
from dialog_service.main.container import create_container
from dialog_service.main.settings import DialogGeneratorKind, DialogServiceSettings
from dishka import AsyncContainer


def test_dialog_settings_defaults_and_env_prefix(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("DIALOG_GENERATOR_NAME", "custom-generator")

    settings = DialogServiceSettings()

    assert settings.service_name == "dialog-service"
    assert settings.generator_name == "custom-generator"


def test_dialog_settings_include_llm_defaults() -> None:
    settings = DialogServiceSettings()

    assert settings.generator_kind == DialogGeneratorKind.TEMPLATE
    assert settings.generator_name == "template-dialog-generator"
    assert str(settings.llm_base_url) == "http://localhost:8080/"
    assert settings.llm_model == "Qwen3-0.6B-Instruct-GGUF"
    assert settings.llm_timeout_seconds == 30.0
    assert settings.llm_temperature == 0.2
    assert settings.llm_max_tokens == 512


def test_dialog_settings_read_prefixed_llm_env(
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
