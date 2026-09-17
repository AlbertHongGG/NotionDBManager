from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Callable

from notion_db_manager.application.interfaces.notion_gateway import NotionGateway
from notion_db_manager.application.interfaces.photo_provider import PhotoStorage
from notion_db_manager.domain.properties.file import FileProperty
from notion_db_manager.domain.travel import TravelContext
from notion_db_manager.domain.travel.summary import PushItemResult, TravelPhotoPushSummary

ProgressCallback = Callable[[int, int, str, str], None]


class TravelPushPhotosCommand:
    """Use case command for uploading locally staged photos to Notion via the official File Uploads API.

    Coordinates reading place records from local manifest.json, loading binary photo bytes,
    executing native file uploads to Notion workspace storage, and attaching file_upload IDs
    to each page's '照片' (Files & media) property.
    Employs an asynchronous Worker Pool (bounded by MAX_PUSH_CONCURRENCY) and rate-limiting
    delay to strictly prevent Notion API HTTP 429 rate limit errors.
    """

    def __init__(
        self,
        gateway: NotionGateway,
        storage: PhotoStorage,
        progress_callback: ProgressCallback | None = None,
    ) -> None:
        self.gateway = gateway
        self.storage = storage
        self.progress_callback = progress_callback

    async def execute(
        self,
        context: TravelContext | None = None,
        database_name: str | None = None,
        custom_manifest: Path | None = None,
        concurrency: int = 2,
        delay: float = 0.2,
    ) -> TravelPhotoPushSummary:
        db_name = context.database.name if context else (database_name or "default")
        manifest_target = custom_manifest or (context.manifest_path if context else None)
        manifest = self.storage.read_manifest(db_name, custom_path=manifest_target)
        total_items = len(manifest.items)

        if total_items == 0:
            return TravelPhotoPushSummary(
                database_name=db_name,
                total_items=0,
                processed_count=0,
                skipped_count=0,
                success_count=0,
                failed_count=0,
                items=[],
            )

        results: list[PushItemResult | None] = [None] * total_items
        queue: asyncio.Queue = asyncio.Queue()

        for item in manifest.items:
            # Pre-evaluate items: only those with status == "success" and local_path are targets
            if item.status != "success" or not item.local_path:
                results[item.index - 1] = PushItemResult(
                    index=item.index,
                    page_id=item.page_id,
                    name=item.name,
                    status="skipped",
                    error_message=item.error_message or "未於前置步驟成功抓取相片",
                )
                if self.progress_callback:
                    self.progress_callback(item.index, total_items, item.name, "skipped")
            else:
                queue.put_nowait(item)

        mime_map = {
            ".jpg": "image/jpeg",
            ".jpeg": "image/jpeg",
            ".png": "image/png",
            ".webp": "image/webp",
            ".gif": "image/gif",
        }

        async def _worker() -> None:
            while not queue.empty():
                try:
                    target_item = queue.get_nowait()
                except asyncio.QueueEmpty:
                    break

                try:
                    photo_bytes = self.storage.load_photo_bytes(db_name, target_item)
                    filename = Path(target_item.local_path).name if target_item.local_path else f"{target_item.index}_{target_item.name}.jpg"
                    ext = Path(filename).suffix.lower()
                    mime_type = mime_map.get(ext, "image/jpeg")

                    # Step 1 & 2: Upload file binary to Notion via official File Uploads API
                    file_upload_id = self.gateway.upload_file(
                        filename=filename,
                        file_bytes=photo_bytes,
                        mime_type=mime_type,
                    )

                    # Step 3: Attach file_upload to Notion page '照片' property
                    file_prop = FileProperty([{"name": filename, "type": "file_upload", "file_upload_id": file_upload_id}])
                    payload = {"照片": file_prop.to_notion_payload()}
                    self.gateway.update_page_properties(target_item.page_id, payload)

                    results[target_item.index - 1] = PushItemResult(
                        index=target_item.index,
                        page_id=target_item.page_id,
                        name=target_item.name,
                        status="success",
                        file_upload_id=file_upload_id,
                    )
                    if self.progress_callback:
                        self.progress_callback(target_item.index, total_items, target_item.name, "uploaded")

                    if delay > 0:
                        await asyncio.sleep(delay)
                except Exception as exc:
                    results[target_item.index - 1] = PushItemResult(
                        index=target_item.index,
                        page_id=target_item.page_id,
                        name=target_item.name,
                        status="failed",
                        error_message=str(exc),
                    )
                    if self.progress_callback:
                        self.progress_callback(target_item.index, total_items, target_item.name, f"failed: {exc}")
                finally:
                    queue.task_done()

        worker_count = min(concurrency, max(1, queue.qsize()))
        if worker_count > 0:
            workers = [asyncio.create_task(_worker()) for _ in range(worker_count)]
            await asyncio.gather(*workers)

        final_items: list[PushItemResult] = [
            r if r is not None else PushItemResult(index=i + 1, page_id="", name="unknown", status="skipped")
            for i, r in enumerate(results)
        ]

        success_count = sum(1 for r in final_items if r.status == "success")
        skipped_count = sum(1 for r in final_items if r.status == "skipped")
        failed_count = sum(1 for r in final_items if r.status == "failed")
        processed_count = success_count + failed_count

        return TravelPhotoPushSummary(
            database_name=db_name,
            total_items=total_items,
            processed_count=processed_count,
            skipped_count=skipped_count,
            success_count=success_count,
            failed_count=failed_count,
            items=final_items,
        )

    def execute_sync(
        self,
        context: TravelContext | None = None,
        database_name: str | None = None,
        custom_manifest: Path | None = None,
        concurrency: int = 2,
        delay: float = 0.2,
    ) -> TravelPhotoPushSummary:
        """Synchronous wrapper for execute."""
        return asyncio.run(
            self.execute(
                context=context,
                database_name=database_name,
                custom_manifest=custom_manifest,
                concurrency=concurrency,
                delay=delay,
            )
        )

