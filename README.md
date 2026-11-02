# ln-manager-plugins

Default Plugin Repository for LN Manager

## Add Repo

```
https://raw.githubusercontent.com/reubensinha/ln-manager-plugins/main/index.json
```

## Plugins

| Plugin | Version | Description |
| --- | --- | --- |
| [AutomatedPipeline](AutomatedPipe/) | 0.1.0 | Automated pipeline for RSS feed processing and download automation |
| [MCPServer](MCPServer/) | 0.1.0 | Exposes the library over the Model Context Protocol (read-only) |
| [RanobeDB](RanobeDB/) | 0.1.1 | RanobeDB metadata source plugin |
| [Reviews](Reviews/) | 0.1.0 | Shows community reviews for a series, sourced from AniList |
| [Torznab](Torznab/) | 0.1.0 | Torznab indexer plugin |
| [qBittorrent](qBittorrent/) | 0.1.0 | qBittorrent download client plugin |

## File Structure

```
Plugin Folder
|
L manifest.json     # 2nd level manifest for index.json. Lists every published version
                    # of this plugin and the .lna in the Release it shipped in.
L ReadMe.md
L src
    L manifest.yaml
    L backend
        L ...
    L frontend (optional)
        L ...
```

## Publishing

Each plugin is versioned and released on its own. A release is a tag naming the plugin
and its version, so there is no repository-wide version to keep in step with the others:

1. Bump `version` in `<Plugin>/src/manifest.yaml`.
2. Commit and push.
3. Tag that plugin at that version:

   ```bash
   git tag Torznab-v0.2.0 && git push origin Torznab-v0.2.0
   ```

`.github/workflows/publish.yml` packages only that plugin, attaches its `.lna` to a
release of the same name, then records the version in `<Plugin>/manifest.json` and
rebuilds `index.json`. No other plugin's manifest is touched. The workflow refuses to
publish if the tag's version disagrees with the manifest's, so a forgotten version bump
fails the release instead of shipping a mislabelled one.

Tagging several plugins at once is fine - the runs are serialised so their commits do not
race. The tag may name either the folder or the plugin inside it, which matters where the
two differ (`AutomatedPipe` holds `AutomatedPipeline`).

Each version keeps the URL of the release it shipped in, so earlier versions stay
installable after newer ones appear.

In the app, open **Repositories** and hit refresh after a release. Catalogs are cached and
are not re-fetched on a schedule. `raw.githubusercontent.com` also caches for a few
minutes, so a refresh immediately after a release may still see the previous index.

## Hosting this elsewhere

Nothing the app reads is GitHub-specific: a version's `url` is simply an https URL it
fetches and checksums, and the index is any https document in the two-level shape above.
Both tools take explicit bases, so the same sources publish to any host:

```bash
python tools/build_index.py --plugin Torznab \
    --artifact-base https://files.example.com/lna \
    --manifest-base https://files.example.com/plugins
```

`--repo` with `--tag` is just a shorthand that derives the GitHub release URL.

## Trying it before publishing

Both manifest levels and the artifacts can be served from one local http server, which the
app accepts because plain `http` is allowed for localhost:

```bash
pip install pyyaml
python tools/build_lna.py --dist dist
python tools/build_index.py --plugin Torznab \
    --artifact-base http://127.0.0.1:8411/dist \
    --manifest-base http://127.0.0.1:8411
python -m http.server 8411 --bind 127.0.0.1
```

Then add `http://127.0.0.1:8411/index.json` in the app. Revert `manifest.json` and
`index.json` before committing, so the published URLs are not left pointing at localhost.

## Working on a plugin

`src/` is the `.lna` layout itself: `manifest.yaml` at its root, `backend/` beside it and
`frontend/` if the plugin contributes UI. To run a plugin from the app's source tree
instead, copy `src/manifest.yaml` and `src/backend/` into
`ln-manager/backend/plugins/<Name>/`, and `src/frontend/` into
`ln-manager/frontend/src/plugins/<Name>/`.

`ReadMe.md` sits beside `src/` and documents the plugin for this repository - it is not
packaged into the artifact.

### Manifest requirements

`uid`, `name`, `version`, `author`, `description` and `entry_point` are all required, and
`build_lna.py` refuses to package without them.

`uid` is a UUID generated once per plugin and never changed. It is how the app recognises
the same plugin across repositories and reinstalls, so a missing one makes the plugin
invisible and a recycled one collides it with another:

```bash
python -c "import uuid; print(uuid.uuid4())"
```

`entry_point` is `module:Class` with a colon - the loader splits on it.
