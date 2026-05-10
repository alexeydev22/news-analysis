import sys
from pathlib import Path

import pytest

sys.path.append(str(Path(__file__).resolve().parents[1]))

from tools.prepare_fnspid import label_impact_from_text


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("Company profit rises and outlook improves after strong demand", "positive"),
        ("Shares fall as losses widen and demand weakens", "negative"),
        ("The company announced a board meeting on Monday", "neutral"),
        ("Revenue rises but inflation risks increase and demand weakens", "neutral"),
    ],
)
def test_label_impact_from_text_uses_economic_markers(text: str, expected: str) -> None:
    assert label_impact_from_text(text) == expected
