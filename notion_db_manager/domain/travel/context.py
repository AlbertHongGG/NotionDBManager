from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from notion_db_manager.domain.models.database import Database


@dataclass(frozen=True, slots=True)
class TravelContext:
    """Immutable domain context encapsulating the authoritative Database entity
    and its deterministic storage paths for a Travel Subsystem execution session.
    """

    database: Database
    images_dir: Path
    manifest_path: Path
