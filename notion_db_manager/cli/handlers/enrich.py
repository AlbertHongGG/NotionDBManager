from __future__ import annotations

import argparse

from notion_db_manager.application.commands.enrich_photos import EnrichPlacePhotosCommand
from notion_db_manager.cli.handlers.base import ActionHandler
from notion_db_manager.cli.prompt import resolve_settings
from notion_db_manager.cli.runner import AsyncCommandRunner
from notion_db_manager.core.config import ConfigurationResolver
from notion_db_manager.core.exceptions import ValidationError
from notion_db_manager.domain.models import DatabaseQuery, PageReference
from notion_db_manager.domain.places import PhotoEnrichSummary, PlaceItem
from notion_db_manager.infrastructure.notion import NotionGatewayImpl, NotionHttpClient
from notion_db_manager.infrastructure.photos import LocalPhotoStorage, PhotoProviderFactory, sanitize_filename
from notion_db_manager.infrastructure.storage import JsonDocumentStorage, PathResolver


class EnrichHandler(ActionHandler):
    """Handles all 'enrich' CLI subcommands (data enhancement and asset fetching)."""

    def handle(self, args: argparse.Namespace) -> None:
        action = args.action
        if action != "photos":
            raise ValidationError(f"未知的 enrich 動作: {action}")

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
        enrich_config = ConfigurationResolver.resolve_enrich_config(
            args,
            default_concurrency=default_concurrency,
        )

        provider = PhotoProviderFactory.create_from_config(enrich_config)
        photo_storage = LocalPhotoStorage(path_resolver=PathResolver())

        def on_progress(idx: int, total: int, item: PlaceItem, status: str) -> None:
            cat_str = f" [{', '.join(item.categories)}]" if item.categories else ""
            print(f"[{idx}/{total}] {item.name}{cat_str}: {status}")

        cmd = EnrichPlacePhotosCommand(
            provider=provider,
            storage=photo_storage,
            progress_callback=on_progress,
        )

        async def _run() -> PhotoEnrichSummary:
            try:
                return await cmd.execute(
                    database_name=db_name,
                    pages=pages,
                    categories=enrich_config.categories,
                    provider_name=enrich_config.provider,
                    clean_directory=enrich_config.clean_directory,
                    concurrency=enrich_config.concurrency,
                )
            finally:
                await provider.close()

        summary = AsyncCommandRunner.run(_run)

        clean_db = sanitize_filename(db_name)
        print("\n" + "=" * 55)
        print(f"圖片獲取完成！總計 {summary.total_items} 筆項目（並發數: {enrich_config.concurrency}）：")
        print(f"  - 成功下載: {summary.success_count} 筆")
        print(f"  - 略過項目: {summary.skipped_count} 筆")
        print(f"  - 失敗項目: {summary.failed_count} 筆")
        print(f"圖片儲存目錄: output/images/{clean_db}/")
        print(f"詳細報告檔案: output/images/{clean_db}/manifest.json")
        print("=" * 55)


