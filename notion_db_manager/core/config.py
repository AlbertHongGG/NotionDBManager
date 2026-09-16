from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from notion_db_manager.core.exceptions import ConfigurationError


ENV_TOKEN_KEYS = ("NOTION_DB_MANAGER_TOKEN", "NOTION_TOKEN")
ENV_DB_KEYS = ("NOTION_DB_MANAGER_DATABASE_NAME", "NOTION_DATABASE_NAME")


@dataclass(frozen=True, slots=True)
class Settings:
    token: str
    database_name: str

    def __post_init__(self) -> None:
        if not self.token or not self.token.strip():
            raise ConfigurationError("Notion API Token 不能為空")
        if not self.database_name or not self.database_name.strip():
            raise ConfigurationError("Notion Database Name 不能為空")


class EnvLoader:
    @staticmethod
    def load(env_path: Path | None = None) -> Path | None:
        target = env_path or (Path.cwd() / ".env")
        if not target.is_file():
            return None

        for raw_line in target.read_text(encoding="utf-8").splitlines():
            line = raw_line.strip()
            if not line or line.startswith("#"):
                continue
            if line.startswith("export "):
                line = line[7:].strip()
            if "=" not in line:
                continue

            key, value = line.split("=", 1)
            key = key.strip()
            value = EnvLoader._normalize_val(value.strip())
            if key and key not in os.environ:
                os.environ[key] = value
        return target

    @staticmethod
    def _normalize_val(value: str) -> str:
        if len(value) >= 2 and value[0] == value[-1] and value[0] in {'"', "'"}:
            return value[1:-1]
        if " #" in value:
            return value.split(" #", 1)[0].rstrip()
        return value

    @staticmethod
    def get_token() -> str | None:
        for key in ENV_TOKEN_KEYS:
            val = os.getenv(key)
            if val:
                return val.strip()
        return None

    @staticmethod
    def get_database_name() -> str | None:
        for key in ENV_DB_KEYS:
            val = os.getenv(key)
            if val:
                return val.strip()
        return None
