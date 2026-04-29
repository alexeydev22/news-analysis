from pathlib import Path

from economic_news_framework.settings import BaseServiceSettings
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
