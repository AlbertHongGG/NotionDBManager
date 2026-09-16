from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from notion_db_manager.core.types import ORDER_PROPERTY
from notion_db_manager.domain.models.database import Database
from notion_db_manager.domain.properties.base import BasePropertyValue
from notion_db_manager.domain.properties.registry import PropertyRegistry


@dataclass(slots=True)
class Page:
    index: int
    properties: dict[str, BasePropertyValue] = field(default_factory=dict)
    id: str | None = None

    def get_property(self, name: str) -> BasePropertyValue | None:
        return self.properties.get(name)

    def set_property(self, name: str, property_value: BasePropertyValue) -> None:
        self.properties[name] = property_value

    def to_storage_dict(self, selected_columns: list[str] | None = None) -> dict[str, Any]:
        result_properties: dict[str, Any] = {}
        for name, prop in self.properties.items():
            if name == ORDER_PROPERTY:
                continue
            if selected_columns is not None and name not in selected_columns:
                continue
            result_properties[name] = prop.to_storage_dict()

        return {
            "index": self.index,
            "page_id": self.id or "",
            "properties": result_properties,
        }

    def to_notion_payload(
        self,
        database: Database,
        erase_missing_writable: bool = False,
    ) -> dict[str, Any]:
        payload: dict[str, Any] = {}

        if erase_missing_writable:
            for name, prop_def in database.properties.items():
                if name == database.order_property_name:
                    continue
                if prop_def.is_writable and name not in self.properties:
                    empty_prop = PropertyRegistry.create_empty(prop_def.property_type)
                    payload[name] = empty_prop.get_empty_notion_payload()

        for name, prop in self.properties.items():
            if name == database.order_property_name:
                continue
            prop_def = database.get_property(name)
            if not prop_def or prop_def.is_readonly:
                continue
            payload[name] = prop.to_notion_payload()

        # Ensure order property is always set to page index
        payload[database.order_property_name] = {"number": self.index}

        # Ensure title property is present
        if database.title_property_name not in payload:
            payload[database.title_property_name] = {"title": []}

        return payload
