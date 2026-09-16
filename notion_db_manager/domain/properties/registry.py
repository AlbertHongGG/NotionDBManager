from __future__ import annotations

from typing import Any, Type

from notion_db_manager.domain.properties.base import BasePropertyValue
from notion_db_manager.domain.properties.file import FileProperty
from notion_db_manager.domain.properties.number import NumberProperty
from notion_db_manager.domain.properties.primitive import (
    CheckboxProperty,
    DateProperty,
    EmailProperty,
    PhoneNumberProperty,
    UrlProperty,
)
from notion_db_manager.domain.properties.readonly import ReadOnlyProperty
from notion_db_manager.domain.properties.relation import PeopleProperty, RelationProperty
from notion_db_manager.domain.properties.select import (
    MultiSelectProperty,
    SelectProperty,
    StatusProperty,
)
from notion_db_manager.domain.properties.text import RichTextProperty, TitleProperty


class PropertyRegistry:
    """Registry managing mapping between Notion property types and polymorphic Property classes."""

    _WRITABLE_REGISTRY: dict[str, Type[BasePropertyValue]] = {
        "title": TitleProperty,
        "rich_text": RichTextProperty,
        "number": NumberProperty,
        "select": SelectProperty,
        "status": StatusProperty,
        "multi_select": MultiSelectProperty,
        "checkbox": CheckboxProperty,
        "date": DateProperty,
        "url": UrlProperty,
        "email": EmailProperty,
        "phone_number": PhoneNumberProperty,
        "relation": RelationProperty,
        "people": PeopleProperty,
        "files": FileProperty,
    }

    _READONLY_TYPES: set[str] = {
        "button",
        "created_by",
        "created_time",
        "formula",
        "last_edited_by",
        "last_edited_time",
        "rollup",
        "unique_id",
        "verification",
    }

    @classmethod
    def register(cls, property_type: str, handler_cls: Type[BasePropertyValue]) -> None:
        """Register a new property handler type (OCP extension point)."""
        cls._WRITABLE_REGISTRY[property_type] = handler_cls

    @classmethod
    def is_writable(cls, property_type: str) -> bool:
        return property_type in cls._WRITABLE_REGISTRY

    @classmethod
    def is_readonly(cls, property_type: str) -> bool:
        return property_type in cls._READONLY_TYPES or property_type not in cls._WRITABLE_REGISTRY

    @classmethod
    def from_notion(cls, raw_property: dict[str, Any]) -> BasePropertyValue:
        prop_type = raw_property.get("type", "")
        handler_cls = cls._WRITABLE_REGISTRY.get(prop_type)
        if handler_cls:
            return handler_cls.from_notion(raw_property)  # type: ignore[attr-defined]
        return ReadOnlyProperty.from_notion(raw_property, prop_type)

    @classmethod
    def from_storage(cls, raw_storage: dict[str, Any]) -> BasePropertyValue:
        prop_type = raw_storage.get("type", "")
        handler_cls = cls._WRITABLE_REGISTRY.get(prop_type)
        if handler_cls:
            return handler_cls.from_storage(raw_storage)  # type: ignore[attr-defined]
        return ReadOnlyProperty.from_storage(raw_storage, prop_type)

    @classmethod
    def create_empty(cls, property_type: str) -> BasePropertyValue:
        handler_cls = cls._WRITABLE_REGISTRY.get(property_type)
        if handler_cls:
            return handler_cls()  # type: ignore[call-arg]
        return ReadOnlyProperty(property_type)
