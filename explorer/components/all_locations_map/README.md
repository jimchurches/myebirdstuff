# All locations map — Streamlit component

Leaflet map embedded via `streamlit.components.v1.declare_component`. The committed **`frontend/build`** output is what Streamlit loads at runtime (Node is not required at app runtime).

**Architecture and maintainer docs:** [docs/development.md](../../../docs/development.md) (Map architecture, marker schemes, perf guardrails). **#222 close-out / baselines (historical):** [docs/explorer/issue-222-plain-summary.md](../../../docs/explorer/issue-222-plain-summary.md).

Rebuild after TS/React changes (also validated on every PR by **Python CI** → *All locations map (frontend CI)*: `npm test`, `tsc --noEmit`, production `npm audit`, `npm run build`):

```bash
# From repo root (recommended — checks for junk under build/ afterward)
python3 scripts/build_all_locations_map_frontend.py
```

Or manually (full CI parity):

```bash
cd explorer/components/all_locations_map/frontend
npm ci
npm run test:ci
npm run typecheck
npm run audit:prod
npm run build
```

Quick rebuild only (skips test/audit):

```bash
cd explorer/components/all_locations_map/frontend
npm ci && npm run build
```

### What to commit after a build

| Path | Commit? |
|------|--------|
| `frontend/src/` | Yes — source you edited |
| `frontend/package.json`, `package-lock.json` | Yes — when dependencies change |
| `frontend/build/index.html`, `asset-manifest.json` | Yes |
| `frontend/build/static/css/main.<hash>.css` | Yes — **one** hashed file |
| `frontend/build/static/js/main.<hash>.js` and `.LICENSE.txt` | Yes — **one** bundle + license |
| `frontend/node_modules/` | **No** (gitignored) |
| `frontend/build/**/*.map` | **No** (gitignored source maps) |
| Folders like `static/css 4/` or `static/js 5/` | **No** — not from npm; delete or run the script with `--prune-junk` |
| Extra `main.<oldhash>.js` left after a rebuild | **No** — remove; git should show the old hash **deleted** and the new one **added** |

A normal rebuild changes the hash in the filenames above; `git status` should look like renames/updates under `build/static/`, not a pile of parallel `main.*.js` files. If unsure, run `python3 scripts/build_all_locations_map_frontend.py --check-only` before committing.

Dev server (optional):

```bash
npm start
```

## Production data flow

1. **`app_prep_map_ui.py`** — For the active **Map view**, build or restore a cached payload (`*_LEAFLET_PAYLOAD_CACHE_KEY` session LRUs, keyed by `leaflet_payload_cache_key()` + mode-specific `revision_extra`).
2. **GeoJSON builders** (`all_locations_geojson.py`, `species_locations_geojson.py`, …) — Features carry structured popup properties (`popup_v1`, `species_popup_v1`, …), not pre-rendered HTML.
3. **`render_all_locations_map_component`** — Passes `geojson`, `revision`, banner/legend HTML, viewport extras, and pin/cluster styles into the iframe.
4. **`AllLocationsMap.tsx`** — Renders markers, clustering, popups, and fixed banner/legend overlays inside the iframe document.

Warm reruns with unchanged inputs skip GeoJSON and overlay HTML rebuilds (`payload_cache_hit` in `EXPLORER_PERF` extras).

## Marker clustering

Clustering uses **Leaflet.markercluster** with defaults aligned to `explorer/app/streamlit/defaults.py`
(max radius 40px, clustering disables from zoom 9, `removeOutsideVisibleBounds` false).

The sidebar **Group nearby pins** toggle is passed as `cluster_options.enabled`; cluster options are mixed into the GeoJSON **revision** hash so toggling clustering bumps revision and reloads the overlay.

**Pins:** `circle_marker_style` comes from Python via `all_locations_marker_style.circle_marker_style_for_all_locations_map` (sidebar marker scheme index).

## Banner + legend inside the iframe

Banner and legend use `map_overlay_theme_stylesheet()` plus HTML from `build_*_banner_html` / `build_legend_html` in `map_renderer.py`, passed as component args. React injects merged CSS into the iframe `document` and renders overlay HTML as siblings of the Leaflet pane so `position:fixed` anchors to the map viewport (top-right banner, bottom-left legend). Popup width is finalized in TS only (`AllLocationsMap.tsx` + `AllLocationsMapPopup.css`).

## Popup anchor vs iframe size

If popups open offset from CircleMarkers, the usual cause is Leaflet measuring the map **before** the Streamlit iframe gets its final height. The component attaches a `ResizeObserver` on the outer wrapper and calls `invalidateSize` (plus delayed bumps) after updates.

## Popups / structured payloads

The component sends **structured facts and URLs** per pin; the client renders one template per mode (`AllLocationsMap.tsx` + `AllLocationsMapPopup.css`, kept in sync with `map_popup_theme_stylesheet()` in `map_renderer.py`).

- **Payload:** `feature.properties.popup_v1` with `v: 1` (and mode-specific variants for species / lifer / family).
- **All locations:** With `records_by_location`, `visited` holds `{ label: "Visited:", entries: [{label,href}] }`; lifelist heading link is rendered in TS. Minimal tests may use `summary_lines` + `links` only.
- **Optional env:** `EXPLORER_EXPERIMENTAL_VISITS_INLINE_CAP` truncates `visited.entries` for very large exports (lifelist still covers full history).

Export HTML uses the same class names via `popup_v1_export_html.py` (standalone file embeds `AllLocationsMapPopup.css`).

## Client performance (instrumentation scope)

For regressions, rely on **Python** `EXPLORER_PERF` (including `map.*.leaflet.payload` / `component_embed`) and Playwright **`e2e.first_paint`** — not in-iframe timings. See [`docs/explorer/issue-222-section-8-prior-art.md`](../../../docs/explorer/issue-222-section-8-prior-art.md) §8.2.

**Frontend unit tests:** `cd frontend && npm run test:ci` (viewport parser and related). CI also runs `npm run typecheck` and `npm run audit:prod`.
