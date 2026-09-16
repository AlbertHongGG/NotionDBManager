from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from notion_db_manager.core.exceptions import StorageError
from notion_db_manager.domain.models import Document
from notion_db_manager.infrastructure.storage.path_resolver import PathResolver


class JsonDocumentStorage:
    """JSON implementation of DocumentStorage interface."""

    def __init__(self, path_resolver: PathResolver | None = None) -> None:
        self.resolver = path_resolver or PathResolver()

    def resolve_read_path(self, raw_path: str) -> Path:
        return self.resolver.resolve_input_path(raw_path)

    def resolve_write_path(self, raw_path: str) -> Path:
        return self.resolver.resolve_output_path(raw_path)

    def read(self, raw_path: str) -> Document:
        target_path = self.resolve_read_path(raw_path)
        if not target_path.is_file():
            raise StorageError(f"找不到輸入檔案: {raw_path} (已檢查 {target_path})")

        try:
            with target_path.open("r", encoding="utf-8") as f:
                data: dict[str, Any] = json.load(f)
        except json.JSONDecodeError as exc:
            raise StorageError(f"JSON 檔案解析失敗 ({target_path}): {exc}") from exc
        except OSError as exc:
            raise StorageError(f"讀取檔案失敗 ({target_path}): {exc}") from exc

        return Document.from_dict(data)

    def write(self, raw_path: str, document: Document) -> Path:
        target_path = self.resolve_write_path(raw_path)
        try:
            with target_path.open("w", encoding="utf-8") as f:
                json.dump(document.to_dict(), f, ensure_ascii=False, indent=2)
        except OSError as exc:
            raise StorageError(f"寫入檔案失敗 ({target_path}): {exc}") from exc

        return target_path
