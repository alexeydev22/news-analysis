class AnalysisServiceUnavailableError(RuntimeError):
    """Raised when analysis-service cannot process a gateway request."""


class RetrievalServiceUnavailableError(RuntimeError):
    """Raised when retrieval-service cannot process a gateway request."""


class DialogServiceUnavailableError(RuntimeError):
    """Raised when dialog-service cannot process a gateway request."""
