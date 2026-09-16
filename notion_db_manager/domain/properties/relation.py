from __future__ import annotations

from typing import Any

from notion_db_manager.domain.properties.base import BasePropertyValue


class RelationProperty(BasePropertyValue):
    property_type = "relation"

    def __init__(self, value: list[str] | None = None) -> None:
        self._value = list(value) if value else []

    @property
    def value(self) -> list[str]:
        return list(self._value)

    def to_notion_payload(self) -> dict[str, Any]:
        return {"relation": [{"id": item} for item in self._value]}

    def get_empty_notion_payload(self) -> dict[str, Any]:
        return {"relation": []}

    @classmethod
    def from_notion(cls, raw: dict[str, Any]) -> RelationProperty:
        items = raw.get("relation", [])
        return cls([item.get("id", "") for item in items if "id" in item])

    @classmethod
    def from_storage(cls, raw: dict[str, Any]) -> RelationProperty:
        return cls(raw.get("value") or [])


class PeopleProperty(BasePropertyValue):
    property_type = "people"

    def __init__(self, value: list[str] | None = None) -> None:
        self._value = list(value) if value else []

    @property
    def value(self) -> list[str]:
        return list(self._value)

    def to_notion_payload(self) -> dict[str, Any]:
        return {"people": [{"id": item} for item in self._value]}

    def get_empty_notion_payload(self) -> dict[str, Any]:
        return {"people": []}

    @classmethod
    def from_notion(cls, raw: dict[str, Any]) -> PeopleProperty:
        items = raw.get("people", [])
        return cls([item.get("id", "") for item in items if "id" in item])

    @classmethod
    def from_storage(cls, raw: dict[str, Any]) -> PeopleProperty:
        return cls(raw.get("value") or [])
