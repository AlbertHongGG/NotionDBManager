from __future__ import annotations

from typing import Literal

ORDER_PROPERTY = "__NDM_INDEX__"
NOTION_API_VERSION = "2022-06-28"

ExportType = Literal["full", "columns", "rows"]
ImportMode = Literal["append", "replace"]
WriteRowsMode = Literal["append", "insert", "overwrite"]
