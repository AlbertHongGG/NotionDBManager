from __future__ import annotations

import pytest

from notion_db_manager.core.exceptions import ValidationError
from notion_db_manager.domain.models.query import DatabaseQuery, PageReference, extract_uuid


def test_extract_uuid() -> None:
    # 32 hex chars
    raw_hex = "c1387d8998314c289ea9952467d3df13"
    assert extract_uuid(raw_hex) == "c1387d89-9831-4c28-9ea9-952467d3df13"

    # Standard UUID with dashes
    std_uuid = "c1387d89-9831-4c28-9ea9-952467d3df13"
    assert extract_uuid(std_uuid) == "c1387d89-9831-4c28-9ea9-952467d3df13"

    # Notion URL with title prefix
    notion_url = "https://www.notion.so/myworkspace/Nagoya-Trip-c1387d8998314c289ea9952467d3df13?pvs=4"
    assert extract_uuid(notion_url) == "c1387d89-9831-4c28-9ea9-952467d3df13"

    # Plain text without UUID
    assert extract_uuid("Just a page title") is None


def test_page_reference_parsing() -> None:
    # Title
    ref_title = PageReference.from_raw("Nagoya Trip")
    assert ref_title.title == "Nagoya Trip"
    assert ref_title.page_id is None

    # UUID
    ref_id = PageReference.from_raw("c1387d89-9831-4c28-9ea9-952467d3df13")
    assert ref_id.page_id == "c1387d89-9831-4c28-9ea9-952467d3df13"
    assert ref_id.title is None

    # Notion URL
    ref_url = PageReference.from_raw(
        "https://www.notion.so/Nagoya-c1387d8998314c289ea9952467d3df13"
    )
    assert ref_url.page_id == "c1387d89-9831-4c28-9ea9-952467d3df13"
    assert ref_url.title is None

    with pytest.raises(ValidationError):
        PageReference.from_raw("")


def test_database_query() -> None:
    q1 = DatabaseQuery(database_name="Tasks")
    assert q1.database_name == "Tasks"

    # Normalize database_id URL
    q2 = DatabaseQuery(
        database_id="https://www.notion.so/workspace/Tasks-c1387d8998314c289ea9952467d3df13?v=1"
    )
    assert q2.database_id == "c1387d89-9831-4c28-9ea9-952467d3df13"

    # Error when both are missing
    with pytest.raises(ValidationError):
        DatabaseQuery()
