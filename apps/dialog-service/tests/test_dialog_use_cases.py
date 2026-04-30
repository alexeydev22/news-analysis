import inspect

import pytest
from dialog_service.application.use_cases import GenerateDialogAnswer
from dialog_service.domain.model import DialogContextItem, DialogGeneration, DialogQuestion


class FakeGenerator:
    def __init__(self) -> None:
        self.question: str | None = None
        self.context_count: int | None = None
        self.language: str | None = None

    async def generate(self, question, context, impact_summaries, language):
        self.question = question.value
        self.context_count = len(context)
        self.language = language
        return DialogGeneration(
            answer="Рост ВВП выглядит позитивным фактором.",
            used_context_ids=[item.id for item in context],
            model_name="fake-generator",
            metadata={"language": language},
        )


def test_generate_dialog_answer_has_domain_boundary() -> None:
    signature = inspect.signature(GenerateDialogAnswer.execute)

    assert "request" not in signature.parameters
    assert list(signature.parameters) == [
        "self",
        "question",
        "context",
        "impact_summaries",
        "language",
    ]
    module = inspect.getmodule(GenerateDialogAnswer)
    assert module is not None
    assert "economic_news_contracts.dialog" not in inspect.getsource(module)


@pytest.mark.asyncio
async def test_generate_dialog_answer_delegates_to_generator() -> None:
    generator = FakeGenerator()
    use_case = GenerateDialogAnswer(generator)

    response = await use_case.execute(
        question=DialogQuestion("Что значит рост ВВП?"),
        context=[
            DialogContextItem(
                id="news-1",
                title="GDP grows",
                text="GDP grew by 2 percent.",
                source="demo",
                score=0.75,
            ),
        ],
        impact_summaries=[],
        language="ru",
    )

    assert generator.question == "Что значит рост ВВП?"
    assert generator.context_count == 1
    assert generator.language == "ru"
    assert response.answer == "Рост ВВП выглядит позитивным фактором."
    assert response.used_context_ids == ["news-1"]
    assert response.model_name == "fake-generator"
