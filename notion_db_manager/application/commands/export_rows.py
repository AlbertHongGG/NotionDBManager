from __future__ import annotations

from typing import Any

from notion_db_manager.application.commands.base import BaseCommand, CommandResult
from notion_db_manager.core.exceptions import ValidationError
from notion_db_manager.domain.models import Database, Document, DocumentMeta, Page
from notion_db_manager.domain.validation import parse_row_indices


class ExportRowsCommand(BaseCommand):
    """Use case for exporting only designated row numbers/ranges from a Notion database."""

    def execute(
        self,
        database: Database,
        output_path: str,
        row_expression: str,
        **kwargs: Any,
    ) -> CommandResult:
        selected_rows = parse_row_indices(row_expression)
        pages = self.gateway.get_ordered_pages(database)
        total_pages = len(pages)

        selected_pages: list[Page] = []
        for row_index in selected_rows:
            if row_index > total_pages:
                raise ValidationError(f"指定列 index {row_index} 超出目前資料庫筆數 {total_pages}")
            page = pages[row_index - 1]
            page.index = row_index
            selected_pages.append(page)

        meta = DocumentMeta(
            database_id=database.id,
            database_name=database.name,
            export_type="rows",
            selected_rows=selected_rows,
            order_property=database.order_property_name,
        )
        document = Document(meta=meta, pages=selected_pages)
        written_path = self.storage.write(output_path, document)

        return CommandResult(
            affected_count=len(selected_pages),
            message=f"已匯出 {len(selected_pages)} 筆指定 row 到 {written_path}",
            target_path=written_path,
        )
