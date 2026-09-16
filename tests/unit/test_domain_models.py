from __future__ import annotations

import pytest

from notion_db_manager.core.exceptions import ValidationError
from notion_db_manager.domain.models import (
    Database,
    Document,
    DocumentMeta,
    Page,
    PropertyDefinition,
)
from notion_db_manager.domain.properties import NumberProperty, TitleProperty


def test_database_validation() -> None:
    db = Database(
        id="db-123",
        name="Tasks",
        properties={
            "Name": PropertyDefinition(name="Name", property_type="title", raw_config={}),
            "Score": PropertyDefinition(name="Score", property_type="number", raw_config={}),
        },
        title_property_name="Name",
    )
    assert db.has_property("Name")
    assert db.has_property("Score")
    assert not db.has_property("NonExistent")

    db.validate_columns(["Name", "Score"])
    with pytest.raises(ValidationError):
        db.validate_columns(["Name", "UnknownCol"])


def test_page_to_notion_payload() -> None:
    db = Database(
        id="db-123",
        name="Tasks",
        properties={
            "Name": PropertyDefinition(name="Name", property_type="title", raw_config={}),
            "Score": PropertyDefinition(name="Score", property_type="number", raw_config={}),
            "Extra": PropertyDefinition(name="Extra", property_type="number", raw_config={}),
            "__NDM_INDEX__": PropertyDefinition(name="__NDM_INDEX__", property_type="number", raw_config={}),
        },
        title_property_name="Name",
    )

    page = Page(
        index=3,
        properties={
            "Name": TitleProperty("Task C"),
            "Score": NumberProperty(99),
        },
    )

    # Without erase_missing_writable
    payload = page.to_notion_payload(db, erase_missing_writable=False)
    assert payload["Name"] == {"title": [{"type": "text", "text": {"content": "Task C"}}]}
    assert payload["Score"] == {"number": 99}
    assert payload["__NDM_INDEX__"] == {"number": 3}
    assert "Extra" not in payload

    # With erase_missing_writable
    payload_erase = page.to_notion_payload(db, erase_missing_writable=True)
    assert payload_erase["Extra"] == {"number": None}


def test_document_roundtrip() -> None:
    meta = DocumentMeta(
        database_id="db-123",
        database_name="Tasks",
        export_type="full",
    )
    page1 = Page(index=1, properties={"Name": TitleProperty("Task 1"), "Score": NumberProperty(10)})
    page2 = Page(index=2, properties={"Name": TitleProperty("Task 2"), "Score": NumberProperty(20)})
    doc = Document(meta=meta, pages=[page1, page2])

    data = doc.to_dict()
    assert data["meta"]["database_id"] == "db-123"
    assert len(data["rows"]) == 2
    assert data["rows"][0]["index"] == 1
    assert data["rows"][0]["properties"]["Name"]["value"] == "Task 1"

    restored = Document.from_dict(data)
    assert restored.meta.database_id == "db-123"
    assert len(restored.pages) == 2
    assert restored.pages[0].properties["Name"].value == "Task 1"
    assert restored.pages[1].properties["Score"].value == 20
