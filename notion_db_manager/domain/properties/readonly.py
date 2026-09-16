from __future__ import annotations

from typing import Any

from notion_db_manager.core.exceptions import ValidationError
from notion_db_manager.domain.properties.base import BasePropertyValue


class ReadOnlyProperty(BasePropertyValue):
    """Encapsulates Notion properties that cannot be modified via API."""

    def __init__(self, property_type: str, value: Any = None) -> None:
        self._property_type = property_type
        self._value = value

    @property
    def property_type(self) -> str:
        return self._property_type

    @property
    def is_readonly(self) -> bool:
        return True

    @property
    def value(self) -> Any:
        return self._value

    def to_notion_payload(self) -> dict[str, Any]:
        raise ValidationError(f"唯讀欄位型別 '{self._property_type}' 不可寫入 Notion")

    def get_empty_notion_payload(self) -> dict[str, Any]:
        raise ValidationError(f"唯讀欄位型別 '{self._property_type}' 不可清空或寫入")

    @classmethod
    def from_notion(cls, raw: dict[str, Any], property_type: str) -> ReadOnlyProperty:
        body = raw.get(property_type)
        if property_type == "formula":
            value = body.get(body.get("type")) if isinstance(body, dict) else body
        elif property_type == "rollup":
            if isinstance(body, dict) and body.get("type") == "array":
                # Rollup array contains raw property dicts
                from notion_db_manager.domain.properties.registry import PropertyRegistry

                value = [
                    PropertyRegistry.from_notion(item).to_storage_dict()
                    for item in body.get("array", [])
                    if isinstance(item, dict) and "type" in item
                ]
            elif isinstance(body, dict):
                value = body.get(body.get("type"))
            else:
                value = body
        elif property_type in {"created_by", "last_edited_by"}:
            value = body.get("id") if isinstance(body, dict) else None
        else:
            value = body
        return cls(property_type, value)

    @classmethod
    def from_storage(cls, raw: dict[str, Any], property_type: str) -> ReadOnlyProperty:
        return cls(property_type, raw.get("value"))
