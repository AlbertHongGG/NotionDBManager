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
