from __future__ import annotations

from typing import Any

from notion_db_manager.application.interfaces.photo_provider import PlacePhotoProvider
from notion_db_manager.core.config import PhotoEnrichConfig
from notion_db_manager.core.exceptions import ConfigurationError, ValidationError
from notion_db_manager.domain.places import PhotoProviderType
from notion_db_manager.infrastructure.photos.google_places import GooglePlacesPhotoProvider
from notion_db_manager.infrastructure.photos.playwright_provider import PlaywrightPhotoProvider


class PhotoProviderFactory:
    """Factory and registry for concrete PlacePhotoProvider implementations (OCP Compliant)."""

    _REGISTRY: dict[str, type[PlacePhotoProvider]] = {
        PhotoProviderType.PLAYWRIGHT.value: PlaywrightPhotoProvider,
        PhotoProviderType.GOOGLE.value: GooglePlacesPhotoProvider,
    }

    @classmethod
    def get_default_concurrency(cls, provider_type: PhotoProviderType | str) -> int:
        """Retrieves default concurrency defined by the provider implementation (Information Expert)."""
        raw_val = provider_type.value if isinstance(provider_type, PhotoProviderType) else str(provider_type).lower()
        provider_cls = cls._REGISTRY.get(raw_val)
        if provider_cls is not None and hasattr(provider_cls, "DEFAULT_CONCURRENCY"):
            return getattr(provider_cls, "DEFAULT_CONCURRENCY")
        return 1

    @classmethod
    def create_from_config(
        cls,
        config: PhotoEnrichConfig,
        headless: bool = True,
    ) -> PlacePhotoProvider:
        """Instantiates a provider based on a PhotoEnrichConfig value object."""
        raw_val = config.provider.value if isinstance(config.provider, PhotoProviderType) else str(config.provider).lower()

        if raw_val == PhotoProviderType.GOOGLE.value:
            if not config.google_api_key or not config.google_api_key.strip():
                raise ConfigurationError(
                    "指定了 Google Places API (google)，但未提供 GOOGLE_MAP_API 金鑰。請於 .env 設定或透過參數提供。"
                )
            return GooglePlacesPhotoProvider(api_key=config.google_api_key)

        elif raw_val == PhotoProviderType.PLAYWRIGHT.value:
            return PlaywrightPhotoProvider(headless=headless)

        else:
            raise ValidationError(
                f"未知的照片提供者: '{config.provider}'。可用選項為 'playwright' (預設) 或 'google'。"
            )

    @classmethod
    def create(
        cls,
        provider_type: PhotoProviderType | str,
        google_api_key: str | None = None,
        headless: bool = True,
    ) -> PlacePhotoProvider:
        """Backward-compatible factory method delegating to create_from_config."""
        raw_val = provider_type.value if isinstance(provider_type, PhotoProviderType) else str(provider_type).lower()
        enrich_config = PhotoEnrichConfig(
            provider=raw_val,
            concurrency=cls.get_default_concurrency(raw_val),
            google_api_key=google_api_key,
        )
        return cls.create_from_config(enrich_config, headless=headless)

