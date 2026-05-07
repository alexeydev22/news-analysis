class NewsDomainError(Exception):
    """Base class for news-service domain errors."""


class EmptyNewsFieldError(NewsDomainError, ValueError):
    """Raised when required news field is empty."""


class NewsSourceUnavailableError(Exception):
    """Raised when configured news source cannot be loaded."""


class NewsSourceValidationError(ValueError):
    """Raised when configured news source has invalid shape or rows."""


class RetrievalIndexUnavailableError(Exception):
    """Raised when retrieval-service indexing is unavailable."""
