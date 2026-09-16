from __future__ import annotations

from typing import Any

from notion_db_manager.application.commands.base import BaseCommand, CommandResult
from notion_db_manager.application.interfaces.document_storage import DocumentStorage
from notion_db_manager.application.interfaces.notion_gateway import NotionGateway
from notion_db_manager.application.naming import ExportNamingPolicy, TimestampedNamingPolicy
from notion_db_manager.domain.models import Database, Document, DocumentMeta


class ExportColumnsCommand(BaseCommand):
    """Use case for exporting only designated columns from a Notion database."""

    ACTION_NAME = "export-columns"

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
        columns: list[str],
        output_path: str | None = None,
        **kwargs: Any,
    ) -> CommandResult:
        database.validate_columns(columns)
        pages = self.gateway.get_ordered_pages(database)
        for idx, page in enumerate(pages, start=1):
            page.index = idx

        meta = DocumentMeta(
            database_id=database.id,
            database_name=database.name,
            export_type="columns",
            selected_columns=columns,
            order_property=database.order_property_name,
        )
        document = Document(meta=meta, pages=pages)
        target_path_str = output_path or self.naming_policy.generate(self.ACTION_NAME)
        written_path = self.storage.write(target_path_str, document)

        return CommandResult(
            affected_count=len(pages),
            message=f"已匯出 {len(pages)} 筆資料的指定欄位到 {written_path}",
            target_path=written_path,
        )
