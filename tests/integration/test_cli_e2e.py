from __future__ import annotations

from pathlib import Path
from unittest.mock import patch, MagicMock
import pytest

from notion_db_manager.cli.main import main
from notion_db_manager.domain.models import Database, Page, PropertyDefinition
from notion_db_manager.domain.properties import TitleProperty


@pytest.fixture
def mock_gateway_db() -> Database:
    return Database(
        id="db-mock",
        name="MockTasks",
        properties={
            "Name": PropertyDefinition("Name", "title", {}),
            "__NDM_INDEX__": PropertyDefinition("__NDM_INDEX__", "number", {}),
        },
        title_property_name="Name",
    )


def test_cli_export_all(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, mock_gateway_db: Database) -> None:
    monkeypatch.setattr(
        "sys.argv",
        [
            "notion-db-manager",
            "reader",
            "export-all",
            "--token",
            "secret_test",
            "--database-name",
            "MockTasks",
            "-o",
            str(tmp_path / "output.json"),
        ],
    )

    with (
        patch("notion_db_manager.cli.dispatch.NotionHttpClient"),
        patch("notion_db_manager.cli.dispatch.NotionGatewayImpl") as mock_gw_cls,
    ):
        mock_gw = mock_gw_cls.return_value
        mock_gw.search_database_by_name.return_value = mock_gateway_db
        mock_gw.ensure_order_property.return_value = mock_gateway_db
        mock_gw.get_ordered_pages.return_value = [
            Page(index=1, properties={"Name": TitleProperty("Item 1")}, id="p1")
        ]

        # Should execute successfully without SystemExit error
        main()

    assert (tmp_path / "output.json").is_file()


def test_cli_missing_database_error(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "sys.argv",
        [
            "notion-db-manager",
            "reader",
            "export-all",
            "--token",
            "secret_test",
            "--database-name",
            "NonExistentDB",
            "-o",
            "out.json",
        ],
    )

    with (
        patch("notion_db_manager.cli.dispatch.NotionHttpClient"),
        patch("notion_db_manager.cli.dispatch.NotionGatewayImpl") as mock_gw_cls,
    ):
        mock_gw = mock_gw_cls.return_value
        from notion_db_manager.core.exceptions import DomainError

        mock_gw.search_database_by_name.side_effect = DomainError("找不到名稱為 'NonExistentDB' 的資料庫")

        with pytest.raises(SystemExit) as exc_info:
            main()

        assert exc_info.value.code == 1
