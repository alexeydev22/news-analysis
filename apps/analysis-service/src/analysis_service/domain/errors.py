from economic_news_contracts.analysis import AnalysisModelName


class AnalysisServiceError(Exception):
    """Base exception for analysis-service."""


class EmptyNewsTextError(AnalysisServiceError):
    def __init__(self) -> None:
        super().__init__("News text must not be empty")


class InvalidPredictionConfidenceError(AnalysisServiceError):
    def __init__(self, confidence: float) -> None:
        self.confidence = confidence
        super().__init__("Prediction confidence must be between 0.0 and 1.0")


class ModelUnavailableError(AnalysisServiceError):
    def __init__(self, model_name: AnalysisModelName) -> None:
        self.model_name = model_name
        super().__init__(f"Analysis model is unavailable: {model_name}")


class MlReportJobNotFoundError(AnalysisServiceError):
    def __init__(self, job_id: str) -> None:
        self.job_id = job_id
        super().__init__(f"ML report job not found: {job_id}")
