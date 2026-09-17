from __future__ import annotations

from typing import Any
import httpx

from notion_db_manager.application.interfaces.photo_provider import PlacePhotoProvider
from notion_db_manager.core.exceptions import ConfigurationError, PhotoProviderError
from notion_db_manager.domain.travel.places import PlaceItem, PlacePhoto



class GooglePlacesPhotoProvider(PlacePhotoProvider):
    """Retrieves official Google Maps place cover photos via Google Places API (New) asynchronously.

    Enforces Fail-Fast: Any API error (bad key, quota limit, HTTP error) immediately
    raises PhotoProviderError rather than falling back.
    """

    SEARCH_ENDPOINT = "https://places.googleapis.com/v1/places:searchText"
    MEDIA_ENDPOINT_TEMPLATE = "https://places.googleapis.com/v1/{name}/media"
    DEFAULT_CONCURRENCY = 8


    def __init__(self, api_key: str, timeout: float = 15.0) -> None:
        if not api_key or not api_key.strip():
            raise ConfigurationError("未提供 Google Places API 金鑰。請於 .env 設定 GOOGLE_MAP_API 或透過參數提供。")
        self.api_key = api_key.strip()
        self.timeout = timeout
        self._client: httpx.AsyncClient | None = None

    def _get_client(self) -> httpx.AsyncClient:
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(timeout=self.timeout, follow_redirects=True)
        return self._client

    async def fetch_photo(self, place: PlaceItem) -> PlacePhoto | None:
        client = self._get_client()

        # Step 1: Text search for the place
        query = place.best_search_query()
        data = await self._search_place(client, query)

        places = data.get("places", [])
        if not places and place.alias and place.name != place.alias:
            # Try once with primary name if alias did not yield results
            data = await self._search_place(client, place.name)
            places = data.get("places", [])

        if not places:
            return None

        primary_place = places[0]
        photos = primary_place.get("photos", [])
        if not photos:
            return None

        # Step 2: Extract top photo metadata
        first_photo = photos[0]
        photo_name = first_photo.get("name")
        if not photo_name:
            return None

        width = first_photo.get("widthPx")
        height = first_photo.get("heightPx")
        author = None
        attributions = first_photo.get("authorAttributions", [])
        if attributions:
            author = attributions[0].get("displayName")

        # Step 3: Fetch photo media
        return await self._fetch_media(client, photo_name, width=width, height=height, author=author)

    async def _search_place(self, client: httpx.AsyncClient, text_query: str) -> dict[str, Any]:
        headers = {
            "Content-Type": "application/json",
            "X-Goog-Api-Key": self.api_key,
            "X-Goog-FieldMask": "places.displayName,places.id,places.photos",
        }
        body = {"textQuery": text_query}

        try:
            res = await client.post(self.SEARCH_ENDPOINT, json=body, headers=headers)
        except Exception as exc:
            raise PhotoProviderError(f"連線 Google Places API 失敗 [{text_query}]: {exc}") from exc

        if res.status_code != 200:
            err_detail = res.text
            try:
                err_json = res.json()
                if "error" in err_json and "message" in err_json["error"]:
                    err_detail = err_json["error"]["message"]
            except Exception:
                pass
            raise PhotoProviderError(f"Google Places API 錯誤 (HTTP {res.status_code}): {err_detail}")

        return res.json()

    async def _fetch_media(
        self,
        client: httpx.AsyncClient,
        photo_name: str,
        width: int | None = None,
        height: int | None = None,
        author: str | None = None,
    ) -> PlacePhoto:
        url = self.MEDIA_ENDPOINT_TEMPLATE.format(name=photo_name)
        params = {"maxWidthPx": 1600, "key": self.api_key}

        try:
            res = await client.get(url, params=params)
        except Exception as exc:
            raise PhotoProviderError(f"下載 Google Places 照片媒體失敗 [{photo_name}]: {exc}") from exc

        if res.status_code != 200:
            raise PhotoProviderError(f"Google Places 照片媒體請求失敗 (HTTP {res.status_code})")

        content_type = res.headers.get("Content-Type", "image/jpeg")
        extension = "png" if "png" in content_type else "jpg"

        return PlacePhoto(
            data=res.content,
            mime_type=content_type,
            extension=extension,
            source_url=str(res.url),
            width=width,
            height=height,
            author=author,
        )

    async def close(self) -> None:
        """Closes the underlying HTTP client session."""
        if self._client and not self._client.is_closed:
            await self._client.aclose()
            self._client = None

    async def __aenter__(self) -> GooglePlacesPhotoProvider:
        return self

    async def __aexit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        await self.close()

