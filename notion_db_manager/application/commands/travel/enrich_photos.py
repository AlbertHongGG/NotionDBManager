from __future__ import annotations

import asyncio
from typing import Callable

from notion_db_manager.application.interfaces.photo_provider import PhotoStorage, PlacePhotoProvider
from notion_db_manager.core.exceptions import ValidationError
from notion_db_manager.domain.models.page import Page
from notion_db_manager.domain.travel import EnrichItemResult, PlaceItem, TravelContext, TravelPhotoEnrichSummary

ProgressCallback = Callable[[int, int, PlaceItem, str], None]


class TravelEnrichPhotosCommand:
    """Use case command for concurrently enriching Travel Notion Template place pages with representative photos.

    Coordinates reading places from Travel Template pages, evaluating category filters,
    querying the chosen photo provider via an asynchronous Worker Pool (asyncio.Queue),
    persisting photos locally, and recording the execution manifest in strict index order.
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
        context: TravelContext | None = None,
        database_name: str | None = None,
        pages: list[Page] | None = None,
        categories: list[str] | None = None,
        provider_name: str = "unknown",
        clean_directory: bool = True,
        concurrency: int = 1,
    ) -> TravelPhotoEnrichSummary:
        if concurrency < 1:
            raise ValidationError(f"並發數量 (concurrency) 必須為大於或等於 1 的正整數，收到: {concurrency}")

        db_name = context.database.name if context else (database_name or "default")

        # Purge stale contents if clean_directory is True before processing new items
        self.storage.prepare_directory(db_name, clean=clean_directory)

        target_pages = pages if pages is not None else []
        items = [PlaceItem.from_page(p) for p in target_pages]
        allowed_cats = set(categories) if categories else None
        total_count = len(items)

        if total_count == 0:
            empty_summary = TravelPhotoEnrichSummary(
                database_name=db_name,
                provider=provider_name,
                total_items=0,
                processed_count=0,
                skipped_count=0,
                success_count=0,
                failed_count=0,
                items=[],
            )
            self.storage.save_manifest(db_name, empty_summary)
            return empty_summary

        # Pre-allocate results array to guarantee exact original index ordering without locks
        results: list[EnrichItemResult | None] = [None] * total_count

        # Populate FIFO work queue
        queue: asyncio.Queue[tuple[int, PlaceItem]] = asyncio.Queue()
        for idx, item in enumerate(items):
            queue.put_nowait((idx, item))

        async def worker() -> None:
            while not queue.empty():
                try:
                    slot_idx, item = queue.get_nowait()
                except asyncio.QueueEmpty:
                    break

                try:
                    if not item.is_target(allowed_cats):
                        self._report(item.index, total_count, item, "略過 (不符類別篩選)")
                        results[slot_idx] = EnrichItemResult(
                            index=item.index,
                            page_id=item.page_id,
                            name=item.name,
                            status="skipped",
                            categories=item.categories,
                        )
                        continue

                    self._report(item.index, total_count, item, "獲取圖片中...")

                    # Fail-fast: Provider errors propagate directly and terminate worker pool
                    photo = await self.provider.fetch_photo(item)

                    if photo is None:
                        self._report(item.index, total_count, item, "無可用照片")
                        results[slot_idx] = EnrichItemResult(
                            index=item.index,
                            page_id=item.page_id,
                            name=item.name,
                            status="failed",
                            categories=item.categories,
                            error_message="找不到對應的代表相片",
                        )
                    else:
                        saved_path = self.storage.save_photo(db_name, item, photo)
                        self._report(item.index, total_count, item, f"已儲存 -> {saved_path.name}")
                        results[slot_idx] = EnrichItemResult(
                            index=item.index,
                            page_id=item.page_id,
                            name=item.name,
                            status="success",
                            categories=item.categories,
                            local_path=str(saved_path),
                            source_url=photo.source_url,
                        )
                finally:
                    queue.task_done()

        # Spawn exactly N workers (N = min(concurrency, total_count))
        num_workers = min(concurrency, total_count)
        worker_tasks = [asyncio.create_task(worker()) for _ in range(num_workers)]

        try:
            await asyncio.gather(*worker_tasks)
        except Exception:
            # Fail-fast: cancel all remaining workers immediately
            for task in worker_tasks:
                if not task.done():
                    task.cancel()
            await asyncio.gather(*worker_tasks, return_exceptions=True)
            raise

        final_items: list[EnrichItemResult] = [r for r in results if r is not None]
        success_count = sum(1 for r in final_items if r.status == "success")
        skipped_count = sum(1 for r in final_items if r.status == "skipped")
        failed_count = sum(1 for r in final_items if r.status == "failed")
        processed_count = success_count + failed_count

        summary = TravelPhotoEnrichSummary(
            database_name=db_name,
            provider=provider_name,
            total_items=total_count,
            processed_count=processed_count,
            skipped_count=skipped_count,
            success_count=success_count,
            failed_count=failed_count,
            items=final_items,
        )

        self.storage.save_manifest(db_name, summary)
        return summary

    def execute_sync(
        self,
        database_name: str,
        pages: list[Page],
        categories: list[str] | None = None,
        provider_name: str = "unknown",
        clean_directory: bool = True,
        concurrency: int = 1,
    ) -> TravelPhotoEnrichSummary:
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

