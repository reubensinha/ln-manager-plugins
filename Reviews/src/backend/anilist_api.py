"""Minimal AniList GraphQL client for fetching light novel reviews.

AniList's public API needs no key but allows only 30 requests/minute, so callers are
expected to cache aggressively (see cache.py).
"""

import asyncio
import logging
from typing import Any

import httpx

API_URL = "https://graphql.anilist.co"
REQUEST_TIMEOUT = 15.0

logger = logging.getLogger(__name__)

# Light novels live in AniList as MANGA with format NOVEL.
_SEARCH_QUERY = """
query ($search: String, $perPage: Int) {
  Page(perPage: $perPage) {
    media(search: $search, type: MANGA, format: NOVEL, sort: SEARCH_MATCH) {
      id
      title { romaji english native }
      synonyms
      startDate { year }
      averageScore
      popularity
      siteUrl
      coverImage { medium }
    }
  }
}
"""

_REVIEWS_QUERY = """
query ($id: Int, $perPage: Int) {
  Media(id: $id, type: MANGA) {
    id
    title { romaji english native }
    averageScore
    siteUrl
    reviews(perPage: $perPage, sort: RATING_DESC) {
      nodes {
        id
        summary
        score
        rating
        ratingAmount
        createdAt
        siteUrl
        user { name avatar { medium } }
      }
    }
  }
}
"""


class AniListError(RuntimeError):
    """Raised when AniList cannot be reached or returns an error."""


class AniListAPI:
    def __init__(self, timeout: float = REQUEST_TIMEOUT):
        self._timeout = timeout
        # AniList allows 30 requests/minute; one in flight at a time is plenty here and
        # keeps a burst of series pages from tripping the limit.
        self._lock = asyncio.Lock()

    async def _post(self, query: str, variables: dict[str, Any]) -> dict[str, Any]:
        async with self._lock:
            try:
                async with httpx.AsyncClient(timeout=self._timeout) as client:
                    response = await client.post(
                        API_URL, json={"query": query, "variables": variables}
                    )
            except httpx.HTTPError as e:
                raise AniListError(f"Could not reach AniList: {e}") from e

        if response.status_code == 429:
            retry_after = response.headers.get("retry-after", "60")
            raise AniListError(
                f"AniList rate limit reached; try again in {retry_after}s"
            )
        if response.status_code >= 400:
            raise AniListError(f"AniList returned HTTP {response.status_code}")

        payload = response.json()
        if payload.get("errors"):
            message = payload["errors"][0].get("message", "unknown error")
            raise AniListError(f"AniList error: {message}")
        return payload.get("data") or {}

    async def search_novels(self, title: str, limit: int = 10) -> list[dict[str, Any]]:
        """Candidate light novels for a title, best search match first."""
        data = await self._post(_SEARCH_QUERY, {"search": title, "perPage": limit})
        page = data.get("Page") or {}
        return page.get("media") or []

    async def get_reviews(self, media_id: int, limit: int = 5) -> dict[str, Any] | None:
        """Media details plus its highest-rated reviews. None if the id is unknown."""
        data = await self._post(_REVIEWS_QUERY, {"id": media_id, "perPage": limit})
        return data.get("Media")
