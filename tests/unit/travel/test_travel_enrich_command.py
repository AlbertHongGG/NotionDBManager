from __future__ import annotations

import asyncio
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock
import pytest

from notion_db_manager.application.interfaces.photo_provider import PhotoStorage, PlacePhotoProvider
from notion_db_manager.application.commands.travel.enrich_photos import TravelEnrichPhotosCommand
from notion_db_manager.core.exceptions import InfrastructureError
from notion_db_manager.domain.models.page import Page
from notion_db_manager.domain.properties import MultiSelectProperty, TitleProperty
from notion_db_manager.domain.travel import PlaceItem, PlacePhoto


@pytest.fixture
def mock_storage() -> MagicMock:
    storage = MagicMock(spec=PhotoStorage)
    storage.save_photo.return_value = Path("output/images/test/01_test.jpg")
    storage.save_manifest.return_value = Path("output/images/test/manifest.json")
    return storage


def test_travel_enrich_photos_command_success(mock_storage: MagicMock) -> None:
    provider = MagicMock(spec=PlacePhotoProvider)
    dummy_photo = PlacePhoto(
        data=b"img_bytes",
        mime_type="image/jpeg",
        extension="jpg",
        source_url="https://example.com/img.jpg",
    )
    provider.fetch_photo = AsyncMock(return_value=dummy_photo)

    pages = [
        Page(
            id="p1",
            index=1,
            properties={
                "地點": TitleProperty("手長足長像"),
                "屬性": MultiSelectProperty(["景點"]),
            },
        ),
        Page(
            id="p2",
            index=2,
            properties={
                "地點": TitleProperty("高山車站"),
                "屬性": MultiSelectProperty(["交通"]),
            },
        ),
    ]

    cmd = TravelEnrichPhotosCommand(provider, mock_storage)
    # Default without categories: all items are processed (including 交通)
    summary = cmd.execute_sync("行程安排", pages, provider_name="google", concurrency=2)

    assert summary.total_items == 2
    assert summary.processed_count == 2
    assert summary.success_count == 2
    assert summary.skipped_count == 0
    assert len(summary.items) == 2
    assert summary.items[0].status == "success"
    assert summary.items[1].status == "success"
    assert mock_storage.save_photo.call_count == 2
    assert mock_storage.save_manifest.call_count == 1


def test_travel_enrich_photos_command_with_category_filter(mock_storage: MagicMock) -> None:
    provider = MagicMock(spec=PlacePhotoProvider)
    dummy_photo = PlacePhoto(
        data=b"img",
        mime_type="image/jpeg",
        extension="jpg",
        source_url="https://example.com/img.jpg",
    )
    provider.fetch_photo = AsyncMock(return_value=dummy_photo)

    pages = [
        Page(
            id="p1",
            index=1,
            properties={
                "地點": TitleProperty("手長足長像"),
                "屬性": MultiSelectProperty(["景點"]),
            },
        ),
        Page(
            id="p2",
            index=2,
            properties={
                "地點": TitleProperty("高山車站"),
                "屬性": MultiSelectProperty(["交通"]),
            },
        ),
    ]

    cmd = TravelEnrichPhotosCommand(provider, mock_storage)
    # Filter only "景點"
    summary = cmd.execute_sync("行程安排", pages, categories=["景點"], provider_name="google")

    assert summary.total_items == 2
    assert summary.processed_count == 1
    assert summary.skipped_count == 1
    assert summary.success_count == 1
    assert summary.items[0].status == "success"
    assert summary.items[1].status == "skipped"
    assert mock_storage.save_photo.call_count == 1


def test_travel_enrich_photos_fail_fast_on_provider_error(mock_storage: MagicMock) -> None:
    provider = MagicMock(spec=PlacePhotoProvider)
    provider.fetch_photo = AsyncMock(side_effect=InfrastructureError("Google Places API 認證失敗"))

    pages = [
        Page(
            id="p1",
            index=1,
            properties={
                "地點": TitleProperty("手長足長像"),
                "屬性": MultiSelectProperty(["景點"]),
            },
        )
    ]

    cmd = TravelEnrichPhotosCommand(provider, mock_storage)
    with pytest.raises(InfrastructureError) as exc_info:
        cmd.execute_sync("行程安排", pages, provider_name="google")

    assert "Google Places API 認證失敗" in str(exc_info.value)
    # Since it failed fast, nothing was saved
    assert mock_storage.save_photo.call_count == 0


def test_travel_enrich_photos_worker_pool_concurrency_and_ordering(mock_storage: MagicMock) -> None:
    provider = MagicMock(spec=PlacePhotoProvider)

    # Simulate variable latency: item 1 takes 0.05s, item 2 takes 0.01s (finishes earlier)
    async def delayed_fetch(item: PlaceItem) -> PlacePhoto:
        delay = 0.05 if item.index == 1 else 0.01
        await asyncio.sleep(delay)
        return PlacePhoto(
            data=f"img_{item.index}".encode(),
            mime_type="image/jpeg",
            extension="jpg",
            source_url=f"https://example.com/img{item.index}.jpg",
        )

    provider.fetch_photo = AsyncMock(side_effect=delayed_fetch)

    pages = [
        Page(
            id=f"p{i}",
            index=i,
            properties={"地點": TitleProperty(f"地點 {i}")},
        )
        for i in range(1, 5)
    ]

    cmd = TravelEnrichPhotosCommand(provider, mock_storage)
    summary = cmd.execute_sync("行程安排", pages, provider_name="google", concurrency=4)

    assert summary.total_items == 4
    assert summary.success_count == 4
    # Ensure final results are in exact index order despite variable completion time
    assert [r.index for r in summary.items] == [1, 2, 3, 4]
    assert [r.name for r in summary.items] == ["地點 1", "地點 2", "地點 3", "地點 4"]


def test_travel_enrich_photos_empty_pages(mock_storage: MagicMock) -> None:
    provider = MagicMock(spec=PlacePhotoProvider)
    cmd = TravelEnrichPhotosCommand(provider, mock_storage)
    summary = cmd.execute_sync("行程安排", [], provider_name="google", concurrency=2)

    assert summary.total_items == 0
    assert summary.processed_count == 0
    assert summary.items == []
    assert mock_storage.save_manifest.call_count == 1
