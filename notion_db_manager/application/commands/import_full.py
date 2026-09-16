from __future__ import annotations

from typing import Any

from notion_db_manager.application.commands.base import BaseCommand, CommandResult
from notion_db_manager.core.exceptions import ValidationError
from notion_db_manager.core.types import ImportMode
from notion_db_manager.domain.models import Database


class ImportFullCommand(BaseCommand):
    """Use case for importing full dataset from a document (append or replace)."""

    def execute(
        self,
        database: Database,
        input_path: str,
        mode: ImportMode,
        **kwargs: Any,
    ) -> CommandResult:
        if mode not in ("append", "replace"):
            raise ValidationError(f"不支援的 import 模式: '{mode}' (僅支援 'append' 或 'replace')")

        document = self.storage.read(input_path)
        existing_pages = self.gateway.get_ordered_pages(database)

        if mode == "replace":
            page_ids_to_archive = [p.id for p in existing_pages if p.id]
            if page_ids_to_archive:
                self.gateway.archive_pages(page_ids_to_archive)
            start_index = 1
        else:
            start_index = len(existing_pages) + 1

        for offset, page in enumerate(document.pages):
            target_index = start_index + offset
            page.index = target_index
            self.gateway.create_page(database, page, erase_missing_writable=False)

        resolved_input = self.storage.resolve_read_path(input_path)
        return CommandResult(
            affected_count=len(document.pages),
            message=f"已從 {resolved_input} 寫入 {len(document.pages)} 筆資料，模式: {mode}",
            target_path=resolved_input,
        )
