from __future__ import annotations

from typing import Callable

from notion_db_manager.application.interfaces.photo_provider import PhotoStorage, PlacePhotoProvider
from notion_db_manager.domain.models.page import Page
from notion_db_manager.domain.places import EnrichItemResult, PhotoEnrichSummary, PlaceItem


ProgressCallback = Callable[[int, int, PlaceItem, str], None]


class EnrichPlacePhotosCommand:
    """Use case command for enriching place pages with representative photos.

    Coordinates reading places, evaluating domain targets, querying the chosen provider,
    persisting photos locally, and recording the execution manifest.
    Fails immediately (Fail-Fast) if the provider encounters an infrastructure or auth error.
    """

    def __init__(
        self,
        provider: PlacePhotoProvider,
        storage: PhotoStorage,
        progress_callback: ProgressCallback | None = None,
    ) -> None:
        self.provider = provider
        self.storage = storage
        self.progress_callback = progress_callback

    def execute(
        self,
        database_name: str,
        pages: list[Page],
        categories: list[str] | None = None,
        provider_name: str = "unknown",
        clean_directory: bool = True,
    ) -> PhotoEnrichSummary:
        # Purge stale contents if clean_directory is True before processing new items
        self.storage.prepare_directory(database_name, clean=clean_directory)

        items = [PlaceItem.from_page(p) for p in pages]
        allowed_cats = set(categories) if categories else None

        summary = PhotoEnrichSummary(
            database_name=database_name,
            provider=provider_name,
            total_items=len(items),
            processed_count=0,
            skipped_count=0,
            success_count=0,
            failed_count=0,
            items=[],
        )

        total_count = len(items)
        for idx, item in enumerate(items, start=1):
            if not item.is_target(allowed_cats):
                summary.skipped_count += 1
                summary.items.append(
                    EnrichItemResult(
                        index=item.index,
                        page_id=item.page_id,
                        name=item.name,
                        status="skipped",
                        categories=item.categories,
                    )
                )
                if self.progress_callback:
                    self.progress_callback(idx, total_count, item, "略過 (不符類別篩選)")
                continue

            summary.processed_count += 1
            if self.progress_callback:
                self.progress_callback(idx, total_count, item, "獲取圖片中...")

            # Fail-fast: Provider errors (e.g. invalid API key, connection loss) propagate directly
            photo = self.provider.fetch_photo(item)

            if photo is None:
                summary.failed_count += 1
                summary.items.append(
                    EnrichItemResult(
                        index=item.index,
                        page_id=item.page_id,
                        name=item.name,
                        status="failed",
                        categories=item.categories,
                        error_message="找不到對應的代表相片",
                    )
                )
                if self.progress_callback:
                    self.progress_callback(idx, total_count, item, "無可用照片")
            else:
                saved_path = self.storage.save_photo(database_name, item, photo)
                summary.success_count += 1
                summary.items.append(
                    EnrichItemResult(
                        index=item.index,
                        page_id=item.page_id,
                        name=item.name,
                        status="success",
                        categories=item.categories,
                        local_path=str(saved_path),
                        source_url=photo.source_url,
                    )
                )
                if self.progress_callback:
                    self.progress_callback(idx, total_count, item, f"已儲存 -> {saved_path.name}")

        self.storage.save_manifest(database_name, summary)
        return summary
