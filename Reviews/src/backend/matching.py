"""Pick the AniList entry that corresponds to a series in the library.

Searching by title alone is not reliable: "Mushoku Tensei" returns a 2023 spin-off ahead
of the 2014 main entry, so candidates are scored against every title the library knows
and ties are broken towards the earliest, most popular entry.
"""

import re
import unicodedata
from typing import Any, Iterable

# Score thresholds used to describe a match to the user.
EXACT = 100
STARTS_WITH = 60
CONTAINS = 30


def normalise(value: str | None) -> str:
    if not value:
        return ""
    text = unicodedata.normalize("NFKD", value).casefold()
    return re.sub(r"[^a-z0-9]+", " ", text).strip()


def library_titles(series: Any) -> list[str]:
    """Every title the library holds for a series, best-known first."""
    titles = [series.title, series.romaji, series.title_orig, *(series.aliases or [])]
    seen: list[str] = []
    for title in titles:
        if title and title not in seen:
            seen.append(title)
    return seen


def _candidate_titles(candidate: dict[str, Any]) -> Iterable[str]:
    title = candidate.get("title") or {}
    yield from (title.get("romaji"), title.get("english"), title.get("native"))
    yield from candidate.get("synonyms") or []


def score_candidate(candidate: dict[str, Any], titles: list[str]) -> int:
    """How well an AniList entry matches the titles we hold for a series."""
    wanted = [normalise(t) for t in titles if normalise(t)]
    best = 0
    for raw in _candidate_titles(candidate):
        theirs = normalise(raw)
        if not theirs:
            continue
        for ours in wanted:
            if theirs == ours:
                best = max(best, EXACT)
            elif theirs.startswith(ours) or ours.startswith(theirs):
                best = max(best, STARTS_WITH)
            elif ours in theirs or theirs in ours:
                best = max(best, CONTAINS)
    return best


def pick_best(
    candidates: list[dict[str, Any]], titles: list[str]
) -> tuple[dict[str, Any] | None, int]:
    """The best-matching candidate and its score, or (None, 0) when nothing matches."""
    if not candidates:
        return None, 0

    scored = [(score_candidate(c, titles), c) for c in candidates]
    scored = [(score, c) for score, c in scored if score > 0]
    if not scored:
        return None, 0

    def sort_key(entry: tuple[int, dict[str, Any]]):
        score, candidate = entry
        year = (candidate.get("startDate") or {}).get("year") or 9999
        # Highest score first, then the original (earliest) and most popular entry —
        # spin-offs are newer and less popular than the series they branch from.
        return (-score, year, -(candidate.get("popularity") or 0))

    scored.sort(key=sort_key)
    best_score, best = scored[0]
    return best, best_score


def confidence(score: int) -> str:
    if score >= EXACT:
        return "exact"
    if score >= STARTS_WITH:
        return "likely"
    return "loose"
