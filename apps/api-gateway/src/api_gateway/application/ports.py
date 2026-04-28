from typing import Protocol


class VersionProvider(Protocol):
    def get_version(self) -> str:
        """Return current service version."""
