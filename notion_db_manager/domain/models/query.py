from __future__ import annotations

import re
from dataclasses import dataclass

from notion_db_manager.core.exceptions import ValidationError

UUID_REGEX = re.compile(
    r"([0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}|[0-9a-fA-F]{32})"
)


def extract_uuid(raw: str) -> str | None:
    """Extract standard or hex UUID from a string or Notion URL."""
    match = UUID_REGEX.search(raw)
    if not match:
        return None
    matched_str = match.group(1).replace("-", "").lower()
    # Format to standard 8-4-4-4-12 UUID format
    return (
        f"{matched_str[:8]}-{matched_str[8:12]}-{matched_str[12:16]}-"
        f"{matched_str[16:20]}-{matched_str[20:]}"
    )


@dataclass(frozen=True, slots=True)
class PageReference:
    """Represents a reference to a Notion Page (either by ID/URL or by title)."""

    page_id: str | None = None
    title: str | None = None

    @classmethod
    def from_raw(cls, raw: str) -> PageReference:
        cleaned = raw.strip()
        if not cleaned:
            raise ValidationError("頁面參照不能為空")

        extracted_id = extract_uuid(cleaned)
        # If the string contains a Notion URL or is a pure UUID
        if ("notion.so" in cleaned or "notion.site" in cleaned) and extracted_id:
            return cls(page_id=extracted_id)

        # If the raw input itself is an exact 32-hex or 36-hyphenated UUID string
        cleaned_no_dash = cleaned.replace("-", "")
        if len(cleaned_no_dash) == 32 and all(c in "0123456789abcdefABCDEF" for c in cleaned_no_dash):
            return cls(page_id=extracted_id)

        # Otherwise treat as a page title
        return cls(title=cleaned)


@dataclass(frozen=True, slots=True)
class DatabaseQuery:
    """Specification for querying and locating a Notion Database."""

    database_name: str | None = None
    database_id: str | None = None
    parent_page: PageReference | None = None

    def __post_init__(self) -> None:
        if not self.database_name and not self.database_id:
            raise ValidationError("查詢資料庫時必須提供 database_name 或 database_id")
        if self.database_id:
            cleaned_id = extract_uuid(self.database_id)
            if cleaned_id:
                object.__setattr__(self, "database_id", cleaned_id)
