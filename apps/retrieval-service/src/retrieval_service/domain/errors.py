class RetrievalServiceError(Exception):
    """Base exception for retrieval-service."""


class EmptyDocumentTextError(RetrievalServiceError):
    def __init__(self, field_name: str) -> None:
        self.field_name = field_name
        super().__init__(f"{field_name} must not be empty")


class InvalidSearchLimitError(RetrievalServiceError):
    def __init__(self, limit: int) -> None:
        self.limit = limit
        super().__init__("Search limit must be between 1 and 20")


class RetrievalUnavailableError(RetrievalServiceError):
    def __init__(self) -> None:
        super().__init__("Retrieval infrastructure is unavailable")
