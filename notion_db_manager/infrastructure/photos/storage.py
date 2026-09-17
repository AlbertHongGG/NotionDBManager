from __future__ import annotations

import json
import re
from pathlib import Path

from notion_db_manager.application.interfaces.photo_provider import PhotoStorage
from notion_db_manager.core.exceptions import StorageError
from notion_db_manager.domain.travel import EnrichItemResult, PlaceItem, PlacePhoto, TravelPhotoEnrichSummary

from notion_db_manager.infrastructure.storage.path_resolver import PathResolver


def sanitize_filename(name: str) -> str:
    """Removes or replaces characters not permitted in Windows/Linux file systems."""
    cleaned = re.sub(r'[\\/*?:"<>|]', "_", name).strip()
    return cleaned or "unnamed"


class LocalPhotoStorage(PhotoStorage):
    """Persists downloaded place photos and manifest records to the local filesystem."""

    def __init__(self, path_resolver: PathResolver | None = None) -> None:
        self.path_resolver = path_resolver or PathResolver()

    def get_images_dir(self, database_name: str) -> Path:
        clean_db = sanitize_filename(database_name)
        target_dir = self.path_resolver.get_output_dir() / "images" / clean_db
        target_dir.mkdir(parents=True, exist_ok=True)
        return target_dir

    def prepare_directory(self, database_name: str, clean: bool = True) -> Path:
        """Prepares the database images directory, purging stale contents if clean=True."""
        try:
            import shutil

            clean_db = sanitize_filename(database_name)
            target_dir = self.path_resolver.get_output_dir() / "images" / clean_db
            if clean and target_dir.exists():
                for item in target_dir.iterdir():
                    if item.is_file():
                        item.unlink()
                    elif item.is_dir():
                        shutil.rmtree(item)
            target_dir.mkdir(parents=True, exist_ok=True)
            return target_dir
        except Exception as exc:
            raise StorageError(f"準備或清理圖片目錄失敗 [{database_name}]: {exc}") from exc

    def save_photo(self, database_name: str, place: PlaceItem, photo: PlacePhoto) -> Path:
        try:
            target_dir = self.get_images_dir(database_name)
            clean_name = sanitize_filename(place.name)
            ext = photo.extension.lstrip(".") or "jpg"
            filename = f"{place.index:02d}_{clean_name}.{ext}"
            file_path = target_dir / filename

            file_path.write_bytes(photo.data)
            return file_path
        except Exception as exc:
            raise StorageError(f"寫入相片檔案失敗 [{place.name}]: {exc}") from exc

    def save_manifest(self, database_name: str, summary: TravelPhotoEnrichSummary) -> Path:
        try:
            target_dir = self.get_images_dir(database_name)
            manifest_path = target_dir / "manifest.json"
            content = json.dumps(summary.to_dict(), ensure_ascii=False, indent=2)
            manifest_path.write_text(content, encoding="utf-8")
            return manifest_path
        except Exception as exc:
            raise StorageError(f"寫入 manifest.json 失敗: {exc}") from exc

    def read_manifest(self, database_name: str, custom_path: Path | None = None) -> TravelPhotoEnrichSummary:
        try:
            if custom_path:
                manifest_path = custom_path
            else:
                target_dir = self.get_images_dir(database_name)
                manifest_path = target_dir / "manifest.json"

            if not manifest_path.is_file():
                raise StorageError(
                    f"找不到 manifest.json 紀錄檔案: {manifest_path}。請確認是否已先執行 travel enrich-photos。"
                )

            content = manifest_path.read_text(encoding="utf-8")
            data = json.loads(content)

            items = [
                EnrichItemResult(
                    index=it["index"],
                    page_id=it["page_id"],
                    name=it["name"],
                    status=it["status"],
                    categories=it.get("categories", []),
                    local_path=it.get("local_path"),
                    source_url=it.get("source_url"),
                    error_message=it.get("error_message"),
                )
                for it in data.get("items", [])
            ]

            return TravelPhotoEnrichSummary(
                database_name=data.get("database_name", database_name),
                provider=data.get("provider", "unknown"),
                total_items=data.get("total_items", len(items)),
                processed_count=data.get("processed_count", 0),
                skipped_count=data.get("skipped_count", 0),
                success_count=data.get("success_count", 0),
                failed_count=data.get("failed_count", 0),
                items=items,
            )
        except StorageError:
            raise
        except Exception as exc:
            raise StorageError(f"讀取或解析 manifest.json 失敗: {exc}") from exc

    def load_photo_bytes(self, database_name: str, item: EnrichItemResult) -> bytes:
        if not item.local_path:
            raise StorageError(f"項目 [{item.name}] 沒有記錄 local_path。")
        path = Path(item.local_path)
        if not path.is_file():
            # If relative, check against images dir
            images_dir = self.get_images_dir(database_name)
            alt_path = images_dir / path.name
            if alt_path.is_file():
                path = alt_path
            else:
                raise StorageError(f"本機相片檔案不存在: {item.local_path}")
        try:
            return path.read_bytes()
        except Exception as exc:
            raise StorageError(f"讀取本機相片二進位失敗 [{path}]: {exc}") from exc
