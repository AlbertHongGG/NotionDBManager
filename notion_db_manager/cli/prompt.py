from __future__ import annotations

import argparse

from notion_db_manager.core.config import EnvLoader, Settings


def resolve_settings_from_cli(args: argparse.Namespace) -> Settings:
    """Resolve token and database_name from CLI args, .env/env-vars, or interactive prompt."""
    EnvLoader.load()

    token = getattr(args, "token", None) or EnvLoader.get_token()
    if not token:
        token = input("Notion token: ").strip()

    database_name = getattr(args, "database_name", None) or EnvLoader.get_database_name()
    if not database_name:
        database_name = input("Database name: ").strip()

    return Settings(token=token, database_name=database_name)
