from __future__ import annotations

from pathlib import Path

from notion_db_manager.application.interfaces.notion_gateway import NotionGateway
from notion_db_manager.application.interfaces.photo_provider import PhotoStorage
from notion_db_manager.domain.models.query import DatabaseQuery, PageReference
from notion_db_manager.domain.travel.context import TravelContext


class TravelContextResolver:
    """Application service for deterministically resolving the unique TravelContext
    for both photo enrichment and pushing workflows.
    Ensures a single authoritative Database entity is resolved from Notion,
    and maps exact, deterministic file system paths without guessing.
    """

    @staticmethod
    def resolve(
        gateway: NotionGateway,
        storage: PhotoStorage,
        database_name: str | None = None,
        database_id: str | None = None,
        page: str | None = None,
        custom_manifest: Path | None = None,
    ) -> TravelContext:
        parent_ref = PageReference.from_raw(page) if page else None
        query = DatabaseQuery(
            database_name=database_name,
            database_id=database_id,
            parent_page=parent_ref,
        )
        database = gateway.locate_database(query)

        if custom_manifest:
            manifest_path = custom_manifest
            images_dir = custom_manifest.parent
        else:
            images_dir = storage.get_images_dir(database.name)
            manifest_path = images_dir / "manifest.json"

        return TravelContext(
            database=database,
            images_dir=images_dir,
            manifest_path=manifest_path,
        )
