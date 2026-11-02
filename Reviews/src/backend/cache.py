"""TTL'd JSON cache under the plugin's data directory.

AniList allows 30 requests/minute, so every lookup is cached. Files rather than tables
because plugins cannot own database migrations.
"""

import json
import logging
import time
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


class JsonCache:
    def __init__(self, directory: Path, ttl_seconds: int):
        self.directory = directory
        self.ttl_seconds = ttl_seconds
        self.directory.mkdir(parents=True, exist_ok=True)

    def _path(self, key: str) -> Path:
        safe = "".join(c for c in key if c.isalnum() or c in "-_")
        return self.directory / f"{safe}.json"

    def get(self, key: str, ttl_seconds: int | None = None) -> Any | None:
        path = self._path(key)
        if not path.exists():
            return None

        ttl = self.ttl_seconds if ttl_seconds is None else ttl_seconds
        try:
            payload = json.loads(path.read_text())
        except (OSError, json.JSONDecodeError):
            logger.warning(f"Discarding unreadable cache entry: {path}")
            return None

        if ttl >= 0 and time.time() - payload.get("stored_at", 0) > ttl:
            return None
        return payload.get("value")

    def set(self, key: str, value: Any) -> None:
        try:
            self._path(key).write_text(
                json.dumps({"stored_at": time.time(), "value": value})
            )
        except OSError as e:
            logger.warning(f"Could not write cache entry '{key}': {e}")

    def delete(self, key: str) -> None:
        self._path(key).unlink(missing_ok=True)
