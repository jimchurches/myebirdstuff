# All locations map — Streamlit component (spike #221)

Leaflet map embedded via `streamlit.components.v1`. The committed **`frontend/build`** output is what Streamlit loads at runtime.

Rebuild after TS/React changes:

```bash
cd explorer/components/all_locations_map/frontend
npm install
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

**Pins:** `circle_marker_style` comes from Python via `_all_locations_marker_params_from_scheme(MAP_MARKER_COLOUR_SCHEME_1)` — same CircleMarker fill/stroke/radius/weight/opacity as classic Folium **All locations** for **preset 1 (Eucalypt)** only in this spike (sidebar marker-scheme radio not applied).

## Pop-ups / eBird richness (design)

Classic Folium builds large HTML popups in Python. The component approach keeps **the same facts and URLs**
(species pages, lifelist, hotspots, history summaries) without sending **thousands of pre-rendered HTML blobs**:

1. **Structured payload** — Per-pin JSON (stable IDs, display strings, link URLs).
2. **Client templates** — One TS/HTML/CSS template renders cards matching today’s intent.
3. **Lazy sections** — Optional: defer **heavy** chunks (long tables, full history) until the user opens a popup, if bytes or Python time dominate — provided lazy paths avoid **full Streamlit reruns per click** where possible.

**Priorities (spike):** Like-for-like functionality first; performance second; small UX differences acceptable if they buy clear speed/design wins.

**Typical session:** Many pins on map (~7k possible), few popups opened (tens to low hundreds). Prefer embedding **compact** structured data for every pin; reserve lazy loading for sections that are large or rarely viewed — **re-measure on this architecture** (the classic Folium “lazy popup” experiment showed little gain because bottlenecks differed).

**Current payload:** `feature.properties.popup_v1` with `v: 1`. With **`records_by_location`** (production experimental tab), **`visited`** holds `{ label: "Visited:", entries: [{label,href}] }` — classic All locations checklist list + lifelist heading link in TS. Without per-location rows (minimal tests), **`summary_lines`** + **`links`** compact fallback.

Popup width aims for Folium parity (`MAP_POPUP_MAX_WIDTH_PX` = 420 in `defaults.py`).

This avoids regressing the “rich tie-back” story while staying faster than `popup_html × N` on the server.
