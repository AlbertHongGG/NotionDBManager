from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from notion_db_manager.core.exceptions import ValidationError


class BasePropertyValue(ABC):
    """Abstract Base Class for all polymorphic Notion property values."""

    @property
    @abstractmethod
    def property_type(self) -> str:
        """Notion property type identifier (e.g. 'title', 'number')."""

    @property
    def is_readonly(self) -> bool:
        """Whether this property is read-only in Notion."""
        return False

    @property
    @abstractmethod
    def value(self) -> Any:
        """The normalized native Python value."""

    def to_storage_dict(self) -> dict[str, Any]:
        """Serialize property into standardized JSON document structure."""
        result: dict[str, Any] = {
            "type": self.property_type,
            "value": self.value,
        }
        if self.is_readonly:
            result["readonly"] = True
        return result

    @abstractmethod
    def to_notion_payload(self) -> dict[str, Any]:
        """Convert this property into the format expected by Notion API for updates/creates."""

    def get_empty_notion_payload(self) -> dict[str, Any]:
        """Generate payload that clears/resets this property in Notion."""
        if self.is_readonly:
            raise ValidationError(f"唯讀欄位型別 '{self.property_type}' 不可清空或寫入")
        raise NotImplementedError(f"{self.property_type} 尚未實作清空行為")

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__} type={self.property_type} value={self.value!r}>"

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, BasePropertyValue):
            return False
        return self.property_type == other.property_type and self.value == other.value
