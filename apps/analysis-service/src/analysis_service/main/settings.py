from pathlib import Path

from economic_news_contracts.analysis import AnalysisModelName
from economic_news_framework.settings import BaseServiceSettings
from pydantic import Field, RedisDsn
from pydantic_settings import SettingsConfigDict


class AnalysisServiceSettings(BaseServiceSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        env_prefix="ANALYSIS_",
        extra="ignore",
    )

    service_name: str = "analysis-service"
    version: str = "0.1.0"
    use_static_classifier: bool = False
    tfidf_artifact_path: Path = Path("artifacts/models/baseline/tfidf-logreg.joblib")
    embedding_artifact_path: Path = Path("artifacts/models/embedding/embedding-logreg.joblib")
    transformer_artifact_path: Path = Path(
        "artifacts/models/transformer/tiny-transformer-classifier.joblib",
    )
    ml_dataset_path: Path = Path("data/raw/news_impact.csv")
    ml_comparison_path: Path = Path("artifacts/models/model_comparison.csv")
    ml_report_output_path: Path = Path("reports/ml/model-report.json")
    ml_report_jobs_dir: Path = Path("reports/ml/jobs")
    ml_random_state: int = 42
    topic_forecast_output_path: Path = Path("reports/topic-forecast/latest.json")
    topic_forecast_jobs_dir: Path = Path("reports/topic-forecast/jobs")
    topic_forecast_document_limit: int = Field(default=100, ge=1, le=500)
    topic_forecast_neighbor_limit: int = Field(default=5, ge=1, le=20)
    topic_forecast_min_neighbor_score: float = Field(default=0.8, ge=-1.0, le=1.0)
    topic_forecast_max_topic_size: int = Field(default=5, ge=1)
    topic_forecast_analysis_model: AnalysisModelName = AnalysisModelName.TFIDF_LOGREG
    retrieval_service_url: str = "http://retrieval-service:8000"
    retrieval_service_timeout_seconds: float = Field(default=10.0, gt=0.0)
    redis_url: RedisDsn = RedisDsn("redis://redis:6379/0")
    task_queue_name: str = Field(default="analysis-ml-reporting", min_length=1)
    task_result_ttl_seconds: int = Field(default=3600, ge=60)
