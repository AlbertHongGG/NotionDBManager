from __future__ import annotations

import json
import time
from typing import Any

import requests

from notion_db_manager.core.exceptions import NotionGatewayError
from notion_db_manager.core.types import NOTION_API_VERSION


class NotionHttpClient:
    """Low-level HTTP client dedicated to communication with Notion REST API."""

    BASE_URL = "https://api.notion.com/v1"

    def __init__(self, token: str, timeout: int = 30) -> None:
        self.token = token
        self.version = NOTION_API_VERSION
        self.session = requests.Session()
        self.session.headers.update(
            {
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json",
                "Notion-Version": self.version,
            }
        )
        self.timeout = timeout

    def request(
        self,
        method: str,
        endpoint: str,
        payload: dict[str, Any] | None = None,
        max_retries: int = 3,
    ) -> dict[str, Any]:
        url = f"{self.BASE_URL}{endpoint}"
        retries = 0

        while True:
            try:
                response = self.session.request(
                    method=method,
                    url=url,
                    json=payload,
                    timeout=self.timeout,
                )
            except requests.RequestException as exc:
                raise NotionGatewayError(f"無法連線至 Notion API: {exc}") from exc

            # Handle 429 Rate Limit with exponential backoff & Retry-After
            if response.status_code == 429 and retries < max_retries:
                retries += 1
                retry_after_header = response.headers.get("Retry-After")
                try:
                    sleep_time = float(retry_after_header) if retry_after_header else (2.0 ** retries)
                except ValueError:
                    sleep_time = 2.0 ** retries
                time.sleep(sleep_time)
                continue

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

    def upload_file(
        self,
        filename: str,
        file_bytes: bytes,
        mime_type: str = "image/jpeg",
        max_retries: int = 3,
    ) -> str:
        """Uploads raw binary bytes to Notion workspace storage using the official File Uploads API.

        Step 1: POST /v1/file_uploads (Create upload session in JSON).
        Step 2: POST /v1/file_uploads/{id}/send (Send binary data via multipart/form-data).
        Returns the created file_upload_id for attaching to page properties.
        """
        # Step 1: Create file upload session
        create_payload = {
            "mode": "single_part",
            "filename": filename,
            "content_type": mime_type,
        }
        create_res = self.request("POST", "/file_uploads", create_payload)
        file_upload_id = create_res.get("id")
        if not file_upload_id:
            raise NotionGatewayError("Notion API 建立檔案上傳 session 未回傳 ID")

        # Step 2: Send file content via multipart/form-data
        send_url = f"{self.BASE_URL}/file_uploads/{file_upload_id}/send"
        headers_send = {
            "Authorization": f"Bearer {self.token}",
            "Notion-Version": self.version,
        }
        files = {"file": (filename, file_bytes, mime_type)}

        retries = 0
        while True:
            try:
                send_res = requests.post(
                    send_url,
                    headers=headers_send,
                    files=files,
                    timeout=self.timeout,
                )
            except requests.RequestException as exc:
                raise NotionGatewayError(f"傳輸檔案二進位至 Notion 失敗: {exc}") from exc

            if send_res.status_code == 429 and retries < max_retries:
                retries += 1
                retry_after_header = send_res.headers.get("Retry-After")
                try:
                    sleep_time = float(retry_after_header) if retry_after_header else (2.0 ** retries)
                except ValueError:
                    sleep_time = 2.0 ** retries
                time.sleep(sleep_time)
                continue

            if send_res.status_code >= 400:
                try:
                    body = send_res.json()
                    message = body.get("message", send_res.text)
                except Exception:
                    body = None
                    message = send_res.text
                raise NotionGatewayError(
                    f"Notion File Upload send 失敗 {send_res.status_code}: {message}",
                    status_code=send_res.status_code,
                    response_body=body,
                )

            return file_upload_id
