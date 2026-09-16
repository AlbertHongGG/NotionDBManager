from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from notion_db_manager.core.exceptions import ConfigurationError


ENV_TOKEN_KEYS = ("NOTION_DB_MANAGER_TOKEN", "NOTION_TOKEN")
ENV_DB_KEYS = ("NOTION_DB_MANAGER_DATABASE_NAME", "NOTION_DATABASE_NAME")
ENV_DB_ID_KEYS = ("NOTION_DB_MANAGER_DATABASE_ID", "NOTION_DATABASE_ID")
ENV_PAGE_KEYS = ("NOTION_DB_MANAGER_PAGE", "NOTION_PAGE", "NOTION_DB_MANAGER_PARENT_PAGE", "NOTION_PARENT_PAGE")
ENV_GOOGLE_MAP_KEYS = ("GOOGLE_MAP_API", "GOOGLE_MAPS_API_KEY", "GOOGLE_PLACES_API_KEY")
ENV_CONCURRENCY_KEY = "NOTION_DB_MANAGER_CONCURRENCY"


@dataclass(frozen=True, slots=True)
class NotionConnectionConfig:
    """Configuration required to connect and interact with Notion databases."""

    token: str
    database_name: str | None = None
    database_id: str | None = None
    page: str | None = None

    def __post_init__(self) -> None:
        if not self.token or not self.token.strip():
            raise ConfigurationError("Notion API Token 不能為空")
        if not self.database_name and not self.database_id:
            raise ConfigurationError("必須提供 Notion Database Name 或 Database ID (可由參數或 .env 設定)")


# Alias Settings to NotionConnectionConfig for domain compatibility
Settings = NotionConnectionConfig


@dataclass(frozen=True, slots=True)
class PhotoEnrichConfig:
    """Configuration required for photo enrichment tasks."""

    provider: str
    concurrency: int
    categories: list[str] | None = None
    clean_directory: bool = True
    google_api_key: str | None = None

    def __post_init__(self) -> None:
        if not self.provider or not self.provider.strip():
            raise ConfigurationError("照片提供者 (provider) 不能為空")
        if self.concurrency < 1:
            raise ConfigurationError(f"並發數量 (concurrency) 必須為大於或等於 1 的正整數，收到: {self.concurrency}")



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

    @staticmethod
    def get_database_id() -> str | None:
        for key in ENV_DB_ID_KEYS:
            val = os.getenv(key)
            if val:
                return val.strip()
        return None

    @staticmethod
    def get_page() -> str | None:
        for key in ENV_PAGE_KEYS:
            val = os.getenv(key)
            if val:
                return val.strip()
        return None

    @staticmethod
    def get_google_map_api() -> str | None:
        for key in ENV_GOOGLE_MAP_KEYS:
            val = os.getenv(key)
            if val:
                return val.strip()
        return None

    @staticmethod
    def get_concurrency() -> int | None:
        val = os.getenv(ENV_CONCURRENCY_KEY)
        if val is None:
            return None
        cleaned = val.strip()
        if not cleaned:
            return None
        try:
            val_int = int(cleaned)
        except ValueError as exc:
            raise ConfigurationError(f"環境變數 {ENV_CONCURRENCY_KEY} 必須為整數，收到: {cleaned}") from exc
        if val_int < 1:
            raise ConfigurationError(f"環境變數 {ENV_CONCURRENCY_KEY} 必須為大於或等於 1 的正整數，收到: {val_int}")
        return val_int


class ConfigurationResolver:
    """Unified resolver managing configuration hierarchy (CLI args > .env > Domain defaults)."""

    @classmethod
    def resolve_notion_config(cls, args: Any, env_path: Path | None = None) -> NotionConnectionConfig:
        """Resolves Notion connection parameters without interactive prompt."""
        EnvLoader.load(env_path)
        token = getattr(args, "token", None) or EnvLoader.get_token() or ""
        database_id = getattr(args, "database_id", None) or EnvLoader.get_database_id()
        database_name = getattr(args, "database_name", None) or EnvLoader.get_database_name()
        page = getattr(args, "page", None) or EnvLoader.get_page()
        return NotionConnectionConfig(
            token=token,
            database_name=database_name,
            database_id=database_id,
            page=page,
        )

    @classmethod
    def resolve_enrich_config(
        cls,
        args: Any,
        default_concurrency: int = 3,
        env_path: Path | None = None,
    ) -> PhotoEnrichConfig:
        """Resolves photo enrichment parameters."""
        EnvLoader.load(env_path)

        provider = getattr(args, "provider", "playwright") or "playwright"

        # Concurrency resolution: CLI -> .env -> Provider default
        cli_concurrency = getattr(args, "concurrency", None)
        if cli_concurrency is not None:
            if cli_concurrency < 1:
                from notion_db_manager.core.exceptions import ValidationError
                raise ValidationError(f"--concurrency 必須為大於或等於 1 的正整數，收到: {cli_concurrency}")
            concurrency = cli_concurrency
        else:
            env_concurrency = EnvLoader.get_concurrency()
            concurrency = env_concurrency if env_concurrency is not None else default_concurrency

        # Google API Key resolution: CLI -> .env
        google_api_key = getattr(args, "google_api_key", None) or EnvLoader.get_google_map_api()

        categories = getattr(args, "categories", None)
        clean_directory = not getattr(args, "no_clean", False)

        return PhotoEnrichConfig(
            provider=provider,
            concurrency=concurrency,
            categories=categories,
            clean_directory=clean_directory,
            google_api_key=google_api_key,
        )



