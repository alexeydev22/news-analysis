from typing import Protocol


class VersionProvider(Protocol):
    def get_version(self) -> str:
        """Return current service version."""


class StaticVersionProvider:
    def __init__(self, version: str) -> None:
        self._version = version

    def get_version(self) -> str:
        return self._version
