from __future__ import annotations

import re

POSITIVE_MARKERS = frozenset(
    {
        "beat",
        "beats",
        "gain",
        "gains",
        "grow",
        "grows",
        "growth",
        "improve",
        "improves",
        "increase",
        "increases",
        "profit",
        "profits",
        "raise",
        "raises",
        "rise",
        "rises",
        "strong demand",
        "upgrade",
        "upgrades",
    },
)
NEGATIVE_MARKERS = frozenset(
    {
        "decline",
        "declines",
        "drop",
        "drops",
        "fall",
        "falls",
        "inflation risks",
        "loss",
        "losses",
        "recession",
        "risk",
        "risks",
        "slowdown",
        "weak demand",
        "weaken",
        "weakens",
    },
)


def _marker_score(text: str, markers: frozenset[str]) -> int:
    matched_spans: list[tuple[int, int]] = []

    for marker in sorted(markers, key=len, reverse=True):
        pattern = rf"\b{re.escape(marker)}\b"
        for match in re.finditer(pattern, text):
            span = match.span()
            if any(start < span[1] and span[0] < end for start, end in matched_spans):
                continue
            matched_spans.append(span)

    return len(matched_spans)


def label_impact_from_text(text: str) -> str:
    normalized_text = text.lower()
    positive_score = _marker_score(normalized_text, POSITIVE_MARKERS)
    negative_score = _marker_score(normalized_text, NEGATIVE_MARKERS)

    if positive_score > negative_score:
        return "positive"
    if negative_score > positive_score:
        return "negative"
    return "neutral"
