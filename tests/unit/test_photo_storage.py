from __future__ import annotations

import json
from pathlib import Path
import pytest

from notion_db_manager.domain.travel import EnrichItemResult, TravelPhotoEnrichSummary, PlaceItem, PlacePhoto

from notion_db_manager.infrastructure.photos.storage import LocalPhotoStorage, sanitize_filename
from notion_db_manager.infrastructure.storage.path_resolver import PathResolver


def test_sanitize_filename() -> None:
    assert sanitize_filename('A/B\\C:D*E?F"G<H>I|J') == "A_B_C_D_E_F_G_H_I_J"
    assert sanitize_filename("   ") == "unnamed"
    assert sanitize_filename("中部電力未來塔") == "中部電力未來塔"


def test_local_photo_storage_save_photo(tmp_path: Path) -> None:
    resolver = PathResolver(base_dir=tmp_path)
    storage = LocalPhotoStorage(path_resolver=resolver)

    item = PlaceItem(
        page_id="p1",
        index=6,
        name="手長足長像",
        categories=["景點"],
    )
    photo = PlacePhoto(
        data=b"fake-image-bytes",
        mime_type="image/jpeg",
        extension="jpg",
        source_url="https://example.com/test.jpg",
    )

    saved_path = storage.save_photo("行程安排", item, photo)
    assert saved_path.is_file()
    assert saved_path.name == "06_手長足長像.jpg"
    assert saved_path.read_bytes() == b"fake-image-bytes"
    assert "images" in saved_path.parts
    assert "行程安排" in saved_path.parts


def test_local_photo_storage_save_manifest(tmp_path: Path) -> None:
    resolver = PathResolver(base_dir=tmp_path)
    storage = LocalPhotoStorage(path_resolver=resolver)

    summary = TravelPhotoEnrichSummary(
        database_name="行程安排",
        provider="playwright",
        total_items=1,
        processed_count=1,
        skipped_count=0,
        success_count=1,
        failed_count=0,
        items=[
            EnrichItemResult(
                index=1,
                page_id="p1",
                name="手長足長像",
                status="success",
                categories=["景點"],
                local_path="output/images/行程安排/01_手長足長像.jpg",
                source_url="https://example.com/test.jpg",
            )
        ],
    )

    manifest_path = storage.save_manifest("行程安排", summary)
    assert manifest_path.is_file()
    assert manifest_path.name == "manifest.json"

    data = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert data["database_name"] == "行程安排"
    assert data["provider"] == "playwright"
    assert len(data["items"]) == 1


def test_local_photo_storage_prepare_directory_clean(tmp_path: Path) -> None:
    resolver = PathResolver(base_dir=tmp_path)
    storage = LocalPhotoStorage(path_resolver=resolver)

    target_dir = storage.get_images_dir("行程安排")
    old_file = target_dir / "old_residual.jpg"
    old_file.write_text("old", encoding="utf-8")
    assert old_file.is_file()

    # prepare_directory with clean=True should delete existing files
    storage.prepare_directory("行程安排", clean=True)
    assert not old_file.exists()
    assert target_dir.is_dir()
