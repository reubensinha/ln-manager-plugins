# Reviews plugin

Adds a **Reviews** section to the bottom of the Series page, showing community reviews
from [AniList](https://anilist.co). Read-only, no API key required.

## Settings

Settings → Plugins → gear icon:

| Setting | Default | Purpose |
| --- | --- | --- |
| Review source | `anilist` | Where reviews come from. AniList is the only source today. |
| Reviews per series | 5 | How many reviews to fetch and show. |
| Cache lifetime (hours) | 24 | How long fetched reviews are reused before refetching. |

## How matching works

Light novels are `MANGA` entries with format `NOVEL` on AniList, and there is no shared
id with RanobeDB, so the plugin searches by every title the library holds (title, romaji,
original title, aliases) and scores the candidates. Ties break towards the earliest and
most popular entry, because spin-offs are newer and less popular than the series they
branch from — without that, "Mushoku Tensei" resolves to a 2023 side story instead of the
2014 main entry.

The resolved match is cached permanently; reviews are cached for the configured lifetime.
If the match is wrong, use **Wrong series?** in the section header to pick from the
candidate list — that pins the choice and clears the cached reviews.

## Endpoints

| Endpoint | Purpose |
| --- | --- |
| `GET /api/plugins/Reviews/series/{series_id}/reviews` | Match + reviews for a series |
| `GET /api/plugins/Reviews/series/{series_id}/candidates` | Alternative AniList entries |
| `PUT /api/plugins/Reviews/series/{series_id}/match` | Pin an entry (`{"external_id": 85737}`) |

## Notes and limits

- **AniList allows 30 requests/minute** unauthenticated, which is why everything is
  cached on disk (under `config/plugin-data/Reviews/`) rather than fetched per page view.
- **Review coverage is thin.** Popular series have one or two reviews; niche light novels
  usually have none. "No one has reviewed this series yet" is the normal case.
- Only review summaries are sent to the browser. Full review bodies (~11KB of AniList
  markdown each) are deliberately not fetched for display.
- An AI-generated summary of the reviews is planned but not implemented.
