from __future__ import annotations

import pytest

from notion_db_manager.domain.models.page import Page
from notion_db_manager.domain.places import (
    EnrichItemResult,
    PhotoEnrichSummary,
    PhotoProviderType,
    PlaceItem,
    PlacePhoto,
)
from notion_db_manager.domain.properties import MultiSelectProperty, RichTextProperty, TitleProperty, UrlProperty


def test_place_item_from_page() -> None:
    page = Page(
        id="page-123",
        index=6,
        properties={
            "地點": TitleProperty("手長足長像"),
            "地點日文": RichTextProperty("足長像"),
            "屬性": MultiSelectProperty(["景點", "拍照"]),
            "導航": UrlProperty("https://maps.app.goo.gl/example"),
        },
    )

    item = PlaceItem.from_page(page)
    assert item.page_id == "page-123"
    assert item.index == 6
    assert item.name == "手長足長像"
    assert item.alias == "足長像"
    assert item.categories == ["景點", "拍照"]
    assert item.navigation_url == "https://maps.app.goo.gl/example"
    assert item.best_search_query() == "足長像"


def test_place_item_best_search_query_fallback() -> None:
    page = Page(
        id="page-456",
        index=1,
        properties={
            "地點": TitleProperty("桃園機場"),
            "屬性": MultiSelectProperty(["交通"]),
        },
    )
    item = PlaceItem.from_page(page)
    assert item.alias is None
    assert item.best_search_query() == "桃園機場"


def test_place_item_is_target_default_all() -> None:
    # Default without allowed_categories includes everything (even 交通)
    transport_item = PlaceItem(
        page_id="p1", index=1, name="高山車站", categories=["交通"]
    )
    assert transport_item.is_target() is True
    assert transport_item.is_target(set()) is True

    # With filtered categories
    assert transport_item.is_target({"景點", "用餐"}) is False

    scenic_item = PlaceItem(
        page_id="p2", index=2, name="宮川朝市", categories=["購物", "景點"]
    )
    assert scenic_item.is_target({"景點"}) is True


def test_place_photo_value_object() -> None:
    photo = PlacePhoto(
        data=b"imagebytes",
        mime_type="image/jpeg",
        extension="jpg",
        source_url="https://lh3.googleusercontent.com/test",
        width=1200,
        height=800,
        author="John Doe",
    )
    assert photo.extension == "jpg"
    assert photo.width == 1200
    with pytest.raises(AttributeError):
        # Frozen dataclass cannot be mutated
        photo.width = 1000  # type: ignore[misc]


def test_photo_enrich_summary_to_dict() -> None:
    summary = PhotoEnrichSummary(
        database_name="行程安排",
        provider="google",
        total_items=10,
        processed_count=5,
        skipped_count=5,
        success_count=5,
        failed_count=0,
        items=[
            EnrichItemResult(
                index=1,
                page_id="p1",
                name="手長足長像",
                status="success",
                categories=["景點"],
                local_path="output/images/行程安排/01_手長足長像.jpg",
                source_url="https://example.com/img.jpg",
            )
        ],
    )
    data = summary.to_dict()
    assert data["database_name"] == "行程安排"
    assert data["provider"] == "google"
    assert len(data["items"]) == 1
    assert data["items"][0]["status"] == "success"
