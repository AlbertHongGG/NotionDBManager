from __future__ import annotations

from typing import Any

from notion_db_manager.application.commands.base import BaseCommand, CommandResult
from notion_db_manager.application.interfaces.document_storage import DocumentStorage
from notion_db_manager.application.interfaces.notion_gateway import NotionGateway
from notion_db_manager.application.naming import ExportNamingPolicy, TimestampedNamingPolicy
from notion_db_manager.core.exceptions import ValidationError
from notion_db_manager.domain.models import Database, Document, DocumentMeta, Page
from notion_db_manager.domain.validation import parse_row_indices


class ExportRowsCommand(BaseCommand):
    """Use case for exporting only designated row numbers/ranges from a Notion database."""

    ACTION_NAME = "export-rows"

    def __init__(
        self,
        gateway: NotionGateway,
        storage: DocumentStorage,
        naming_policy: ExportNamingPolicy | None = None,
    ) -> None:
        super().__init__(gateway, storage)
        self.naming_policy = naming_policy or TimestampedNamingPolicy()

    def execute(
        self,
        database: Database,
        row_expression: str,
        output_path: str | None = None,
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
        target_path_str = output_path or self.naming_policy.generate(self.ACTION_NAME)
        written_path = self.storage.write(target_path_str, document)

        return CommandResult(
            affected_count=len(selected_pages),
            message=f"已匯出 {len(selected_pages)} 筆指定 row 到 {written_path}",
            target_path=written_path,
        )
