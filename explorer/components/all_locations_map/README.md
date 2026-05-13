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

## Pop-ups / eBird richness (design)

Classic Folium builds large HTML popups in Python. The component approach keeps **the same facts and URLs**
(species pages, lifelist, hotspots, history summaries) without sending **thousands of pre-rendered HTML blobs**:

1. **Structured payload** — Per-pin JSON (stable IDs, display strings, link URLs).
2. **Client templates** — One TS/HTML/CSS template renders cards matching today’s intent.
3. **Lazy sections** — Minimal payload by default; expand tables or rare blocks on popup open if needed.

This avoids regressing the “rich tie-back” story while staying faster than `popup_html × N` on the server.
