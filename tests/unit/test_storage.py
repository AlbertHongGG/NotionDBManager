from __future__ import annotations

import json
from pathlib import Path
import pytest

from notion_db_manager.core.exceptions import StorageError
from notion_db_manager.domain.models import Document, DocumentMeta, Page
from notion_db_manager.domain.properties import TitleProperty
from notion_db_manager.infrastructure.storage.json_storage import JsonDocumentStorage
from notion_db_manager.infrastructure.storage.path_resolver import PathResolver


def test_path_resolver(tmp_path: Path) -> None:
    resolver = PathResolver(base_dir=tmp_path)

    # Relative path defaults to output/
    out_path = resolver.resolve_output_path("data.json")
    assert out_path == tmp_path / "output" / "data.json"
    assert out_path.parent.is_dir()

    # If starts with output/
    out_path2 = resolver.resolve_output_path("output/test.json")
    assert out_path2 == tmp_path / "output" / "test.json"

    # Absolute path
    abs_file = tmp_path / "custom.json"
    assert resolver.resolve_output_path(str(abs_file)) == abs_file


def test_json_storage_roundtrip(tmp_path: Path) -> None:
    resolver = PathResolver(base_dir=tmp_path)
    storage = JsonDocumentStorage(path_resolver=resolver)

    meta = DocumentMeta(database_id="db1", database_name="TestDB", export_type="full")
    doc = Document(meta=meta, pages=[Page(index=1, properties={"Name": TitleProperty("Item 1")})])

    written_path = storage.write("sample.json", doc)
    assert written_path.is_file()

    loaded_doc = storage.read("sample.json")
    assert loaded_doc.meta.database_id == "db1"
    assert len(loaded_doc.pages) == 1
    assert loaded_doc.pages[0].properties["Name"].value == "Item 1"


def test_json_storage_errors(tmp_path: Path) -> None:
    resolver = PathResolver(base_dir=tmp_path)
    storage = JsonDocumentStorage(path_resolver=resolver)

    with pytest.raises(StorageError):
        storage.read("non_existent.json")

    bad_json = tmp_path / "output" / "bad.json"
    bad_json.parent.mkdir(parents=True, exist_ok=True)
    bad_json.write_text("invalid json content", encoding="utf-8")

    with pytest.raises(StorageError):
        storage.read("bad.json")
