from __future__ import annotations
from dataclasses import dataclass, field

from notion_db_manager.domain.models.page import Page
from notion_db_manager.domain.properties import MultiSelectProperty, TitleProperty


@dataclass(slots=True)
class PlaceItem:
    """Domain Entity representing a place record extracted from a Travel Notion Template page."""

    page_id: str
    index: int
    name: str
    alias: str | None = None
    categories: list[str] = field(default_factory=list)
    navigation_url: str | None = None

    @classmethod
    def from_page(cls, page: Page) -> PlaceItem:
        props = page.properties

        # Extract name (Title: "地點")
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

        # Extract categories ("屬性" or multi-select: 景點, 用餐, 住宿, 交通, etc.)
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

    def has_valid_maps_url(self) -> bool:
        """Determines if navigation_url contains a valid Google Maps link."""
        if not self.navigation_url:
            return False
        url_lower = self.navigation_url.lower().strip()
        return (
            "maps.app.goo.gl" in url_lower
            or "goo.gl/maps" in url_lower
            or "google.com/maps" in url_lower
            or "maps.google." in url_lower
            or ("maps" in url_lower and url_lower.startswith("http"))
        )

    def best_target_url(self) -> str:
        """Returns direct navigation URL if valid Google Maps link, otherwise generates search URL."""
        if self.has_valid_maps_url():
            assert self.navigation_url is not None
            return self.navigation_url.strip()
        import urllib.parse
        query = self.best_search_query()
        return f"https://www.google.com/maps/search/{urllib.parse.quote(query)}"
