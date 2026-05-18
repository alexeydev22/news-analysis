from typing import Any

from dishka import Provider, Scope, make_async_container, provide
from dishka.integrations.fastapi import FastapiProvider

from dialog_service.application.ports import DialogGenerator
from dialog_service.application.use_cases import GenerateDialogAnswer
from dialog_service.infrastructure.fallback_generator import FallbackDialogGenerator
from dialog_service.infrastructure.llm_generator import LlmDialogGenerator
from dialog_service.infrastructure.prompt_builder import DialogPromptBuilder
from dialog_service.infrastructure.template_generator import TemplateDialogGenerator
from dialog_service.main.settings import DialogGeneratorKind, DialogServiceSettings


class DialogServiceProvider(Provider):
    def __init__(self, settings: DialogServiceSettings | None = None) -> None:
        super().__init__()
        self._settings = settings

    @provide(scope=Scope.APP)
    def settings(self) -> DialogServiceSettings:
        return self._settings or DialogServiceSettings()

    @provide(scope=Scope.APP)
    def dialog_prompt_builder(self) -> DialogPromptBuilder:
        return DialogPromptBuilder()

    @provide(scope=Scope.APP, provides=DialogGenerator)
    def dialog_generator(
        self,
        settings: DialogServiceSettings,
        prompt_builder: DialogPromptBuilder,
    ) -> DialogGenerator:
        if settings.generator_kind == DialogGeneratorKind.LLM:
            primary = LlmDialogGenerator(
                base_url=str(settings.llm_base_url),
                model_name=settings.llm_model,
                timeout_seconds=settings.llm_timeout_seconds,
                temperature=settings.llm_temperature,
                max_tokens=settings.llm_max_tokens,
                prompt_builder=prompt_builder,
            )
            return FallbackDialogGenerator(
                primary=primary,
                fallback=TemplateDialogGenerator(model_name=settings.generator_name),
            )
        if settings.generator_kind == DialogGeneratorKind.GEMINI:
            primary = LlmDialogGenerator(
                base_url=str(settings.gemini_base_url),
                model_name=settings.gemini_model,
                timeout_seconds=settings.llm_timeout_seconds,
                temperature=settings.llm_temperature,
                max_tokens=settings.llm_max_tokens,
                api_key=(
                    settings.gemini_api_key.get_secret_value()
                    if settings.gemini_api_key
                    else None
                ),
                generator_kind="gemini",
                prompt_builder=prompt_builder,
            )
            return FallbackDialogGenerator(
                primary=primary,
                fallback=TemplateDialogGenerator(model_name=settings.generator_name),
            )
        return TemplateDialogGenerator(model_name=settings.generator_name)

    @provide(scope=Scope.APP)
    def generate_dialog_answer(self, generator: DialogGenerator) -> GenerateDialogAnswer:
        return GenerateDialogAnswer(generator)


def create_container(settings: DialogServiceSettings | None = None) -> Any:
    return make_async_container(DialogServiceProvider(settings), FastapiProvider())
