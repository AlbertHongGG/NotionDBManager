from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch
import httpx
import pytest

from notion_db_manager.cli import main


@pytest.fixture
def sample_export_json(tmp_path: Path) -> Path:
    data = {
        "meta": {
            "database_id": "db-test",
            "database_name": "行程安排",
            "export_type": "full",
            "order_property": "__NDM_INDEX__",
        },
        "rows": [
            {
                "index": 1,
                "page_id": "p1",
                "properties": {
                    "地點": {"type": "title", "value": "手長足長像"},
                    "屬性": {"type": "multi_select", "value": ["景點"]},
                },
            },
            {
                "index": 2,
                "page_id": "p2",
                "properties": {
                    "地點": {"type": "title", "value": "高山車站"},
                    "屬性": {"type": "multi_select", "value": ["交通"]},
                },
            },
        ],
    }
    input_file = tmp_path / "export.json"
    input_file.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
    return input_file


def test_cli_travel_enrich_photos_google(tmp_path: Path, sample_export_json: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(
        "sys.argv",
        [
            "notion-db-manager",
            "travel",
            "enrich-photos",
            "--input",
            str(sample_export_json),
            "--provider",
            "google",
            "--google-api-key",
            "AIzaSyFakeKey123",
            "--concurrency",
            "2",
        ],
    )

    search_response = MagicMock()
    search_response.status_code = 200
    search_response.json.return_value = {
        "places": [
            {
                "id": "place_1",
                "displayName": {"text": "手長足長像"},
                "photos": [{"name": "places/p1/photos/ph1", "widthPx": 1200, "heightPx": 800}],
            }
        ]
    }

    media_response = MagicMock()
    media_response.status_code = 200
    media_response.content = b"fake-image-bytes"
    media_response.headers = {"Content-Type": "image/jpeg"}
    media_response.url = "https://places.googleapis.com/v1/places/p1/photos/ph1/media"

    with patch.object(httpx.AsyncClient, "post", new=AsyncMock(return_value=search_response)), patch.object(
        httpx.AsyncClient, "get", new=AsyncMock(return_value=media_response)
    ):
        main()

    manifest_file = tmp_path / "output" / "images" / "行程安排" / "manifest.json"
    assert manifest_file.is_file()

    manifest = json.loads(manifest_file.read_text(encoding="utf-8"))
    assert manifest["database_name"] == "行程安排"
    assert manifest["provider"] == "google"
    # By default, both items are processed (including 交通)
    assert manifest["total_items"] == 2
    assert manifest["success_count"] == 2

    img1 = tmp_path / "output" / "images" / "行程安排" / "01_手長足長像.jpg"
    assert img1.is_file()
    assert img1.read_bytes() == b"fake-image-bytes"


def test_cli_travel_enrich_photos_category_filter(
    tmp_path: Path, sample_export_json: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(
        "sys.argv",
        [
            "notion-db-manager",
            "travel",
            "enrich-photos",
            "--input",
            str(sample_export_json),
            "--provider",
            "google",
            "--google-api-key",
            "AIzaSyFakeKey123",
            "--categories",
            "景點",
        ],
    )

    search_response = MagicMock()
    search_response.status_code = 200
    search_response.json.return_value = {
        "places": [
            {
                "id": "place_1",
                "displayName": {"text": "手長足長像"},
                "photos": [{"name": "places/p1/photos/ph1", "widthPx": 1200, "heightPx": 800}],
            }
        ]
    }

    media_response = MagicMock()
    media_response.status_code = 200
    media_response.content = b"fake-image-bytes"
    media_response.headers = {"Content-Type": "image/jpeg"}
    media_response.url = "https://places.googleapis.com/v1/places/p1/photos/ph1/media"

    with patch.object(httpx.AsyncClient, "post", new=AsyncMock(return_value=search_response)), patch.object(
        httpx.AsyncClient, "get", new=AsyncMock(return_value=media_response)
    ):
        main()

    manifest_file = tmp_path / "output" / "images" / "行程安排" / "manifest.json"
    manifest = json.loads(manifest_file.read_text(encoding="utf-8"))
    assert manifest["processed_count"] == 1
    assert manifest["skipped_count"] == 1
    assert manifest["success_count"] == 1


def test_cli_travel_enrich_photos_fail_fast(
    tmp_path: Path, sample_export_json: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(
        "sys.argv",
        [
            "notion-db-manager",
            "travel",
            "enrich-photos",
            "--input",
            str(sample_export_json),
            "--provider",
            "google",
            "--google-api-key",
            "BadKey",
        ],
    )

    error_response = MagicMock()
    error_response.status_code = 400
    error_response.text = '{"error": {"message": "API key not valid."}}'
    error_response.json.return_value = {"error": {"message": "API key not valid."}}

    with patch.object(httpx.AsyncClient, "post", new=AsyncMock(return_value=error_response)):
        with pytest.raises(SystemExit) as exc_info:
            main()

        assert exc_info.value.code == 1


def test_cli_travel_enrich_photos_cleans_stale_files(
    tmp_path: Path, sample_export_json: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.chdir(tmp_path)

    # Pre-create a stale directory with an obsolete file
    stale_dir = tmp_path / "output" / "images" / "行程安排"
    stale_dir.mkdir(parents=True, exist_ok=True)
    stale_file = stale_dir / "old_leftover.jpg"
    stale_file.write_text("old content", encoding="utf-8")
    assert stale_file.is_file()

    monkeypatch.setattr(
        "sys.argv",
        [
            "notion-db-manager",
            "travel",
            "enrich-photos",
            "--input",
            str(sample_export_json),
            "--provider",
            "google",
            "--google-api-key",
            "AIzaSyFakeKey123",
            "--categories",
            "景點",
        ],
    )

    search_response = MagicMock()
    search_response.status_code = 200
    search_response.json.return_value = {
        "places": [
            {
                "id": "place_1",
                "displayName": {"text": "手長足長像"},
                "photos": [{"name": "places/p1/photos/ph1", "widthPx": 1200, "heightPx": 800}],
            }
        ]
    }

    media_response = MagicMock()
    media_response.status_code = 200
    media_response.content = b"fake-image-bytes"
    media_response.headers = {"Content-Type": "image/jpeg"}
    media_response.url = "https://places.googleapis.com/v1/places/p1/photos/ph1/media"

    with patch.object(httpx.AsyncClient, "post", new=AsyncMock(return_value=search_response)), patch.object(
        httpx.AsyncClient, "get", new=AsyncMock(return_value=media_response)
    ):
        main()

    # The stale file must have been deleted before new files were written
    assert not stale_file.exists()
    assert (stale_dir / "01_手長足長像.jpg").is_file()


def test_cli_travel_enrich_photos_env_concurrency(
    tmp_path: Path, sample_export_json: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("NOTION_DB_MANAGER_CONCURRENCY", "1")
    monkeypatch.setattr(
        "sys.argv",
        [
            "notion-db-manager",
            "travel",
            "enrich-photos",
            "--input",
            str(sample_export_json),
            "--provider",
            "google",
            "--google-api-key",
            "AIzaSyFakeKey123",
        ],
    )

    search_response = MagicMock()
    search_response.status_code = 200
    search_response.json.return_value = {
        "places": [
            {
                "id": "place_1",
                "displayName": {"text": "手長足長像"},
                "photos": [{"name": "places/p1/photos/ph1", "widthPx": 1200, "heightPx": 800}],
            }
        ]
    }

    media_response = MagicMock()
    media_response.status_code = 200
    media_response.content = b"fake-image-bytes"
    media_response.headers = {"Content-Type": "image/jpeg"}
    media_response.url = "https://places.googleapis.com/v1/places/p1/photos/ph1/media"

    with patch.object(httpx.AsyncClient, "post", new=AsyncMock(return_value=search_response)), patch.object(
        httpx.AsyncClient, "get", new=AsyncMock(return_value=media_response)
    ):
        main()

    manifest_file = tmp_path / "output" / "images" / "行程安排" / "manifest.json"
    assert manifest_file.is_file()


def test_cli_travel_enrich_photos_concurrency_cli_override(
    tmp_path: Path, sample_export_json: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.chdir(tmp_path)
    # Even if env is 8, CLI flag --concurrency 1 must take precedence
    monkeypatch.setenv("NOTION_DB_MANAGER_CONCURRENCY", "8")
    monkeypatch.setattr(
        "sys.argv",
        [
            "notion-db-manager",
            "travel",
            "enrich-photos",
            "--input",
            str(sample_export_json),
            "--provider",
            "google",
            "--google-api-key",
            "AIzaSyFakeKey123",
            "--concurrency",
            "1",
        ],
    )

    search_response = MagicMock()
    search_response.status_code = 200
    search_response.json.return_value = {
        "places": [
            {
                "id": "place_1",
                "displayName": {"text": "手長足長像"},
                "photos": [{"name": "places/p1/photos/ph1", "widthPx": 1200, "heightPx": 800}],
            }
        ]
    }

    media_response = MagicMock()
    media_response.status_code = 200
    media_response.content = b"fake-image-bytes"
    media_response.headers = {"Content-Type": "image/jpeg"}
    media_response.url = "https://places.googleapis.com/v1/places/p1/photos/ph1/media"

    with patch.object(httpx.AsyncClient, "post", new=AsyncMock(return_value=search_response)), patch.object(
        httpx.AsyncClient, "get", new=AsyncMock(return_value=media_response)
    ):
        main()

    manifest_file = tmp_path / "output" / "images" / "行程安排" / "manifest.json"
    assert manifest_file.is_file()


def test_cli_travel_push_photos(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(tmp_path)

    # Setup staged photo and manifest
    img_dir = tmp_path / "output" / "images" / "行程安排"
    img_dir.mkdir(parents=True, exist_ok=True)
    photo_path = img_dir / "01_手長足長像.jpg"
    photo_path.write_bytes(b"test_image_binary")

    manifest_data = {
        "database_name": "行程安排",
        "provider": "google",
        "total_items": 1,
        "processed_count": 1,
        "skipped_count": 0,
        "success_count": 1,
        "failed_count": 0,
        "items": [
            {
                "index": 1,
                "page_id": "page_test_1",
                "name": "手長足長像",
                "status": "success",
                "categories": ["景點"],
                "local_path": str(photo_path),
                "source_url": "https://example.com/img.jpg",
                "error_message": None,
            }
        ],
    }
    (img_dir / "manifest.json").write_text(json.dumps(manifest_data, ensure_ascii=False), encoding="utf-8")

    monkeypatch.setattr(
        "sys.argv",
        [
            "notion-db-manager",
            "travel",
            "push-photos",
            "--database-name",
            "行程安排",
            "--token",
            "secret_test_token",
            "-c",
            "2",
        ],
    )

    with patch("notion_db_manager.infrastructure.notion.gateway.NotionGatewayImpl.upload_file", return_value="fu_12345") as mock_upload, \
         patch("notion_db_manager.infrastructure.notion.gateway.NotionGatewayImpl.update_page_properties") as mock_update:
        main()

        mock_upload.assert_called_once_with(
            filename="01_手長足長像.jpg",
            file_bytes=b"test_image_binary",
            mime_type="image/jpeg",
        )
        assert mock_update.call_count == 1
        call_args = mock_update.call_args
        assert call_args[0][0] == "page_test_1"
        assert call_args[0][1]["照片"]["files"][0]["file_upload"]["id"] == "fu_12345"

