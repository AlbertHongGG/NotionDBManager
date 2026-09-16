from __future__ import annotations

import time
from typing import Any

from notion_db_manager.infrastructure.photos.url_enhancer import GooglePhotoUrlEnhancer


class GoogleMapsPageObject:
    """Page Object Model representing Google Maps web interface for place details."""

    PRIMARY_HERO_SELECTOR = 'button[jsaction*="heroHeaderImage"]'
    BACKUP_HERO_SELECTORS = [
        'div[role="main"] button[class*="aoRNld"]',
        'div.ZKCDEc div.RZ66Rb button',
        'button[aria-label$="相片"]',
        'button[aria-label$="Photo"]',
        'button[aria-label$="の写真"]',
    ]
    SEARCH_FEED_ITEM_SELECTOR = 'div[role="feed"] div.Nv2PK a, div[role="feed"] a[href*="/place/"]'

    def __init__(self, page: Any, timeout_ms: int = 20000) -> None:
        self.page = page
        self.timeout_ms = timeout_ms

    def navigate(self, target_url: str) -> None:
        """Navigates to the given place URL or Google search URL."""
        self.page.goto(target_url, wait_until="domcontentloaded", timeout=self.timeout_ms)

    def _find_hero_button(self) -> Any:
        """Finds the hero cover photo button using semantic and backup locators."""
        try:
            btn = self.page.wait_for_selector(self.PRIMARY_HERO_SELECTOR, timeout=min(self.timeout_ms, 5000))
            if btn:
                return btn
        except Exception:
            pass

        for selector in self.BACKUP_HERO_SELECTORS:
            try:
                btn = self.page.wait_for_selector(selector, timeout=1500)
                if btn:
                    return btn
            except Exception:
                continue

        return None

    def ensure_detail_view(self) -> None:
        """If the query resulted in a search results list, click the top entry to enter detail view."""
        try:
            feed_item = self.page.wait_for_selector(self.SEARCH_FEED_ITEM_SELECTOR, timeout=2000)
            if feed_item:
                feed_item.click()
                # Wait briefly for transition to place detail pane
                self.page.wait_for_selector('div[role="main"]', timeout=5000)
        except Exception:
            # Already in detail view or no feed present
            pass

    def locate_hero_photo_url(self) -> str | None:
        """Pinpoints the hero cover photo button and extracts its legitimate photo URL."""
        hero_btn = self._find_hero_button()
        if not hero_btn:
            # Maybe query landed on search results list; try entering first item
            self.ensure_detail_view()
            hero_btn = self._find_hero_button()

        if not hero_btn:
            return None

        # Wait for the child img tag inside the hero button
        try:
            img_elem = hero_btn.wait_for_selector("img", timeout=5000)
            if not img_elem:
                return None
        except Exception:
            return None

        # Poll briefly until src is loaded with a legitimate photo URL
        src: str | None = None
        for _ in range(15):
            src = img_elem.get_attribute("src")
            if src and src.startswith("http") and GooglePhotoUrlEnhancer.is_valid_place_photo(src):
                return src
            time.sleep(0.2)

        # Final check if src is a valid place photo
        if src and GooglePhotoUrlEnhancer.is_valid_place_photo(src):
            return src

        return None
