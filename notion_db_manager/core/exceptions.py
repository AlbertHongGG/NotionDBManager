from __future__ import annotations


class NDMError(Exception):
    """Base exception for all NotionDBManager errors."""


class DomainError(NDMError):
    """Raised when a business or domain invariant rule is violated."""


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
