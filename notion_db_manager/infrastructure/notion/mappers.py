from __future__ import annotations

from typing import Any

from notion_db_manager.core.exceptions import DomainError
from notion_db_manager.core.types import ORDER_PROPERTY
from notion_db_manager.domain.models import Database, Page, PropertyDefinition
from notion_db_manager.domain.properties.registry import PropertyRegistry


class NotionMapper:
    """Mappers for converting between raw Notion API responses and Domain Entities."""

    @staticmethod
    def database_from_notion(data: dict[str, Any], order_property: str = ORDER_PROPERTY) -> Database:
        database_id = data.get("id", "")
        title_items = data.get("title", [])
        title = "".join(item.get("plain_text", "") for item in title_items) or database_id

        raw_properties = data.get("properties", {})
        properties: dict[str, PropertyDefinition] = {}
        title_property_name: str | None = None

        for name, config in raw_properties.items():
            prop_type = config.get("type", "")
            if prop_type == "title":
                title_property_name = name
            properties[name] = PropertyDefinition(
                name=name,
                property_type=prop_type,
                raw_config=config,
            )

        if not title_property_name:
            raise DomainError(f"資料庫 (ID: {database_id}) 缺少 title 欄位，無法操作")

        from notion_db_manager.domain.models.database import DatabaseParent

        parent_data = data.get("parent", {})
        parent_type = parent_data.get("type", "")
        parent_id = parent_data.get(parent_type) if parent_type in ("page_id", "block_id", "database_id") else None
        parent_obj = DatabaseParent(parent_type=parent_type, parent_id=parent_id) if parent_type else None

        return Database(
            id=database_id,
            name=title,
            properties=properties,
            title_property_name=title_property_name,
            order_property_name=order_property,
            parent=parent_obj,
        )

    @staticmethod
    def page_from_notion(
        data: dict[str, Any],
        order_property: str = ORDER_PROPERTY,
        fallback_index: int = 1,
    ) -> Page:
        page_id = data.get("id")
        raw_properties = data.get("properties", {})

        # Extract order index from order_property
        order_config = raw_properties.get(order_property, {})
        index_val = order_config.get("number")
        page_index = index_val if index_val is not None else fallback_index

        properties = {}
        for name, prop_data in raw_properties.items():
            if isinstance(prop_data, dict):
                properties[name] = PropertyRegistry.from_notion(prop_data)

        return Page(
            id=page_id,
            index=page_index,
            properties=properties,
        )
