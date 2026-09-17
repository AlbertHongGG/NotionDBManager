from __future__ import annotations

from pathlib import Path
from typing import Protocol

from notion_db_manager.domain.travel import (
    EnrichItemResult,
    PlaceItem,
    PlacePhoto,
    TravelPhotoEnrichSummary,
)



class PlacePhotoProvider(Protocol):
    """Abstraction for external photo retrieval mechanisms."""

    async def fetch_photo(self, place: PlaceItem) -> PlacePhoto | None:
        """Fetches the representative photo for a place asynchronously.

        Returns PlacePhoto if found, None if the place has no photos available.
        Raises an exception if the provider itself encounters a fatal error (Fail-Fast).
        """
        ...

    async def close(self) -> None:
        """Closes provider resources (browser, HTTP client, etc.) asynchronously."""
        ...




class PhotoStorage(Protocol):
    """Abstraction for persisting place photos and manifest metadata."""

    def prepare_directory(self, database_name: str, clean: bool = True) -> Path:
        """Prepares the target storage directory. If clean=True, empties existing files first."""
        ...

    def save_photo(self, database_name: str, place: PlaceItem, photo: PlacePhoto) -> Path:
        """Saves a photo binary to disk and returns the saved file path."""
        ...

    def save_manifest(self, database_name: str, summary: TravelPhotoEnrichSummary) -> Path:
        """Saves an enrichment run manifest JSON and returns the saved file path."""
        ...

    def read_manifest(self, database_name: str, custom_path: Path | None = None) -> TravelPhotoEnrichSummary:
        """Reads and deserializes the local manifest.json record."""
        ...

    def load_photo_bytes(self, database_name: str, item: EnrichItemResult) -> bytes:
        """Reads local photo binary bytes from disk for the specified place item."""
        ...
