from pathlib import Path

import pytest
from news_service.domain.errors import NewsSourceValidationError
from news_service.infrastructure.local_dataset_storage import LocalDatasetStorage

CSV_BYTES = b"id,title,text,source,published_at\nn1,GDP grows,GDP grew,demo,2026-05-07T09:30:00Z\n"


@pytest.mark.asyncio
async def test_storage_saves_upload_with_stable_dataset_id(tmp_path: Path) -> None:
    storage = LocalDatasetStorage(
        upload_dir=tmp_path / "uploads",
        active_dataset_file=tmp_path / "uploads" / "active_dataset.json",
        max_upload_bytes=1024,
    )

    dataset = await storage.save_upload(filename="news.csv", content=CSV_BYTES)

    assert dataset.dataset_id == "news"
    assert dataset.filename == "news.csv"
    assert dataset.path == tmp_path / "uploads" / "news.csv"
    assert dataset.size_bytes == len(CSV_BYTES)
    assert dataset.path.read_bytes() == CSV_BYTES


@pytest.mark.asyncio
async def test_storage_rejects_non_csv_upload(tmp_path: Path) -> None:
    storage = LocalDatasetStorage(
        upload_dir=tmp_path / "uploads",
        active_dataset_file=tmp_path / "uploads" / "active_dataset.json",
        max_upload_bytes=1024,
    )

    with pytest.raises(NewsSourceValidationError, match="Only CSV uploads are supported"):
        await storage.save_upload(filename="news.txt", content=CSV_BYTES)


@pytest.mark.asyncio
async def test_storage_rejects_too_large_upload(tmp_path: Path) -> None:
    storage = LocalDatasetStorage(
        upload_dir=tmp_path / "uploads",
        active_dataset_file=tmp_path / "uploads" / "active_dataset.json",
        max_upload_bytes=4,
    )

    with pytest.raises(NewsSourceValidationError, match="Dataset upload is too large"):
        await storage.save_upload(filename="news.csv", content=CSV_BYTES)


@pytest.mark.asyncio
async def test_storage_activates_and_returns_active_dataset(tmp_path: Path) -> None:
    storage = LocalDatasetStorage(
        upload_dir=tmp_path / "uploads",
        active_dataset_file=tmp_path / "uploads" / "active_dataset.json",
        max_upload_bytes=1024,
    )
    uploaded = await storage.save_upload(filename="news.csv", content=CSV_BYTES)

    active = await storage.activate(uploaded.dataset_id)

    assert active.dataset_id == uploaded.dataset_id
    assert active.path == uploaded.path
    assert await storage.get_active_path() == uploaded.path
    active_dataset = await storage.get_active()
    assert active_dataset is not None
    assert active_dataset.dataset_id == uploaded.dataset_id


@pytest.mark.asyncio
async def test_storage_lists_uploaded_datasets(tmp_path: Path) -> None:
    storage = LocalDatasetStorage(
        upload_dir=tmp_path / "uploads",
        active_dataset_file=tmp_path / "uploads" / "active_dataset.json",
        max_upload_bytes=1024,
    )

    await storage.save_upload(filename="b.csv", content=CSV_BYTES)
    await storage.save_upload(filename="a.csv", content=CSV_BYTES)
    datasets = await storage.list_datasets()

    assert [dataset.filename for dataset in datasets] == ["a.csv", "b.csv"]
