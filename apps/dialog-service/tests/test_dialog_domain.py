from typing import Any, cast

import pytest
from dialog_service.domain.errors import EmptyDialogTextError
from dialog_service.domain.model import DialogContextItem, DialogGeneration, DialogQuestion


def test_dialog_question_trims_value() -> None:
    question = DialogQuestion("  Что значит рост ВВП?  ")

    assert question.value == "Что значит рост ВВП?"


def test_dialog_question_rejects_empty_value() -> None:
    with pytest.raises(EmptyDialogTextError):
        DialogQuestion("   ")


def test_dialog_context_item_copies_metadata_to_immutable_mapping() -> None:
    metadata = {"sector": "macro"}
    item = DialogContextItem(
        id="news-1",
        title="GDP grows",
        text="GDP grew by 2 percent.",
        source="demo",
        score=0.75,
        metadata=metadata,
    )
    metadata["sector"] = "changed"

    assert item.metadata == {"sector": "macro"}
    with pytest.raises(TypeError):
        cast(dict[str, Any], item.metadata)["sector"] = "changed"


def test_dialog_generation_rejects_empty_answer() -> None:
    with pytest.raises(EmptyDialogTextError):
        DialogGeneration(answer=" ", used_context_ids=[], model_name="template")
