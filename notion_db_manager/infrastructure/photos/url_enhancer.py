from __future__ import annotations

import re


class GooglePhotoUrlEnhancer:
    """Validates and scales Google Maps photo URLs to high resolution."""

    # Disallowed URL path segments (Google account user avatars & default icons)
    AVATAR_PATTERNS = ("/a/", "/a-/", "/ogw/")

    # Known place photo path segments
    PLACE_PHOTO_PATTERNS = ("/gps-cs-s/", "/p/", "/place-photos/")

    @classmethod
    def is_valid_place_photo(cls, url: str | None) -> bool:
        """Determines if the given URL is a legitimate place photo and not a user avatar."""
        if not url or not isinstance(url, str):
            return False

        if (
            "googleusercontent.com" not in url
            and "ggpht.com" not in url
            and "googleapis.com" not in url
        ):
            return False

        # Exclude user avatars and account profile pictures
        for avatar_pattern in cls.AVATAR_PATTERNS:
            if avatar_pattern in url:
                return False

        # Accept known place photo paths or general google photo formats
        return any(pattern in url for pattern in cls.PLACE_PHOTO_PATTERNS) or (
            "=w" in url or "=s" in url or "streetview" in url
        )

    @classmethod
    def enhance_resolution(cls, url: str, width: int = 1600, height: int = 1200) -> str:
        """Scales Google thumbnail URLs (e.g. w408-h306) to high-definition (e.g. w1600-h1200)."""
        if not url:
            return url

        target_suffix = f"=w{width}-h{height}-k-no"

        # Match =w408-h306-k-no or =w\d+
        if "=w" in url:
            return re.sub(r"=w\d+.*", target_suffix, url)

        # Match =s100 or =s\d+
        if "=s" in url:
            return re.sub(r"=s\d+.*", f"=s{width}", url)

        # If no size parameter is present, append the target high-res suffix
        if "=" in url:
            base, _ = url.rsplit("=", 1)
            return f"{base}{target_suffix}"

        return f"{url}{target_suffix}"
