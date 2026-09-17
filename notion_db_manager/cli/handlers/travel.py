from __future__ import annotations

import argparse
from typing import Callable

from notion_db_manager.application.commands.travel import (
    TravelEnrichPhotosCommand,
    TravelPushPhotosCommand,
)
from notion_db_manager.application.services import TravelContextResolver
from notion_db_manager.cli.handlers.base import ActionHandler
from notion_db_manager.cli.prompt import resolve_settings
from notion_db_manager.cli.runner import AsyncCommandRunner
from notion_db_manager.core.config import ConfigurationResolver
from notion_db_manager.core.exceptions import ValidationError
from notion_db_manager.domain.models import DatabaseQuery, PageReference
from notion_db_manager.domain.travel import (
    PlaceItem,
    TravelContext,
    TravelPhotoEnrichSummary,
    TravelPhotoPushSummary,
)
from notion_db_manager.infrastructure.notion import NotionGatewayImpl, NotionHttpClient
from notion_db_manager.infrastructure.photos import LocalPhotoStorage, PhotoProviderFactory, sanitize_filename
from notion_db_manager.infrastructure.storage import JsonDocumentStorage, PathResolver


class TravelHandler(ActionHandler):
    """Handles all 'travel' CLI subcommands for the Travel Notion Template.

    Employs an Action Strategy Map so new travel-specific subcommands
    (e.g., sync-routes, plan, geocode) can be added cleanly without modifying existing methods.
    """

    def __init__(self) -> None:
        self._actions: dict[str, Callable[[argparse.Namespace], None]] = {
            "enrich-photos": self._handle_enrich_photos,
            "push-photos": self._handle_push_photos,
        }

    def handle(self, args: argparse.Namespace) -> None:
        action = args.action
        action_fn = self._actions.get(action)
        if not action_fn:
            raise ValidationError(f"未知的 travel 動作: {action}")
        action_fn(args)

    def _handle_enrich_photos(self, args: argparse.Namespace) -> None:
        storage = JsonDocumentStorage(path_resolver=PathResolver())
        photo_storage = LocalPhotoStorage(path_resolver=PathResolver())

        # Determine data source: input JSON document (offline mode) or live Notion database
        context: TravelContext | None = None
        if args.input:
            document = storage.read(args.input)
            db_name = document.meta.database_name or "default"
            pages = document.pages
        else:
            settings = resolve_settings(args)
            client = NotionHttpClient(token=settings.token)
            gateway = NotionGatewayImpl(client=client)
            context = TravelContextResolver.resolve(
                gateway=gateway,
                storage=photo_storage,
                database_name=settings.database_name,
                database_id=settings.database_id,
                page=settings.page,
            )
            updated_database = gateway.ensure_order_property(context.database)
            context = TravelContext(
                database=updated_database,
                images_dir=context.images_dir,
                manifest_path=context.manifest_path,
            )
            pages = gateway.get_ordered_pages(context.database)
            db_name = context.database.name

        provider_name = getattr(args, "provider", "playwright") or "playwright"
        default_concurrency = PhotoProviderFactory.get_default_concurrency(provider_name)
        config = ConfigurationResolver.resolve_travel_photo_config(
            args,
            default_concurrency=default_concurrency,
        )

        provider = PhotoProviderFactory.create(config)

        def on_progress(idx: int, total: int, item: PlaceItem, status: str) -> None:
            cat_str = f" [{', '.join(item.categories)}]" if item.categories else ""
            print(f"[{idx}/{total}] {item.name}{cat_str}: {status}")

        cmd = TravelEnrichPhotosCommand(
            provider=provider,
            storage=photo_storage,
            progress_callback=on_progress,
        )

        async def _run() -> TravelPhotoEnrichSummary:
            try:
                return await cmd.execute(
                    context=context,
                    database_name=db_name,
                    pages=pages,
                    categories=config.categories,
                    provider_name=config.provider,
                    clean_directory=config.clean_directory,
                    concurrency=config.concurrency,
                )
            finally:
                await provider.close()

        summary = AsyncCommandRunner.run(_run)

        clean_db = sanitize_filename(db_name)
        print("\n" + "=" * 55)
        print(f"旅遊代表圖片獲取完成！總計 {summary.total_items} 筆項目（並發數: {config.concurrency}）：")
        print(f"  - 成功下載: {summary.success_count} 筆")
        print(f"  - 略過項目: {summary.skipped_count} 筆")
        print(f"  - 失敗項目: {summary.failed_count} 筆")
        print(f"圖片儲存目錄: output/images/{clean_db}/")
        print(f"詳細報告檔案: output/images/{clean_db}/manifest.json")
        print("=" * 55)

    def _handle_push_photos(self, args: argparse.Namespace) -> None:
        push_config = ConfigurationResolver.resolve_travel_push_config(args)
        if not push_config.token:
            settings = resolve_settings(args)
            token = settings.token
            db_name = push_config.database_name or settings.database_name or ""
            db_id = push_config.database_id or settings.database_id
            page_val = push_config.page or settings.page
        else:
            token = push_config.token
            db_name = push_config.database_name
            db_id = push_config.database_id
            page_val = push_config.page

        if not db_name and not db_id and not push_config.input_manifest:
            db_name = input("Database name: ").strip()

        client = NotionHttpClient(token=token)
        gateway = NotionGatewayImpl(client=client)
        photo_storage = LocalPhotoStorage(path_resolver=PathResolver())

        context: TravelContext | None = None
        if not push_config.input_manifest and (db_name or db_id):
            context = TravelContextResolver.resolve(
                gateway=gateway,
                storage=photo_storage,
                database_name=db_name,
                database_id=db_id,
                page=page_val,
            )

        def on_progress(idx: int, total: int, name: str, status: str) -> None:
            print(f"[{idx}/{total}] {name}: {status}")

        cmd = TravelPushPhotosCommand(
            gateway=gateway,
            storage=photo_storage,
            progress_callback=on_progress,
        )

        async def _run() -> TravelPhotoPushSummary:
            return await cmd.execute(
                context=context,
                database_name=context.database.name if context else db_name,
                custom_manifest=push_config.input_manifest,
                concurrency=push_config.concurrency,
                delay=push_config.delay,
            )

        summary = AsyncCommandRunner.run(_run)

        print("\n" + "=" * 55)
        print(f"照片上傳 Notion 完成！總計 {summary.total_items} 筆項目（並發數: {push_config.concurrency}）：")
        print(f"  - 成功上傳: {summary.success_count} 筆")
        print(f"  - 略過項目: {summary.skipped_count} 筆")
        print(f"  - 失敗項目: {summary.failed_count} 筆")
        print("=" * 55)

