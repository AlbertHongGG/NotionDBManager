from __future__ import annotations

import argparse

from notion_db_manager.core.config import EnvLoader, Settings


def resolve_settings(args: argparse.Namespace) -> Settings:
    """Resolve token, database_name, database_id, and page from CLI arguments, environment, or prompt."""
    EnvLoader.load()

    token = getattr(args, "token", None) or EnvLoader.get_token()
    if not token:
        token = input("Notion token: ").strip()

    database_id = getattr(args, "database_id", None) or EnvLoader.get_database_id()
    database_name = getattr(args, "database_name", None) or EnvLoader.get_database_name()

    if not database_name and not database_id:
        database_name = input("Database name: ").strip()

    page = getattr(args, "page", None) or EnvLoader.get_page()

    return Settings(
        token=token,
        database_name=database_name,
        database_id=database_id,
        page=page,
    )
