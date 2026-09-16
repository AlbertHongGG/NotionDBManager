from __future__ import annotations

from typing import Any

from notion_db_manager.application.commands.base import BaseCommand, CommandResult
from notion_db_manager.core.exceptions import ValidationError
from notion_db_manager.domain.models import Database


class WriteColumnsCommand(BaseCommand):
    """Use case for writing partial column data from a document starting from a designated index."""

    def execute(
        self,
        database: Database,
        input_path: str,
        start_index: int = 1,
        **kwargs: Any,
    ) -> CommandResult:
        if start_index <= 0:
            raise ValidationError("start-index 需從 1 開始")

        document = self.storage.read(input_path)
        existing_pages = self.gateway.get_ordered_pages(database)
        max_allowed_start = len(existing_pages) + 1

        if start_index > max_allowed_start:
            raise ValidationError(f"start-index 最多只能到 {max_allowed_start} (目前資料筆數: {len(existing_pages)})")

        for offset, page in enumerate(document.pages):
            target_index = start_index + offset
            col_names = [k for k in page.properties.keys() if k != database.order_property_name]
            database.validate_columns(col_names)

            if target_index <= len(existing_pages):
                target_page_id = existing_pages[target_index - 1].id
                if not target_page_id:
                    raise ValidationError(f"既有第 {target_index} 列缺少 Page ID，無法更新")

                partial_payload: dict[str, Any] = {}
                for name, prop in page.properties.items():
                    if name == database.order_property_name:
                        continue
                    prop_def = database.get_property(name)
                    if prop_def and prop_def.is_writable:
                        partial_payload[name] = prop.to_notion_payload()

                partial_payload[database.order_property_name] = {"number": target_index}
                self.gateway.update_page_properties(target_page_id, partial_payload)
            else:
                page.index = target_index
                self.gateway.create_page(database, page, erase_missing_writable=False)

        resolved_input = self.storage.resolve_read_path(input_path)
        return CommandResult(
            affected_count=len(document.pages),
            message=(
                f"已從 {resolved_input} 讀取資料，並自 index {start_index} 開始寫入 {len(document.pages)} 筆欄位資料"
            ),
            target_path=resolved_input,
        )
