from __future__ import annotations

from typing import Any

from notion_db_manager.domain.properties.base import BasePropertyValue


class NumberProperty(BasePropertyValue):
    property_type = "number"

    def __init__(self, value: int | float | None = None) -> None:
        self._value = value

    @property
    def value(self) -> int | float | None:
        return self._value

    def to_notion_payload(self) -> dict[str, Any]:
        return {"number": self._value}

    def get_empty_notion_payload(self) -> dict[str, Any]:
        return {"number": None}

    @classmethod
    def from_notion(cls, raw: dict[str, Any]) -> NumberProperty:
        return cls(raw.get("number"))

    @classmethod
    def from_storage(cls, raw: dict[str, Any]) -> NumberProperty:
        return cls(raw.get("value"))
