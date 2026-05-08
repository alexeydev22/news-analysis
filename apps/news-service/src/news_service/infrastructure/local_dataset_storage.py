import json
import re
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from news_service.domain.dataset import ActiveDataset, UploadedDataset, utc_now
from news_service.domain.errors import NewsSourceValidationError

_SAFE_FILENAME_PATTERN = re.compile(r"[^a-zA-Z0-9_.-]+")


class LocalDatasetStorage:
    def __init__(
        self,
        *,
        upload_dir: Path | str,
        active_dataset_file: Path | str,
        max_upload_bytes: int,
    ) -> None:
        self._upload_dir = Path(upload_dir)
        self._active_dataset_file = Path(active_dataset_file)
        self._max_upload_bytes = max_upload_bytes

    async def save_upload(self, *, filename: str, content: bytes) -> UploadedDataset:
        clean_filename = self._clean_filename(filename)
        if Path(clean_filename).suffix.lower() != ".csv":
            raise NewsSourceValidationError("Only CSV uploads are supported")
        if len(content) > self._max_upload_bytes:
            raise NewsSourceValidationError("Dataset upload is too large")

        dataset_id = self._dataset_id_from_filename(clean_filename)
        dataset_path = self._upload_dir / f"{dataset_id}.csv"
        self._upload_dir.mkdir(parents=True, exist_ok=True)
        dataset_path.write_bytes(content)

        return UploadedDataset(
            dataset_id=dataset_id,
            filename=dataset_path.name,
            path=dataset_path,
            size_bytes=len(content),
            uploaded_at=utc_now(),
        )

    async def list_datasets(self) -> list[UploadedDataset]:
        datasets: list[UploadedDataset] = []
        for dataset_path in sorted(self._upload_dir.glob("*.csv"), key=lambda path: path.name):
            try:
                file_stat = dataset_path.stat()
            except OSError:
                continue
            datasets.append(
                UploadedDataset(
                    dataset_id=dataset_path.stem,
                    filename=dataset_path.name,
                    path=dataset_path,
                    size_bytes=file_stat.st_size,
                    uploaded_at=datetime.fromtimestamp(file_stat.st_mtime, tz=UTC),
                )
            )
        return datasets

    async def activate(self, dataset_id: str) -> ActiveDataset:
        dataset = await self._find_dataset(dataset_id)
        if dataset is None:
            raise NewsSourceValidationError("Dataset upload does not exist")

        activated_at = utc_now()
        active = ActiveDataset(
            dataset_id=dataset.dataset_id,
            filename=dataset.filename,
            path=dataset.path,
            activated_at=activated_at,
        )
        self._active_dataset_file.parent.mkdir(parents=True, exist_ok=True)
        self._active_dataset_file.write_text(
            json.dumps(
                {
                    "dataset_id": active.dataset_id,
                    "filename": active.filename,
                    "path": str(active.path),
                    "activated_at": active.activated_at.isoformat(),
                }
            ),
            encoding="utf-8",
        )
        return active

    async def get_active(self) -> ActiveDataset | None:
        try:
            raw_active = json.loads(self._active_dataset_file.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return None

        active = self._active_from_json(raw_active)
        if active is None or not active.path.exists():
            return None
        return active

    async def get_active_path(self) -> Path | None:
        active = await self.get_active()
        if active is None:
            return None
        return active.path

    async def _find_dataset(self, dataset_id: str) -> UploadedDataset | None:
        if not dataset_id or _SAFE_FILENAME_PATTERN.search(dataset_id):
            return None

        dataset_path = self._upload_dir / f"{dataset_id}.csv"
        if not dataset_path.is_file():
            return None

        file_stat = dataset_path.stat()
        return UploadedDataset(
            dataset_id=dataset_path.stem,
            filename=dataset_path.name,
            path=dataset_path,
            size_bytes=file_stat.st_size,
            uploaded_at=datetime.fromtimestamp(file_stat.st_mtime, tz=UTC),
        )

    def _clean_filename(self, filename: str) -> str:
        clean_filename = _SAFE_FILENAME_PATTERN.sub("_", Path(filename).name.strip())
        if not clean_filename:
            raise NewsSourceValidationError("Dataset filename is required")
        return clean_filename

    def _dataset_id_from_filename(self, filename: str) -> str:
        dataset_id = Path(filename).stem
        if not dataset_id:
            raise NewsSourceValidationError("Dataset filename is required")
        return dataset_id

    def _active_from_json(self, raw_active: Any) -> ActiveDataset | None:
        if not isinstance(raw_active, dict):
            return None

        dataset_id = raw_active.get("dataset_id")
        filename = raw_active.get("filename")
        path = raw_active.get("path")
        activated_at = raw_active.get("activated_at")
        if not all(isinstance(value, str) for value in (dataset_id, filename, path, activated_at)):
            return None

        try:
            activated_at_datetime = datetime.fromisoformat(activated_at)
        except ValueError:
            return None

        return ActiveDataset(
            dataset_id=dataset_id,
            filename=filename,
            path=Path(path),
            activated_at=activated_at_datetime,
        )
