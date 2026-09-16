from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from notion_db_manager.application.interfaces.document_storage import DocumentStorage
from notion_db_manager.application.interfaces.notion_gateway import NotionGateway
from notion_db_manager.domain.models import Database


@dataclass(frozen=True, slots=True)
class CommandResult:
    """Outcome of executing an Application Command."""

    affected_count: int
    message: str
    target_path: Path | None = None
    extra_data: dict[str, Any] | None = None


class BaseCommand(ABC):
    """Abstract Base Class for all discrete business capabilities (Use Cases)."""

    def __init__(self, gateway: NotionGateway, storage: DocumentStorage) -> None:
        self.gateway = gateway
        self.storage = storage

    @abstractmethod
    def execute(self, database: Database, **kwargs: Any) -> CommandResult:
        """Execute the use case against the given Notion database."""
