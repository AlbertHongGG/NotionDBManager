from __future__ import annotations

from typing import Any

from notion_db_manager.core.exceptions import AmbiguousDatabaseError, DomainError
from notion_db_manager.core.types import ORDER_PROPERTY
from notion_db_manager.domain.models import Database, DatabaseQuery, Page, PageReference
from notion_db_manager.infrastructure.notion.client import NotionHttpClient
from notion_db_manager.infrastructure.notion.mappers import NotionMapper


class NotionGatewayImpl:
    """Production implementation of NotionGateway interfacing with NotionHttpClient."""

    def __init__(self, client: NotionHttpClient) -> None:
        self.client = client

    def locate_database(self, query: DatabaseQuery) -> Database:
        if query.database_id:
            return self.get_database(query.database_id)

        if not query.database_name:
            raise DomainError("未指定資料庫名稱或 ID")

        # 1. Search all databases matching database_name in workspace
        matches = self._search_databases(query.database_name)
        if not matches:
            raise DomainError(f"在工作區中找不到名稱為 '{query.database_name}' 的資料庫")

        # 2. If parent_page is specified, resolve target_page_id and filter
        if query.parent_page:
            target_page_id = self._resolve_page_id(query.parent_page)
            normalized_target_id = target_page_id.replace("-", "").lower()
            filtered_matches = []
            for item in matches:
                parent = item.get("parent", {})
                parent_id = parent.get("page_id") or parent.get("block_id")
                if parent_id and parent_id.replace("-", "").lower() == normalized_target_id:
                    filtered_matches.append(item)

            if not filtered_matches:
                page_desc = query.parent_page.title or query.parent_page.page_id
                raise DomainError(f"在指定頁面 '{page_desc}' 底下找不到名稱為 '{query.database_name}' 的資料庫")
            matches = filtered_matches

        # 3. Disambiguation
        normalized_name = query.database_name.strip().lower()

        def extract_title(item: dict[str, Any]) -> str:
            return "".join(t.get("plain_text", "") for t in item.get("title", []))

        exact_matches = [item for item in matches if extract_title(item).strip().lower() == normalized_name]

        if len(exact_matches) == 1:
            return self.get_database(exact_matches[0]["id"])
        if not exact_matches and len(matches) == 1:
            return self.get_database(matches[0]["id"])

        # Multiple matches exist (exact or fuzzy)
        candidates_to_report = exact_matches or matches
        candidate_infos: list[dict[str, str | None]] = []
        for cand in candidates_to_report:
            parent = cand.get("parent", {})
            p_type = parent.get("type")
            p_id = parent.get(p_type) if p_type in ("page_id", "block_id") else None
            p_title = self._get_page_title(p_id) if p_type == "page_id" and p_id else None
            candidate_infos.append(
                {
                    "database_id": cand["id"],
                    "parent_type": p_type,
                    "parent_id": p_id,
                    "parent_title": p_title,
                }
            )

        raise AmbiguousDatabaseError(database_name=query.database_name, candidates=candidate_infos)

    def search_database_by_name(self, database_name: str) -> Database:
        return self.locate_database(DatabaseQuery(database_name=database_name))

    def _search_databases(self, database_name: str) -> list[dict[str, Any]]:
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
        return matches

    def _resolve_page_id(self, page_ref: PageReference) -> str:
        if page_ref.page_id:
            return page_ref.page_id

        assert page_ref.title is not None
        payload = {
            "query": page_ref.title,
            "filter": {"value": "page", "property": "object"},
            "page_size": 100,
        }
        results: list[dict[str, Any]] = []
        while True:
            res = self.client.request("POST", "/search", payload)
            results.extend(res.get("results", []))
            if not res.get("has_more"):
                break
            payload["start_cursor"] = res["next_cursor"]

        def get_page_title(item: dict[str, Any]) -> str:
            props = item.get("properties", {})
            for p in props.values():
                if p.get("type") == "title":
                    return "".join(t.get("plain_text", "") for t in p.get("title", []))
            return ""

        norm_title = page_ref.title.strip().lower()
        exact = [item for item in results if get_page_title(item).strip().lower() == norm_title]
        candidates = exact or results
        if not candidates:
            raise DomainError(f"在工作區中找不到名稱為 '{page_ref.title}' 的父頁面")
        if len(candidates) > 1 and not exact:
            names = ", ".join(get_page_title(item) or item["id"] for item in candidates[:5])
            raise DomainError(f"找到多個相近的父頁面，請改用 Page ID 或網址精確指定: {names}")
        return candidates[0]["id"]

    def _get_page_title(self, page_id: str) -> str | None:
        try:
            res = self.client.request("GET", f"/pages/{page_id}")
            props = res.get("properties", {})
            for p in props.values():
                if p.get("type") == "title":
                    return "".join(t.get("plain_text", "") for t in p.get("title", []))
        except Exception:
            return None
        return None

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
