from __future__ import annotations

import asyncio
from pathlib import Path
from unittest.mock import MagicMock
import pytest

from notion_db_manager.application.commands.travel.push_photos import TravelPushPhotosCommand
from notion_db_manager.application.interfaces.notion_gateway import NotionGateway
from notion_db_manager.application.interfaces.photo_provider import PhotoStorage
from notion_db_manager.domain.travel import (
    EnrichItemResult,
    TravelPhotoEnrichSummary,
)


@pytest.fixture
def mock_storage() -> MagicMock:
    storage = MagicMock(spec=PhotoStorage)
    items = [
        EnrichItemResult(
            index=1,
            page_id="page_1",
            name="熱田神宮",
            status="success",
            local_path="output/images/test/01_熱田神宮.jpg",
            source_url="https://lh3.googleusercontent.com/abc",
        ),
        EnrichItemResult(
            index=2,
            page_id="page_2",
            name="名古屋車站",
            status="skipped",
            local_path=None,
            source_url=None,
            error_message="非目標分類",
        ),
        EnrichItemResult(
            index=3,
            page_id="page_3",
            name="大須觀音",
            status="success",
            local_path="output/images/test/03_大須觀音.png",
            source_url="https://lh3.googleusercontent.com/def",
        ),
    ]
    storage.read_manifest.return_value = TravelPhotoEnrichSummary(
        database_name="名古屋之旅",
        provider="playwright",
        total_items=3,
        processed_count=2,
        skipped_count=1,
        success_count=2,
        failed_count=0,
        items=items,
    )
    storage.load_photo_bytes.return_value = b"fake_photo_bytes"
    return storage


@pytest.fixture
def mock_gateway() -> MagicMock:
    gateway = MagicMock(spec=NotionGateway)
    gateway.upload_file.side_effect = lambda filename, file_bytes, mime_type: f"fu_{filename}"
    return gateway


def test_travel_push_photos_command_success(mock_gateway: MagicMock, mock_storage: MagicMock) -> None:
    progress_events: list[tuple[int, int, str, str]] = []

    def on_progress(idx: int, total: int, name: str, status: str) -> None:
        progress_events.append((idx, total, name, status))

    cmd = TravelPushPhotosCommand(
        gateway=mock_gateway,
        storage=mock_storage,
        progress_callback=on_progress,
    )

    summary = cmd.execute_sync(
        database_name="名古屋之旅",
        concurrency=2,
        delay=0.0,
    )

    assert summary.total_items == 3
    assert summary.success_count == 2
    assert summary.skipped_count == 1
    assert summary.failed_count == 0
    assert summary.processed_count == 2

    # Check upload_file was called for the 2 success items
    assert mock_gateway.upload_file.call_count == 2
    mock_gateway.upload_file.assert_any_call(
        filename="01_熱田神宮.jpg",
        file_bytes=b"fake_photo_bytes",
        mime_type="image/jpeg",
    )
    mock_gateway.upload_file.assert_any_call(
        filename="03_大須觀音.png",
        file_bytes=b"fake_photo_bytes",
        mime_type="image/png",
    )

    # Check update_page_properties calls
    assert mock_gateway.update_page_properties.call_count == 2
    mock_gateway.update_page_properties.assert_any_call(
        "page_1",
        {
            "照片": {
                "files": [
                    {
                        "name": "01_熱田神宮.jpg",
                        "type": "file_upload",
                        "file_upload": {"id": "fu_01_熱田神宮.jpg"},
                    }
                ]
            }
        },
    )
    mock_gateway.update_page_properties.assert_any_call(
        "page_3",
        {
            "照片": {
                "files": [
                    {
                        "name": "03_大須觀音.png",
                        "type": "file_upload",
                        "file_upload": {"id": "fu_03_大須觀音.png"},
                    }
                ]
            }
        },
    )

    # Verify progress callback fired for all items
    statuses = {name: status for _, _, name, status in progress_events}
    assert statuses["熱田神宮"] == "uploaded"
    assert statuses["名古屋車站"] == "skipped"
    assert statuses["大須觀音"] == "uploaded"


def test_travel_push_photos_command_handles_failure(mock_gateway: MagicMock, mock_storage: MagicMock) -> None:
    # Simulate gateway upload failure on second call
    mock_gateway.upload_file.side_effect = Exception("Notion API 500: internal error")

    cmd = TravelPushPhotosCommand(gateway=mock_gateway, storage=mock_storage)
    summary = cmd.execute_sync(database_name="名古屋之旅", concurrency=1, delay=0.0)

    assert summary.total_items == 3
    assert summary.success_count == 0
    assert summary.failed_count == 2
    assert summary.skipped_count == 1
    assert "internal error" in (summary.items[0].error_message or "")


def test_travel_push_photos_command_empty_manifest(mock_gateway: MagicMock, mock_storage: MagicMock) -> None:
    mock_storage.read_manifest.return_value = TravelPhotoEnrichSummary(
        database_name="空資料庫",
        provider="playwright",
        total_items=0,
        processed_count=0,
        skipped_count=0,
        success_count=0,
        failed_count=0,
        items=[],
    )

    cmd = TravelPushPhotosCommand(gateway=mock_gateway, storage=mock_storage)
    summary = cmd.execute_sync(database_name="空資料庫")

    assert summary.total_items == 0
    assert summary.success_count == 0
    assert mock_gateway.upload_file.call_count == 0

    assert summary.success_count == 0
    assert mock_gateway.upload_file.call_count == 0
