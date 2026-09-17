from __future__ import annotations

import pytest

from notion_db_manager.infrastructure.photos.url_enhancer import GooglePhotoUrlEnhancer


def test_is_valid_place_photo() -> None:
    enhancer = GooglePhotoUrlEnhancer

    # Valid place photos
    assert enhancer.is_valid_place_photo(
        "https://lh3.googleusercontent.com/gps-cs-s/AHRPTWlqeWvlznTY=w408-h306-k-no"
    ) is True
    assert enhancer.is_valid_place_photo(
        "https://lh5.googleusercontent.com/p/AF1QipM5zT4k8v6b_1=w900-h600-k-no"
    ) is True
    assert enhancer.is_valid_place_photo(
        "https://lh3.googleusercontent.com/place-photos/AG9NLjBBt_rn=s4800-w1600"
    ) is True
    assert enhancer.is_valid_place_photo(
        "https://lh3.googleusercontent.com/grass-cs/ACvplmM0suE8GfA3=w426-h240-k-no"
    ) is True

    # User review and profile avatars (Must be rejected!)
    assert enhancer.is_valid_place_photo(
        "https://lh3.googleusercontent.com/a/ACg8ocKPdMWjBguyfLow6w-V1XT8bVPpHsAZeRMk8tJBoONsdqhhug=s100-p-k-no-mo"
    ) is False
    assert enhancer.is_valid_place_photo(
        "https://lh3.googleusercontent.com/a-/ALV-UjUlsbopIw1gCQ8Y4Uf8IQFKOXDJM8gkF96zzJq73D-caWGoZVXhwA=s100-p-k-no-mo"
    ) is False
    assert enhancer.is_valid_place_photo(
        "https://lh3.googleusercontent.com/ogw/default-user"
    ) is False

    # Invalid URLs
    assert enhancer.is_valid_place_photo(None) is False
    assert enhancer.is_valid_place_photo("") is False
    assert enhancer.is_valid_place_photo("https://example.com/photo.jpg") is False


def test_enhance_resolution() -> None:
    enhancer = GooglePhotoUrlEnhancer

    # Thumbnail w408-h306 to high-res w1600-h1200
    low_res = "https://lh3.googleusercontent.com/gps-cs-s/ABC123xyz=w408-h306-k-no"
    high_res = enhancer.enhance_resolution(low_res, width=1600, height=1200)
    assert high_res == "https://lh3.googleusercontent.com/gps-cs-s/ABC123xyz=w1600-h1200-k-no"

    # =s100 scale parameter
    low_res_s = "https://lh3.googleusercontent.com/p/XYZ789=s100"
    high_res_s = enhancer.enhance_resolution(low_res_s, width=1600)
    assert high_res_s == "https://lh3.googleusercontent.com/p/XYZ789=s1600"
