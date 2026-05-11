from analysis_service.application.topic_forecast import build_topic_forecast
from economic_news_contracts.analysis import AnalysisModelName, ImpactLabel
from economic_news_contracts.dialog import DialogImpactSummary
from economic_news_contracts.retrieval import (
    IndexedNewsDocument,
    NewsNeighbor,
    NewsNeighborGroup,
)


def _document(news_id: str, title: str) -> IndexedNewsDocument:
    return IndexedNewsDocument(
        id=news_id,
        title=title,
        text=f"{title}. Подробности события.",
        source="test-source",
    )


def _impact(
    news_id: str,
    impact: ImpactLabel,
    confidence: float = 0.8,
) -> DialogImpactSummary:
    return DialogImpactSummary(
        news_id=news_id,
        model_name=AnalysisModelName.TFIDF_LOGREG,
        impact=impact,
        confidence=confidence,
        explanation="Тестовая оценка влияния",
    )


def _neighbor(document: IndexedNewsDocument, score: float) -> NewsNeighbor:
    return NewsNeighbor(
        id=document.id,
        title=document.title,
        text=document.text,
        source=document.source,
        published_at=document.published_at,
        metadata=document.metadata,
        score=score,
    )


def test_build_topic_forecast_groups_neighbors_and_aggregates_impact() -> None:
    documents = [
        _document("news-1", "Экспорт растет"),
        _document("news-2", "Поставки ускоряются"),
        _document("news-3", "Спрос снижается"),
    ]
    neighbor_groups = [
        NewsNeighborGroup(
            document_id="news-1",
            neighbors=[_neighbor(documents[1], score=0.88)],
        ),
    ]
    impacts_by_news_id = {
        "news-1": _impact("news-1", ImpactLabel.POSITIVE, confidence=0.9),
        "news-2": _impact("news-2", ImpactLabel.POSITIVE, confidence=0.7),
        "news-3": _impact("news-3", ImpactLabel.NEGATIVE, confidence=0.5),
    }

    topics = build_topic_forecast(
        documents=documents,
        neighbor_groups=neighbor_groups,
        impacts_by_news_id=impacts_by_news_id,
        min_neighbor_score=0.8,
        max_topic_size=5,
    )

    assert len(topics) == 2
    topic = topics[0]
    assert topic.overall_impact == ImpactLabel.POSITIVE
    assert topic.positive_count == 2
    assert "не финансовая рекомендация" in topic.forecast
    assert {news.id for news in topic.news} == {"news-1", "news-2"}


def test_build_topic_forecast_ignores_neighbors_below_threshold() -> None:
    documents = [
        _document("news-1", "Нефть дорожает"),
        _document("news-2", "Транспортные расходы растут"),
    ]
    neighbor_groups = [
        NewsNeighborGroup(
            document_id="news-1",
            neighbors=[_neighbor(documents[1], score=0.79)],
        ),
    ]

    topics = build_topic_forecast(
        documents=documents,
        neighbor_groups=neighbor_groups,
        impacts_by_news_id={
            "news-1": _impact("news-1", ImpactLabel.POSITIVE),
            "news-2": _impact("news-2", ImpactLabel.NEGATIVE),
        },
        min_neighbor_score=0.8,
        max_topic_size=5,
    )

    assert [{news.id for news in topic.news} for topic in topics] == [
        {"news-1"},
        {"news-2"},
    ]


def test_build_topic_forecast_deduplicates_documents_and_tie_is_neutral() -> None:
    documents = [
        _document("news-1", "Банки снижают ставки"),
        _document("news-2", "Кредитование бизнеса растет"),
        _document("news-3", "Инфляционные риски сохраняются"),
    ]
    neighbor_groups = [
        NewsNeighborGroup(
            document_id="news-1",
            neighbors=[_neighbor(documents[1], score=0.9)],
        ),
        NewsNeighborGroup(
            document_id="news-3",
            neighbors=[_neighbor(documents[1], score=0.95)],
        ),
    ]

    topics = build_topic_forecast(
        documents=documents,
        neighbor_groups=neighbor_groups,
        impacts_by_news_id={
            "news-1": _impact("news-1", ImpactLabel.POSITIVE),
            "news-2": _impact("news-2", ImpactLabel.NEGATIVE),
            "news-3": _impact("news-3", ImpactLabel.NEUTRAL),
        },
        min_neighbor_score=0.8,
        max_topic_size=2,
    )

    topic_news_ids = [{news.id for news in topic.news} for topic in topics]
    assert topic_news_ids == [{"news-1", "news-2"}, {"news-3"}]
    assert topics[0].overall_impact == ImpactLabel.NEUTRAL


def test_build_topic_forecast_uses_only_available_predictions_for_vote() -> None:
    documents = [
        _document("news-1", "Промышленность ускоряется"),
        _document("news-2", "Заказы заводов растут"),
        _document("news-3", "Компании обновляют прогноз"),
    ]
    neighbor_groups = [
        NewsNeighborGroup(
            document_id="news-1",
            neighbors=[
                _neighbor(documents[1], score=0.9),
                _neighbor(documents[2], score=0.91),
            ],
        ),
    ]

    topics = build_topic_forecast(
        documents=documents,
        neighbor_groups=neighbor_groups,
        impacts_by_news_id={"news-1": _impact("news-1", ImpactLabel.POSITIVE)},
        min_neighbor_score=0.8,
        max_topic_size=5,
    )

    assert topics[0].overall_impact == ImpactLabel.POSITIVE
    assert topics[0].positive_count == 1
    assert topics[0].neutral_count == 0


def test_build_topic_forecast_empty_predictions_are_neutral() -> None:
    topics = build_topic_forecast(
        documents=[_document("news-1", "Индекс деловой активности стабилен")],
        neighbor_groups=[],
        impacts_by_news_id={},
        min_neighbor_score=0.8,
        max_topic_size=5,
    )

    assert topics[0].overall_impact == ImpactLabel.NEUTRAL
    assert topics[0].positive_count == 0
    assert topics[0].neutral_count == 0
    assert topics[0].negative_count == 0
