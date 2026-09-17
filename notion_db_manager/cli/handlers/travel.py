from __future__ import annotations

import argparse
from typing import Callable

from notion_db_manager.application.travel import TravelEnrichPhotosCommand
from notion_db_manager.cli.handlers.base import ActionHandler
from notion_db_manager.cli.prompt import resolve_settings
from notion_db_manager.cli.runner import AsyncCommandRunner
from notion_db_manager.core.config import ConfigurationResolver
from notion_db_manager.core.exceptions import ValidationError
from notion_db_manager.domain.models import DatabaseQuery, PageReference
from notion_db_manager.domain.travel.places import PlaceItem, TravelPhotoEnrichSummary
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
        }

    def handle(self, args: argparse.Namespace) -> None:
        action = args.action
        action_fn = self._actions.get(action)
        if not action_fn:
            raise ValidationError(f"未知的 travel 動作: {action}")
        action_fn(args)

    def _handle_enrich_photos(self, args: argparse.Namespace) -> None:
        storage = JsonDocumentStorage(path_resolver=PathResolver())

        # Determine data source: input JSON document (offline mode) or live Notion database
        if args.input:
            document = storage.read(args.input)
            db_name = document.meta.database_name or "default"
            pages = document.pages
        else:
            settings = resolve_settings(args)
            client = NotionHttpClient(token=settings.token)
            gateway = NotionGatewayImpl(client=client)
            parent_ref = PageReference.from_raw(settings.page) if settings.page else None
            query = DatabaseQuery(
                database_name=settings.database_name,
                database_id=settings.database_id,
                parent_page=parent_ref,
            )
            database = gateway.locate_database(query)
            database = gateway.ensure_order_property(database)
            pages = gateway.get_ordered_pages(database)
            db_name = database.name

        provider_name = getattr(args, "provider", "playwright") or "playwright"
        default_concurrency = PhotoProviderFactory.get_default_concurrency(provider_name)
        config = ConfigurationResolver.resolve_travel_photo_config(
            args,
            default_concurrency=default_concurrency,
        )

        provider = PhotoProviderFactory.create_from_config(config)
        photo_storage = LocalPhotoStorage(path_resolver=PathResolver())

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
