from __future__ import annotations

import json
from typing import Any

import requests

from notion_db_manager.core.exceptions import NotionGatewayError
from notion_db_manager.core.types import NOTION_API_VERSION


class NotionHttpClient:
    """Low-level HTTP client dedicated to communication with Notion REST API."""

    BASE_URL = "https://api.notion.com/v1"

    def __init__(self, token: str, timeout: int = 30) -> None:
        self.session = requests.Session()
        self.session.headers.update(
            {
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json",
                "Notion-Version": NOTION_API_VERSION,
            }
        )
        self.timeout = timeout

    def request(self, method: str, endpoint: str, payload: dict[str, Any] | None = None) -> dict[str, Any]:
        url = f"{self.BASE_URL}{endpoint}"
        try:
            response = self.session.request(
                method=method,
                url=url,
                json=payload,
                timeout=self.timeout,
            )
        except requests.RequestException as exc:
            raise NotionGatewayError(f"無法連線至 Notion API: {exc}") from exc

        if response.status_code >= 400:
            try:
                body = response.json()
                message = body.get("message", response.text)
            except json.JSONDecodeError:
                body = None
                message = response.text
            raise NotionGatewayError(
                f"Notion API {response.status_code}: {message}",
                status_code=response.status_code,
                response_body=body,
            )

        if not response.content:
            return {}

        try:
            return response.json()
        except json.JSONDecodeError as exc:
            raise NotionGatewayError(f"Notion API 回應非有效 JSON: {exc}") from exc
