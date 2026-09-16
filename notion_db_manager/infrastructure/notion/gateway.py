from __future__ import annotations

from typing import Any

from notion_db_manager.core.exceptions import DomainError
from notion_db_manager.core.types import ORDER_PROPERTY
from notion_db_manager.domain.models import Database, Page
from notion_db_manager.infrastructure.notion.client import NotionHttpClient
from notion_db_manager.infrastructure.notion.mappers import NotionMapper


class NotionGatewayImpl:
    """Production implementation of NotionGateway interfacing with NotionHttpClient."""

    def __init__(self, client: NotionHttpClient) -> None:
        self.client = client

    def search_database_by_name(self, database_name: str) -> Database:
        payload: dict[str, Any] = {
            "query": database_name,
            "filter": {"value": "database", "property": "object"},
            "page_size": 100,
        }
        matches: list[dict[str, Any]] = []
        while True:
            result = self.client.request("POST", "/search", payload)
            matches.extend(result.get("results", []))
            if not result.get("has_more"):
                break
            payload["start_cursor"] = result["next_cursor"]

        normalized_name = database_name.strip().lower()

        def extract_title(item: dict[str, Any]) -> str:
            return "".join(t.get("plain_text", "") for t in item.get("title", []))

        exact_matches = [item for item in matches if extract_title(item).strip().lower() == normalized_name]
        candidates = exact_matches or matches

        if not candidates:
            raise DomainError(f"找不到名稱為 '{database_name}' 的資料庫")
        if len(candidates) > 1 and not exact_matches:
            names = ", ".join(extract_title(item) or item["id"] for item in candidates[:5])
            raise DomainError(f"找到多個相近資料庫，請改用更精確名稱: {names}")

        return self.get_database(candidates[0]["id"])

    def get_database(self, database_id: str) -> Database:
        result = self.client.request("GET", f"/databases/{database_id}")
        return NotionMapper.database_from_notion(result)

    def ensure_order_property(self, database: Database) -> Database:
        order_prop = database.get_property(database.order_property_name)
        if order_prop and order_prop.property_type != "number":
            raise DomainError(
                f"資料庫中已存在 '{database.order_property_name}' 欄位，但型別不是 number，請手動更名或移除"
            )

        current_db = database
        if not order_prop:
            self.client.request(
                "PATCH",
                f"/databases/{database.id}",
                {"properties": {database.order_property_name: {"number": {}}}},
            )
            current_db = self.get_database(database.id)

        # Retrieve all pages ordered by creation time to initialize sequential numbers if needed
        pages_raw = self._query_all_pages(
            current_db.id,
            sorts=[{"timestamp": "created_time", "direction": "ascending"}],
        )

        for index, raw_page in enumerate(pages_raw, start=1):
            curr_num = raw_page.get("properties", {}).get(current_db.order_property_name, {}).get("number")
            if curr_num != index:
                self.update_page_properties(
                    raw_page["id"],
                    {current_db.order_property_name: {"number": index}},
                )

        return self.get_database(current_db.id)

    def get_ordered_pages(self, database: Database) -> list[Page]:
        raw_pages = self._query_all_pages(
            database.id,
            sorts=[
                {"property": database.order_property_name, "direction": "ascending"},
                {"timestamp": "created_time", "direction": "ascending"},
            ],
        )
        return [
            NotionMapper.page_from_notion(
                page_data,
                order_property=database.order_property_name,
                fallback_index=idx,
            )
            for idx, page_data in enumerate(raw_pages, start=1)
        ]

    def create_page(self, database: Database, page: Page, erase_missing_writable: bool = False) -> Page:
        payload = {
            "parent": {"database_id": database.id},
            "properties": page.to_notion_payload(database, erase_missing_writable=erase_missing_writable),
        }
        result = self.client.request("POST", "/pages", payload)
        return NotionMapper.page_from_notion(
            result,
            order_property=database.order_property_name,
            fallback_index=page.index,
        )

    def update_page_properties(self, page_id: str, properties_payload: dict[str, Any]) -> None:
        self.client.request("PATCH", f"/pages/{page_id}", {"properties": properties_payload})

    def archive_pages(self, page_ids: list[str]) -> None:
        for page_id in page_ids:
            self.client.request("PATCH", f"/pages/{page_id}", {"archived": True})

    def _query_all_pages(self, database_id: str, sorts: list[dict[str, Any]] | None = None) -> list[dict[str, Any]]:
        payload: dict[str, Any] = {"page_size": 100}
        if sorts:
            payload["sorts"] = sorts
        results: list[dict[str, Any]] = []
        while True:
            response = self.client.request("POST", f"/databases/{database_id}/query", payload)
            results.extend(response.get("results", []))
            if not response.get("has_more"):
                break
            payload["start_cursor"] = response["next_cursor"]
        return results
