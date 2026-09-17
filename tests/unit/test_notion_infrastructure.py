from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock
import pytest

from notion_db_manager.core.exceptions import DomainError
from notion_db_manager.domain.models import Page
from notion_db_manager.domain.properties import TitleProperty
from notion_db_manager.infrastructure.notion.gateway import NotionGatewayImpl
from notion_db_manager.infrastructure.notion.mappers import NotionMapper


def test_notion_mapper_database() -> None:
    raw_db = {
        "id": "db-abc",
        "title": [{"plain_text": "Project Tasks"}],
        "properties": {
            "Task Name": {"type": "title", "title": {}},
            "Status": {"type": "status", "status": {}},
            "__NDM_INDEX__": {"type": "number", "number": {}},
        },
    }
    db = NotionMapper.database_from_notion(raw_db)
    assert db.id == "db-abc"
    assert db.name == "Project Tasks"
    assert db.title_property_name == "Task Name"
    assert db.has_property("Status")


def test_notion_mapper_missing_title() -> None:
    raw_db = {
        "id": "db-abc",
        "title": [{"plain_text": "Invalid DB"}],
        "properties": {
            "Status": {"type": "status", "status": {}},
        },
    }
    with pytest.raises(DomainError):
        NotionMapper.database_from_notion(raw_db)


def test_notion_gateway_search_and_query() -> None:
    mock_client = MagicMock()
    # Mock /search response
    mock_client.request.side_effect = [
        # Call 1: search
        {
            "results": [
                {
                    "id": "db-123",
                    "title": [{"plain_text": "My Database"}],
                }
            ],
            "has_more": False,
        },
        # Call 2: get_database
        {
            "id": "db-123",
            "title": [{"plain_text": "My Database"}],
            "properties": {
                "Name": {"type": "title", "title": {}},
                "__NDM_INDEX__": {"type": "number", "number": {}},
            },
        },
    ]

    gateway = NotionGatewayImpl(client=mock_client)
    db = gateway.search_database_by_name("My Database")
    assert db.id == "db-123"
    assert db.name == "My Database"


def test_notion_gateway_create_page() -> None:
    mock_client = MagicMock()
    mock_client.request.return_value = {
        "id": "new-page-id",
        "properties": {
            "Name": {"type": "title", "title": [{"plain_text": "New Task"}]},
            "__NDM_INDEX__": {"type": "number", "number": 1},
        },
    }

    raw_db = {
        "id": "db-123",
        "title": [{"plain_text": "My DB"}],
        "properties": {
            "Name": {"type": "title", "title": {}},
            "__NDM_INDEX__": {"type": "number", "number": {}},
        },
    }
    db = NotionMapper.database_from_notion(raw_db)
    gateway = NotionGatewayImpl(client=mock_client)

    new_page = Page(index=1, properties={"Name": TitleProperty("New Task")})
    created = gateway.create_page(db, new_page)
    assert created.id == "new-page-id"
    assert created.index == 1
    assert created.properties["Name"].value == "New Task"


def test_notion_gateway_upload_file() -> None:
    mock_client = MagicMock()
    mock_client.upload_file.return_value = "fu_test_789"

    gateway = NotionGatewayImpl(client=mock_client)
    upload_id = gateway.upload_file("sample.jpg", b"fake_bytes", "image/jpeg")

    assert upload_id == "fu_test_789"
    mock_client.upload_file.assert_called_once_with(
        filename="sample.jpg",
        file_bytes=b"fake_bytes",
        mime_type="image/jpeg",
    )


def test_notion_gateway_archive_pages_in_trash() -> None:
    mock_client = MagicMock()
    gateway = NotionGatewayImpl(client=mock_client)
    gateway.archive_pages(["page-1", "page-2"])

    assert mock_client.request.call_count == 2
    mock_client.request.assert_any_call("PATCH", "/pages/page-1", {"in_trash": True})
    mock_client.request.assert_any_call("PATCH", "/pages/page-2", {"in_trash": True})


def test_notion_mapper_data_source() -> None:
    ds_raw = {
        "id": "ds-456",
        "name": "Trip Schedule DS",
        "parent": {"type": "database_id", "database_id": "db-container-123"},
        "properties": {
            "Item": {"type": "title", "title": {}},
            "__NDM_INDEX__": {"type": "number", "number": {}},
        },
    }
    db_raw = {
        "id": "db-container-123",
        "title": [{"plain_text": "Trip Schedule"}],
        "parent": {"type": "page_id", "page_id": "page-nagoya-789"},
        "data_sources": [{"id": "ds-456", "name": "Trip Schedule DS"}],
    }

    db = NotionMapper.database_from_data_source(ds_raw, db_raw)
    assert db.id == "db-container-123"
    assert db.data_source_id == "ds-456"
    assert db.name == "Trip Schedule"
    assert db.title_property_name == "Item"
    assert db.has_property("__NDM_INDEX__")
    assert db.parent is not None
    assert db.parent.parent_id == "page-nagoya-789"


def test_notion_gateway_data_source_operations() -> None:
    mock_client = MagicMock()
    gateway = NotionGatewayImpl(client=mock_client)

    ds_raw = {
        "id": "ds-456",
        "name": "Trip Schedule DS",
        "parent": {"type": "database_id", "database_id": "db-container-123"},
        "properties": {
            "Item": {"type": "title", "title": {}},
        },
    }
    db_raw = {
        "id": "db-container-123",
        "title": [{"plain_text": "Trip Schedule"}],
        "parent": {"type": "page_id", "page_id": "page-nagoya-789"},
        "data_sources": [{"id": "ds-456", "name": "Trip Schedule DS"}],
    }

    db = NotionMapper.database_from_data_source(ds_raw, db_raw)

    # 1. Test create_page uses parent.data_source_id
    mock_client.request.return_value = {
        "id": "new-row-id",
        "properties": {
            "Item": {"type": "title", "title": [{"plain_text": "Flight"}]},
            "__NDM_INDEX__": {"type": "number", "number": 1},
        },
    }
    page = Page(index=1, properties={"Item": TitleProperty("Flight")})
    created = gateway.create_page(db, page)
    assert created.id == "new-row-id"
    mock_client.request.assert_called_with(
        "POST",
        "/pages",
        {
            "parent": {"data_source_id": "ds-456"},
            "properties": {
                "Item": {"title": [{"type": "text", "text": {"content": "Flight"}}]},
                "__NDM_INDEX__": {"number": 1},
            },
        },
    )

    # 2. Test get_ordered_pages queries /data_sources/{data_source_id}/query
    mock_client.request.return_value = {
        "results": [
            {
                "id": "row-1",
                "properties": {
                    "Item": {"type": "title", "title": [{"plain_text": "Flight"}]},
                    "__NDM_INDEX__": {"type": "number", "number": 1},
                },
            }
        ],
        "has_more": False,
    }
    pages = gateway.get_ordered_pages(db)
    assert len(pages) == 1
    assert pages[0].id == "row-1"
    mock_client.request.assert_called_with(
        "POST",
        "/data_sources/ds-456/query",
        {
            "page_size": 100,
            "sorts": [
                {"property": "__NDM_INDEX__", "direction": "ascending"},
                {"timestamp": "created_time", "direction": "ascending"},
            ],
        },
    )


