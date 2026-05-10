from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path


@dataclass(frozen=True, slots=True)
class UploadedDataset:
    dataset_id: str
    filename: str
    path: Path
    size_bytes: int
    uploaded_at: datetime


@dataclass(frozen=True, slots=True)
class ActiveDataset:
    dataset_id: str
    filename: str
    path: Path
    activated_at: datetime


def utc_now() -> datetime:
    return datetime.now(tz=UTC)
