import pytest
from dialog_service.application.use_cases import GenerateDialogAnswer
from dialog_service.main.container import create_container
from dialog_service.main.settings import DialogServiceSettings
from dishka import AsyncContainer


def test_dialog_settings_defaults_and_env_prefix(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("DIALOG_GENERATOR_NAME", "custom-generator")

    settings = DialogServiceSettings()

    assert settings.service_name == "dialog-service"
    assert settings.generator_name == "custom-generator"


@pytest.mark.asyncio
async def test_container_resolves_generate_dialog_answer() -> None:
    container: AsyncContainer = create_container()

    try:
        use_case = await container.get(GenerateDialogAnswer)
    finally:
        await container.close()

    assert isinstance(use_case, GenerateDialogAnswer)
