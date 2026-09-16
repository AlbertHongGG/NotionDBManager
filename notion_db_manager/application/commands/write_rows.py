from __future__ import annotations

from typing import Any

from notion_db_manager.application.commands.base import BaseCommand, CommandResult
from notion_db_manager.core.exceptions import ValidationError
from notion_db_manager.core.types import WriteRowsMode
from notion_db_manager.domain.models import Database


class WriteRowsCommand(BaseCommand):
    """Use case for writing complete rows (append, insert with shift, or overwrite)."""

    def execute(
        self,
        database: Database,
        input_path: str,
        mode: WriteRowsMode,
        index: int | None = None,
        **kwargs: Any,
    ) -> CommandResult:
        if mode not in ("append", "insert", "overwrite"):
            raise ValidationError(f"不支援的 write-rows 模式: '{mode}'")

        document = self.storage.read(input_path)
        existing_pages = self.gateway.get_ordered_pages(database)
        resolved_input = self.storage.resolve_read_path(input_path)
        rows_count = len(document.pages)

        if mode == "append":
            start_index = len(existing_pages) + 1
            for offset, page in enumerate(document.pages):
                page.index = start_index + offset
                self.gateway.create_page(database, page, erase_missing_writable=False)

            return CommandResult(
                affected_count=rows_count,
                message=f"已從 {resolved_input} append {rows_count} 筆 row",
                target_path=resolved_input,
            )

        if index is None or index <= 0:
            raise ValidationError(f"{mode} 模式需要提供 --index，且需從 1 開始")

        if mode == "insert":
            max_insert_index = len(existing_pages) + 1
            if index > max_insert_index:
                raise ValidationError(f"insert index 最多只能到 {max_insert_index}")

            # Shift existing rows forward
            shift_amount = rows_count
            for existing_page in reversed(existing_pages[index - 1 :]):
                if existing_page.id:
                    new_order = existing_page.index + shift_amount
                    self.gateway.update_page_properties(
                        existing_page.id,
                        {database.order_property_name: {"number": new_order}},
                    )

            # Insert new pages into the vacant positions
            for offset, page in enumerate(document.pages):
                page.index = index + offset
                self.gateway.create_page(database, page, erase_missing_writable=False)

            return CommandResult(
                affected_count=rows_count,
                message=f"已從 {resolved_input} 讀取資料，並自 index {index} 插入 {rows_count} 筆 row",
                target_path=resolved_input,
            )

        # mode == "overwrite"
        required_count = index - 1 + rows_count
        if required_count > len(existing_pages):
            raise ValidationError(
                f"overwrite 需要覆蓋的 row 超出現有資料筆數，至少需要 {required_count} 筆，目前只有 {len(existing_pages)} 筆"
            )

        for offset, page in enumerate(document.pages):
            target_page = existing_pages[index - 1 + offset]
            if not target_page.id:
                raise ValidationError(f"既有第 {index + offset} 列缺少 Page ID，無法覆蓋")

            page.index = index + offset
            payload = page.to_notion_payload(database, erase_missing_writable=True)
            self.gateway.update_page_properties(target_page.id, payload)

        return CommandResult(
            affected_count=rows_count,
            message=f"已從 {resolved_input} 讀取資料，並自 index {index} 開始覆蓋 {rows_count} 筆 row",
            target_path=resolved_input,
        )
