from __future__ import annotations

import pytest

from notion_db_manager.core.exceptions import ValidationError
from notion_db_manager.domain.properties import (
    CheckboxProperty,
    DateProperty,
    EmailProperty,
    FileProperty,
    MultiSelectProperty,
    NumberProperty,
    PeopleProperty,
    PhoneNumberProperty,
    PropertyRegistry,
    ReadOnlyProperty,
    RelationProperty,
    RichTextProperty,
    SelectProperty,
    StatusProperty,
    TitleProperty,
    UrlProperty,
)


def test_title_property() -> None:
    prop = TitleProperty("Hello Notion")
    assert prop.value == "Hello Notion"
    assert prop.to_storage_dict() == {"type": "title", "value": "Hello Notion"}
    assert prop.to_notion_payload() == {"title": [{"type": "text", "text": {"content": "Hello Notion"}}]}
    assert prop.get_empty_notion_payload() == {"title": []}

    from_notion = TitleProperty.from_notion(
        {"title": [{"plain_text": "Hello "}, {"plain_text": "Notion"}]}
    )
    assert from_notion.value == "Hello Notion"


def test_rich_text_chunking() -> None:
    long_text = "a" * 2500
    prop = RichTextProperty(long_text)
    payload = prop.to_notion_payload()
    assert len(payload["rich_text"]) == 2
    assert payload["rich_text"][0]["text"]["content"] == "a" * 1900
    assert payload["rich_text"][1]["text"]["content"] == "a" * 600


def test_number_property() -> None:
    prop = NumberProperty(42.5)
    assert prop.value == 42.5
    assert prop.to_storage_dict() == {"type": "number", "value": 42.5}
    assert prop.to_notion_payload() == {"number": 42.5}
    assert prop.get_empty_notion_payload() == {"number": None}

    from_storage = NumberProperty.from_storage({"type": "number", "value": 100})
    assert from_storage.value == 100


def test_select_and_status_properties() -> None:
    sel = SelectProperty("High")
    assert sel.to_storage_dict() == {"type": "select", "value": "High"}
    assert sel.to_notion_payload() == {"select": {"name": "High"}}
    assert sel.get_empty_notion_payload() == {"select": None}

    stat = StatusProperty("Done")
    assert stat.to_storage_dict() == {"type": "status", "value": "Done"}
    assert stat.to_notion_payload() == {"status": {"name": "Done"}}
    assert stat.get_empty_notion_payload() == {"status": None}


def test_multi_select_property() -> None:
    ms = MultiSelectProperty(["Tag1", "Tag2"])
    assert ms.to_storage_dict() == {"type": "multi_select", "value": ["Tag1", "Tag2"]}
    assert ms.to_notion_payload() == {
        "multi_select": [{"name": "Tag1"}, {"name": "Tag2"}]
    }
    assert ms.get_empty_notion_payload() == {"multi_select": []}


def test_primitive_properties() -> None:
    cb = CheckboxProperty(True)
    assert cb.to_storage_dict() == {"type": "checkbox", "value": True}
    assert cb.to_notion_payload() == {"checkbox": True}
    assert cb.get_empty_notion_payload() == {"checkbox": False}

    dt = DateProperty("2026-09-17")
    assert dt.to_notion_payload() == {"date": {"start": "2026-09-17"}}
    assert dt.get_empty_notion_payload() == {"date": None}

    url = UrlProperty("https://google.com")
    assert url.to_notion_payload() == {"url": "https://google.com"}
    assert url.get_empty_notion_payload() == {"url": None}

    em = EmailProperty("test@example.com")
    assert em.to_notion_payload() == {"email": "test@example.com"}
    assert em.get_empty_notion_payload() == {"email": None}

    phone = PhoneNumberProperty("+123456789")
    assert phone.to_notion_payload() == {"phone_number": "+123456789"}
    assert phone.get_empty_notion_payload() == {"phone_number": None}


def test_relation_and_people() -> None:
    rel = RelationProperty(["page-id-1", "page-id-2"])
    assert rel.to_notion_payload() == {
        "relation": [{"id": "page-id-1"}, {"id": "page-id-2"}]
    }
    assert rel.get_empty_notion_payload() == {"relation": []}

    peop = PeopleProperty(["user-id-1"])
    assert peop.to_notion_payload() == {"people": [{"id": "user-id-1"}]}
    assert peop.get_empty_notion_payload() == {"people": []}


def test_file_property() -> None:
    files = FileProperty([{"name": "file.pdf", "url": "https://example.com/file.pdf"}])
    assert files.to_notion_payload() == {
        "files": [
            {
                "name": "file.pdf",
                "type": "external",
                "external": {"url": "https://example.com/file.pdf"},
            }
        ]
    }
    assert files.get_empty_notion_payload() == {"files": []}


def test_file_property_upload() -> None:
    files = FileProperty([{"name": "photo.jpg", "type": "file_upload", "file_upload_id": "fu_123"}])
    assert files.to_notion_payload() == {
        "files": [
            {
                "name": "photo.jpg",
                "type": "file_upload",
                "file_upload": {"id": "fu_123"},
            }
        ]
    }

    # Test from_notion
    notion_raw = {
        "files": [
            {
                "name": "uploaded.png",
                "type": "file_upload",
                "file_upload": {"id": "upload_456"},
            }
        ]
    }
    deserialized = FileProperty.from_notion(notion_raw)
    assert deserialized.value == [
        {
            "name": "uploaded.png",
            "type": "file_upload",
            "file_upload_id": "upload_456",
        }
    ]


def test_readonly_property() -> None:
    ro = ReadOnlyProperty("formula", 123)
    assert ro.is_readonly is True
    assert ro.to_storage_dict() == {"type": "formula", "value": 123, "readonly": True}

    with pytest.raises(ValidationError):
        ro.to_notion_payload()

    with pytest.raises(ValidationError):
        ro.get_empty_notion_payload()


def test_property_registry_roundtrip() -> None:
    raw_notion = {
        "type": "status",
        "status": {"id": "s1", "name": "In Progress", "color": "blue"},
    }
    prop = PropertyRegistry.from_notion(raw_notion)
    assert isinstance(prop, StatusProperty)
    assert prop.value == "In Progress"

    storage_dict = prop.to_storage_dict()
    assert storage_dict == {"type": "status", "value": "In Progress"}

    restored = PropertyRegistry.from_storage(storage_dict)
    assert isinstance(restored, StatusProperty)
    assert restored.value == "In Progress"
