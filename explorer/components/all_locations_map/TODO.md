# All locations Leaflet map — backlog (#222)

Living checklist for the Streamlit **custom component** path (`declare_component` + committed `frontend/build`).  
Update this file as items ship so the backlog stays visible outside chat history.

**Related:** [README.md](./README.md) (build, clustering, banner/legend, popups).

**Working principles (#222):** Ship only after all map modes leave Folium. Until then, legacy Folium paths only need to stay runnable for development — defer cross-stack DRY and deep edge-case polish until Folium is removed and one architecture remains.

---

### #222 status and rollout (source narrative)

**Where we are (May 2026):** Two map modes are on the **Leaflet custom component** and merged to **`beta-next`**:

| Map mode | Status | PR (approx.) |
|----------|--------|----------------|
| **All locations** | **Done** — §1–5 | #224 |
| **Lifer locations** | **Done** — §6 (lifer row) | #225 |
| **Species locations** | Folium (`st_folium`) | — |
| **Family locations** | Folium | — |

**#222 stays open** until species + family (and any remaining Folium map paths) are migrated. This is a **WIP partial** rollout, not “close #222” yet.

**Integrate onto `beta-next` in batches:** Prefer **several small PRs into `beta-next` only** (per [CONTRIBUTING.md](../../../CONTRIBUTING.md)), **not** one monolith and **not** landing on **`main`** until promotion. Flow: merge slice → dogfood on `beta-next` → next slice.

**Recommended order for remaining §6 work** (same iframe / patterns as All locations + Lifer):

1. **Species locations** — highest user traffic; more edge cases (selected species, lifer/last-seen pins, filters) than lifer but shares visit-popup DNA with All locations.
2. **Family locations** — richest logic (`family_map_folium`, composition pins, highlight species); do last.
3. **Optional in parallel or between maps:** §11 zoom debug overlay (small), §7 export decision, §8 perf (#205) when instrumentation work starts.

**Defer until all maps migrated:** §10 full documentation pass.

**Working branch:** Keep using **`222-replace-folium-custom-component`** for ongoing #222 work (do **not** delete — partial milestone branch).

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

## 6. Other map modes — Folium → Leaflet component (#222)

**Rule:** **One map mode per PR** to `beta-next`, not all maps in one change set.

| Mode | Status | Notes |
|------|--------|--------|
| **All locations** | **Done** | `build_all_locations_geojson_payload`, `popup_v1`, clustering, scope/GPS — Prep: `use_all_locations_leaflet` |
| **Lifer locations** | **Done** | `build_lifer_locations_geojson_payload`, `lifer_popup_v1`, per-feature `circle_pin`, no cluster — Prep: `use_lifer_leaflet` |
| **Species locations** | **Next** | `build_visit_overlay_map` / `build_species_overlay_map`; visit + lifer/last-seen pin roles |
| **Family locations** | **Later** | `build_family_composition_folium_map`, `family_map_compute` / `family_map_folium` |

**Lifer implementation pointers:** `explorer/core/lifer_locations_geojson.py`, `lifer_leaflet_viewport_recipe` in `map_overlay_lifer_map.py`, `LIFER_LEAFLET_PAYLOAD_CACHE_KEY` in `app_constants.py`, lifer branch in `app_prep_map_ui.py`, TS: `lifer_popup_v1` + `circle_pin` in `AllLocationsMap.tsx`.

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

---

## 12. Agent handover (update when status changes)

*Last updated: May 2026 — after All locations + Lifer merged to `beta-next`.*

### For the next agent

**Goal:** Finish **#222** by migrating **Species** then **Family** off Folium onto the same Streamlit component (`explorer/components/all_locations_map/`). All locations and Lifer are the reference implementations.

**Branch & git**

- Long-lived branch: **`222-replace-folium-custom-component`** — **keep it** (partial #222; user requested no delete after merges).
- **`beta-next`** already has: All locations (#224), Lifer (#225). New work: branch from `beta-next`, PR back to `beta-next`.
- After `npm run build` in `frontend/`, commit **`frontend/build/`** (hashed bundles) — CI runs `npm ci` + build.

**Architecture (repeat per map mode)**

1. **Core:** GeoJSON builder + `revision` / `revision_extra` (see `all_locations_geojson.py`, `lifer_locations_geojson.py`).
2. **Viewport:** versioned dict `v: 1` — TS `parseViewportV1` / `applyAllLocationsViewport` (lifer uses `lifer_leaflet_viewport_recipe`).
3. **Popups:** structured JSON on feature properties (not HTML×N) — TS builds HTML with `escapeHtml` + `safeHttpUrlForAnchor`.
4. **Prep:** `app_prep_map_ui.py` — flag like `use_*_leaflet`, session payload cache key, `render_all_locations_map_component(...)` (name is historical).
5. **Folium builders:** leave in place for tests/export until mode is fully cut over in Prep.

**Session cache keys** (`app_constants.py`)

- All locations: `ALL_LOCATIONS_LEAFLET_PAYLOAD_CACHE_KEY`
- Lifer: `LIFER_LEAFLET_PAYLOAD_CACHE_KEY`
- Cleared on dataset signature change in prep (with Folium static map cache).

**Do not**

- Inject Folium `map_popup_width_fix_script` into the component iframe (double-shrink / jiggle).
- Bundle species + family + docs in one PR.
- Close **#222** until species + family are on the component (unless product owner says otherwise).

**Manual test checklist (each new mode)**

- Pins, popups, banner, legend, basemap sidebar, colour scheme.
- Mode-specific toggles (e.g. subspecies lifers — done for Lifer).
- Warnings when data missing (mirror Folium strings).

**Deferred (explicitly OK to skip for now)**

- Warm-rerun / payload cache hit verification in perf logs — instrumentation pass later (#205 / §8).
- Shared “lifer model” refactor to dedupe Folium vs GeoJSON (nice-to-have).
- Rename component from `all_locations_map` to something generic (after all maps).

**Useful docs**

- [README.md](./README.md) — build, clustering, popups.
- [docs/AI_CONTEXT.md](../../../docs/AI_CONTEXT.md) — Streamlit vs core, caching, small PRs.
- Issue **#222** — umbrella; PRs are partial.

**Suggested next task**

Start **Species locations** on `222-replace-folium-custom-component`: read `build_visit_overlay_map` + existing All locations path in `app_prep_map_ui.py`, then add `species_*_geojson` (or extend visit overlay) + TS popup variant if needed.
