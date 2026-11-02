from datetime import date, timedelta
from typing import Any
from uuid import UUID

import anyio
from mcp.server import MCPServer
from mcp.server.mcpserver.exceptions import ToolError
from sqlalchemy.orm import selectinload
from sqlmodel import Session, select

from backend.core.database.database import engine
from backend.core.database.models import (
    Book,
    BookPublicWithReleases,
    CollectionPublicSimple,
    Release,
    ReleasePublicSimple,
    Series,
    SeriesGroupPublicWithSeries,
    SeriesPublicSimple,
    SeriesPublicWithBooks,
)
from backend.core.exceptions import ResourceNotFoundError
from backend.core.services import library_service

# metadata_source carries the source's config (API keys, URLs) — never export it.
_SERIES_EXCLUDE = {"metadata_source"}
_SERIES_LIST_EXCLUDE = {"series": {"__all__": {"metadata_source"}}}


def _dump(model_cls: Any, obj: Any, exclude: Any = None) -> dict[str, Any]:
    return model_cls.model_validate(obj, from_attributes=True).model_dump(
        mode="json", exclude=exclude
    )


def _parse_uuid(value: str, label: str) -> UUID:
    try:
        return UUID(value)
    except ValueError:
        raise ToolError(f"{label} '{value}' is not a valid UUID")


async def _run(fn: Any, *args: Any) -> Any:
    try:
        return await anyio.to_thread.run_sync(fn, *args)
    except ResourceNotFoundError as e:
        raise ToolError(str(e))


def register_tools(mcp: MCPServer) -> None:
    @mcp.tool()
    async def list_collections() -> list[dict[str, Any]]:
        """List the collections the library is organised into."""

        def work() -> list[dict[str, Any]]:
            with Session(engine) as session:
                return [
                    _dump(CollectionPublicSimple, c)
                    for c in library_service.get_all_collections(session)
                ]

        return await _run(work)

    @mcp.tool()
    async def list_library() -> list[dict[str, Any]]:
        """List every series group in the library with aggregates: volume count,
        last and next release dates, and available languages. Use the returned
        `id` with get_series_group for the individual editions."""

        def work() -> list[dict[str, Any]]:
            with Session(engine) as session:
                return [
                    item.model_dump(mode="json")
                    for item in library_service.get_all_series_groups(session)
                ]

        return await _run(work)

    @mcp.tool()
    async def get_series_group(group_id: str) -> dict[str, Any]:
        """Get a series group and the series (editions/languages) it contains."""
        gid = _parse_uuid(group_id, "group_id")

        def work() -> dict[str, Any]:
            with Session(engine) as session:
                group = library_service.get_series_group_by_id(session, gid)
                return _dump(SeriesGroupPublicWithSeries, group, _SERIES_LIST_EXCLUDE)

        return await _run(work)

    @mcp.tool()
    async def get_series(series_id: str) -> dict[str, Any]:
        """Get a single series with its full metadata and its books (volumes)."""
        sid = _parse_uuid(series_id, "series_id")

        def work() -> dict[str, Any]:
            with Session(engine) as session:
                series = library_service.get_series_by_id(session, sid)
                return _dump(SeriesPublicWithBooks, series, _SERIES_EXCLUDE)

        return await _run(work)

    @mcp.tool()
    async def get_book(book_id: str) -> dict[str, Any]:
        """Get a single book (volume) with its releases."""
        bid = _parse_uuid(book_id, "book_id")

        def work() -> dict[str, Any]:
            with Session(engine) as session:
                book = library_service.get_book_by_id(session, bid)
                return _dump(BookPublicWithReleases, book)

        return await _run(work)

    @mcp.tool()
    async def search_library(query: str) -> list[dict[str, Any]]:
        """Case-insensitive search of series already in the library by title,
        romaji, original title or alias. Returns matching series without their books."""
        needle = query.strip().lower()
        if not needle:
            raise ToolError("query must not be empty")

        def work() -> list[dict[str, Any]]:
            with Session(engine) as session:
                matches = []
                for series in library_service.get_all_series(session):
                    if series.deleted:
                        continue
                    haystack = [series.title, series.romaji, series.title_orig, *(series.aliases or [])]
                    if any(needle in (h or "").lower() for h in haystack):
                        matches.append(_dump(SeriesPublicSimple, series, _SERIES_EXCLUDE))
                return matches

        return await _run(work)

    @mcp.tool()
    async def upcoming_releases(days: int = 30) -> list[dict[str, Any]]:
        """Releases dated from today through the next `days` days (default 30),
        soonest first, with the book and series titles they belong to."""
        if days < 0:
            raise ToolError("days must be >= 0")
        today = date.today()
        end = today + timedelta(days=days)

        def work() -> list[dict[str, Any]]:
            with Session(engine) as session:
                releases = session.exec(
                    select(Release)
                    .where(
                        Release.deleted == False,  # noqa: E712
                        Release.release_date >= today,
                        Release.release_date <= end,
                    )
                    .options(selectinload(Release.book).selectinload(Book.series))
                    .order_by(Release.release_date)
                ).all()
                out = []
                for release in releases:
                    item = _dump(ReleasePublicSimple, release)
                    item["book_title"] = release.book.title if release.book else None
                    item["series_title"] = (
                        release.book.series.title if release.book and release.book.series else None
                    )
                    out.append(item)
                return out

        return await _run(work)
