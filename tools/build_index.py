#!/usr/bin/env python3
"""Record a published plugin version in its `manifest.json`, and rebuild `index.json`.

The repository publishes two levels. `index.json` names each plugin and delegates to that
plugin's own `manifest.json`; the per-plugin manifest carries the version list, the URL of
each `.lna` and its checksum. The app fetches the index, then one manifest per plugin.

Plugins are versioned and released independently, so this only ever writes the manifest of
the plugin named by `--plugin`. Every other manifest is left exactly as it is, which is
what keeps one plugin's release from disturbing another's version history. `index.json` is
then rebuilt from whatever manifests are on disk.

Nothing about the app requires GitHub: a version's `url` is just an https URL it will
fetch and checksum. `--artifact-base` sets that URL directly for any host; `--repo` with
`--tag` is a shorthand that builds a GitHub release URL.

    # publish one plugin, artifacts attached to its own release
    python tools/build_index.py --plugin Torznab --dist dist \
        --repo owner/name --tag Torznab-v0.2.0

    # rebuild index.json only, touching no manifest
    python tools/build_index.py --repo owner/name
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
import uuid
import zipfile
from pathlib import Path
from typing import Any

import yaml

RAW_BASE = "https://raw.githubusercontent.com"


def sha256_of(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def manifest_in(lna: Path) -> dict[str, Any]:
    """Read manifest.yaml out of the archive, which is the authority on what it is."""
    with zipfile.ZipFile(lna) as archive:
        try:
            raw = archive.read("manifest.yaml")
        except KeyError:
            raise SystemExit(f"{lna.name}: no manifest.yaml at the archive root")
    manifest = yaml.safe_load(raw)
    if not isinstance(manifest, dict):
        raise SystemExit(f"{lna.name}: manifest.yaml is not a mapping")
    try:
        manifest["uid"] = str(uuid.UUID(str(manifest["uid"])))
    except (KeyError, ValueError):
        raise SystemExit(f"{lna.name}: uid {manifest.get('uid')!r} is not a UUID")
    return manifest


def load_json(path: Path) -> dict[str, Any]:
    """Read a manifest that may not exist yet, or may still be an empty placeholder."""
    if not path.exists() or not path.read_text().strip():
        return {}
    try:
        document = json.loads(path.read_text())
    except json.JSONDecodeError as exc:
        raise SystemExit(f"{path}: not valid JSON ({exc})")
    return document if isinstance(document, dict) else {}


def write_json(path: Path, document: dict[str, Any]) -> None:
    path.write_text(json.dumps(document, indent=2) + "\n")


def find_folder(root: Path, wanted: str) -> Path:
    """Locate a plugin by folder name or by the name its manifest declares.

    Both are accepted because the two are allowed to differ, and a release tag naming the
    plugin still has to find its folder.
    """
    for manifest_path in sorted(root.glob("*/src/manifest.yaml")):
        folder = manifest_path.parent.parent
        declared = str((yaml.safe_load(manifest_path.read_text()) or {}).get("name") or "")
        if wanted in {folder.name, declared}:
            return folder
    raise SystemExit(f"no plugin folder or manifest name matching {wanted!r}")


def publish(folder: Path, dist: Path, artifact_base: str) -> None:
    """Add the built artifact to `folder`'s manifest as its newest version."""
    source = yaml.safe_load((folder / "src" / "manifest.yaml").read_text())
    expected = dist / f"{source['name']}-{source['version']}.lna"
    if not expected.exists():
        raise SystemExit(
            f"{expected} not found - build it first with "
            f"tools/build_lna.py --plugin {folder.name} --dist {dist}"
        )

    packaged = manifest_in(expected)
    offer: dict[str, Any] = {
        "version": str(packaged["version"]),
        "url": f"{artifact_base.rstrip('/')}/{expected.name}",
        "sha256": sha256_of(expected),
    }
    for field in ("min_app_version", "changelog"):
        if packaged.get(field):
            offer[field] = str(packaged[field])

    manifest = load_json(folder / "manifest.json")
    versions: list[dict[str, Any]] = list(manifest.get("versions") or [])
    # Replaced rather than appended, so re-publishing a version updates its checksum and
    # URL instead of listing the same version twice with different bytes - which the app
    # would report to the user as a conflict between repositories.
    versions = [v for v in versions if v.get("version") != offer["version"]]
    versions.insert(0, offer)

    write_json(
        folder / "manifest.json",
        {
            "uid": packaged["uid"],
            "name": packaged["name"],
            "author": packaged.get("author"),
            "description": packaged.get("description"),
            "versions": versions,
        },
    )
    print(f"{folder.name}: published {offer['version']}  {offer['sha256'][:12]}…")
    print(f"  {offer['url']}")


def rebuild_index(root: Path, repo_name: str, manifest_base: str) -> int:
    """Rewrite index.json from the manifests on disk."""
    plugins: list[dict[str, Any]] = []
    for manifest_path in sorted(root.glob("*/src/manifest.yaml")):
        folder = manifest_path.parent.parent
        manifest = load_json(folder / "manifest.json")
        if not manifest.get("versions"):
            print(f"{folder.name}: nothing published yet - left out of the index")
            continue
        source = yaml.safe_load(manifest_path.read_text())
        plugins.append(
            {
                "uid": manifest.get("uid") or str(uuid.UUID(str(source["uid"]))),
                "name": manifest.get("name") or source["name"],
                "manifest": f"{manifest_base.rstrip('/')}/{folder.name}/manifest.json",
            }
        )

    write_json(root / "index.json", {"name": repo_name, "plugins": plugins})
    return len(plugins)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path("."))
    parser.add_argument("--plugin", help="Folder or plugin name being published. "
                                         "Omit to rebuild index.json only")
    parser.add_argument("--dist", type=Path, default=Path("dist"),
                        help="Where build_lna.py wrote the artifact")
    parser.add_argument("--repo", help="GitHub owner/name, used for the default URLs")
    parser.add_argument("--tag", help="Release tag the artifact was uploaded to")
    parser.add_argument("--artifact-base",
                        help="Serve artifacts from here instead of a GitHub release")
    parser.add_argument("--manifest-base",
                        help="Serve the per-plugin manifests from here instead of raw.githubusercontent.com")
    parser.add_argument("--branch", default="main",
                        help="Branch the per-plugin manifests are served from")
    parser.add_argument("--name", default="LN-Manager Plugins",
                        help="Repository display name, shown in the app")
    args = parser.parse_args()

    manifest_base = args.manifest_base
    if not manifest_base:
        if not args.repo:
            parser.error("pass --manifest-base, or --repo to derive it")
        manifest_base = f"{RAW_BASE}/{args.repo}/{args.branch}"

    if args.plugin:
        artifact_base = args.artifact_base
        if not artifact_base:
            if not (args.repo and args.tag):
                parser.error(
                    "publishing needs --artifact-base, or --repo and --tag to derive it"
                )
            artifact_base = f"https://github.com/{args.repo}/releases/download/{args.tag}"
        publish(find_folder(args.root, args.plugin), args.dist, artifact_base)

    count = rebuild_index(args.root, args.name, manifest_base)
    print(f"\nindex.json lists {count} plugin(s)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
