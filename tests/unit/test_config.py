from __future__ import annotations

import os
from pathlib import Path

from notion_db_manager.core.config import EnvLoader, Settings


def test_env_loader_with_page(tmp_path: Path, monkeypatch) -> None:
    env_file = tmp_path / ".env"
    env_file.write_text(
        "NOTION_DB_MANAGER_TOKEN=secret_token_123\n"
        "NOTION_DB_MANAGER_DATABASE_NAME=行程安排\n"
        "NOTION_DB_MANAGER_PAGE=名古屋自由行\n"
        "NOTION_DB_MANAGER_DATABASE_ID=c1387d8998314c289ea9952467d3df13\n"
        "GOOGLE_MAP_API=AIzaSyTestKey123\n",
        encoding="utf-8",
    )

    # Clear env vars if any
    for k in (
        "NOTION_DB_MANAGER_TOKEN",
        "NOTION_TOKEN",
        "NOTION_DB_MANAGER_DATABASE_NAME",
        "NOTION_DATABASE_NAME",
        "NOTION_DB_MANAGER_PAGE",
        "NOTION_PAGE",
        "NOTION_DB_MANAGER_DATABASE_ID",
        "NOTION_DATABASE_ID",
        "GOOGLE_MAP_API",
        "GOOGLE_MAPS_API_KEY",
        "GOOGLE_PLACES_API_KEY",
    ):
        monkeypatch.delenv(k, raising=False)

    EnvLoader.load(env_file)

    assert EnvLoader.get_token() == "secret_token_123"
    assert EnvLoader.get_database_name() == "行程安排"
    assert EnvLoader.get_page() == "名古屋自由行"
    assert EnvLoader.get_database_id() == "c1387d8998314c289ea9952467d3df13"
    assert EnvLoader.get_google_map_api() == "AIzaSyTestKey123"

    settings = Settings(
        token=EnvLoader.get_token() or "",
        database_name=EnvLoader.get_database_name(),
        page=EnvLoader.get_page(),
        database_id=EnvLoader.get_database_id(),
        google_map_api=EnvLoader.get_google_map_api(),
    )
    assert settings.token == "secret_token_123"
    assert settings.database_name == "行程安排"
    assert settings.page == "名古屋自由行"
    assert settings.google_map_api == "AIzaSyTestKey123"
