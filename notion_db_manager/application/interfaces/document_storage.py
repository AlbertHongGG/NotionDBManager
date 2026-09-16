from __future__ import annotations

from pathlib import Path
from typing import Protocol

from notion_db_manager.domain.models import Document


class DocumentStorage(Protocol):
    """Abstraction for reading and writing Document objects to/from storage."""

    def read(self, raw_path: str) -> Document:
        """Read and parse a Document from a raw file path."""
        ...

    def write(self, raw_path: str, document: Document) -> Path:
        """Write a Document to storage, returning the resolved absolute or normalized path."""
        ...

    def resolve_read_path(self, raw_path: str) -> Path:
        """Resolve a user-provided input path according to storage conventions."""
        ...

    def resolve_write_path(self, raw_path: str) -> Path:
        """Resolve a user-provided output path according to storage conventions."""
        ...
