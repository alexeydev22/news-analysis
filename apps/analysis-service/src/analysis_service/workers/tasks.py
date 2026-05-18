from pathlib import Path

from economic_news_contracts.analysis import MlReportJobResponse, MlReportJobStatus

from analysis_service.application.use_cases import GenerateTopicForecastReport
from analysis_service.infrastructure.ml_report_storage import JsonMlReportStorage
from analysis_service.infrastructure.topic_forecast_retrieval_client import (
    HttpTopicForecastRetrievalGateway,
)
from analysis_service.infrastructure.topic_forecast_storage import JsonTopicForecastStorage
from analysis_service.main.container import AnalysisServiceProvider
from analysis_service.main.settings import AnalysisServiceSettings
from analysis_service.workers.broker import broker
from economic_news_research.cli import (
    run_build_model_report,
    run_compare_models,
    run_train_baseline,
    run_train_embedding,
    run_train_transformer,
)


@broker.task
async def generate_ml_report_task(
    job_id: str,
) -> dict[str, object]:
    settings = AnalysisServiceSettings()
    storage = JsonMlReportStorage(
        jobs_dir=settings.ml_report_jobs_dir,
        latest_report_path=settings.ml_report_output_path,
    )
    selected_dataset_path = Path(settings.ml_dataset_path)
    await storage.save_job(
        MlReportJobResponse(job_id=job_id, status=MlReportJobStatus.STARTED),
    )
    try:
        run_train_baseline(
            dataset_path=selected_dataset_path,
            output_dir=settings.tfidf_artifact_path.parent,
            random_state=settings.ml_random_state,
            max_rows=settings.ml_train_max_rows,
        )
        run_train_embedding(
            dataset_path=selected_dataset_path,
            output_dir=settings.embedding_artifact_path.parent,
            random_state=settings.ml_random_state,
            max_rows=settings.ml_embedding_max_rows,
        )
        run_train_transformer(
            dataset_path=selected_dataset_path,
            output_dir=settings.transformer_artifact_path.parent,
            random_state=settings.ml_random_state,
            max_rows=settings.ml_transformer_max_rows,
        )
        run_compare_models(
            comparison_paths=[
                settings.tfidf_artifact_path.parent / "model_comparison.csv",
                settings.embedding_artifact_path.parent / "model_comparison.csv",
                settings.transformer_artifact_path.parent / "model_comparison.csv",
            ],
            output_path=settings.ml_comparison_path,
        )
        report_path = run_build_model_report(
            dataset_path=selected_dataset_path,
            comparison_path=settings.ml_comparison_path,
            model_dirs=[
                settings.tfidf_artifact_path.parent,
                settings.embedding_artifact_path.parent,
                settings.transformer_artifact_path.parent,
            ],
            output_path=settings.ml_report_output_path,
            training_limits={
                "classic_max_rows": settings.ml_train_max_rows,
                "embedding_max_rows": settings.ml_embedding_max_rows,
                "transformer_max_rows": settings.ml_transformer_max_rows,
            },
        )
    except Exception as error:
        await storage.save_job(
            MlReportJobResponse(
                job_id=job_id,
                status=MlReportJobStatus.FAILED,
                message=str(error),
            ),
        )
        raise

    await storage.save_job(
        MlReportJobResponse(
            job_id=job_id,
            status=MlReportJobStatus.SUCCEEDED,
            report_path=str(report_path),
        ),
    )
    return {"report_path": str(report_path)}


@broker.task
async def generate_topic_forecast_task(
    job_id: str,
) -> dict[str, object]:
    settings = AnalysisServiceSettings()
    use_case = _build_topic_forecast_report_use_case(settings)
    report = await use_case.execute(job_id)
    return report.model_dump(mode="json")


def _build_topic_forecast_report_use_case(
    settings: AnalysisServiceSettings,
) -> GenerateTopicForecastReport:
    storage = JsonTopicForecastStorage(
        jobs_dir=settings.topic_forecast_jobs_dir,
        latest_report_path=settings.topic_forecast_output_path,
    )
    retrieval_gateway = HttpTopicForecastRetrievalGateway(
        base_url=settings.retrieval_service_url,
        timeout_seconds=settings.retrieval_service_timeout_seconds,
    )
    registry = AnalysisServiceProvider(settings).model_registry(settings)
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
