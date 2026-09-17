from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock

import pytest

from notion_db_manager.application.services.travel_context_resolver import TravelContextResolver
from notion_db_manager.domain.models import Database, DatabaseQuery


def test_travel_context_resolver_standard(tmp_path: Path) -> None:
    fake_gateway = MagicMock()
    fake_storage = MagicMock()

    db = Database(id="db-456", name="行程安排", properties={}, title_property_name="地點")
    fake_gateway.locate_database.return_value = db
    fake_storage.get_images_dir.return_value = tmp_path / "output" / "images" / "行程安排"

    context = TravelContextResolver.resolve(
        gateway=fake_gateway,
        storage=fake_storage,
        database_name="行程表",
        page="日本 - 名古屋",
    )

    assert context.database == db
    assert context.database.name == "行程安排"
    assert context.images_dir == tmp_path / "output" / "images" / "行程安排"
    assert context.manifest_path == tmp_path / "output" / "images" / "行程安排" / "manifest.json"

    # Verify query passed to locate_database
    call_query = fake_gateway.locate_database.call_args[0][0]
    assert isinstance(call_query, DatabaseQuery)
    assert call_query.database_name == "行程表"
    assert call_query.parent_page is not None
    assert call_query.parent_page.title == "日本 - 名古屋"


def test_travel_context_resolver_with_custom_manifest(tmp_path: Path) -> None:
    fake_gateway = MagicMock()
    fake_storage = MagicMock()

    db = Database(id="db-456", name="行程安排", properties={}, title_property_name="地點")
    fake_gateway.locate_database.return_value = db

    custom_manifest = tmp_path / "custom" / "my_manifest.json"

    context = TravelContextResolver.resolve(
        gateway=fake_gateway,
        storage=fake_storage,
        database_name="行程安排",
        custom_manifest=custom_manifest,
    )

    assert context.database == db
    assert context.manifest_path == custom_manifest
    assert context.images_dir == custom_manifest.parent
    fake_storage.get_images_dir.assert_not_called()
