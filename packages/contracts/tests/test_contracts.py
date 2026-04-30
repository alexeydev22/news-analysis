import pytest
from economic_news_contracts.analysis import (
    AnalysisModelName,
    AnalyzeNewsRequest,
    AnalyzeNewsResponse,
    ImpactLabel,
)
from economic_news_contracts.chat import ChatRequest, ChatResponse
from economic_news_contracts.dialog import (
    DialogContextNews,
    DialogImpactSummary,
    GenerateDialogRequest,
    GenerateDialogResponse,
)
from economic_news_contracts.events import EventEnvelope
from economic_news_contracts.health import HealthResponse
from economic_news_contracts.retrieval import (
    IndexNewsRequest,
    IndexNewsResponse,
    NewsDocumentPayload,
    SearchNewsRequest,
    SearchNewsResponse,
    SearchNewsResult,
)
from pydantic import ValidationError


def test_impact_label_values_are_stable() -> None:
    assert ImpactLabel.POSITIVE == "positive"
    assert ImpactLabel.NEUTRAL == "neutral"
    assert ImpactLabel.NEGATIVE == "negative"


def test_analysis_model_names_are_stable() -> None:
    assert AnalysisModelName.TFIDF_LOGREG == "tfidf-logreg"
    assert AnalysisModelName.EMBEDDING_LOGREG == "embedding-logreg"
    assert AnalysisModelName.TINY_TRANSFORMER_CLASSIFIER == "tiny-transformer-classifier"


def test_analyze_news_request_trims_text() -> None:
    request = AnalyzeNewsRequest(
        text="  Central bank keeps rates unchanged.  ",
        analysis_model=AnalysisModelName.TFIDF_LOGREG,
    )

    assert request.text == "Central bank keeps rates unchanged."
    assert request.analysis_model == AnalysisModelName.TFIDF_LOGREG


def test_analyze_news_response_serializes_model_and_impact() -> None:
    response = AnalyzeNewsResponse(
        model_name=AnalysisModelName.TFIDF_LOGREG,
        impact=ImpactLabel.NEUTRAL,
        confidence=None,
        explanation="Model classified the news text as neutral.",
        metadata={},
    )

    assert response.model_dump(mode="json") == {
        "model_name": "tfidf-logreg",
        "impact": "neutral",
        "confidence": None,
        "explanation": "Model classified the news text as neutral.",
        "metadata": {},
    }


def test_event_envelope_contains_type_and_payload() -> None:
    event = EventEnvelope(event_type="analysis.completed", payload={"article_id": "a-1"})

    assert event.event_type == "analysis.completed"
    assert event.payload == {"article_id": "a-1"}


def test_health_response_defaults_to_ok() -> None:
    response = HealthResponse(service="api-gateway")

    assert response.status == "ok"
    assert response.service == "api-gateway"


def test_news_document_payload_trims_required_text_fields() -> None:
    document = NewsDocumentPayload(
        id=" news-1 ",
        title="  Inflation slows  ",
        text="  Prices grew slower than expected.  ",
        source="  Reuters  ",
    )

    assert document.id == "news-1"
    assert document.title == "Inflation slows"
    assert document.text == "Prices grew slower than expected."
    assert document.source == "Reuters"


def test_index_news_request_requires_documents() -> None:
    request = IndexNewsRequest(
        documents=[
            NewsDocumentPayload(
                id="news-1",
                title="GDP grows",
                text="GDP grew by 2 percent.",
                source="demo",
            ),
        ],
    )

    assert len(request.documents) == 1


def test_search_news_request_trims_query_and_defaults_limit() -> None:
    request = SearchNewsRequest(query="  key rate decision  ")

    assert request.query == "key rate decision"
    assert request.limit == 5
    assert request.source is None


def test_search_news_response_serializes_results() -> None:
    response = SearchNewsResponse(
        results=[
            SearchNewsResult(
                id="news-1",
                score=0.91,
                title="GDP grows",
                text="GDP grew by 2 percent.",
                source="demo",
                metadata={"sector": "macro"},
            ),
        ],
    )

    assert response.model_dump(mode="json") == {
        "results": [
            {
                "id": "news-1",
                "score": 0.91,
                "title": "GDP grows",
                "text": "GDP grew by 2 percent.",
                "source": "demo",
                "published_at": None,
                "metadata": {"sector": "macro"},
            },
        ],
    }


def test_search_news_result_accepts_negative_cosine_score() -> None:
    result = SearchNewsResult(
        id="news-1",
        score=-0.25,
        title="GDP grows",
        text="GDP grew by 2 percent.",
        source="demo",
    )

    assert result.score == -0.25


def test_index_news_response_reports_collection_and_count() -> None:
    response = IndexNewsResponse(indexed_count=2, collection_name="economic_news")

    assert response.indexed_count == 2
    assert response.collection_name == "economic_news"


def test_news_document_payload_rejects_empty_required_text_fields() -> None:
    try:
        NewsDocumentPayload(
            id="news-1",
            title="   ",
            text="GDP grew by 2 percent.",
            source="demo",
        )
    except ValidationError:
        return

    raise AssertionError("Expected title validation error")


def test_search_news_request_rejects_empty_query() -> None:
    try:
        SearchNewsRequest(query="   ")
    except ValidationError:
        return

    raise AssertionError("Expected query validation error")


def test_search_news_request_limit_bounds_are_enforced() -> None:
    for limit in (0, 21):
        try:
            SearchNewsRequest(query="key rate decision", limit=limit)
        except ValidationError:
            continue

        raise AssertionError(f"Expected limit validation error for {limit}")


def test_generate_dialog_request_trims_question_and_serializes_context() -> None:
    request = GenerateDialogRequest(
        question="  Что значит рост ВВП?  ",
        context=[
            DialogContextNews(
                id="news-1",
                title="GDP grows",
                text="GDP grew by 2 percent.",
                source="demo",
                score=0.75,
            ),
        ],
        impact_summaries=[
            DialogImpactSummary(
                news_id="news-1",
                model_name=AnalysisModelName.TFIDF_LOGREG,
                impact=ImpactLabel.POSITIVE,
                confidence=0.82,
                explanation="Рост ВВП обычно поддерживает рынок.",
            ),
        ],
    )

    assert request.question == "Что значит рост ВВП?"
    assert request.language == "ru"
    assert request.model_dump(mode="json")["context"][0]["published_at"] is None


def test_generate_dialog_request_rejects_empty_question() -> None:
    with pytest.raises(ValueError, match="Question must not be empty"):
        GenerateDialogRequest(question="   ")


def test_generate_dialog_response_requires_answer_and_used_context() -> None:
    response = GenerateDialogResponse(
        answer="Рост ВВП выглядит позитивным фактором.",
        used_context_ids=["news-1"],
        model_name="template-dialog-generator",
        metadata={"context_count": 1},
    )

    assert response.answer == "Рост ВВП выглядит позитивным фактором."
    assert response.used_context_ids == ["news-1"]


def test_chat_request_trims_question_and_defaults_model() -> None:
    request = ChatRequest(question="  Что с инфляцией?  ")

    assert request.question == "Что с инфляцией?"
    assert request.analysis_model == AnalysisModelName.TFIDF_LOGREG
    assert request.limit == 5
    assert request.source is None


def test_chat_request_limit_bounds_are_enforced() -> None:
    with pytest.raises(ValueError):
        ChatRequest(question="Что с рынком?", limit=0)
    with pytest.raises(ValueError):
        ChatRequest(question="Что с рынком?", limit=21)


def test_chat_response_serializes_sources_and_summaries() -> None:
    source = DialogContextNews(
        id="news-1",
        title="GDP grows",
        text="GDP grew by 2 percent.",
        source="demo",
        score=0.75,
    )
    summary = DialogImpactSummary(
        news_id="news-1",
        model_name=AnalysisModelName.TFIDF_LOGREG,
        impact=ImpactLabel.POSITIVE,
        confidence=0.82,
        explanation="Позитивное влияние.",
    )
    response = ChatResponse(
        answer="Новость выглядит позитивной.",
        sources=[source],
        impact_summaries=[summary],
        analysis_model=AnalysisModelName.TFIDF_LOGREG,
        metadata={"used_context_count": 1},
    )

    assert response.model_dump(mode="json")["sources"][0]["id"] == "news-1"
    assert response.model_dump(mode="json")["impact_summaries"][0]["impact"] == "positive"
