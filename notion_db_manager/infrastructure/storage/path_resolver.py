from __future__ import annotations

from pathlib import Path


class PathResolver:
    """Encapsulates path resolution rules, defaulting relative paths to the output/ directory."""

    def __init__(self, output_dir_name: str = "output", base_dir: Path | None = None) -> None:
        self.base_dir = base_dir or Path.cwd()
        self.output_dir_name = output_dir_name

    def get_output_dir(self) -> Path:
        return self.base_dir / self.output_dir_name

    def resolve_output_path(self, raw_path: str) -> Path:
        path = Path(raw_path).expanduser()
        if path.is_absolute():
            resolved = path
        elif self._is_output_relative(path):
            resolved = self.base_dir / path
        else:
            resolved = self.get_output_dir() / path

        resolved.parent.mkdir(parents=True, exist_ok=True)
        return resolved

    def resolve_input_path(self, raw_path: str) -> Path:
        path = Path(raw_path).expanduser()
        if path.is_absolute():
            return path
        if self._is_output_relative(path):
            return self.base_dir / path

        output_candidate = self.get_output_dir() / path
        if output_candidate.is_file():
            return output_candidate
        return self.base_dir / path

    def _is_output_relative(self, path: Path) -> bool:
        return bool(path.parts) and path.parts[0] == self.output_dir_name
