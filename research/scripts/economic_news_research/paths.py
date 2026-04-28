from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
DATA_DIR = REPO_ROOT / "data"
RAW_DATA_DIR = DATA_DIR / "raw"
PROCESSED_DATA_DIR = DATA_DIR / "processed"
RESEARCH_DIR = REPO_ROOT / "research"
REPORTS_DIR = RESEARCH_DIR / "reports"
ARTIFACTS_DIR = REPO_ROOT / "artifacts"
MODELS_DIR = ARTIFACTS_DIR / "models"
MLFLOW_DIR = ARTIFACTS_DIR / "mlflow"

DEFAULT_RAW_DATASET = RAW_DATA_DIR / "news_impact.csv"
DEFAULT_PROCESSED_DATASET = PROCESSED_DATA_DIR / "news_impact_processed.csv"
