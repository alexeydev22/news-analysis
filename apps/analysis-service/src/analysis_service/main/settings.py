from pathlib import Path

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
    redis_url: RedisDsn = RedisDsn("redis://redis:6379/0")
    task_queue_name: str = Field(default="analysis-ml-reporting", min_length=1)
    task_result_ttl_seconds: int = Field(default=3600, ge=60)
