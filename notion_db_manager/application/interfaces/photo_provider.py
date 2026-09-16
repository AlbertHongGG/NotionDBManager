from __future__ import annotations

from pathlib import Path
from typing import Protocol

from notion_db_manager.domain.places import PhotoEnrichSummary, PlaceItem, PlacePhoto


class PlacePhotoProvider(Protocol):
    """Abstraction for external photo retrieval mechanisms."""

    def fetch_photo(self, place: PlaceItem) -> PlacePhoto | None:
        """Fetches the representative photo for a place.

        Returns PlacePhoto if found, None if the place has no photos available.
        Raises an exception if the provider itself encounters a fatal error (Fail-Fast).
        """
        ...


class PhotoStorage(Protocol):
    """Abstraction for persisting place photos and manifest metadata."""

    def prepare_directory(self, database_name: str, clean: bool = True) -> Path:
        """Prepares the target storage directory. If clean=True, empties existing files first."""
        ...

    def save_photo(self, database_name: str, place: PlaceItem, photo: PlacePhoto) -> Path:
        """Saves a photo binary to disk and returns the saved file path."""
        ...

    def save_manifest(self, database_name: str, summary: PhotoEnrichSummary) -> Path:
        """Saves an enrichment run manifest JSON and returns the saved file path."""
        ...
