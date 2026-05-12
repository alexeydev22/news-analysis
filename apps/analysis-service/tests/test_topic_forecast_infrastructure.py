from pathlib import Path
from typing import Any, cast

import pytest
from analysis_service.application.use_cases import (
    EnqueueTopicForecastJob,
    GenerateTopicForecastReport,
    GetLatestTopicForecast,
    GetTopicForecastJob,
)
from analysis_service.domain.errors import TopicForecastJobNotFoundError
from analysis_service.domain.model import ImpactPrediction, NewsText
from analysis_service.infrastructure.topic_forecast_retrieval_client import (
    HttpTopicForecastRetrievalGateway,
    _make_zapros_client,
)
from analysis_service.infrastructure.topic_forecast_storage import JsonTopicForecastStorage
from economic_news_contracts.analysis import (
    AnalysisModelName,
    ImpactLabel,
    TopicForecastJobResponse,
    TopicForecastJobStatus,
    TopicForecastResponse,
)
from economic_news_contracts.retrieval import (
    IndexedNewsDocument,
    NewsNeighbor,
    NewsNeighborGroup,
)
from zapros import Response


class FakeZaprosClient:
    def __init__(self, responses: list[Response]) -> None:
        self._responses = responses
        self.get_calls: list[tuple[str, dict[str, list[str]]]] = []
        self.post_calls: list[tuple[str, dict[str, object]]] = []

    async def get(self, url: str, params: dict[str, list[str]]) -> Response:
        self.get_calls.append((url, params))
        return self._responses.pop(0)

    async def post(self, url: str, json: dict[str, object]) -> Response:
        self.post_calls.append((url, json))
        return self._responses.pop(0)


class StubTopicForecastTaskQueue:
    def __init__(self) -> None:
        self.job_id: str | None = None

    async def enqueue(self, *, job_id: str) -> None:
        self.job_id = job_id


class FakeTopicForecastRetrievalGateway:
    def __init__(self, documents: list[IndexedNewsDocument]) -> None:
        self.documents = documents
        self.document_limit: int | None = None
        self.neighbor_limit: int | None = None

    async def list_documents(self, *, limit: int) -> list[IndexedNewsDocument]:
        self.document_limit = limit
        return self.documents[:limit]

    async def find_neighbors(
        self,
        *,
        documents: list[IndexedNewsDocument],
        limit: int,
    ) -> list[NewsNeighborGroup]:
        self.neighbor_limit = limit
        if len(documents) < 2:
            return []
        return [
            NewsNeighborGroup(
                document_id=documents[0].id,
                neighbors=[
                    NewsNeighbor(
                        id=documents[1].id,
                        title=documents[1].title,
                        text=documents[1].text,
                        source=documents[1].source,
                        published_at=documents[1].published_at,
                        metadata=documents[1].metadata,
                        score=0.91,
                    ),
                ],
            ),
        ]


class FailingTopicForecastRetrievalGateway:
    async def list_documents(self, *, limit: int) -> list[IndexedNewsDocument]:
        raise RuntimeError("retrieval unavailable")

    async def find_neighbors(
        self,
        *,
        documents: list[IndexedNewsDocument],
        limit: int,
    ) -> list[NewsNeighborGroup]:
        return []


class FakeClassifier:
    def __init__(self, model_name: AnalysisModelName = AnalysisModelName.TFIDF_LOGREG) -> None:
        self.model_name = model_name
        self.texts: list[str] = []

    def predict(self, text: NewsText) -> ImpactPrediction:
        self.texts.append(text.value)
        return ImpactPrediction(
            model_name=self.model_name,
            impact=ImpactLabel.POSITIVE,
            confidence=0.8,
            explanation="Позитивное влияние",
        )


class FakeRegistry:
    def __init__(self, classifier: FakeClassifier | None = None) -> None:
        self.classifier = classifier or FakeClassifier()
        self.requested_models: list[AnalysisModelName] = []

    def get(self, model_name: AnalysisModelName) -> FakeClassifier:
        self.requested_models.append(model_name)
        return FakeClassifier(model_name=model_name)


def _document(news_id: str, title: str) -> IndexedNewsDocument:
    return IndexedNewsDocument(
        id=news_id,
        title=title,
        text=f"{title}. Details.",
        source="demo",
    )


def test_topic_forecast_zapros_client_keeps_std_handler_timeout_disabled() -> None:
    client = _make_zapros_client(timeout_seconds=5.0)
    handler = cast(Any, client.handler)

    assert handler.total_timeout is None


@pytest.mark.asyncio
async def test_topic_forecast_retrieval_gateway_uses_zapros_transport() -> None:
    transport = FakeZaprosClient(
        [
            Response(
                200,
                json={
                    "documents": [
                        {
                            "id": "news-1",
                            "title": "GDP grows",
                            "text": "GDP grew by 2 percent.",
                            "source": "demo",
                            "published_at": None,
                            "metadata": {},
                        },
                    ],
                },
            ),
            Response(
                200,
                json={
                    "groups": [
                        {
                            "document_id": "news-1",
                            "neighbors": [
                                {
                                    "id": "news-2",
                                    "score": 0.91,
                                    "title": "Exports rise",
                                    "text": "Exports rise.",
                                    "source": "demo",
                                    "published_at": None,
                                    "metadata": {},
                                },
                            ],
                        },
                    ],
                },
            ),
        ],
    )
    gateway = HttpTopicForecastRetrievalGateway(
        base_url="http://retrieval-service:8000/",
        timeout_seconds=3.0,
        client=transport,
    )

    documents = await gateway.list_documents(limit=10)
    neighbors = await gateway.find_neighbors(documents=documents, limit=3)

    assert documents[0].id == "news-1"
    assert neighbors[0].neighbors[0].id == "news-2"
    assert transport.get_calls == [
        ("http://retrieval-service:8000/api/v1/documents", {"limit": ["10"]}),
    ]
    assert transport.post_calls == [
        (
            "http://retrieval-service:8000/api/v1/neighbors",
            {"document_ids": ["news-1"], "limit": 3, "source": None},
        ),
    ]


@pytest.mark.asyncio
async def test_json_topic_forecast_storage_round_trips_job_and_latest_report(
    tmp_path: Path,
) -> None:
    storage = JsonTopicForecastStorage(
        jobs_dir=tmp_path / "jobs",
        latest_report_path=tmp_path / "latest.json",
    )
    report = TopicForecastResponse(
        generated_at="2026-05-10T10:00:00Z",
        topics=[],
        metadata={"document_count": 0},
    )

    await storage.save_job(
        TopicForecastJobResponse(
            job_id="job-1",
            status=TopicForecastJobStatus.SUCCEEDED,
            report_path="reports/topic-forecast/latest.json",
        ),
    )
    await storage.save_latest_report(report)

    assert await storage.get_job("job-1") == TopicForecastJobResponse(
        job_id="job-1",
        status=TopicForecastJobStatus.SUCCEEDED,
        report_path="reports/topic-forecast/latest.json",
    )
    assert await storage.get_latest_report() == report


@pytest.mark.asyncio
async def test_json_topic_forecast_storage_raises_for_missing_job(tmp_path: Path) -> None:
    storage = JsonTopicForecastStorage(
        jobs_dir=tmp_path / "jobs",
        latest_report_path=tmp_path / "latest.json",
    )

    with pytest.raises(TopicForecastJobNotFoundError):
        await storage.get_job("missing-job")


@pytest.mark.asyncio
async def test_enqueue_topic_forecast_job_persists_queued_status_before_enqueue(
    tmp_path: Path,
) -> None:
    storage = JsonTopicForecastStorage(
        jobs_dir=tmp_path / "jobs",
        latest_report_path=tmp_path / "latest.json",
    )
    queue = StubTopicForecastTaskQueue()
    use_case = EnqueueTopicForecastJob(queue, storage)

    response = await use_case.execute()

    assert response.job_id
    assert queue.job_id == response.job_id
    assert await GetTopicForecastJob(storage).execute(response.job_id) == TopicForecastJobResponse(
        job_id=response.job_id,
        status=TopicForecastJobStatus.QUEUED,
    )


@pytest.mark.asyncio
async def test_get_latest_topic_forecast_returns_none_when_report_missing(
    tmp_path: Path,
) -> None:
    storage = JsonTopicForecastStorage(
        jobs_dir=tmp_path / "jobs",
        latest_report_path=tmp_path / "latest.json",
    )

    assert await GetLatestTopicForecast(storage).execute() is None


@pytest.mark.asyncio
async def test_generate_topic_forecast_report_builds_and_persists_latest_report(
    tmp_path: Path,
) -> None:
    storage = JsonTopicForecastStorage(
        jobs_dir=tmp_path / "jobs",
        latest_report_path=tmp_path / "latest.json",
    )
    documents = [
        _document("news-1", "GDP grows"),
        _document("news-2", "Exports rise"),
    ]
    retrieval_gateway = FakeTopicForecastRetrievalGateway(documents)
    classifier = FakeClassifier()
    registry = FakeRegistry(classifier)
    use_case = GenerateTopicForecastReport(
        retrieval_gateway=retrieval_gateway,
        registry=registry,
        storage=storage,
        analysis_model=AnalysisModelName.TFIDF_LOGREG,
        document_limit=10,
        neighbor_limit=3,
        min_neighbor_score=0.8,
        max_topic_size=5,
        report_path=tmp_path / "latest.json",
    )

    report = await use_case.execute("job-1")

    assert retrieval_gateway.document_limit == 10
    assert retrieval_gateway.neighbor_limit == 3
    assert registry.requested_models == [
        AnalysisModelName.TFIDF_LOGREG,
        AnalysisModelName.EMBEDDING_LOGREG,
        AnalysisModelName.TINY_TRANSFORMER_CLASSIFIER,
    ]
    assert len(report.model_reports) == 3
    assert [item.model_name for item in report.model_reports] == [
        "tfidf-logreg",
        "embedding-logreg",
        "tiny-transformer-classifier",
    ]
    assert all(item.error is None for item in report.model_reports)
    assert all(item.topics for item in report.model_reports)
    assert report.metadata["analysis_models"] == [
        "tfidf-logreg",
        "embedding-logreg",
        "tiny-transformer-classifier",
    ]
    assert report.topics[0].overall_impact == ImpactLabel.POSITIVE
    assert {news.id for news in report.topics[0].news} == {"news-1", "news-2"}
    assert (await storage.get_latest_report()) == report
    assert await storage.get_job("job-1") == TopicForecastJobResponse(
        job_id="job-1",
        status=TopicForecastJobStatus.SUCCEEDED,
        report_path=str(tmp_path / "latest.json"),
    )


@pytest.mark.asyncio
async def test_generate_topic_forecast_report_marks_job_failed_on_error(
    tmp_path: Path,
) -> None:
    storage = JsonTopicForecastStorage(
        jobs_dir=tmp_path / "jobs",
        latest_report_path=tmp_path / "latest.json",
    )
    use_case = GenerateTopicForecastReport(
        retrieval_gateway=FailingTopicForecastRetrievalGateway(),
        registry=FakeRegistry(FakeClassifier()),
        storage=storage,
        analysis_model=AnalysisModelName.TFIDF_LOGREG,
        document_limit=10,
        neighbor_limit=3,
        min_neighbor_score=0.8,
        max_topic_size=5,
        report_path=tmp_path / "latest.json",
    )

    with pytest.raises(RuntimeError, match="retrieval unavailable"):
        await use_case.execute("job-1")

    job = await storage.get_job("job-1")
    assert job.status == TopicForecastJobStatus.FAILED
    assert job.message == "retrieval unavailable"
