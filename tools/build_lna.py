#!/usr/bin/env python3
"""Package each plugin's `src/` tree into a `.lna` archive.

A `.lna` is a zip whose root holds `manifest.yaml` beside `backend/` and an optional
`frontend/` - which is exactly the shape of a plugin's `src/` directory here, so
packaging is a straight zip of that directory's contents and needs no layout rewriting.

Archives are built deterministically: entries sorted, timestamps fixed, compression
level pinned. Rebuilding an unchanged plugin therefore produces the same bytes and the
same sha256, so a republished version cannot look to the app like a different artifact
offered under a version number it has already seen.
"""

from __future__ import annotations

import argparse
import hashlib
import sys
import uuid
import zipfile
from pathlib import Path
from typing import Any

import yaml

REQUIRED = ("uid", "name", "version", "author", "description", "entry_point")

# Build leftovers and live database state, neither of which belongs in a published
# artifact. The `.lock`/`-shm`/`-wal` entries are not hypothetical: a plugin that rate
# limits itself keeps its SQLite file inside its own package directory.
EXCLUDED_DIRS = {"__pycache__", "node_modules", ".git", ".pytest_cache", ".mypy_cache"}
EXCLUDED_SUFFIXES = {".pyc", ".pyo", ".pyd", ".lock", "-shm", "-wal"}
EXCLUDED_NAMES = {".DS_Store", "Thumbs.db"}

# A fixed timestamp for every entry. Zip stores local mtimes, so without this the
# archive's bytes would change on every checkout.
FIXED_TIMESTAMP = (1980, 1, 1, 0, 0, 0)


def is_excluded(path: Path, src: Path) -> bool:
    relative = path.relative_to(src)
    if any(part in EXCLUDED_DIRS for part in relative.parts):
        return True
    if path.name in EXCLUDED_NAMES:
        return True
    # Matched on the whole name, not just `suffix`: SQLite writes "foo.sqlite-wal",
    # whose suffix is ".sqlite-wal".
    return any(
        path.suffix == excluded or path.name.endswith(excluded)
        for excluded in EXCLUDED_SUFFIXES
    )


def read_manifest(path: Path) -> dict[str, Any]:
    manifest = yaml.safe_load(path.read_text())
    if not isinstance(manifest, dict):
        raise SystemExit(f"{path}: manifest.yaml is not a mapping")

    missing = [f for f in REQUIRED if not manifest.get(f)]
    if missing:
        raise SystemExit(f"{path}: manifest is missing {', '.join(missing)}")
    try:
        # The app normalises uids through uuid.UUID and drops anything it cannot read,
        # which would make the plugin vanish from every catalog rather than fail loudly.
        manifest["uid"] = str(uuid.UUID(str(manifest["uid"])))
    except ValueError:
        raise SystemExit(f"{path}: uid {manifest['uid']!r} is not a UUID")

    entry_point = str(manifest["entry_point"])
    if ":" not in entry_point:
        raise SystemExit(
            f"{path}: entry_point {entry_point!r} must be 'module:Class' - the loader "
            "splits on the colon"
        )
    return manifest


def build(src: Path, dest: Path) -> str:
    files = sorted(p for p in src.rglob("*") if p.is_file() and not is_excluded(p, src))
    with zipfile.ZipFile(dest, "w", zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
        for path in files:
            info = zipfile.ZipInfo(
                path.relative_to(src).as_posix(), date_time=FIXED_TIMESTAMP
            )
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o644 << 16
            archive.writestr(info, path.read_bytes())

    return hashlib.sha256(dest.read_bytes()).hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path("."),
                        help="Repository root holding the plugin folders")
    parser.add_argument("--dist", type=Path, default=Path("dist"),
                        help="Where to write the .lna files")
    parser.add_argument("--plugin", action="append",
                        help="Folder or plugin name to build; repeatable. "
                             "Default: all of them")
    args = parser.parse_args()

    manifests = sorted(args.root.glob("*/src/manifest.yaml"))
    if args.plugin:
        # Matched against the folder *and* the declared plugin name, because the two are
        # allowed to differ - a release tag naming the plugin must still find its folder.
        wanted = set(args.plugin)
        selected, matched = [], set()
        for manifest_path in manifests:
            names = {
                manifest_path.parent.parent.name,
                str((yaml.safe_load(manifest_path.read_text()) or {}).get("name") or ""),
            }
            hit = wanted & names
            if hit:
                selected.append(manifest_path)
                matched |= hit
        missing = wanted - matched
        if missing:
            raise SystemExit(f"no plugin folder or manifest name matching: {', '.join(sorted(missing))}")
        manifests = selected
    if not manifests:
        raise SystemExit(f"no */src/manifest.yaml found under {args.root}")

    args.dist.mkdir(parents=True, exist_ok=True)
    for manifest_path in manifests:
        manifest = read_manifest(manifest_path)
        src = manifest_path.parent
        dest = args.dist / f"{manifest['name']}-{manifest['version']}.lna"
        digest = build(src, dest)
        print(f"{manifest['name']:<20} {manifest['version']:<8} {digest[:12]}…  "
              f"{dest.name} ({dest.stat().st_size:,} bytes)")

    print(f"\nBuilt {len(manifests)} artifact(s) into {args.dist}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
