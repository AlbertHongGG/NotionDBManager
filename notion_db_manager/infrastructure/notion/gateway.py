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

        # 1. Search all data sources matching database_name in workspace
        ds_matches = self._search_data_sources(query.database_name)
        if not ds_matches:
            raise DomainError(f"在工作區中找不到名稱為 '{query.database_name}' 的資料庫")

        # 2. For each data source, fetch its parent database container
        candidates: list[tuple[dict[str, Any], dict[str, Any]]] = []
        for ds in ds_matches:
            parent_info = ds.get("parent", {})
            db_id = parent_info.get("database_id")
            if db_id:
                try:
                    db_container = self.client.request("GET", f"/databases/{db_id}")
                    candidates.append((ds, db_container))
                except Exception:
                    candidates.append((ds, {}))
            else:
                candidates.append((ds, {}))

        # 3. If parent_page is specified, resolve target_page_id and filter
        if query.parent_page:
            target_page_id = self._resolve_page_id(query.parent_page)
            normalized_target_id = target_page_id.replace("-", "").lower()
            filtered_candidates: list[tuple[dict[str, Any], dict[str, Any]]] = []
            for ds, db in candidates:
                p_data = db.get("parent", {}) or ds.get("parent", {})
                p_type = p_data.get("type", "")
                parent_id = p_data.get(p_type) if p_type in ("page_id", "block_id") else None
                if not parent_id:
                    parent_id = p_data.get("page_id") or p_data.get("block_id")
                if parent_id and parent_id.replace("-", "").lower() == normalized_target_id:
                    filtered_candidates.append((ds, db))

            if not filtered_candidates:
                page_desc = query.parent_page.title or query.parent_page.page_id
                raise DomainError(f"在指定頁面 '{page_desc}' 底下找不到名稱為 '{query.database_name}' 的資料庫")
            candidates = filtered_candidates

        # 4. Disambiguation
        normalized_name = query.database_name.strip().lower()

        def extract_name(ds: dict[str, Any], db: dict[str, Any]) -> str:
            title_items = db.get("title", [])
            db_title = "".join(t.get("plain_text", "") for t in title_items)
            return (db_title or ds.get("name", "")).strip()

        exact_matches = [
            (ds, db) for (ds, db) in candidates if extract_name(ds, db).lower() == normalized_name
        ]

        if len(exact_matches) == 1:
            matched_ds, matched_db = exact_matches[0]
            if matched_ds.get("properties"):
                return NotionMapper.database_from_data_source(matched_ds, matched_db)
            return self.get_database(matched_db.get("id") or matched_ds.get("id"))

        if not exact_matches and len(candidates) == 1:
            matched_ds, matched_db = candidates[0]
            if matched_ds.get("properties"):
                return NotionMapper.database_from_data_source(matched_ds, matched_db)
            return self.get_database(matched_db.get("id") or matched_ds.get("id"))

        # Multiple matches exist (exact or fuzzy)
        candidates_to_report = exact_matches or candidates
        candidate_infos: list[dict[str, str | None]] = []
        for ds, db in candidates_to_report:
            parent = db.get("parent", {}) or ds.get("parent", {})
            p_type = parent.get("type")
            p_id = parent.get(p_type) if p_type in ("page_id", "block_id") else None
            p_title = self._get_page_title(p_id) if p_type == "page_id" and p_id else None
            candidate_infos.append(
                {
                    "database_id": db.get("id") or ds.get("id"),
                    "parent_type": p_type,
                    "parent_id": p_id,
                    "parent_title": p_title,
                }
            )

        raise AmbiguousDatabaseError(database_name=query.database_name, candidates=candidate_infos)

    def search_database_by_name(self, database_name: str) -> Database:
        return self.locate_database(DatabaseQuery(database_name=database_name))

    def _search_data_sources(self, database_name: str) -> list[dict[str, Any]]:
        payload: dict[str, Any] = {
            "query": database_name,
            "filter": {"value": "data_source", "property": "object"},
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
        # First try GET /databases/{database_id}
        try:
            db_res = self.client.request("GET", f"/databases/{database_id}")
            data_sources = db_res.get("data_sources", [])
            if data_sources:
                ds_id = data_sources[0]["id"]
                ds_res = self.client.request("GET", f"/data_sources/{ds_id}")
                return NotionMapper.database_from_data_source(ds_res, db_data=db_res)
            # If properties are present directly (e.g. mock tests / legacy fixture payload)
            if db_res.get("properties"):
                return NotionMapper.database_from_notion(db_res)
        except Exception:
            pass

        # Try GET /data_sources/{database_id} in case caller passed data_source_id directly
        ds_res = self.client.request("GET", f"/data_sources/{database_id}")
        parent_info = ds_res.get("parent", {})
        parent_db_id = parent_info.get("database_id")
        db_res = None
        if parent_db_id:
            try:
                db_res = self.client.request("GET", f"/databases/{parent_db_id}")
            except Exception:
                pass
        return NotionMapper.database_from_data_source(ds_res, db_data=db_res)

    def ensure_order_property(self, database: Database) -> Database:
        order_prop = database.get_property(database.order_property_name)
        if order_prop and order_prop.property_type != "number":
            raise DomainError(
                f"資料庫中已存在 '{database.order_property_name}' 欄位，但型別不是 number，請手動更名或移除"
            )

        current_db = database
        if not order_prop:
            # Under Notion 2026-03-11, schema property updates are performed on data_sources endpoint
            self.client.request(
                "PATCH",
                f"/data_sources/{database.data_source_id}",
                {"properties": {database.order_property_name: {"number": {}}}},
            )
            current_db = self.get_database(database.id)

        # Retrieve all pages ordered by creation time to initialize sequential numbers if needed
        pages_raw = self._query_all_pages(
            current_db.data_source_id,
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
            database.data_source_id,
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
            "parent": {"data_source_id": database.data_source_id},
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
            self.client.request("PATCH", f"/pages/{page_id}", {"in_trash": True})

    def upload_file(self, filename: str, file_bytes: bytes, mime_type: str = "image/jpeg") -> str:
        return self.client.upload_file(filename=filename, file_bytes=file_bytes, mime_type=mime_type)

    def _query_all_pages(self, data_source_id: str, sorts: list[dict[str, Any]] | None = None) -> list[dict[str, Any]]:
        payload: dict[str, Any] = {"page_size": 100}
        if sorts:
            payload["sorts"] = sorts
        results: list[dict[str, Any]] = []
        while True:
            response = self.client.request("POST", f"/data_sources/{data_source_id}/query", payload)
            results.extend(response.get("results", []))
            if not response.get("has_more"):
                break
            payload["start_cursor"] = response["next_cursor"]
        return results
