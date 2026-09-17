from __future__ import annotations

import argparse
import os
from pathlib import Path
import pytest

from notion_db_manager.core.config import EnvLoader, NotionConnectionConfig


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

    config = NotionConnectionConfig(
        token=EnvLoader.get_token() or "",
        database_name=EnvLoader.get_database_name(),
        page=EnvLoader.get_page(),
        database_id=EnvLoader.get_database_id(),
    )
    assert config.token == "secret_token_123"
    assert config.database_name == "行程安排"
    assert config.page == "名古屋自由行"
    assert config.database_id == "c1387d8998314c289ea9952467d3df13"



def test_env_loader_concurrency(monkeypatch) -> None:
    import pytest
    from notion_db_manager.core.exceptions import ConfigurationError

    monkeypatch.setenv("NOTION_DB_MANAGER_CONCURRENCY", "4")
    assert EnvLoader.get_concurrency() == 4

    monkeypatch.setenv("NOTION_DB_MANAGER_CONCURRENCY", "1")
    assert EnvLoader.get_concurrency() == 1

    monkeypatch.setenv("NOTION_DB_MANAGER_CONCURRENCY", "0")
    with pytest.raises(ConfigurationError, match="大於或等於 1"):
        EnvLoader.get_concurrency()

    monkeypatch.setenv("NOTION_DB_MANAGER_CONCURRENCY", "not_a_number")
    with pytest.raises(ConfigurationError, match="必須為整數"):
        EnvLoader.get_concurrency()


def test_travel_photo_enrich_config_validation() -> None:
    import pytest
    from notion_db_manager.core.config import TravelPhotoEnrichConfig
    from notion_db_manager.core.exceptions import ConfigurationError

    # Valid config
    cfg = TravelPhotoEnrichConfig(provider="google", concurrency=5)
    assert cfg.provider == "google"
    assert cfg.concurrency == 5
    assert cfg.clean_directory is True

    # Empty provider
    with pytest.raises(ConfigurationError, match="不能為空"):
        TravelPhotoEnrichConfig(provider="", concurrency=3)

    # Concurrency < 1
    with pytest.raises(ConfigurationError, match="必須為大於或等於 1"):
        TravelPhotoEnrichConfig(provider="google", concurrency=0)


def test_configuration_resolver_travel_photo(tmp_path: Path, monkeypatch) -> None:
    import argparse
    import pytest
    from notion_db_manager.core.config import ConfigurationResolver
    from notion_db_manager.core.exceptions import ValidationError

    empty_env = tmp_path / ".env"
    empty_env.write_text("", encoding="utf-8")

    # Clear env
    monkeypatch.delenv("NOTION_DB_MANAGER_CONCURRENCY", raising=False)
    monkeypatch.delenv("GOOGLE_MAP_API", raising=False)
    monkeypatch.delenv("GOOGLE_MAPS_API_KEY", raising=False)
    monkeypatch.delenv("GOOGLE_PLACES_API_KEY", raising=False)

    # 1. Fallback to default
    args1 = argparse.Namespace()
    res1 = ConfigurationResolver.resolve_travel_photo_config(args1, default_concurrency=3, env_path=empty_env)
    assert res1.provider == "playwright"
    assert res1.concurrency == 3
    assert res1.clean_directory is True

    # 2. Env overrides default
    monkeypatch.setenv("NOTION_DB_MANAGER_CONCURRENCY", "6")
    res2 = ConfigurationResolver.resolve_travel_photo_config(args1, default_concurrency=3, env_path=empty_env)
    assert res2.concurrency == 6

    # 3. CLI overrides env
    args3 = argparse.Namespace(concurrency=2, provider="google", no_clean=True, google_api_key="cli_key")
    res3 = ConfigurationResolver.resolve_travel_photo_config(args3, default_concurrency=3, env_path=empty_env)
    assert res3.provider == "google"
    assert res3.concurrency == 2
    assert res3.clean_directory is False
    assert res3.google_api_key == "cli_key"

    # 4. Invalid CLI concurrency raises ValidationError
    args_invalid = argparse.Namespace(concurrency=0)
    with pytest.raises(ValidationError, match="大於或等於 1"):
        ConfigurationResolver.resolve_travel_photo_config(args_invalid, default_concurrency=3, env_path=empty_env)


def test_resolve_travel_push_config(tmp_path: Path, monkeypatch) -> None:
    from notion_db_manager.core.config import ConfigurationResolver, MAX_PUSH_CONCURRENCY, TravelPhotoPushConfig
    from notion_db_manager.core.exceptions import ValidationError

    empty_env = tmp_path / ".env"
    empty_env.write_text("", encoding="utf-8")
    monkeypatch.delenv("NOTION_DB_MANAGER_CONCURRENCY", raising=False)

    # 1. Default resolution
    args = argparse.Namespace(token="token_abc", database_name="db_1")
    cfg = ConfigurationResolver.resolve_travel_push_config(args, env_path=empty_env)
    assert cfg.token == "token_abc"
    assert cfg.database_name == "db_1"
    assert cfg.concurrency == 2
    assert cfg.delay == 0.2

    # 2. Concurrency capped at MAX_PUSH_CONCURRENCY
    args_over_cap = argparse.Namespace(token="token_abc", database_name="db_1", concurrency=4)
    with pytest.raises(ValidationError, match=f"最高為 {MAX_PUSH_CONCURRENCY}"):
        ConfigurationResolver.resolve_travel_push_config(args_over_cap, env_path=empty_env)

    # 3. Concurrency < 1 rejected
    args_zero = argparse.Namespace(token="token_abc", database_name="db_1", concurrency=0)
    with pytest.raises(ValidationError, match=f"最高為 {MAX_PUSH_CONCURRENCY}"):
        ConfigurationResolver.resolve_travel_push_config(args_zero, env_path=empty_env)

    # 4. Valid custom concurrency (3)
    args_valid = argparse.Namespace(token="token_abc", database_name="db_1", concurrency=3, delay=0.5)
    cfg_valid = ConfigurationResolver.resolve_travel_push_config(args_valid, env_path=empty_env)
    assert cfg_valid.concurrency == 3
    assert cfg_valid.delay == 0.5



