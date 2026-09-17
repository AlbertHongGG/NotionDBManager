import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
import pytest

from notion_db_manager.domain.travel import PlaceItem

from notion_db_manager.infrastructure.photos.playwright_provider import PlaywrightPhotoProvider


def test_playwright_provider_url_resolution() -> None:
    provider = PlaywrightPhotoProvider()

    # With navigation URL
    p1 = PlaceItem(
        page_id="1",
        index=1,
        name="手長足長像",
        navigation_url="https://maps.app.goo.gl/test123",
    )
    assert provider._resolve_target_url(p1) == "https://maps.app.goo.gl/test123"

    # Without navigation URL
    p2 = PlaceItem(page_id="2", index=2, name="中部電力未來塔")
    assert "https://www.google.com/maps/search/" in provider._resolve_target_url(p2)


def test_playwright_provider_enhance_resolution() -> None:
    provider = PlaywrightPhotoProvider()
    low_res = "https://lh3.googleusercontent.com/p/AF1Qip=w408-h306-k-no"
    high_res = provider._enhance_resolution(low_res)
    assert "=w1600-h1200-k-no" in high_res


def test_playwright_provider_fetch_photo_mocked() -> None:
    provider = PlaywrightPhotoProvider()
    item = PlaceItem(page_id="1", index=1, name="手長足長像")

    mock_page = MagicMock()
    mock_page.goto = AsyncMock()
    mock_page.close = AsyncMock()

    mock_btn = MagicMock()
    mock_img = MagicMock()
    mock_img.get_attribute = AsyncMock(return_value="https://lh3.googleusercontent.com/p/test=w100-h100")
    mock_btn.wait_for_selector = AsyncMock(return_value=mock_img)
    mock_page.wait_for_selector = AsyncMock(return_value=mock_btn)

    mock_res = MagicMock()
    mock_res.ok = True
    mock_res.body = AsyncMock(return_value=b"fake-playwright-bytes")
    mock_res.headers = {"content-type": "image/jpeg"}
    mock_page.request.get = AsyncMock(return_value=mock_res)

    mock_browser = MagicMock()
    mock_browser.new_page = AsyncMock(return_value=mock_page)

    with patch.object(provider, "_ensure_browser", new=AsyncMock(return_value=mock_browser)):
        photo = asyncio.run(provider.fetch_photo(item))

    assert photo is not None
    assert photo.data == b"fake-playwright-bytes"
    assert photo.extension == "jpg"
    assert "=w1600-h1200-k-no" in photo.source_url
    mock_page.close.assert_called_once()


def test_playwright_provider_fatal_error_fails_fast() -> None:
    from notion_db_manager.core.exceptions import PhotoProviderError

    provider = PlaywrightPhotoProvider()
    item = PlaceItem(page_id="1", index=1, name="手長足長像")

    mock_page = MagicMock()
    mock_page.goto = AsyncMock(side_effect=Exception("Target page, context or browser has been closed"))
    mock_page.close = AsyncMock()
    mock_browser = MagicMock()
    mock_browser.new_page = AsyncMock(return_value=mock_page)

    with patch.object(provider, "_ensure_browser", new=AsyncMock(return_value=mock_browser)):
        with pytest.raises(PhotoProviderError, match="瀏覽器異常終止"):
            asyncio.run(provider.fetch_photo(item))


def test_maps_page_locate_hero_photo_ignores_avatar() -> None:
    from notion_db_manager.infrastructure.photos.maps_page import GoogleMapsPageObject

    mock_page = MagicMock()
    mock_btn = MagicMock()
    mock_img = MagicMock()
    # Returns avatar URL on all attempts
    mock_img.get_attribute = AsyncMock(return_value="https://lh3.googleusercontent.com/a/ACg8ocIS-avatar=s60-c-mo")
    mock_btn.wait_for_selector = AsyncMock(return_value=mock_img)
    mock_page.wait_for_selector = AsyncMock(return_value=mock_btn)

    maps_page = GoogleMapsPageObject(mock_page, timeout_ms=500)
    with patch("asyncio.sleep", new=AsyncMock()):
        url = asyncio.run(maps_page.locate_hero_photo_url())

    assert url is None


