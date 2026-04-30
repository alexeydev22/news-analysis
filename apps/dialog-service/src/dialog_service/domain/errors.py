class DialogServiceError(RuntimeError):
    """Base exception for dialog-service."""


class EmptyDialogTextError(DialogServiceError, ValueError):
    def __init__(self, field_name: str) -> None:
        super().__init__(f"{field_name} must not be empty")


class DialogGeneratorUnavailableError(DialogServiceError):
    """Raised when dialog generation cannot be completed."""
