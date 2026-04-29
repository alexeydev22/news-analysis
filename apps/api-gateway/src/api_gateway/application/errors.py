class AnalysisServiceUnavailableError(RuntimeError):
    """Raised when analysis-service cannot process a gateway request."""


class RetrievalServiceUnavailableError(RuntimeError):
    """Raised when retrieval-service cannot process a gateway request."""
