from economic_news_research.results import measure_prediction_time


def test_measure_prediction_time_returns_predictions_and_average_seconds() -> None:
    predictions, seconds = measure_prediction_time(
        predictor=lambda values: [value.upper() for value in values],
        values=["a", "b", "c"],
    )

    assert predictions == ["A", "B", "C"]
    assert seconds >= 0


def test_measure_prediction_time_handles_empty_values() -> None:
    predictions, seconds = measure_prediction_time(
        predictor=lambda values: [],
        values=[],
    )

    assert predictions == []
    assert seconds == 0
