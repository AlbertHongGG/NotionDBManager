from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from notion_db_manager.domain.models.page import Page
from notion_db_manager.domain.properties import MultiSelectProperty, RichTextProperty, TitleProperty, UrlProperty


class PhotoProviderType(str, Enum):
    PLAYWRIGHT = "playwright"
    GOOGLE = "google"


@dataclass(slots=True)
class PlaceItem:
    """Domain Entity representing a place record extracted from a Notion page."""

    page_id: str
    index: int
    name: str
    alias: str | None = None
    categories: list[str] = field(default_factory=list)
    navigation_url: str | None = None

    @classmethod
    def from_page(cls, page: Page) -> PlaceItem:
        props = page.properties

        # Extract name (Title)
        name = ""
        for prop in props.values():
            if isinstance(prop, TitleProperty):
                name = str(prop.value) if prop.value else ""
                break
        if not name and "地點" in props:
            val = props["地點"].value
            name = str(val) if val else ""

        # Extract alias ("地點日文" or rich text)
        alias: str | None = None
        if "地點日文" in props:
            raw_alias = props["地點日文"].value
            if raw_alias:
                alias = str(raw_alias).strip()

        # Extract categories ("屬性" or multi-select)
        categories: list[str] = []
        if "屬性" in props:
            cat_prop = props["屬性"]
            if isinstance(cat_prop, MultiSelectProperty) and isinstance(cat_prop.value, list):
                categories = [str(c) for c in cat_prop.value]
            elif isinstance(cat_prop.value, list):
                categories = [str(c) for c in cat_prop.value]
            elif cat_prop.value:
                categories = [str(cat_prop.value)]

        # Extract navigation URL ("導航" or url)
        navigation_url: str | None = None
        if "導航" in props:
            url_prop = props["導航"]
            if url_prop.value:
                navigation_url = str(url_prop.value).strip()

        return cls(
            page_id=page.id or "",
            index=page.index,
            name=name,
            alias=alias,
            categories=categories,
            navigation_url=navigation_url,
        )

    def is_target(self, allowed_categories: set[str] | None = None) -> bool:
        """Determines if this place matches the category filter.

        If allowed_categories is None or empty, all items are considered targets (including transportation).
        """
        if not allowed_categories:
            return True
        return any(cat in allowed_categories for cat in self.categories)

    def best_search_query(self) -> str:
        """Derives the best search term for querying place photos."""
        if self.alias and self.alias.strip():
            return self.alias.strip()
        return self.name.strip()


@dataclass(frozen=True, slots=True)
class PlacePhoto:
    """Value Object encapsulating a downloaded place photo."""

    data: bytes
    mime_type: str
    extension: str
    source_url: str
    width: int | None = None
    height: int | None = None
    author: str | None = None


@dataclass(slots=True)
class EnrichItemResult:
    """Value Object representing the enrichment outcome for a single place."""

    index: int
    page_id: str
    name: str
    status: str  # "success" | "skipped" | "failed"
    categories: list[str] = field(default_factory=list)
    local_path: str | None = None
    source_url: str | None = None
    error_message: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "index": self.index,
            "page_id": self.page_id,
            "name": self.name,
            "status": self.status,
            "categories": self.categories,
            "local_path": self.local_path,
            "source_url": self.source_url,
            "error_message": self.error_message,
        }


@dataclass(slots=True)
class PhotoEnrichSummary:
    """Aggregate report of a photo enrichment run."""

    database_name: str
    provider: str
    total_items: int
    processed_count: int
    skipped_count: int
    success_count: int
    failed_count: int
    items: list[EnrichItemResult] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "database_name": self.database_name,
            "provider": self.provider,
            "total_items": self.total_items,
            "processed_count": self.processed_count,
            "skipped_count": self.skipped_count,
            "success_count": self.success_count,
            "failed_count": self.failed_count,
            "items": [item.to_dict() for item in self.items],
        }
