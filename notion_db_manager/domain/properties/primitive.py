from __future__ import annotations

from typing import Any

from notion_db_manager.domain.properties.base import BasePropertyValue


class CheckboxProperty(BasePropertyValue):
    property_type = "checkbox"

    def __init__(self, value: bool | None = False) -> None:
        self._value = bool(value)

    @property
    def value(self) -> bool:
        return self._value

    def to_notion_payload(self) -> dict[str, Any]:
        return {"checkbox": self._value}

    def get_empty_notion_payload(self) -> dict[str, Any]:
        return {"checkbox": False}

    @classmethod
    def from_notion(cls, raw: dict[str, Any]) -> CheckboxProperty:
        return cls(raw.get("checkbox", False))

    @classmethod
    def from_storage(cls, raw: dict[str, Any]) -> CheckboxProperty:
        return cls(raw.get("value", False))


class DateProperty(BasePropertyValue):
    property_type = "date"

    def __init__(self, value: dict[str, Any] | str | None = None) -> None:
        if isinstance(value, str):
            self._value = {"start": value}
        else:
            self._value = value

    @property
    def value(self) -> dict[str, Any] | None:
        return self._value

    def to_notion_payload(self) -> dict[str, Any]:
        return {"date": self._value}

    def get_empty_notion_payload(self) -> dict[str, Any]:
        return {"date": None}

    @classmethod
    def from_notion(cls, raw: dict[str, Any]) -> DateProperty:
        return cls(raw.get("date"))

    @classmethod
    def from_storage(cls, raw: dict[str, Any]) -> DateProperty:
        return cls(raw.get("value"))


class UrlProperty(BasePropertyValue):
    property_type = "url"

    def __init__(self, value: str | None = None) -> None:
        self._value = value

    @property
    def value(self) -> str | None:
        return self._value

    def to_notion_payload(self) -> dict[str, Any]:
        return {"url": self._value}

    def get_empty_notion_payload(self) -> dict[str, Any]:
        return {"url": None}

    @classmethod
    def from_notion(cls, raw: dict[str, Any]) -> UrlProperty:
        return cls(raw.get("url"))

    @classmethod
    def from_storage(cls, raw: dict[str, Any]) -> UrlProperty:
        return cls(raw.get("value"))


class EmailProperty(BasePropertyValue):
    property_type = "email"

    def __init__(self, value: str | None = None) -> None:
        self._value = value

    @property
    def value(self) -> str | None:
        return self._value

    def to_notion_payload(self) -> dict[str, Any]:
        return {"email": self._value}

    def get_empty_notion_payload(self) -> dict[str, Any]:
        return {"email": None}

    @classmethod
    def from_notion(cls, raw: dict[str, Any]) -> EmailProperty:
        return cls(raw.get("email"))

    @classmethod
    def from_storage(cls, raw: dict[str, Any]) -> EmailProperty:
        return cls(raw.get("value"))


class PhoneNumberProperty(BasePropertyValue):
    property_type = "phone_number"

    def __init__(self, value: str | None = None) -> None:
        self._value = value

    @property
    def value(self) -> str | None:
        return self._value

    def to_notion_payload(self) -> dict[str, Any]:
        return {"phone_number": self._value}

    def get_empty_notion_payload(self) -> dict[str, Any]:
        return {"phone_number": None}

    @classmethod
    def from_notion(cls, raw: dict[str, Any]) -> PhoneNumberProperty:
        return cls(raw.get("phone_number"))

    @classmethod
    def from_storage(cls, raw: dict[str, Any]) -> PhoneNumberProperty:
        return cls(raw.get("value"))
