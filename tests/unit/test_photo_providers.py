import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
import pytest

from notion_db_manager.core.exceptions import ConfigurationError, PhotoProviderError, ValidationError
from notion_db_manager.domain.travel.places import PhotoProviderType, PlaceItem

from notion_db_manager.infrastructure.photos.factory import PhotoProviderFactory
from notion_db_manager.infrastructure.photos.google_places import GooglePlacesPhotoProvider
from notion_db_manager.infrastructure.photos.playwright_provider import PlaywrightPhotoProvider


def test_photo_provider_factory_google() -> None:
    provider = PhotoProviderFactory.create("google", google_api_key="AIzaSyValidKey")
    assert isinstance(provider, GooglePlacesPhotoProvider)
    assert provider.api_key == "AIzaSyValidKey"


def test_photo_provider_factory_google_missing_key() -> None:
    with pytest.raises(ConfigurationError) as exc_info:
        PhotoProviderFactory.create("google", google_api_key=None)
    assert "未提供 GOOGLE_MAP_API 金鑰" in str(exc_info.value)


def test_photo_provider_factory_playwright() -> None:
    provider = PhotoProviderFactory.create("playwright")
    assert isinstance(provider, PlaywrightPhotoProvider)


def test_photo_provider_factory_invalid() -> None:
    with pytest.raises(ValidationError):
        PhotoProviderFactory.create("unknown_provider")


def test_photo_provider_factory_default_concurrency() -> None:
    assert PhotoProviderFactory.get_default_concurrency("playwright") == 3
    assert PhotoProviderFactory.get_default_concurrency("google") == 8
    assert PhotoProviderFactory.get_default_concurrency(PhotoProviderType.PLAYWRIGHT) == 3
    assert PhotoProviderFactory.get_default_concurrency(PhotoProviderType.GOOGLE) == 8
    assert PhotoProviderFactory.get_default_concurrency("unknown") == 1


def test_photo_provider_factory_create_from_config() -> None:
    from notion_db_manager.core.config import TravelPhotoEnrichConfig

    cfg_google = TravelPhotoEnrichConfig(provider="google", concurrency=5, google_api_key="AIzaSyKey")
    provider = PhotoProviderFactory.create_from_config(cfg_google)
    assert isinstance(provider, GooglePlacesPhotoProvider)
    assert provider.api_key == "AIzaSyKey"

    cfg_pw = TravelPhotoEnrichConfig(provider="playwright", concurrency=2)
    provider_pw = PhotoProviderFactory.create_from_config(cfg_pw)
    assert isinstance(provider_pw, PlaywrightPhotoProvider)



def test_google_places_photo_provider_success() -> None:
    provider = GooglePlacesPhotoProvider(api_key="AIzaSyTest")
    item = PlaceItem(page_id="p1", index=1, name="中部電力未來塔")

    search_response = MagicMock()
    search_response.status_code = 200
    search_response.json.return_value = {
        "places": [
            {
                "id": "place_123",
                "displayName": {"text": "中部電力未來塔"},
                "photos": [
                    {
                        "name": "places/p1/photos/photo_abc",
                        "widthPx": 1600,
                        "heightPx": 1200,
                    }
                ],
            }
        ]
    }

    media_response = MagicMock()
    media_response.status_code = 200
    media_response.content = b"fake-jpeg-binary"
    media_response.headers = {"Content-Type": "image/jpeg"}
    media_response.url = "https://places.googleapis.com/v1/places/p1/photos/photo_abc/media"

    mock_client = MagicMock()
    mock_client.post = AsyncMock(return_value=search_response)
    mock_client.get = AsyncMock(return_value=media_response)

    with patch.object(provider, "_get_client", return_value=mock_client):
        photo = asyncio.run(provider.fetch_photo(item))

    assert photo is not None
    assert photo.data == b"fake-jpeg-binary"
    assert photo.extension == "jpg"
    assert photo.width == 1600
    assert photo.height == 1200


def test_google_places_photo_provider_api_error_fail_fast() -> None:
    provider = GooglePlacesPhotoProvider(api_key="AIzaSyBadKey")
    item = PlaceItem(page_id="p1", index=1, name="中部電力未來塔")

    error_response = MagicMock()
    error_response.status_code = 400
    error_response.text = '{"error": {"message": "API key not valid."}}'
    error_response.json.return_value = {"error": {"message": "API key not valid."}}

    mock_client = MagicMock()
    mock_client.post = AsyncMock(return_value=error_response)

    with patch.object(provider, "_get_client", return_value=mock_client):
        with pytest.raises(PhotoProviderError) as exc_info:
            asyncio.run(provider.fetch_photo(item))

    assert "API key not valid" in str(exc_info.value)

