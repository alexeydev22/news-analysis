from typing import Any

from dishka import Provider, Scope, make_async_container, provide
from dishka.integrations.fastapi import FastapiProvider

from dialog_service.application.ports import DialogGenerator
from dialog_service.application.use_cases import GenerateDialogAnswer
from dialog_service.infrastructure.template_generator import TemplateDialogGenerator
from dialog_service.main.settings import DialogServiceSettings


class DialogServiceProvider(Provider):
    def __init__(self, settings: DialogServiceSettings | None = None) -> None:
        super().__init__()
        self._settings = settings

    @provide(scope=Scope.APP)
    def settings(self) -> DialogServiceSettings:
        return self._settings or DialogServiceSettings()

    @provide(scope=Scope.APP, provides=DialogGenerator)
    def dialog_generator(self, settings: DialogServiceSettings) -> DialogGenerator:
        return TemplateDialogGenerator(model_name=settings.generator_name)

    @provide(scope=Scope.APP)
    def generate_dialog_answer(self, generator: DialogGenerator) -> GenerateDialogAnswer:
        return GenerateDialogAnswer(generator)


def create_container(settings: DialogServiceSettings | None = None) -> Any:
    return make_async_container(DialogServiceProvider(settings), FastapiProvider())
