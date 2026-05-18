import pytest
from dialog_service.domain.errors import DialogGeneratorUnavailableError
from dialog_service.domain.model import (
    DialogContextItem,
    DialogGeneration,
    DialogImpactItem,
    DialogQuestion,
)
from dialog_service.infrastructure.fallback_generator import FallbackDialogGenerator


class FailingGenerator:
    async def generate(
        self,
        question: DialogQuestion,
        context: list[DialogContextItem],
        impact_summaries: list[DialogImpactItem],
        language: str,
    ) -> DialogGeneration:
        raise DialogGeneratorUnavailableError("provider rate limit")


class SuccessfulGenerator:
    async def generate(
        self,
        question: DialogQuestion,
        context: list[DialogContextItem],
        impact_summaries: list[DialogImpactItem],
        language: str,
    ) -> DialogGeneration:
        return DialogGeneration(
            answer="LLM answer",
            used_context_ids=[item.id for item in context],
            model_name="llm",
            metadata={"generator_kind": "llm"},
        )


class TemplateFallbackGenerator:
    async def generate(
        self,
        question: DialogQuestion,
        context: list[DialogContextItem],
        impact_summaries: list[DialogImpactItem],
        language: str,
    ) -> DialogGeneration:
        return DialogGeneration(
            answer="Template answer",
            used_context_ids=[item.id for item in context],
            model_name="template",
            metadata={"generator_kind": "template"},
        )


def dialog_context() -> list[DialogContextItem]:
    return [
        DialogContextItem(
            id="news-1",
            title="GDP grows",
            text="GDP grew by 2 percent.",
            source="demo",
            score=0.75,
        ),
    ]


@pytest.mark.asyncio
async def test_fallback_generator_uses_primary_when_available() -> None:
    generator = FallbackDialogGenerator(
        primary=SuccessfulGenerator(),
        fallback=TemplateFallbackGenerator(),
    )

    generation = await generator.generate(
        question=DialogQuestion("Что значит рост ВВП?"),
        context=dialog_context(),
        impact_summaries=[],
        language="ru",
    )

    assert generation.answer == "LLM answer"
    assert generation.metadata == {"generator_kind": "llm"}


@pytest.mark.asyncio
async def test_fallback_generator_returns_template_when_primary_is_unavailable() -> None:
    generator = FallbackDialogGenerator(
        primary=FailingGenerator(),
        fallback=TemplateFallbackGenerator(),
    )

    generation = await generator.generate(
        question=DialogQuestion("Что значит рост ВВП?"),
        context=dialog_context(),
        impact_summaries=[],
        language="ru",
    )

    assert generation.answer == "Template answer"
    assert generation.model_name == "template"
    assert generation.metadata == {
        "generator_kind": "template",
        "fallback_from": "llm",
        "fallback_reason": "DialogGeneratorUnavailableError",
    }
