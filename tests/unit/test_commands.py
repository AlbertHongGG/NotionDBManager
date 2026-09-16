from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock
import pytest

from notion_db_manager.application.commands import (
    ExportAllCommand,
    ExportColumnsCommand,
    ExportRowsCommand,
    ImportFullCommand,
    WriteColumnsCommand,
    WriteRowsCommand,
)
from notion_db_manager.core.exceptions import ValidationError
from notion_db_manager.domain.models import Database, Document, DocumentMeta, Page, PropertyDefinition
from notion_db_manager.domain.properties import NumberProperty, TitleProperty


@pytest.fixture
def mock_db() -> Database:
    return Database(
        id="db-123",
        name="Test Database",
        properties={
            "Name": PropertyDefinition("Name", "title", {}),
            "Status": PropertyDefinition("Status", "select", {}),
            "Score": PropertyDefinition("Score", "number", {}),
            "__NDM_INDEX__": PropertyDefinition("__NDM_INDEX__", "number", {}),
        },
        title_property_name="Name",
    )


def test_export_all_command(mock_db: Database) -> None:
    gateway = MagicMock()
    storage = MagicMock()
    storage.write.return_value = Path("/out/all.json")

    p1 = Page(index=1, properties={"Name": TitleProperty("Row 1")}, id="p1")
    p2 = Page(index=2, properties={"Name": TitleProperty("Row 2")}, id="p2")
    gateway.get_ordered_pages.return_value = [p1, p2]

    cmd = ExportAllCommand(gateway, storage)
    result = cmd.execute(mock_db, output_path="all.json")

    assert result.affected_count == 2
    assert result.target_path == Path("/out/all.json")
    storage.write.assert_called_once()
    doc_arg = storage.write.call_args[0][1]
    assert isinstance(doc_arg, Document)
    assert doc_arg.meta.export_type == "full"


def test_export_columns_command(mock_db: Database) -> None:
    gateway = MagicMock()
    storage = MagicMock()
    storage.write.return_value = Path("/out/cols.json")

    p1 = Page(index=1, properties={"Name": TitleProperty("Row 1"), "Score": NumberProperty(10)})
    gateway.get_ordered_pages.return_value = [p1]

    cmd = ExportColumnsCommand(gateway, storage)
    result = cmd.execute(mock_db, output_path="cols.json", columns=["Name", "Score"])

    assert result.affected_count == 1
    doc_arg = storage.write.call_args[0][1]
    assert doc_arg.meta.export_type == "columns"
    assert doc_arg.meta.selected_columns == ["Name", "Score"]


def test_export_rows_command(mock_db: Database) -> None:
    gateway = MagicMock()
    storage = MagicMock()
    storage.write.return_value = Path("/out/rows.json")

    p1 = Page(index=1, properties={"Name": TitleProperty("Row 1")})
    p2 = Page(index=2, properties={"Name": TitleProperty("Row 2")})
    p3 = Page(index=3, properties={"Name": TitleProperty("Row 3")})
    gateway.get_ordered_pages.return_value = [p1, p2, p3]

    cmd = ExportRowsCommand(gateway, storage)
    result = cmd.execute(mock_db, output_path="rows.json", row_expression="1, 3")

    assert result.affected_count == 2
    doc_arg = storage.write.call_args[0][1]
    assert doc_arg.meta.export_type == "rows"
    assert doc_arg.meta.selected_rows == [1, 3]

    # Out of bounds
    with pytest.raises(ValidationError):
        cmd.execute(mock_db, output_path="rows.json", row_expression="5")


def test_import_full_replace_and_append(mock_db: Database) -> None:
    gateway = MagicMock()
    storage = MagicMock()
    storage.resolve_read_path.return_value = Path("/in/all.json")

    existing_p = Page(index=1, id="old-page-id")
    gateway.get_ordered_pages.return_value = [existing_p]

    new_p1 = Page(index=1, properties={"Name": TitleProperty("New 1")})
    new_p2 = Page(index=2, properties={"Name": TitleProperty("New 2")})
    storage.read.return_value = Document(
        meta=DocumentMeta(database_id="db-123", database_name="Test Database", export_type="full"),
        pages=[new_p1, new_p2],
    )

    cmd = ImportFullCommand(gateway, storage)

    # Test replace mode
    result_replace = cmd.execute(mock_db, input_path="all.json", mode="replace")
    assert result_replace.affected_count == 2
    gateway.archive_pages.assert_called_once_with(["old-page-id"])
    assert gateway.create_page.call_count == 2

    # Test append mode
    gateway.archive_pages.reset_mock()
    gateway.create_page.reset_mock()
    result_append = cmd.execute(mock_db, input_path="all.json", mode="append")
    assert result_append.affected_count == 2
    gateway.archive_pages.assert_not_called()
    assert gateway.create_page.call_count == 2


def test_write_columns_command(mock_db: Database) -> None:
    gateway = MagicMock()
    storage = MagicMock()
    storage.resolve_read_path.return_value = Path("/in/cols.json")

    existing_p1 = Page(index=1, id="page-1")
    existing_p2 = Page(index=2, id="page-2")
    gateway.get_ordered_pages.return_value = [existing_p1, existing_p2]

    # Document has 2 pages, starting at index 2 (updates page 2, and creates page 3)
    p_in_1 = Page(index=1, properties={"Score": NumberProperty(50)})
    p_in_2 = Page(index=2, properties={"Score": NumberProperty(60)})
    storage.read.return_value = Document(
        meta=DocumentMeta(database_id="db-123", database_name="Test Database", export_type="columns"),
        pages=[p_in_1, p_in_2],
    )

    cmd = WriteColumnsCommand(gateway, storage)
    result = cmd.execute(mock_db, input_path="cols.json", start_index=2)

    assert result.affected_count == 2
    gateway.update_page_properties.assert_called_once_with(
        "page-2",
        {"Score": {"number": 50}, "__NDM_INDEX__": {"number": 2}},
    )
    gateway.create_page.assert_called_once()
    created_page = gateway.create_page.call_args[0][1]
    assert created_page.index == 3


def test_write_rows_insert_mode(mock_db: Database) -> None:
    gateway = MagicMock()
    storage = MagicMock()
    storage.resolve_read_path.return_value = Path("/in/rows.json")

    existing_p1 = Page(index=1, id="p1")
    existing_p2 = Page(index=2, id="p2")
    gateway.get_ordered_pages.return_value = [existing_p1, existing_p2]

    insert_p = Page(index=1, properties={"Name": TitleProperty("Inserted")})
    storage.read.return_value = Document(
        meta=DocumentMeta(database_id="db-123", database_name="Test Database", export_type="rows"),
        pages=[insert_p],
    )

    cmd = WriteRowsCommand(gateway, storage)
    # Insert at index 2: existing_p2 (currently at 2) should shift to index 3
    result = cmd.execute(mock_db, input_path="rows.json", mode="insert", index=2)

    assert result.affected_count == 1
    # Check shift update was called on existing_p2
    gateway.update_page_properties.assert_called_once_with(
        "p2",
        {"__NDM_INDEX__": {"number": 3}},
    )
    # Check inserted page created at index 2
    gateway.create_page.assert_called_once()
    assert gateway.create_page.call_args[0][1].index == 2


def test_write_rows_overwrite_mode(mock_db: Database) -> None:
    gateway = MagicMock()
    storage = MagicMock()
    storage.resolve_read_path.return_value = Path("/in/rows.json")

    existing_p1 = Page(index=1, id="p1")
    existing_p2 = Page(index=2, id="p2")
    gateway.get_ordered_pages.return_value = [existing_p1, existing_p2]

    over_p = Page(index=1, properties={"Name": TitleProperty("Overwritten")})
    storage.read.return_value = Document(
        meta=DocumentMeta(database_id="db-123", database_name="Test Database", export_type="rows"),
        pages=[over_p],
    )

    cmd = WriteRowsCommand(gateway, storage)
    result = cmd.execute(mock_db, input_path="rows.json", mode="overwrite", index=2)

    assert result.affected_count == 1
    gateway.update_page_properties.assert_called_once()
    target_id, payload = gateway.update_page_properties.call_args[0]
    assert target_id == "p2"
    assert payload["Name"] == {"title": [{"type": "text", "text": {"content": "Overwritten"}}]}
    assert payload["Score"] == {"number": None}  # erased missing writable
