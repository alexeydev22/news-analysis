from typing import Any

from dishka import Provider, Scope, make_async_container, provide
from dishka.integrations.fastapi import FastapiProvider
from economic_news_contracts.analysis import AnalysisModelName, ImpactLabel

from analysis_service.application.ports import (
    EconomicForecastGenerator,
    MlReportStorage,
    MlReportTaskQueue,
    ModelRegistry,
    TopicForecastRetrievalGateway,
    TopicForecastStorage,
    TopicForecastTaskQueue,
)
from analysis_service.application.use_cases import (
    AnalyzeNewsImpact,
    EnqueueMlReportJob,
    EnqueueTopicForecastJob,
    GenerateGroqTopicForecast,
    GenerateTopicForecastReport,
    GetLatestMlReport,
    GetLatestTopicForecast,
    GetMlReportJob,
    GetTopicForecastJob,
)
from analysis_service.infrastructure.classifiers import (
    JoblibImpactClassifier,
    StaticImpactClassifier,
    StaticModelRegistry,
)
from analysis_service.infrastructure.groq_forecast_client import GroqEconomicForecastGenerator
from analysis_service.infrastructure.ml_report_queue import TaskiqMlReportTaskQueue
from analysis_service.infrastructure.ml_report_storage import JsonMlReportStorage
from analysis_service.infrastructure.topic_forecast_queue import TaskiqTopicForecastTaskQueue
from analysis_service.infrastructure.topic_forecast_retrieval_client import (
    HttpTopicForecastRetrievalGateway,
)
from analysis_service.infrastructure.topic_forecast_storage import JsonTopicForecastStorage
from analysis_service.main.settings import AnalysisServiceSettings


class AnalysisServiceProvider(Provider):
    def __init__(self, settings: AnalysisServiceSettings | None = None) -> None:
        super().__init__()
        self._settings = settings

    @provide(scope=Scope.APP)
    def settings(self) -> AnalysisServiceSettings:
        return self._settings or AnalysisServiceSettings()

    @provide(scope=Scope.APP, provides=ModelRegistry)
    def model_registry(self, settings: AnalysisServiceSettings) -> StaticModelRegistry:
        if settings.use_static_classifier:
            return StaticModelRegistry(
                [
                    StaticImpactClassifier(
                        model_name=AnalysisModelName.TFIDF_LOGREG,
                        impact=ImpactLabel.NEUTRAL,
                    ),
                ],
            )
        artifact_paths = {
            AnalysisModelName.TFIDF_LOGREG: settings.tfidf_artifact_path,
            AnalysisModelName.EMBEDDING_LOGREG: settings.embedding_artifact_path,
            AnalysisModelName.TINY_TRANSFORMER_CLASSIFIER: settings.transformer_artifact_path,
        }
        return StaticModelRegistry(
            [
                JoblibImpactClassifier(model_name=model_name, artifact_path=artifact_path)
                for model_name, artifact_path in artifact_paths.items()
                if artifact_path.exists()
            ],
        )

    @provide(scope=Scope.APP)
    def analyze_news_impact(self, registry: ModelRegistry) -> AnalyzeNewsImpact:
        return AnalyzeNewsImpact(registry)

    @provide(scope=Scope.APP, provides=MlReportStorage)
    def ml_report_storage(self, settings: AnalysisServiceSettings) -> JsonMlReportStorage:
        return JsonMlReportStorage(
            jobs_dir=settings.ml_report_jobs_dir,
            latest_report_path=settings.ml_report_output_path,
        )

    @provide(scope=Scope.APP, provides=MlReportTaskQueue)
    def ml_report_task_queue(self) -> TaskiqMlReportTaskQueue:
        return TaskiqMlReportTaskQueue()

    @provide(scope=Scope.APP)
    def enqueue_ml_report_job(
        self,
        task_queue: MlReportTaskQueue,
        storage: MlReportStorage,
    ) -> EnqueueMlReportJob:
        return EnqueueMlReportJob(task_queue, storage)

    @provide(scope=Scope.APP)
    def get_ml_report_job(self, storage: MlReportStorage) -> GetMlReportJob:
        return GetMlReportJob(storage)

    @provide(scope=Scope.APP)
    def get_latest_ml_report(self, storage: MlReportStorage) -> GetLatestMlReport:
        return GetLatestMlReport(storage)

    @provide(scope=Scope.APP, provides=TopicForecastStorage)
    def topic_forecast_storage(
        self,
        settings: AnalysisServiceSettings,
    ) -> JsonTopicForecastStorage:
        return JsonTopicForecastStorage(
            jobs_dir=settings.topic_forecast_jobs_dir,
            latest_report_path=settings.topic_forecast_output_path,
        )

    @provide(scope=Scope.APP, provides=TopicForecastTaskQueue)
    def topic_forecast_task_queue(self) -> TaskiqTopicForecastTaskQueue:
        return TaskiqTopicForecastTaskQueue()

    @provide(scope=Scope.APP, provides=TopicForecastRetrievalGateway)
    def topic_forecast_retrieval_gateway(
        self,
        settings: AnalysisServiceSettings,
    ) -> HttpTopicForecastRetrievalGateway:
        return HttpTopicForecastRetrievalGateway(
            base_url=settings.retrieval_service_url,
            timeout_seconds=settings.retrieval_service_timeout_seconds,
        )

    @provide(scope=Scope.APP)
    def enqueue_topic_forecast_job(
        self,
        task_queue: TopicForecastTaskQueue,
        storage: TopicForecastStorage,
    ) -> EnqueueTopicForecastJob:
        return EnqueueTopicForecastJob(task_queue, storage)

    @provide(scope=Scope.APP)
    def get_topic_forecast_job(
        self,
        storage: TopicForecastStorage,
    ) -> GetTopicForecastJob:
        return GetTopicForecastJob(storage)

    @provide(scope=Scope.APP)
    def get_latest_topic_forecast(
        self,
        storage: TopicForecastStorage,
    ) -> GetLatestTopicForecast:
        return GetLatestTopicForecast(storage)

    @provide(scope=Scope.APP, provides=EconomicForecastGenerator)
    def economic_forecast_generator(
        self,
        settings: AnalysisServiceSettings,
    ) -> EconomicForecastGenerator:
        return GroqEconomicForecastGenerator(
            base_url=str(settings.groq_base_url),
            api_key=(
                settings.groq_api_key.get_secret_value()
                if settings.groq_api_key
                else None
            ),
            model_name=settings.groq_model,
            timeout_seconds=settings.groq_timeout_seconds,
            temperature=settings.groq_temperature,
            max_tokens=settings.groq_max_tokens,
        )

    @provide(scope=Scope.APP)
    def generate_groq_topic_forecast(
        self,
        generator: EconomicForecastGenerator,
    ) -> GenerateGroqTopicForecast:
        return GenerateGroqTopicForecast(generator)

    @provide(scope=Scope.APP)
    def generate_topic_forecast_report(
        self,
        retrieval_gateway: TopicForecastRetrievalGateway,
        registry: ModelRegistry,
        storage: TopicForecastStorage,
        settings: AnalysisServiceSettings,
    ) -> GenerateTopicForecastReport:
        return GenerateTopicForecastReport(
            retrieval_gateway=retrieval_gateway,
            registry=registry,
            storage=storage,
            analysis_model=settings.topic_forecast_analysis_model,
            document_limit=settings.topic_forecast_document_limit,
            neighbor_limit=settings.topic_forecast_neighbor_limit,
            min_neighbor_score=settings.topic_forecast_min_neighbor_score,
            max_topic_size=settings.topic_forecast_max_topic_size,
            report_path=settings.topic_forecast_output_path,
        )


def create_container(settings: AnalysisServiceSettings | None = None) -> Any:
    return make_async_container(AnalysisServiceProvider(settings), FastapiProvider())
