from __future__ import annotations

from notion_db_manager.application.interfaces.photo_provider import PlacePhotoProvider
from notion_db_manager.core.exceptions import ConfigurationError, ValidationError
from notion_db_manager.domain.places import PhotoProviderType
from notion_db_manager.infrastructure.photos.google_places import GooglePlacesPhotoProvider
from notion_db_manager.infrastructure.photos.playwright_provider import PlaywrightPhotoProvider


class PhotoProviderFactory:
    """Factory for creating concrete PlacePhotoProvider instances based on user selection."""

    @staticmethod
    def create(
        provider_type: PhotoProviderType | str,
        google_api_key: str | None = None,
        headless: bool = True,
    ) -> PlacePhotoProvider:
        raw_val = provider_type.value if isinstance(provider_type, PhotoProviderType) else str(provider_type).lower()

        if raw_val == PhotoProviderType.GOOGLE.value:
            if not google_api_key or not google_api_key.strip():
                raise ConfigurationError(
                    "指定了 Google Places API (google)，但未提供 GOOGLE_MAP_API 金鑰。請於 .env 設定或透過參數提供。"
                )
            return GooglePlacesPhotoProvider(api_key=google_api_key)

        elif raw_val == PhotoProviderType.PLAYWRIGHT.value:
            return PlaywrightPhotoProvider(headless=headless)

        else:
            raise ValidationError(
                f"未知的照片提供者: '{provider_type}'。可用選項為 'playwright' (預設) 或 'google'。"
            )
