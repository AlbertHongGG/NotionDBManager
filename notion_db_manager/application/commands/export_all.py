from __future__ import annotations

from typing import Any

from notion_db_manager.application.commands.base import BaseCommand, CommandResult
from notion_db_manager.domain.models import Database, Document, DocumentMeta


class ExportAllCommand(BaseCommand):
    """Use case for exporting all rows and properties from a Notion database."""

    def execute(self, database: Database, output_path: str, **kwargs: Any) -> CommandResult:
        pages = self.gateway.get_ordered_pages(database)
        # Ensure sequential indices
        for idx, page in enumerate(pages, start=1):
            page.index = idx

        meta = DocumentMeta(
            database_id=database.id,
            database_name=database.name,
            export_type="full",
            order_property=database.order_property_name,
        )
        document = Document(meta=meta, pages=pages)
        written_path = self.storage.write(output_path, document)

        return CommandResult(
            affected_count=len(pages),
            message=f"已匯出 {len(pages)} 筆資料到 {written_path}",
            target_path=written_path,
        )
