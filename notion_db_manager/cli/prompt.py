from __future__ import annotations

import argparse

from notion_db_manager.core.config import EnvLoader, Settings
from notion_db_manager.core.exceptions import ValidationError


def resolve_concurrency(args: argparse.Namespace, default: int) -> int:
    """Resolves concurrency with strict hierarchy: CLI flag > NOTION_DB_MANAGER_CONCURRENCY in .env > default."""
    EnvLoader.load()

    cli_val = getattr(args, "concurrency", None)
    if cli_val is not None:
        if cli_val < 1:
            raise ValidationError(f"--concurrency 必須為大於或等於 1 的正整數，收到: {cli_val}")
        return cli_val

    env_val = EnvLoader.get_concurrency()
    if env_val is not None:
        return env_val

    return default


def resolve_settings(args: argparse.Namespace) -> Settings:
    """Resolve token, database_name, database_id, page, and concurrency from CLI arguments, environment, or prompt."""
    EnvLoader.load()

    token = getattr(args, "token", None) or EnvLoader.get_token()
    if not token:
        token = input("Notion token: ").strip()

    database_id = getattr(args, "database_id", None) or EnvLoader.get_database_id()
    database_name = getattr(args, "database_name", None) or EnvLoader.get_database_name()

    if not database_name and not database_id:
        database_name = input("Database name: ").strip()

    page = getattr(args, "page", None) or EnvLoader.get_page()
    google_map_api = getattr(args, "google_api_key", None) or EnvLoader.get_google_map_api()
    concurrency = resolve_concurrency(args, default=3)

    return Settings(
        token=token,
        database_name=database_name,
        database_id=database_id,
        page=page,
        google_map_api=google_map_api,
        concurrency=concurrency,
    )

