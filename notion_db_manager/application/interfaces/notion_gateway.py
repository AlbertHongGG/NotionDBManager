from __future__ import annotations

from typing import Any, Protocol

from notion_db_manager.domain.models import Database, DatabaseQuery, Page


class NotionGateway(Protocol):
    """Abstraction for interacting with Notion databases and pages."""

    def locate_database(self, query: DatabaseQuery) -> Database:
        """Locate a Notion database matching the given query specification."""
        ...

    def search_database_by_name(self, database_name: str) -> Database:
        """Locate a Notion database by its title."""
        ...

    def get_database(self, database_id: str) -> Database:
        """Fetch database details and schema by its ID."""
        ...

    def ensure_order_property(self, database: Database) -> Database:
        """Ensure order property exists and all pages have sequential indices."""
        ...

    def get_ordered_pages(self, database: Database) -> list[Page]:
        """Fetch all pages sorted ascendingly by order property and creation time."""
        ...

    def create_page(self, database: Database, page: Page, erase_missing_writable: bool = False) -> Page:
        """Create a new page in the database and return the created page with its Notion ID."""
        ...

    def update_page_properties(self, page_id: str, properties_payload: dict[str, Any]) -> None:
        """Update property values of an existing page."""
        ...

    def archive_pages(self, page_ids: list[str]) -> None:
        """Archive a batch of pages by their IDs."""
        ...
