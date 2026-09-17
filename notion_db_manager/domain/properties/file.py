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
            name = item.get("name") or "file"
            file_type = item.get("type")
            upload_id = item.get("file_upload_id") or (
                item.get("file_upload", {}).get("id") if isinstance(item.get("file_upload"), dict) else None
            )

            if file_type == "file_upload" or upload_id:
                files_payload.append(
                    {
                        "name": name,
                        "type": "file_upload",
                        "file_upload": {"id": upload_id or item.get("id")},
                    }
                )
            else:
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
            name = item.get("name")
            if file_type == "file_upload":
                upload_id = item.get("file_upload", {}).get("id")
                serialized.append(
                    {
                        "name": name,
                        "type": "file_upload",
                        "file_upload_id": upload_id,
                    }
                )
            else:
                url = item.get(file_type, {}).get("url", "")
                serialized.append(
                    {
                        "name": name,
                        "type": file_type,
                        "url": url,
                    }
                )
        return cls(serialized)

    @classmethod
    def from_storage(cls, raw: dict[str, Any]) -> FileProperty:
        return cls(raw.get("value") or [])
