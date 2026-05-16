# All locations Leaflet map — backlog (#222)

Living checklist for the Streamlit **custom component** path (`declare_component` + committed `frontend/build`).  
Update this file as items ship so the backlog stays visible outside chat history.

**Related:** [README.md](./README.md) (build, clustering, banner/legend, popups).

**Working principles (#222):** Ship only after all map modes leave Folium. Until then, legacy Folium paths only need to stay runnable for development — defer cross-stack DRY and deep edge-case polish until Folium is removed and one architecture remains.

---

### #222 status and rollout (source narrative)

**Where we are:** The **All locations** map on the Streamlit **custom component** (`declare_component` + committed `frontend/build`) is **complete for this milestone**: viewport/focus (§1), go-to-GPS (§2), basemap swap without full layer rebuild (§3), popups and chrome (§4–5). Work continues under **#222** by **migrating other map modes** (species / lifer / family — §6) and optional hygiene (§7–11).

**Integrate onto `beta-next` in batches:** Prefer **several small PRs into `beta-next` only** (per [CONTRIBUTING.md](../../../CONTRIBUTING.md) — reviewable changes), **not** one huge merge and **not** landing everything on **`main`** until you choose to promote. Flow: merge completed slices → dogfood on `beta-next` → next PR (e.g. §11 zoom debug and/or the next Folium mode). Avoid bundling “all maps + docs” in a single hit.

**Next immediate task:** **Open a PR targeting `beta-next`** for the current All locations / component work (when the branch is ready), merge after review, then pick **§11** or the **first §6** map migration as the following batch.

**Next focus (after PR):** §11 (zoom debug overlay parity) **and/or** start **§6** (first additional map mode — species, lifer, or family as a **separate** milestone). See **§10** for full doc pass **after** all maps are migrated.

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

## 4. Popup open — map motion / width / visit layout — **done**

**Shipped (component iframe, TS + `AllLocationsMapPopup.css`):**

- **Map:** Leaflet ``autoPan: false`` on bound popups; ``maybePanPopupIntoView`` only pans when the balloon would clip the container inset — no centred-marker jiggle (#222).
- **Width:** Single finalize after ``document.fonts.ready`` + double ``requestAnimationFrame`` — measure with content/wrapper held at **map cap** px (avoids cyclic `%` collapse to a character column). Commit attributes skip remeasuring on iframe bumps unless the map cap changes. **Do not** inject Folium ``map_popup_width_fix_script`` here — it duplicated shrink passes.
- **Typography:** Headings ``nowrap`` + row ``overflow-x: auto`` for rare overflow; visit links ``nowrap`` + **inline** + ``<br>`` like ``build_visit_info_html`` (block + ``<br>`` had doubled vertical gaps).

**Folium maps** still use injected ``map_popup_width_fix_script`` + theme CSS from Python — keep ``map_popup_theme_stylesheet`` / ``map_popup_width_fix_script`` aligned when changing popup rules.

---

## 5. Attribution / iframe chrome — **done**

**Attribution:** Bottom-right Leaflet/OSM·CARTO·Google attribution readable on all three basemaps (no clip in iframe). CSS: `AllLocationsMapPopup.css` container padding + `.leaflet-bottom.leaflet-right` inset.

**Legend / banner chrome:** ``.pebird-map-legend`` padding matches the banner (`12px 16px`). All locations iframe: **banner** ``position:fixed`` + ``_BANNER_POSITION`` (16px top/right, Folium parity); **legend** ``STREAMLIT_COMPONENT_MAP_LEGEND_STYLE`` — ``position:absolute``, ``bottom:16px``, ``left:8px`` (frame-relative bottom spacing + viewport-aligned visual left gutter).

**Status:** Closed for All locations; reopen only if attribution clips on a new basemap or Streamlit iframe theme change.

---

## 6. Other map modes still on Folium (later #222)

- **Species / lifer / family** maps: remain `st_folium` until migrated — **one mode per milestone / PR series**, not all maps in a single change set.
- **Lifer locations** — **done (Leaflet component)** (#222): same iframe as All locations; GeoJSON `lifer_popup_v1` + per-feature `circle_pin`; Prep tab switches to the component when Map view = **Lifer locations**.
- Order is not fixed in code: pick **selected species**, **lifer locations**, or **family** next; each needs GeoJSON (or equivalent) + component (or hybrid) wiring and popup/viewport parity in its own batch onto `beta-next`.

---

## 7. Export map HTML

- Export path today serializes Folium. Decide whether All locations on the component needs HTML export or a different artifact.

---

## 8. Performance / benchmarks (#205)

- Optional: extend map perf harness / snapshots for the component path vs Folium HTML size and interaction.

---

## 9. Branch / spike cleanup

- When #222 is landed to your satisfaction, retire or archive branch `221-streamlit-custom-map-component-spike` per original plan.

---

## 10. Repository documentation — custom map architecture (**after all maps migrated**)

The repo describes Streamlit and caps how much “new stack” we add; All locations (and eventual species / lifer / family) on the **declare_component + committed `frontend/build`** path is materially new vs the prior Folium + `st_folium` mental model.

**When:** After every map mode is on the new architecture (close to ship), not patch-by-patch during migration.

**Do:** Audit and refresh **relevant docs** — e.g. root `README` / explorer README, developer guides, `.cursor` commands or rules if they cite Folium-only maps, map build instructions. Replace or branch narrative (Folium vs component), document the component build, cache/revision contract, and where `defaults.py` / prep UI feed the iframe.

---

## 11. Debug: live zoom level overlay (**retain parity**)

Production Folium builders call ``add_zoom_level_debug_overlay(...)`` when ``MAP_DEBUG_SHOW_ZOOM_LEVEL`` is true in ``explorer/app/streamlit/defaults.py`` (see ``map_renderer.py``, ``map_overlay_visit_map.py``, ``map_overlay_lifer_map.py``).

**Gap:** Custom component maps (All locations today) do not yet honour that flag — no live zoom readout in the iframe.

**Do:** Pass the flag through component args (or inject the same Leaflet/HTML pattern used by ``add_zoom_level_debug_overlay``) in ``AllLocationsMap.tsx``, and replicate for future component maps so debug behaviour stays one switch in ``defaults.py``.
