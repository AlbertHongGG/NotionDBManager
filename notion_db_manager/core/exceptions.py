from __future__ import annotations


class NDMError(Exception):
    """Base exception for all NotionDBManager errors."""


class DomainError(NDMError):
    """Raised when a business or domain invariant rule is violated."""


class AmbiguousDatabaseError(DomainError):
    """Raised when multiple matching databases are found across the workspace."""

    def __init__(self, database_name: str, candidates: list[dict[str, str | None]]) -> None:
        lines = [f"找到 {len(candidates)} 個名稱相近的資料庫 '{database_name}'，請使用 --page 指定所屬頁面："]
        for idx, item in enumerate(candidates, start=1):
            parent_name = item.get("parent_title") or "未知頁面"
            parent_id = item.get("parent_id") or "無"
            db_id = item.get("database_id") or ""
            lines.append(f"  {idx}. 所屬頁面: 「{parent_name}」 (Page ID: {parent_id} | Database ID: {db_id})")
        lines.append(f"提示: 可使用 --page \"{candidates[0].get('parent_title') or candidates[0].get('parent_id')}\" 或直接使用 --database-id 精確定位。")
        super().__init__("\n".join(lines))
        self.database_name = database_name
        self.candidates = candidates


class ValidationError(NDMError):
    """Raised when user-provided input, column name, or index range is invalid."""


class NotionGatewayError(NDMError):
    """Raised when communication with Notion API fails or returns an error response."""

    def __init__(self, message: str, status_code: int | None = None, response_body: dict | None = None) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.response_body = response_body


class StorageError(NDMError):
    """Raised when reading, writing, or decoding stored documents fails."""


class ConfigurationError(NDMError):
    """Raised when required settings or tokens are missing or invalid."""
