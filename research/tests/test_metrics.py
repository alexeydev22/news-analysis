from economic_news_research.metrics import ClassificationMetrics, compute_classification_metrics


def test_compute_classification_metrics_returns_macro_scores() -> None:
    metrics = compute_classification_metrics(
        y_true=["positive", "negative", "neutral", "positive"],
        y_pred=["positive", "neutral", "neutral", "positive"],
        labels=["negative", "neutral", "positive"],
    )

    assert isinstance(metrics, ClassificationMetrics)
    assert metrics.accuracy == 0.75
    assert 0 <= metrics.macro_precision <= 1
    assert 0 <= metrics.macro_recall <= 1
    assert 0 <= metrics.macro_f1 <= 1
    assert metrics.confusion_matrix.shape == (3, 3)


def test_compute_classification_metrics_includes_per_class_metrics() -> None:
    metrics = compute_classification_metrics(
        y_true=["negative", "neutral", "positive", "positive"],
        y_pred=["negative", "positive", "positive", "neutral"],
        labels=["negative", "neutral", "positive"],
    )

    assert metrics.per_class["negative"]["recall"] == 1.0
    assert metrics.per_class["neutral"]["recall"] == 0.0
    assert 0.0 <= metrics.per_class["positive"]["f1"] <= 1.0
