from __future__ import annotations

import asyncio
from typing import Callable

from notion_db_manager.application.interfaces.photo_provider import PhotoStorage, PlacePhotoProvider
from notion_db_manager.core.exceptions import ValidationError
from notion_db_manager.domain.models.page import Page
from notion_db_manager.domain.places import EnrichItemResult, PhotoEnrichSummary, PlaceItem

ProgressCallback = Callable[[int, int, PlaceItem, str], None]


class EnrichPlacePhotosCommand:
    """Use case command for concurrently enriching place pages with representative photos.

    Coordinates reading places, evaluating domain targets, querying the chosen provider
    with bounded concurrency (asyncio.Semaphore), persisting photos locally,
    and recording the execution manifest in index order.
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

    def _report(self, idx: int, total: int, item: PlaceItem, status: str) -> None:
        if self.progress_callback:
            self.progress_callback(idx, total, item, status)

    async def execute(
        self,
        database_name: str,
        pages: list[Page],
        categories: list[str] | None = None,
        provider_name: str = "unknown",
        clean_directory: bool = True,
        concurrency: int = 1,
    ) -> PhotoEnrichSummary:
        if concurrency < 1:
            raise ValidationError(f"並發數量 (concurrency) 必須為大於或等於 1 的正整數，收到: {concurrency}")

        # Purge stale contents if clean_directory is True before processing new items
        self.storage.prepare_directory(database_name, clean=clean_directory)

        items = [PlaceItem.from_page(p) for p in pages]
        allowed_cats = set(categories) if categories else None
        total_count = len(items)

        summary = PhotoEnrichSummary(
            database_name=database_name,
            provider=provider_name,
            total_items=total_count,
            processed_count=0,
            skipped_count=0,
            success_count=0,
            failed_count=0,
            items=[],
        )

        semaphore = asyncio.Semaphore(concurrency)
        results: list[EnrichItemResult] = []
        lock = asyncio.Lock()

        async def process_item(item: PlaceItem) -> None:
            if not item.is_target(allowed_cats):
                self._report(item.index, total_count, item, "略過 (不符類別篩選)")
                async with lock:
                    summary.skipped_count += 1
                    results.append(
                        EnrichItemResult(
                            index=item.index,
                            page_id=item.page_id,
                            name=item.name,
                            status="skipped",
                            categories=item.categories,
                        )
                    )
                return

            async with semaphore:
                self._report(item.index, total_count, item, "獲取圖片中...")

                # Fail-fast: Provider errors propagate directly and terminate gather
                photo = await self.provider.fetch_photo(item)

                if photo is None:
                    self._report(item.index, total_count, item, "無可用照片")
                    async with lock:
                        summary.processed_count += 1
                        summary.failed_count += 1
                        results.append(
                            EnrichItemResult(
                                index=item.index,
                                page_id=item.page_id,
                                name=item.name,
                                status="failed",
                                categories=item.categories,
                                error_message="找不到對應的代表相片",
                            )
                        )
                else:
                    saved_path = self.storage.save_photo(database_name, item, photo)
                    self._report(item.index, total_count, item, f"已儲存 -> {saved_path.name}")
                    async with lock:
                        summary.processed_count += 1
                        summary.success_count += 1
                        results.append(
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

        # Launch all tasks bounded by semaphore
        await asyncio.gather(*(process_item(item) for item in items))

        # Sort results strictly by original Notion item index
        results.sort(key=lambda r: r.index)
        summary.items = results

        self.storage.save_manifest(database_name, summary)
        return summary

    def execute_sync(
        self,
        database_name: str,
        pages: list[Page],
        categories: list[str] | None = None,
        provider_name: str = "unknown",
        clean_directory: bool = True,
        concurrency: int = 1,
    ) -> PhotoEnrichSummary:
        """Synchronous wrapper for execute."""
        return asyncio.run(
            self.execute(
                database_name=database_name,
                pages=pages,
                categories=categories,
                provider_name=provider_name,
                clean_directory=clean_directory,
                concurrency=concurrency,
            )
        )

