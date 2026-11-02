from typing import Any
from uuid import UUID

import anyio
from fastapi import APIRouter, HTTPException
from sqlmodel import Session

from backend.core.database.database import engine
from backend.core.exceptions import ResourceNotFoundError
from backend.core.plugins.generic import GenericPlugin
from backend.core.services import library_service
from backend.plugins.Reviews.anilist_api import AniListAPI, AniListError
from backend.plugins.Reviews.cache import JsonCache
from backend.plugins.Reviews import matching


class ReviewsPlugin(GenericPlugin):
    """Adds community reviews from AniList to the series page."""

    name = "Reviews"
    version = "0.1.0"
    description = "Shows community reviews for a series, sourced from AniList."

    def start(self) -> None:
        self.api = AniListAPI()
        self._match_cache = JsonCache(self.data_dir / "matches", ttl_seconds=-1)
        self._reviews_cache = JsonCache(
            self.data_dir / "reviews", ttl_seconds=self._ttl_seconds()
        )
        self.logger.info("Reviews plugin started")

    def stop(self) -> None:
        self.logger.info("Reviews plugin stopped")

    def get_settings_schema(self) -> dict[str, Any]:
        return {
            "source": {
                "type": "string",
                "label": "Review source",
                "description": "Where reviews are fetched from.",
                "enum": ["anilist"],
                "default": "anilist",
            },
            "max_reviews": {
                "type": "number",
                "label": "Reviews per series",
                "default": 5,
            },
            "cache_ttl_hours": {
                "type": "number",
                "label": "Cache lifetime (hours)",
                "description": "How long fetched reviews are reused before refetching.",
                "default": 24,
            },
        }

    def on_settings_changed(self, config: dict[str, Any]) -> None:
        self._reviews_cache.ttl_seconds = self._ttl_seconds()

    def _ttl_seconds(self) -> int:
        return int(float(self.config.get("cache_ttl_hours", 24)) * 3600)

    def _max_reviews(self) -> int:
        return int(self.config.get("max_reviews", 5))

    # -- data ---------------------------------------------------------------

    def _load_series(self, series_id: UUID):
        with Session(engine) as session:
            series = library_service.get_series_by_id(session, series_id)
            return {
                "titles": matching.library_titles(series),
                "title": series.title,
            }

    async def _series_info(self, series_id: UUID) -> dict[str, Any]:
        try:
            return await anyio.to_thread.run_sync(self._load_series, series_id)
        except ResourceNotFoundError as e:
            raise HTTPException(status_code=404, detail=str(e))

    async def _candidates(self, titles: list[str]) -> list[dict[str, Any]]:
        """Search AniList for each known title until something comes back."""
        for title in titles:
            results = await self.api.search_novels(title)
            if results:
                return results
        return []

    async def _resolve_match(
        self, series_id: UUID, titles: list[str]
    ) -> dict[str, Any] | None:
        cached = self._match_cache.get(str(series_id))
        if cached is not None:
            return cached or None

        candidates = await self._candidates(titles)
        best, score = matching.pick_best(candidates, titles)
        if best is None:
            # Remember the miss too, so a niche series doesn't re-query on every visit.
            self._match_cache.set(str(series_id), {})
            return None

        match = {
            "external_id": best["id"],
            "title": (best.get("title") or {}).get("romaji"),
            "site_url": best.get("siteUrl"),
            "confidence": matching.confidence(score),
        }
        self._match_cache.set(str(series_id), match)
        return match

    # -- routes -------------------------------------------------------------

    def get_api_router(self) -> APIRouter:
        router = APIRouter()

        @router.get("/series/{series_id}/reviews")
        async def series_reviews(series_id: UUID):
            """Reviews for a series, with the AniList entry they came from."""
            info = await self._series_info(series_id)

            cached = self._reviews_cache.get(str(series_id))
            if cached is not None:
                return cached

            try:
                match = await self._resolve_match(series_id, info["titles"])
                if match is None:
                    payload = {"match": None, "reviews": []}
                else:
                    media = await self.api.get_reviews(
                        match["external_id"], self._max_reviews()
                    )
                    payload = {
                        "match": {
                            **match,
                            "average_score": (media or {}).get("averageScore"),
                        },
                        "reviews": [
                            {
                                "id": node["id"],
                                "summary": node.get("summary"),
                                "score": node.get("score"),
                                "rating": node.get("rating"),
                                "rating_amount": node.get("ratingAmount"),
                                "created_at": node.get("createdAt"),
                                "site_url": node.get("siteUrl"),
                                "user": (node.get("user") or {}).get("name"),
                                "avatar": ((node.get("user") or {}).get("avatar") or {}).get("medium"),
                            }
                            for node in ((media or {}).get("reviews") or {}).get("nodes", [])
                        ],
                    }
            except AniListError as e:
                raise HTTPException(status_code=502, detail=str(e))

            self._reviews_cache.set(str(series_id), payload)
            return payload

        @router.get("/series/{series_id}/candidates")
        async def series_candidates(series_id: UUID):
            """Alternative AniList entries, for correcting a wrong match."""
            info = await self._series_info(series_id)
            try:
                candidates = await self._candidates(info["titles"])
            except AniListError as e:
                raise HTTPException(status_code=502, detail=str(e))

            return [
                {
                    "external_id": c["id"],
                    "title": (c.get("title") or {}).get("romaji"),
                    "english_title": (c.get("title") or {}).get("english"),
                    "year": (c.get("startDate") or {}).get("year"),
                    "average_score": c.get("averageScore"),
                    "site_url": c.get("siteUrl"),
                    "cover_image": (c.get("coverImage") or {}).get("medium"),
                }
                for c in candidates
            ]

        @router.put("/series/{series_id}/match")
        async def set_series_match(series_id: UUID, body: dict[str, Any]):
            """Pin a series to a specific AniList entry and drop its cached reviews."""
            external_id = body.get("external_id")
            if not isinstance(external_id, int):
                raise HTTPException(status_code=400, detail="external_id must be an integer")

            try:
                media = await self.api.get_reviews(external_id, self._max_reviews())
            except AniListError as e:
                raise HTTPException(status_code=502, detail=str(e))
            if media is None:
                raise HTTPException(status_code=404, detail=f"No AniList entry {external_id}")

            match = {
                "external_id": external_id,
                "title": (media.get("title") or {}).get("romaji"),
                "site_url": media.get("siteUrl"),
                "confidence": "manual",
            }
            self._match_cache.set(str(series_id), match)
            self._reviews_cache.delete(str(series_id))
            return match

        return router
