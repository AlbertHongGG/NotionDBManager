from __future__ import annotations

from typing import Any

from notion_db_manager.domain.properties.base import BasePropertyValue


class FileProperty(BasePropertyValue):
    property_type = "files"

    def __init__(self, value: list[dict[str, Any]] | None = None) -> None:
        self._value = list(value) if value else []

    @property
    def value(self) -> list[dict[str, Any]]:
        return list(self._value)

    def to_notion_payload(self) -> dict[str, Any]:
        files_payload: list[dict[str, Any]] = []
        for item in self._value:
            url = item.get("url", "")
            name = item.get("name") or url
            files_payload.append(
                {
                    "name": name,
                    "type": "external",
                    "external": {"url": url},
                }
            )
        return {"files": files_payload}

    def get_empty_notion_payload(self) -> dict[str, Any]:
        return {"files": []}

    @classmethod
    def from_notion(cls, raw: dict[str, Any]) -> FileProperty:
        raw_files = raw.get("files", [])
        serialized = []
        for item in raw_files:
            file_type = item.get("type", "external")
            url = item.get(file_type, {}).get("url", "")
            serialized.append(
                {
                    "name": item.get("name"),
                    "type": file_type,
                    "url": url,
                }
            )
        return cls(serialized)

    @classmethod
    def from_storage(cls, raw: dict[str, Any]) -> FileProperty:
        return cls(raw.get("value") or [])
