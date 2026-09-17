from dataclasses import dataclass, field
from typing import Any


@dataclass(slots=True)
class EnrichItemResult:
    """Value Object representing the enrichment outcome for a single place."""
    index: int
    page_id: str
    name: str
    status: str  # "success" | "skipped" | "failed"
    categories: list[str] = field(default_factory=list)
    local_path: str | None = None
    source_url: str | None = None
    error_message: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "index": self.index,
            "page_id": self.page_id,
            "name": self.name,
            "status": self.status,
            "categories": self.categories,
            "local_path": self.local_path,
            "source_url": self.source_url,
            "error_message": self.error_message,
        }


@dataclass(slots=True)
class TravelPhotoEnrichSummary:
    """Aggregate report of a Travel template photo enrichment run."""
    database_name: str
    provider: str
    total_items: int
    processed_count: int
    skipped_count: int
    success_count: int
    failed_count: int
    items: list[EnrichItemResult] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "database_name": self.database_name,
            "provider": self.provider,
            "total_items": self.total_items,
            "processed_count": self.processed_count,
            "skipped_count": self.skipped_count,
            "success_count": self.success_count,
            "failed_count": self.failed_count,
            "items": [item.to_dict() for item in self.items],
        }


@dataclass(slots=True)
class PushItemResult:
    """Value Object representing the outcome of pushing a photo to Notion for a single place."""
    index: int
    page_id: str
    name: str
    status: str  # "success" | "skipped" | "failed"
    file_upload_id: str | None = None
    error_message: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "index": self.index,
            "page_id": self.page_id,
            "name": self.name,
            "status": self.status,
            "file_upload_id": self.file_upload_id,
            "error_message": self.error_message,
        }


@dataclass(slots=True)
class TravelPhotoPushSummary:
    """Aggregate report of a Travel template photo push to Notion run."""
    database_name: str
    total_items: int
    processed_count: int
    skipped_count: int
    success_count: int
    failed_count: int
    items: list[PushItemResult] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "database_name": self.database_name,
            "total_items": self.total_items,
            "processed_count": self.processed_count,
            "skipped_count": self.skipped_count,
            "success_count": self.success_count,
            "failed_count": self.failed_count,
            "items": [item.to_dict() for item in self.items],
        }

