from __future__ import annotations

import re
import urllib.parse
from typing import Any

from notion_db_manager.application.interfaces.photo_provider import PlacePhotoProvider
from notion_db_manager.core.exceptions import PhotoProviderError
from notion_db_manager.domain.places import PlaceItem, PlacePhoto


class PlaywrightPhotoProvider(PlacePhotoProvider):
    """Retrieves place photos by automating a headless Chromium browser on Google Maps.

    Enforces Fail-Fast: Any browser launch failure or fatal exception immediately raises
    PhotoProviderError.
    """

    PHOTO_SELECTORS = [
        "button[aria-label*='相片'] img",
        "button[aria-label*='Photo'] img",
        "button.aoDRFc img",
        "div[role='main'] img[src*='googleusercontent.com']",
        "img[src*='googleusercontent.com/p/']",
        "img[src*='googleusercontent.com/gps-cs-s/']",
    ]

    def __init__(self, headless: bool = True, timeout: float = 20.0) -> None:
        self.headless = headless
        self.timeout = timeout
        self.timeout_ms = int(timeout * 1000)
        self._playwright: Any = None
        self._browser: Any = None

    def _ensure_browser(self) -> Any:
        if self._browser is not None:
            return self._browser

        try:
            from playwright.sync_api import sync_playwright  # type: ignore[import-untyped]
        except ImportError as exc:
            raise PhotoProviderError(
                "未安裝 Playwright 套件。請執行 'pip install playwright && playwright install chromium'"
            ) from exc

        try:
            self._playwright = sync_playwright().start()
            self._browser = self._playwright.chromium.launch(
                headless=self.headless,
                args=["--no-sandbox", "--disable-dev-shm-usage", "--disable-gpu"],
            )
            return self._browser
        except Exception as exc:
            raise PhotoProviderError(f"啟動 Playwright 瀏覽器失敗: {exc}") from exc

    def fetch_photo(self, place: PlaceItem) -> PlacePhoto | None:
        browser = self._ensure_browser()
        page = browser.new_page(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            locale="zh-TW",
        )

        try:
            target_url = self._resolve_target_url(place)
            page.goto(target_url, wait_until="domcontentloaded", timeout=self.timeout_ms)

            # Try locating cover photo
            img_src = self._find_photo_src(page)
            if not img_src:
                return None

            # Enhance image resolution if Google thumbnail parameters are present
            high_res_url = self._enhance_resolution(img_src)

            # Download using browser context request to preserve session and headers
            res = page.request.get(high_res_url, timeout=self.timeout_ms)
            if not res.ok:
                # Fallback to original src if high_res_url fails
                res = page.request.get(img_src, timeout=self.timeout_ms)
                if not res.ok:
                    return None

            content_type = res.headers.get("content-type", "image/jpeg")
            extension = "png" if "png" in content_type else "jpg"

            return PlacePhoto(
                data=res.body(),
                mime_type=content_type,
                extension=extension,
                source_url=high_res_url,
            )
        except Exception as exc:
            # Check if this is a fatal browser crash
            if "Target closed" in str(exc) or "browser has been closed" in str(exc):
                raise PhotoProviderError(f"Playwright 瀏覽器異常終止: {exc}") from exc
            # Otherwise return None for unresolvable locations
            return None
        finally:
            try:
                page.close()
            except Exception:
                pass

    def close(self) -> None:
        """Closes browser instances and playwright processes cleanly."""
        if self._browser:
            try:
                self._browser.close()
            except Exception:
                pass
            self._browser = None

        if self._playwright:
            try:
                self._playwright.stop()
            except Exception:
                pass
            self._playwright = None

    def __enter__(self) -> PlaywrightPhotoProvider:
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        self.close()

    def _resolve_target_url(self, place: PlaceItem) -> str:
        if place.navigation_url and "maps" in place.navigation_url:
            return place.navigation_url
        query = place.best_search_query()
        return f"https://www.google.com/maps/search/{urllib.parse.quote(query)}"

    def _find_photo_src(self, page: Any) -> str | None:
        # Wait briefly for either of the photo elements to appear
        for selector in self.PHOTO_SELECTORS:
            try:
                elem = page.wait_for_selector(selector, timeout=3000)
                if elem:
                    src = elem.get_attribute("src")
                    if src and ("googleusercontent.com" in src or "ggpht.com" in src):
                        return src
            except Exception:
                continue

        # If none matched by selector, inspect all images in main pane
        try:
            imgs = page.query_selector_all("img")
            for img in imgs:
                src = img.get_attribute("src")
                if src and ("googleusercontent.com/p/" in src or "googleusercontent.com/gps-cs-s/" in src):
                    return src
        except Exception:
            pass

        return None

    def _enhance_resolution(self, url: str) -> str:
        """Transforms Google image URL size constraints to high-resolution (w1600-h1200)."""
        if "=w" in url:
            return re.sub(r"=w\d+[^\"']*", "=w1600-h1200-k-no", url)
        if "=s" in url:
            return re.sub(r"=s\d+[^\"']*", "=s1600", url)
        return url
