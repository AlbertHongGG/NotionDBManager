from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any

from notion_db_manager.core.types import ORDER_PROPERTY, ExportType
from notion_db_manager.domain.models.page import Page
from notion_db_manager.domain.properties.registry import PropertyRegistry


@dataclass(frozen=True, slots=True)
class DocumentMeta:
    database_id: str
    database_name: str
    export_type: ExportType
    selected_columns: list[str] = field(default_factory=list)
    selected_rows: list[int] = field(default_factory=list)
    order_property: str = ORDER_PROPERTY
    exported_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> DocumentMeta:
        return cls(
            database_id=data.get("database_id", ""),
            database_name=data.get("database_name", ""),
            export_type=data.get("export_type", "full"),
            selected_columns=list(data.get("selected_columns", [])),
            selected_rows=list(data.get("selected_rows", [])),
            order_property=data.get("order_property", ORDER_PROPERTY),
            exported_at=data.get("exported_at", datetime.now(timezone.utc).isoformat()),
        )


@dataclass(slots=True)
class Document:
    meta: DocumentMeta
    pages: list[Page] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        selected_cols = self.meta.selected_columns if self.meta.export_type == "columns" else None
        return {
            "meta": self.meta.to_dict(),
            "rows": [page.to_storage_dict(selected_columns=selected_cols) for page in self.pages],
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Document:
        meta = DocumentMeta.from_dict(data.get("meta", {}))
        pages: list[Page] = []
        for row in data.get("rows", []):
            page_index = row.get("index", len(pages) + 1)
            page_id = row.get("page_id")
            properties = {}
            for name, prop_data in row.get("properties", {}).items():
                if isinstance(prop_data, dict):
                    properties[name] = PropertyRegistry.from_storage(prop_data)
            pages.append(Page(index=page_index, properties=properties, id=page_id))
        return cls(meta=meta, pages=pages)
