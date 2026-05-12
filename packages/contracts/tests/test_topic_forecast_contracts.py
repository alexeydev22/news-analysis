from economic_news_contracts.analysis import (
    EnqueueTopicForecastJobResponse,
    ImpactLabel,
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


def test_topic_forecast_contracts_validate_payloads() -> None:
    news = TopicForecastNewsItemResponse(
        id="news-1",
        title="GDP grows",
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
        forecast=(
            "Вероятно положительное влияние. "
            "Это аналитическая оценка, не финансовая рекомендация."
        ),
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
    assert response.model_reports[0].model_name == "tfidf-logreg"
    assert response.model_reports[0].topics[0].topic_id == "topic-1"
    assert job.status == TopicForecastJobStatus.SUCCEEDED
