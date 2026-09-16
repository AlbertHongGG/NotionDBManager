from __future__ import annotations

from datetime import datetime
from typing import Callable, Protocol


class ExportNamingPolicy(Protocol):
    """Protocol for generating export file names."""

    def generate(self, action: str, ext: str = "json") -> str:
        """Generate a filename for the given action and file extension."""
        ...


class TimestampedNamingPolicy:
    """Generates filenames based on current timestamp and action name:

    Format: yyyymmdd_hhmmss_<action>.<ext>
    """

    def __init__(self, clock: Callable[[], datetime] | None = None) -> None:
        self.clock = clock or datetime.now

    def generate(self, action: str, ext: str = "json") -> str:
        timestamp_str = self.clock().strftime("%Y%m%d_%H%M%S")
        clean_ext = ext.lstrip(".")
        return f"{timestamp_str}_{action}.{clean_ext}"
