from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from notion_db_manager.core.exceptions import ValidationError
from notion_db_manager.core.types import ORDER_PROPERTY
from notion_db_manager.domain.properties.registry import PropertyRegistry


@dataclass(frozen=True, slots=True)
class PropertyDefinition:
    name: str
    property_type: str
    raw_config: dict[str, Any]

    @property
    def is_writable(self) -> bool:
        return PropertyRegistry.is_writable(self.property_type)

    @property
    def is_readonly(self) -> bool:
        return PropertyRegistry.is_readonly(self.property_type)


@dataclass(frozen=True, slots=True)
class DatabaseParent:
    parent_type: str
    parent_id: str | None = None
    parent_title: str | None = None


@dataclass(frozen=True, slots=True)
class Database:
    id: str
    name: str
    properties: dict[str, PropertyDefinition]
    title_property_name: str
    order_property_name: str = ORDER_PROPERTY
    parent: DatabaseParent | None = None

    def has_property(self, name: str) -> bool:
        return name in self.properties

    def get_property(self, name: str) -> PropertyDefinition | None:
        return self.properties.get(name)

    def validate_columns(self, column_names: list[str]) -> None:
        invalid = [col for col in column_names if not self.has_property(col)]
        if invalid:
            raise ValidationError(f"找不到指定的欄位: {', '.join(invalid)}")
