from __future__ import annotations

import pytest

from notion_db_manager.domain.models.page import Page
from notion_db_manager.domain.properties import MultiSelectProperty, RichTextProperty, TitleProperty, UrlProperty
from notion_db_manager.domain.travel import (
    EnrichItemResult,
    PhotoProviderType,
    PlaceItem,
    PlacePhoto,
    TravelPhotoEnrichSummary,
)


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
    summary = TravelPhotoEnrichSummary(
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
    assert data["items"][0]["status"] == "success"


def test_place_item_navigation_url_priority() -> None:
    # Item with valid Google Maps short link
    item_with_maps = PlaceItem(
        page_id="p1",
        index=1,
        name="手長足長像",
        alias="足長像",
        navigation_url="https://maps.app.goo.gl/example123",
    )
    assert item_with_maps.has_valid_maps_url() is True
    assert item_with_maps.best_target_url() == "https://maps.app.goo.gl/example123"

    # Item with full google maps link
    item_with_full_maps = PlaceItem(
        page_id="p2",
        index=2,
        name="名古屋城",
        navigation_url="https://www.google.com/maps/place/%E5%90%8D%E5%8F%A4%E5%B1%8B%E5%9F%8E/",
    )
    assert item_with_full_maps.has_valid_maps_url() is True
    assert "google.com/maps/place" in item_with_full_maps.best_target_url()

    # Item without navigation URL -> search query fallback
    item_no_url = PlaceItem(
        page_id="p3",
        index=3,
        name="中部國際機場",
        alias="中部国際空港 セントレア",
        navigation_url=None,
    )
    assert item_no_url.has_valid_maps_url() is False
    assert "https://www.google.com/maps/search/" in item_no_url.best_target_url()
    assert "%E4%B8%AD%E9%83%A8%E5%9B%BD%E9%9A%9B%E7%A9%BA%E6%B8%AF" in item_no_url.best_target_url()


def test_travel_context_value_object() -> None:
    from pathlib import Path
    from notion_db_manager.domain.models import Database
    from notion_db_manager.domain.travel import TravelContext

    db = Database(id="db_123", name="行程安排", properties={}, title_property_name="地點")
    context = TravelContext(
        database=db,
        images_dir=Path("output/images/行程安排"),
        manifest_path=Path("output/images/行程安排/manifest.json"),
    )

    assert context.database.name == "行程安排"
    assert context.images_dir == Path("output/images/行程安排")
    assert context.manifest_path == Path("output/images/行程安排/manifest.json")

    with pytest.raises(AttributeError):
        context.images_dir = Path("other")  # type: ignore[misc]


def test_file_property_has_files() -> None:
    from notion_db_manager.domain.properties import FileProperty

    empty_prop = FileProperty([])
    assert empty_prop.has_files() is False

    none_prop = FileProperty(None)
    assert none_prop.has_files() is False

    filled_prop = FileProperty([{"name": "photo.jpg", "url": "https://example.com/p.jpg"}])
    assert filled_prop.has_files() is True


def test_place_item_has_photo_detection() -> None:
    from notion_db_manager.domain.properties import FileProperty

    # Case 1: Page with populated "照片" property
    page_with_photo = Page(
        id="p1",
        index=1,
        properties={
            "地點": TitleProperty("手長足長像"),
            "照片": FileProperty([{"name": "01.jpg", "url": "https://example.com/01.jpg"}]),
        },
    )
    item1 = PlaceItem.from_page(page_with_photo)
    assert item1.has_photo is True

    # Case 2: Page with empty "照片" property
    page_empty_photo = Page(
        id="p2",
        index=2,
        properties={
            "地點": TitleProperty("高山車站"),
            "照片": FileProperty([]),
        },
    )
    item2 = PlaceItem.from_page(page_empty_photo)
    assert item2.has_photo is False

    # Case 3: Page without "照片" property at all
    page_no_photo_prop = Page(
        id="p3",
        index=3,
        properties={
            "地點": TitleProperty("宮川朝市"),
        },
    )
    item3 = PlaceItem.from_page(page_no_photo_prop)
    assert item3.has_photo is False


