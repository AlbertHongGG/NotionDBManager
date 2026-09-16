from __future__ import annotations

from datetime import datetime
from pathlib import Path
from unittest.mock import MagicMock

from notion_db_manager.application.commands import (
    ExportAllCommand,
    ExportColumnsCommand,
    ExportRowsCommand,
)
from notion_db_manager.application.naming import TimestampedNamingPolicy
from notion_db_manager.domain.models import Database, Page, PropertyDefinition
from notion_db_manager.domain.properties import TitleProperty


def test_timestamped_naming_policy() -> None:
    fixed_time = datetime(2026, 9, 17, 4, 45, 30)
    policy = TimestampedNamingPolicy(clock=lambda: fixed_time)

    assert policy.generate("export-all") == "20260917_044530_export-all.json"
    assert policy.generate("export-columns") == "20260917_044530_export-columns.json"
    assert policy.generate("export-rows") == "20260917_044530_export-rows.json"
    assert policy.generate("custom", ext="csv") == "20260917_044530_custom.csv"


def test_export_commands_default_naming() -> None:
    fixed_time = datetime(2026, 9, 17, 12, 0, 0)
    policy = TimestampedNamingPolicy(clock=lambda: fixed_time)

    gateway = MagicMock()
    storage = MagicMock()
    storage.write.side_effect = lambda p, doc: Path(f"/output/{p}")

    mock_db = Database(
        id="db-1",
        name="Tasks",
        properties={"Name": PropertyDefinition("Name", "title", {})},
        title_property_name="Name",
    )
    gateway.get_ordered_pages.return_value = [
        Page(index=1, properties={"Name": TitleProperty("Item 1")}, id="p1")
    ]

    # 1. ExportAllCommand without output_path
    cmd_all = ExportAllCommand(gateway, storage, naming_policy=policy)
    res_all = cmd_all.execute(mock_db)
    assert res_all.target_path == Path("/output/20260917_120000_export-all.json")
    storage.write.assert_called_with("20260917_120000_export-all.json", storage.write.call_args[0][1])

    # 2. ExportColumnsCommand without output_path
    cmd_cols = ExportColumnsCommand(gateway, storage, naming_policy=policy)
    res_cols = cmd_cols.execute(mock_db, columns=["Name"])
    assert res_cols.target_path == Path("/output/20260917_120000_export-columns.json")

    # 3. ExportRowsCommand without output_path
    cmd_rows = ExportRowsCommand(gateway, storage, naming_policy=policy)
    res_rows = cmd_rows.execute(mock_db, row_expression="1")
    assert res_rows.target_path == Path("/output/20260917_120000_export-rows.json")

    # 4. If custom output_path is provided, it should be respected
    res_custom = cmd_all.execute(mock_db, output_path="my_custom.json")
    assert res_custom.target_path == Path("/output/my_custom.json")
