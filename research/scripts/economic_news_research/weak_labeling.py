import re
from dataclasses import dataclass
from enum import StrEnum


class ImpactLabel(StrEnum):
    POSITIVE = "positive"
    NEUTRAL = "neutral"
    NEGATIVE = "negative"


POSITIVE_TERMS = frozenset(
    {
        "approval",
        "approved",
        "beat",
        "beats",
        "bullish",
        "gain",
        "gains",
        "grew",
        "grow",
        "grows",
        "growth",
        "higher",
        "improve",
        "improves",
        "profit",
        "profits",
        "record",
        "rise",
        "rises",
        "rose",
        "strong buy",
        "surge",
        "upgraded",
        "upside",
    },
)

NEGATIVE_TERMS = frozenset(
    {
        "bankruptcy",
        "bearish",
        "cut",
        "decline",
        "declines",
        "declined",
        "downgrade",
        "downgraded",
        "drop",
        "drops",
        "fall",
        "falls",
        "fell",
        "lawsuit",
        "loss",
        "losses",
        "lower",
        "miss",
        "misses",
        "recession",
        "risk",
        "risks",
        "weak",
        "warning",
        "warned",
    },
)


@dataclass(frozen=True)
class WeakImpactLabel:
    label: str
    positive_score: int
    negative_score: int
    margin: int


def infer_weak_impact(*, title: object, text: object) -> WeakImpactLabel:
    content = f"{title or ''} {text or ''}".lower()
    positive_score = _score_terms(content=content, terms=POSITIVE_TERMS)
    negative_score = _score_terms(content=content, terms=NEGATIVE_TERMS)
    margin = abs(positive_score - negative_score)
    if margin <= 1:
        label = ImpactLabel.NEUTRAL.value
    elif positive_score > negative_score:
        label = ImpactLabel.POSITIVE.value
    else:
        label = ImpactLabel.NEGATIVE.value
    return WeakImpactLabel(
        label=label,
        positive_score=positive_score,
        negative_score=negative_score,
        margin=margin,
    )


def _score_terms(*, content: str, terms: frozenset[str]) -> int:
    return sum(
        re.search(rf"\b{re.escape(term)}\b", content) is not None
        for term in terms
    )
