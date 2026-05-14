# All locations map — Streamlit component (spike #221)

Leaflet map embedded via `streamlit.components.v1`. The committed **`frontend/build`** output is what Streamlit loads at runtime.

Rebuild after TS/React changes (also validated on every PR by **Python CI** → *All locations map (npm build)*):

```bash
cd explorer/components/all_locations_map/frontend
npm ci
npm run build
```

Dev server (optional):

```bash
npm start
```

## Marker clustering

Clustering uses **Leaflet.markercluster** with defaults aligned to `explorer/app/streamlit/defaults.py`
(max radius 40px, clustering disables from zoom 9, `removeOutsideVisibleBounds` false to match Folium refs #166).

The sidebar **cluster all locations** toggle is passed as `cluster_options.enabled`; full cluster JSON is mixed into the GeoJSON **revision** hash so toggling clustering bumps revision and reloads the overlay.

**Pins:** `circle_marker_style` comes from Python via the same resolver as Folium **All locations**; the sidebar marker scheme index is honoured in production (#222).

## Banner + legend inside the iframe (same as Folium)

Folium injects ``map_overlay_theme_stylesheet`` plus banner/legend HTML **into the map document** so ``position:fixed`` anchors to the map viewport (top-right banner, bottom-left legend). The Streamlit component passes the same stylesheet, ``map_popup_width_fix_script``, ``build_all_locations_banner_html``, and ``build_legend_html`` as component args; React injects CSS/script into the iframe ``document`` and renders overlay HTML **siblings** of the Leaflet pane so chrome matches beta-next (#222). The Python stylesheet is **two** ``<style>`` blocks concatenated (popup + banner/legend); the component merges their inner CSS into one ``<style>`` node so the browser does not terminate the sheet at the first ``</style>`` token.

## Popup anchor vs iframe size

If popups open offset from CircleMarkers, the usual cause is Leaflet measuring the map **before** the Streamlit iframe gets its final height. The component attaches a ``ResizeObserver`` on the outer wrapper and calls ``invalidateSize`` (plus a few delayed bumps) after updates (#222).

## Pop-ups / eBird richness (design)

Classic Folium builds large HTML popups in Python. The component approach keeps **the same facts and URLs**
(species pages, lifelist, hotspots, history summaries) without sending **thousands of pre-rendered HTML blobs**:

1. **Structured payload** — Per-pin JSON (stable IDs, display strings, link URLs).
2. **Client templates** — One TS/HTML/CSS template renders cards matching today’s intent.
3. **Lazy sections** — Optional: defer **heavy** chunks (long tables, full history) until the user opens a popup, if bytes or Python time dominate — provided lazy paths avoid **full Streamlit reruns per click** where possible.

**Priorities (spike):** Like-for-like functionality first; performance second; small UX differences acceptable if they buy clear speed/design wins.

**Typical session:** Many pins on map (~7k possible), few popups opened (tens to low hundreds). Prefer embedding **compact** structured data for every pin; reserve lazy loading for sections that are large or rarely viewed — **re-measure on this architecture** (the classic Folium “lazy popup” experiment showed little gain because bottlenecks differed).

**Perf:** Session-state payload cache (see **`EXPERIMENTAL_ALL_LOCATIONS_PAYLOAD_CACHE_KEY`**) skips rebuilding GeoJSON on warm reruns when the Folium-equivalent map cache key matches. Optional **`EXPLORER_EXPERIMENTAL_VISITS_INLINE_CAP`** (env) truncates ``visited.entries``; lifelist covers full history.

**Current payload:** `feature.properties.popup_v1` with `v: 1`. With **`records_by_location`** (production experimental tab), **`visited`** holds `{ label: "Visited:", entries: [{label,href}] }` — classic All locations checklist list + lifelist heading link in TS. Without per-location rows (minimal tests), **`summary_lines`** + **`links`** compact fallback.

Popup width aims for Folium parity (`MAP_POPUP_MAX_WIDTH_PX` = 420 in `defaults.py`). Popup **styling** mirrors production: `frontend/src/AllLocationsMapPopup.css` tracks `map_popup_theme_stylesheet` in `explorer/presentation/map_renderer.py`; visit-card HTML structure tracks `assemble_location_popup_html` / `LocationPopupModel` in `map_popup_models.py`. Shrink-to-content width uses the same logic as `map_popup_width_fix_script` on `popupopen`.

This avoids regressing the “rich tie-back” story while staying faster than `popup_html × N` on the server.
