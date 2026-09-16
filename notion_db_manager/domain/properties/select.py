from __future__ import annotations

from typing import Any

from notion_db_manager.domain.properties.base import BasePropertyValue


class SelectProperty(BasePropertyValue):
    property_type = "select"

    def __init__(self, value: str | None = None) -> None:
        self._value = value

    @property
    def value(self) -> str | None:
        return self._value

    def to_notion_payload(self) -> dict[str, Any]:
        return {"select": {"name": self._value} if self._value is not None else None}

    def get_empty_notion_payload(self) -> dict[str, Any]:
        return {"select": None}

    @classmethod
    def from_notion(cls, raw: dict[str, Any]) -> SelectProperty:
        data = raw.get("select")
        return cls(data.get("name") if data else None)

    @classmethod
    def from_storage(cls, raw: dict[str, Any]) -> SelectProperty:
        return cls(raw.get("value"))


class StatusProperty(BasePropertyValue):
    property_type = "status"

    def __init__(self, value: str | None = None) -> None:
        self._value = value

    @property
    def value(self) -> str | None:
        return self._value

    def to_notion_payload(self) -> dict[str, Any]:
        return {"status": {"name": self._value} if self._value is not None else None}

    def get_empty_notion_payload(self) -> dict[str, Any]:
        return {"status": None}

    @classmethod
    def from_notion(cls, raw: dict[str, Any]) -> StatusProperty:
        data = raw.get("status")
        return cls(data.get("name") if data else None)

    @classmethod
    def from_storage(cls, raw: dict[str, Any]) -> StatusProperty:
        return cls(raw.get("value"))


class MultiSelectProperty(BasePropertyValue):
    property_type = "multi_select"

    def __init__(self, value: list[str] | None = None) -> None:
        self._value = list(value) if value else []

    @property
    def value(self) -> list[str]:
        return list(self._value)

    def to_notion_payload(self) -> dict[str, Any]:
        return {"multi_select": [{"name": item} for item in self._value]}

    def get_empty_notion_payload(self) -> dict[str, Any]:
        return {"multi_select": []}

    @classmethod
    def from_notion(cls, raw: dict[str, Any]) -> MultiSelectProperty:
        data = raw.get("multi_select", [])
        return cls([item.get("name", "") for item in data if "name" in item])

    @classmethod
    def from_storage(cls, raw: dict[str, Any]) -> MultiSelectProperty:
        return cls(raw.get("value") or [])
