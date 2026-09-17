from dataclasses import dataclass

@dataclass(frozen=True, slots=True)
class PlacePhoto:
    """Value Object encapsulating a downloaded place photo."""
    data: bytes
    mime_type: str
    extension: str
    source_url: str
    width: int | None = None
    height: int | None = None
    author: str | None = None
