from __future__ import annotations

from unittest.mock import MagicMock
import pytest

from notion_db_manager.core.exceptions import AmbiguousDatabaseError, DomainError
from notion_db_manager.domain.models import DatabaseQuery, PageReference
from notion_db_manager.infrastructure.notion.gateway import NotionGatewayImpl


def test_locate_database_by_id() -> None:
    mock_client = MagicMock()
    mock_client.request.return_value = {
        "id": "db-direct-id",
        "title": [{"plain_text": "Direct DB"}],
        "properties": {
            "Name": {"type": "title", "title": {}},
            "__NDM_INDEX__": {"type": "number", "number": {}},
        },
    }
    gw = NotionGatewayImpl(client=mock_client)
    db = gw.locate_database(DatabaseQuery(database_id="db-direct-id"))

    assert db.id == "db-direct-id"
    assert db.name == "Direct DB"
    mock_client.request.assert_called_once_with("GET", "/databases/db-direct-id")


def test_locate_database_ambiguous_error() -> None:
    mock_client = MagicMock()
    # Mock /search for database returns 2 databases with same name
    mock_client.request.side_effect = [
        # Call 1: search databases
        {
            "results": [
                {
                    "id": "db-1",
                    "title": [{"plain_text": "行程安排"}],
                    "parent": {"type": "page_id", "page_id": "page-nagoya"},
                },
                {
                    "id": "db-2",
                    "title": [{"plain_text": "行程安排"}],
                    "parent": {"type": "page_id", "page_id": "page-tokyo"},
                },
            ],
            "has_more": False,
        },
        # Call 2: get page title for page-nagoya
        {
            "properties": {
                "title": {"type": "title", "title": [{"plain_text": "名古屋五日遊"}]}
            }
        },
        # Call 3: get page title for page-tokyo
        {
            "properties": {
                "title": {"type": "title", "title": [{"plain_text": "東京跨年行"}]}
            }
        },
    ]
    gw = NotionGatewayImpl(client=mock_client)

    with pytest.raises(AmbiguousDatabaseError) as exc_info:
        gw.locate_database(DatabaseQuery(database_name="行程安排"))

    err = exc_info.value
    assert len(err.candidates) == 2
    assert err.candidates[0]["parent_title"] == "名古屋五日遊"
    assert err.candidates[1]["parent_title"] == "東京跨年行"


def test_locate_database_with_parent_page_filter() -> None:
    mock_client = MagicMock()
    mock_client.request.side_effect = [
        # Call 1: search databases for "行程安排"
        {
            "results": [
                {
                    "id": "db-nagoya",
                    "title": [{"plain_text": "行程安排"}],
                    "parent": {"type": "page_id", "page_id": "c1387d89-9831-4c28-9ea9-952467d3df13"},
                },
                {
                    "id": "db-tokyo",
                    "title": [{"plain_text": "行程安排"}],
                    "parent": {"type": "page_id", "page_id": "ffffffff-9831-4c28-9ea9-952467d3df13"},
                },
            ],
            "has_more": False,
        },
        # Call 2: search page for "名古屋五日遊"
        {
            "results": [
                {
                    "id": "c1387d89-9831-4c28-9ea9-952467d3df13",
                    "properties": {
                        "title": {"type": "title", "title": [{"plain_text": "名古屋五日遊"}]}
                    },
                }
            ],
            "has_more": False,
        },
        # Call 3: get_database("db-nagoya")
        {
            "id": "db-nagoya",
            "title": [{"plain_text": "行程安排"}],
            "properties": {
                "Name": {"type": "title", "title": {}},
                "__NDM_INDEX__": {"type": "number", "number": {}},
            },
            "parent": {"type": "page_id", "page_id": "c1387d89-9831-4c28-9ea9-952467d3df13"},
        },
    ]
    gw = NotionGatewayImpl(client=mock_client)

    query = DatabaseQuery(
        database_name="行程安排",
        parent_page=PageReference.from_raw("名古屋五日遊"),
    )
    db = gw.locate_database(query)

    assert db.id == "db-nagoya"
    assert db.name == "行程安排"
