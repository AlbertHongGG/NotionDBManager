from __future__ import annotations

import asyncio
from typing import Any

from notion_db_manager.infrastructure.photos.url_enhancer import GooglePhotoUrlEnhancer


class GoogleMapsPageObject:
    """Page Object Model representing Google Maps web interface for place details asynchronously."""

    PRIMARY_HERO_SELECTORS = (
        'button[jsaction*="heroHeaderImage"]',
        'button.aoRNLd',
        'button.aoRNld',
        'div.RZ66Rb button',
        'div[role="main"] button[class*="aoRNld"]',
        'div[role="main"] button[class*="aoRNLd"]',
        'button[aria-label*="相片"]',
        'button[aria-label*="Photo"]',
        'button[aria-label*="写真"]',
        'button[aria-label*="photo"]',
        'button[aria-label*="Street View"]',
        'button[aria-label*="街景"]',
    )
    HERO_BUTTON_GROUP = ", ".join(PRIMARY_HERO_SELECTORS)

    SEARCH_FEED_SELECTORS = (
        'a.hfpxzc',
        'div[role="feed"] a[href*="/place/"]',
        'div[role="feed"] div.Nv2PK a',
    )
    SEARCH_FEED_GROUP = ", ".join(SEARCH_FEED_SELECTORS)

    # Combined race selector for immediate state determination
    COMBINED_SELECTOR = f"{HERO_BUTTON_GROUP}, {SEARCH_FEED_GROUP}"

    def __init__(self, page: Any, timeout_ms: int = 20000) -> None:
        self.page = page
        self.timeout_ms = timeout_ms

    async def navigate(self, target_url: str) -> None:
        """Navigates to the given place URL or Google search URL."""
        await self.page.goto(target_url, wait_until="domcontentloaded", timeout=self.timeout_ms)

    async def _find_hero_button(self) -> Any:
        """Finds the hero cover photo element using semantic locators."""
        try:
            return await self.page.wait_for_selector(self.HERO_BUTTON_GROUP, timeout=min(self.timeout_ms, 5000))
        except Exception:
            return None

    async def ensure_detail_view(self) -> None:
        """If the query resulted in a search results list, click the top entry to enter detail view."""
        try:
            feed_item = await self.page.wait_for_selector(self.SEARCH_FEED_GROUP, timeout=min(self.timeout_ms, 5000))
            if feed_item:
                await feed_item.click()
                await self.page.wait_for_selector('div[role="main"]', timeout=self.timeout_ms)
        except Exception:
            pass

    async def locate_hero_photo_url(self) -> str | None:
        """Pinpoints the hero cover photo button and extracts its legitimate photo URL.

        Concurrently races between detail view hero buttons and search result feed cards,
        eliminating arbitrary sequential wait times and bogus button matches.
        """
        try:
            first_match = await self.page.wait_for_selector(self.COMBINED_SELECTOR, timeout=self.timeout_ms)
        except Exception:
            return None

        if not first_match:
            return None

        tag_name = ""
        try:
            if hasattr(first_match, "evaluate"):
                tag = await first_match.evaluate("el => el.tagName.toLowerCase()")
                if isinstance(tag, str):
                    tag_name = tag
        except Exception:
            pass

        hero_btn = None
        if tag_name == "a":
            # Search feed card matched; click to enter detail view
            try:
                await first_match.click()
            except Exception:
                pass
            try:
                hero_btn = await self.page.wait_for_selector(self.HERO_BUTTON_GROUP, timeout=self.timeout_ms)
            except Exception:
                hero_btn = None
        else:
            hero_btn = first_match

        if not hero_btn:
            return None

        # Wait for the child img tag inside the hero button
        try:
            img_elem = await hero_btn.wait_for_selector("img", timeout=min(self.timeout_ms, 10000))
        except Exception:
            img_elem = None

        if not img_elem:
            try:
                img_elem = await self.page.wait_for_selector(
                    'button[jsaction*="heroHeaderImage"] img, button.aoRNLd img, button.aoRNld img',
                    timeout=3000,
                )
            except Exception:
                img_elem = None

        if not img_elem:
            return None

        # Poll until src is populated by Google CDN with a legitimate place photo URL
        # Google CDN under concurrency takes ~0.8s to 5.0s to inject the high-res URL into img.src
        # Polling budget: 50 iterations * 0.2s = 10.0 seconds
        src: str | None = None
        for _ in range(50):
            src = await img_elem.get_attribute("src")
            if src and src.startswith("http") and GooglePhotoUrlEnhancer.is_valid_place_photo(src):
                return src
            await asyncio.sleep(0.2)

        if src and GooglePhotoUrlEnhancer.is_valid_place_photo(src):
            return src

        return None

