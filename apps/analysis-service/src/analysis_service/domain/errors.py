from economic_news_contracts.analysis import AnalysisModelName


class AnalysisServiceError(Exception):
    """Base exception for analysis-service."""


class EmptyNewsTextError(AnalysisServiceError):
    def __init__(self) -> None:
        super().__init__("News text must not be empty")


class ModelUnavailableError(AnalysisServiceError):
    def __init__(self, model_name: AnalysisModelName) -> None:
        self.model_name = model_name
        super().__init__(f"Analysis model is unavailable: {model_name}")
