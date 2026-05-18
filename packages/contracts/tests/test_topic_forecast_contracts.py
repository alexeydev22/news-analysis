from economic_news_contracts.analysis import (
    EnqueueTopicForecastJobResponse,
    ImpactLabel,
    MlReportResponse,
    TopicForecastItemResponse,
    TopicForecastJobResponse,
    TopicForecastJobStatus,
    TopicForecastModelReportResponse,
    TopicForecastNewsItemResponse,
    TopicForecastResponse,
)
from economic_news_contracts.retrieval import (
    FindNeighborsRequest,
    FindNeighborsResponse,
    IndexedNewsDocument,
    ListIndexedDocumentsResponse,
    NewsNeighbor,
    NewsNeighborGroup,
)


def test_retrieval_neighbor_contracts_validate_payloads() -> None:
    document = IndexedNewsDocument(
        id="news-1",
        title="Inflation slows",
        text="Inflation slowed for the second month",
        source="FNSPID",
    )
    request = FindNeighborsRequest(document_ids=["news-1"], limit=3)
    response = FindNeighborsResponse(
        groups=[
            NewsNeighborGroup(
                document_id="news-1",
                neighbors=[
                    NewsNeighbor(
                        id="news-2",
                        score=0.87,
                        title="Prices cool",
                        text="Price pressure eased",
                        source="FNSPID",
                    ),
                ],
            ),
        ],
    )

    assert ListIndexedDocumentsResponse(documents=[document]).documents[0].id == "news-1"
    assert request.limit == 3
    assert response.groups[0].neighbors[0].score == 0.87


def test_ml_report_contract_validates_training_limits_and_label_quality() -> None:
    response = MlReportResponse.model_validate(
        {
            "generated_at": "2026-05-12T10:00:00Z",
            "dataset": {
                "path": "data/raw/news_impact.csv",
                "row_count": 50_000,
                "class_distribution": {
                    "positive": 20_000,
                    "neutral": 18_000,
                    "negative": 12_000,
                },
                "label_quality": {
                    "label_source": "generated",
                    "low_margin_count": 42,
                    "average_margin": 0.74,
                },
            },
            "training": {
                "classic_max_rows": 20_000,
                "embedding_max_rows": 5_000,
                "transformer_max_rows": 5_000,
            },
            "models": [
                {
                    "model_name": "tfidf-logreg",
                    "validation_accuracy": 0.91,
                    "validation_macro_f1": 0.89,
                    "test_accuracy": 0.9,
                    "test_macro_f1": 0.88,
                    "inference_seconds_per_sample": 0.004,
                    "confusion_matrix": {
                        "labels": ["positive", "neutral", "negative"],
                        "matrix": [
                            [42, 5, 3],
                            [4, 38, 3],
                            [2, 3, 20],
                        ],
                    },
                    "per_class": {
                        "positive": {"precision": 0.875, "recall": 0.84, "f1": 0.875},
                    },
                },
            ],
            "best_model": None,
            "top_features": {},
        },
    )

    assert response.training.classic_max_rows == 20_000
    assert response.training.embedding_max_rows == 5_000
    assert response.training.transformer_max_rows == 5_000
    assert response.dataset.label_quality is not None
    assert response.dataset.label_quality.label_source == "generated"
    assert response.dataset.label_quality.low_margin_count == 42
    assert response.dataset.label_quality.average_margin == 0.74


def test_topic_forecast_contracts_validate_payloads() -> None:
    news = TopicForecastNewsItemResponse(
        id="news-1",
        title="GDP grows",
        text="GDP expanded faster than expected while consumer prices cooled.",
        source="FNSPID",
        impact=ImpactLabel.POSITIVE,
        score=0.91,
    )
    topic = TopicForecastItemResponse(
        topic_id="topic-1",
        title="GDP growth",
        summary="Several news items point to stronger growth.",
        overall_impact=ImpactLabel.POSITIVE,
        confidence=0.75,
        positive_count=2,
        neutral_count=1,
        negative_count=0,
        forecast="Вероятно положительное влияние при сохранении текущих факторов.",
        arguments=["Доля positive-сигналов выше остальных."],
        risks=["Сигналы могут измениться после новых данных."],
        news=[news],
    )
    model_report = TopicForecastModelReportResponse(
        model_name="tfidf-logreg",
        topics=[topic],
    )
    response = TopicForecastResponse(
        generated_at="2026-05-11T10:00:00Z",
        topics=[topic],
        model_reports=[model_report],
    )
    job = TopicForecastJobResponse(
        job_id="job-1",
        status=TopicForecastJobStatus.SUCCEEDED,
        report_path="reports/topics/topic-forecast.json",
    )

    assert EnqueueTopicForecastJobResponse(job_id="job-1").status == TopicForecastJobStatus.QUEUED
    assert response.topics[0].overall_impact == ImpactLabel.POSITIVE
    assert response.topics[0].news[0].text == (
        "GDP expanded faster than expected while consumer prices cooled."
    )
    assert response.model_reports[0].model_name == "tfidf-logreg"
    assert response.model_reports[0].topics[0].topic_id == "topic-1"
    assert job.status == TopicForecastJobStatus.SUCCEEDED
