from __future__ import annotations

from notion_db_manager.core.exceptions import ValidationError


def parse_row_indices(raw: str) -> list[int]:
    """Parse comma-separated row indexes and ranges (e.g. '1,3,5-7') into sorted unique ints."""
    result: set[int] = set()
    chunks = [part.strip() for part in raw.split(",") if part.strip()]
    if not chunks:
        raise ValidationError(f"無效的列索引表示式: '{raw}'")

    for chunk in chunks:
        try:
            if "-" in chunk:
                start_text, end_text = chunk.split("-", 1)
                start = int(start_text.strip())
                end = int(end_text.strip())
                if start <= 0 or end <= 0 or end < start:
                    raise ValidationError(f"無效索引區間: '{chunk}' (需 >= 1 且 起始 <= 結束)")
                result.update(range(start, end + 1))
            else:
                value = int(chunk.strip())
                if value <= 0:
                    raise ValidationError(f"列索引需從 1 開始，收到: '{chunk}'")
                result.add(value)
        except ValueError as exc:
            if isinstance(exc, ValidationError):
                raise
            raise ValidationError(f"無法解析列索引數值: '{chunk}'") from exc

    return sorted(result)
