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
