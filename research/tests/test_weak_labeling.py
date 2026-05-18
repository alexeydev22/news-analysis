from economic_news_research.weak_labeling import infer_weak_impact


def test_infer_weak_impact_returns_positive_with_margin() -> None:
    result = infer_weak_impact(
        title="Company reports profit growth",
        text="Revenue rose and earnings beat expectations.",
    )

    assert result.label == "positive"
    assert result.positive_score > result.negative_score
    assert result.margin >= 2


def test_infer_weak_impact_returns_negative_with_margin() -> None:
    result = infer_weak_impact(
        title="Company shares fall",
        text="Revenue declined and losses increased.",
    )

    assert result.label == "negative"
    assert result.negative_score > result.positive_score
    assert result.margin >= 2


def test_infer_weak_impact_returns_neutral_when_scores_are_close() -> None:
    result = infer_weak_impact(
        title="Company updates outlook",
        text="Revenue rose, but management warned about risks.",
    )

    assert result.label == "neutral"
    assert result.margin <= 1
