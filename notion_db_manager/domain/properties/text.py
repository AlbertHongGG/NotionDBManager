from __future__ import annotations

from typing import Any

from notion_db_manager.domain.properties.base import BasePropertyValue


def _split_text_chunks(value: Any) -> list[dict[str, Any]]:
    if value in (None, ""):
        return []
    text_str = str(value) if not isinstance(value, str) else value
    chunks = [text_str[i : i + 1900] for i in range(0, len(text_str), 1900)]
    return [{"type": "text", "text": {"content": chunk}} for chunk in chunks]


def _extract_plain_text(items: list[dict[str, Any]] | None) -> str:
    if not items:
        return ""
    return "".join(item.get("plain_text", "") for item in items)


class TitleProperty(BasePropertyValue):
    property_type = "title"

    def __init__(self, value: str | None = None) -> None:
        self._value = value or ""

    @property
    def value(self) -> str:
        return self._value

    def to_notion_payload(self) -> dict[str, Any]:
        return {"title": _split_text_chunks(self._value)}

    def get_empty_notion_payload(self) -> dict[str, Any]:
        return {"title": []}

    @classmethod
    def from_notion(cls, raw: dict[str, Any]) -> TitleProperty:
        return cls(_extract_plain_text(raw.get("title", [])))

    @classmethod
    def from_storage(cls, raw: dict[str, Any]) -> TitleProperty:
        return cls(raw.get("value") or "")


class RichTextProperty(BasePropertyValue):
    property_type = "rich_text"

    def __init__(self, value: str | None = None) -> None:
        self._value = value or ""

    @property
    def value(self) -> str:
        return self._value

    def to_notion_payload(self) -> dict[str, Any]:
        return {"rich_text": _split_text_chunks(self._value)}

    def get_empty_notion_payload(self) -> dict[str, Any]:
        return {"rich_text": []}

    @classmethod
    def from_notion(cls, raw: dict[str, Any]) -> RichTextProperty:
        return cls(_extract_plain_text(raw.get("rich_text", [])))

    @classmethod
    def from_storage(cls, raw: dict[str, Any]) -> RichTextProperty:
        return cls(raw.get("value") or "")
