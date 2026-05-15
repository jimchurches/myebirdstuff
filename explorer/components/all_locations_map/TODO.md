# All locations Leaflet map — backlog (#222)

Living checklist for the Streamlit **custom component** path (`declare_component` + committed `frontend/build`).  
Update this file as items ship so the backlog stays visible outside chat history.

**Related:** [README.md](./README.md) (build, clustering, banner/legend, popups).

**Working principles (#222):** Ship only after all map modes leave Folium. Until then, legacy Folium paths only need to stay runnable for development — defer cross-stack DRY and deep edge-case polish until Folium is removed and one architecture remains.

---

## 1. Viewport / focus / zoom parity with legacy Folium — **done (initial)**

**Shipped:** `all_locations_leaflet_viewport_recipe` in `explorer/core/map_overlay_visit_map.py` mirrors the Folium All locations branch (scope pairs, centre-of-gravity, single-point `fitBounds`, padding px, max zoom caps, **go-to-GPS** framing). It is included in the Leaflet `revision_bundle` / `revision_extra` from `explorer/app/streamlit/app_prep_map_ui.py`. The iframe applies it via `parseViewportV1` / `applyAllLocationsViewport` in `explorer/components/all_locations_map/frontend/src/AllLocationsMap.tsx` (fallback: GeoJSON `pad(0.12)` when `viewport` is missing).

**Follow-ups:** Folium path still uses inline logic — consider calling `all_locations_leaflet_viewport_recipe` from `build_visit_overlay_map` to guarantee a single source of truth. Re-verify acceptance with full datasets + edge cases (country focus, empty pairs).

---

## 2. Go to GPS — red temporary marker (Folium parity) — **done**

Implemented in `AllLocationsMap.tsx` (`syncGoToGpsMarker`, `goToGpsMarkerIcon`) + `AllLocationsMapPopup.css` when `viewport.mode === "go_to_gps"`: red DivIcon pin on the map root (not inside MarkerCluster), popup HTML matches Folium (`Temporary GPS marker`). Empty-GeoJSON path still frames GPS + marker.

---

## 3. Base map / layer control — **done (initial)**

**Shipped:** Prep tab sidebar `map_style` (same keys as `create_map` in `map_renderer.py`: `default` OSM, `google` hybrid, `carto` CartoDB Positron) is passed into `render_all_locations_map_component` → `AllLocationsMap.tsx` as `map_style`. A dedicated effect swaps the Leaflet base `TileLayer` (URLs + attribution aligned with Folium) so basemap changes do not force a GeoJSON rebuild when `revision` is unchanged.

**Deferred:** In-iframe `L.control.layers` (or extra tile sources) if we want basemap picking inside the map without the Streamlit sidebar.

---

## 4. Popup open — map jiggle / unexpected pan (investigate)

**Reported:** On the custom map, opening a popup can nudge or recentre the view — usually a small “bump”, occasionally a jump of roughly a full screen. Legacy Folium does **not** move the map on popup open except Leaflet’s normal **auto-pan** when the marker is near the edge and the popup would clip off-screen.

**Parity target:** Popups open in place; map stays fixed unless edge auto-pan is required for visibility.

**Likely areas (when we pick this up):** `popupopen` → `scheduleShrinkPebirdLeafletPopups` / `popup.update()`; `ResizeObserver` + `invalidateSize`; shrink-width layout changing popup anchor; Leaflet `autoPan` / `keepInView` options on `bindPopup`. Gather repro cases (cluster vs single marker, screen position, zoom) before changing behaviour.

---

## 5. Attribution / iframe chrome — **done (verified)**

**Attribution:** Bottom-right Leaflet/OSM·CARTO·Google attribution readable on all three basemaps (no clip in iframe). CSS: `AllLocationsMapPopup.css` container padding + `.leaflet-bottom.leaflet-right` inset.

**Legend inset:** ``.pebird-map-legend`` padding matches the banner (`12px 16px`). In the All locations iframe the **banner** stays ``position:fixed`` with ``_BANNER_POSITION`` (16px top/right — same as Folium). The **legend** uses ``STREAMLIT_COMPONENT_MAP_LEGEND_STYLE``: ``position:absolute; bottom:16px`` from ``.all-locations-map-frame`` (keeps the legend–map bottom gap), with a **tighter** ``left`` than 16px (currently ``8px`` in ``STREAMLIT_COMPONENT_MAP_LEGEND_STYLE`` — tune if iframe chrome changes) so the visual left gutter lines up with the fixed banner’s viewport inset.

---

## 6. Other map modes still on Folium (later #222)

- **Species / lifer / family** maps: remain `st_folium` until migrated; separate milestones (GeoJSON + component or hybrid).

---

## 7. Export map HTML

- Export path today serializes Folium. Decide whether All locations on the component needs HTML export or a different artifact.

---

## 8. Performance / benchmarks (#205)

- Optional: extend map perf harness / snapshots for the component path vs Folium HTML size and interaction.

---

## 9. Branch / spike cleanup

- When #222 is landed to your satisfaction, retire or archive branch `221-streamlit-custom-map-component-spike` per original plan.
