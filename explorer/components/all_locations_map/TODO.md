# All locations Leaflet map — backlog (#222)

Living checklist for the Streamlit **custom component** path (`declare_component` + committed `frontend/build`).  
Update this file as items ship so the backlog stays visible outside chat history.

**Related:** [README.md](./README.md) (build, clustering, banner/legend, popups).

**Working principles (#222):** Ship only after all map modes leave Folium. Until then, legacy Folium paths only need to stay runnable for development — defer cross-stack DRY and deep edge-case polish until Folium is removed and one architecture remains.

---

### #222 status and rollout (source narrative)

**Where we are (May 2026):** Three map modes are on the **Leaflet custom component** and merged to **`beta-next`**; **Family** is the last Folium map mode:

| Map mode | Status | PR (approx.) |
|----------|--------|----------------|
| **All locations** | **Done** — §1–5 | #224 |
| **Lifer locations** | **Done** — §6 (lifer row) | #225 |
| **Species locations** | **Done** — §6 (species row) | #226 |
| **Family locations** | **Done** — §6 (family row); dogfood on branch | — |

**#222 stays open** until Family (and any remaining Folium map paths) are migrated. This is a **WIP partial** rollout, not “close #222” yet.

**Integrate onto `beta-next` in batches:** Prefer **several small PRs into `beta-next` only** (per [CONTRIBUTING.md](../../../CONTRIBUTING.md)), **not** one monolith and **not** landing on **`main`** until promotion. Flow: merge slice → dogfood on `beta-next` → next slice.

**Recommended order for remaining §6 work** (same iframe / patterns as All locations + Lifer + Species):

1. ~~**Family locations**~~ — shipped on branch `222-family-locations-leaflet` (PR to `beta-next` pending).
2. **Optional in parallel or between maps:** §11 zoom debug overlay (small), §7 export decision, §8 perf (#205) when instrumentation work starts.

**Defer until all maps migrated:** §10 full documentation pass.

**Working branch:** **`222-family-locations-leaflet`** (from `beta-next` after #226 merge). The earlier branch **`222-replace-folium-custom-component`** was merged and removed from `origin` during PR #226 — recreate from `beta-next` if you need that name locally.

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
| **Species locations** | **Done** | `build_species_locations_geojson_payload`, `species_popup_v1` / visit-only `popup_v1`, pin roles — Prep: `use_species_leaflet` |
| **Family locations** | **Done** | `family_locations_geojson.py`, `use_family_leaflet`, `FAMILY_LEAFLET_PAYLOAD_CACHE_KEY` |

**Lifer implementation pointers:** `explorer/core/lifer_locations_geojson.py`, `lifer_leaflet_viewport_recipe` in `map_overlay_lifer_map.py`, `LIFER_LEAFLET_PAYLOAD_CACHE_KEY` in `app_constants.py`, lifer branch in `app_prep_map_ui.py`, TS: `lifer_popup_v1` + `circle_pin` in `AllLocationsMap.tsx`.

**Species implementation pointers:** `explorer/core/species_locations_geojson.py`, `explorer/core/map_overlay_species_popups.py`, `species_leaflet_viewport_recipe` in `map_overlay_visit_map.py`, `SPECIES_LEAFLET_PAYLOAD_CACHE_KEY` in `app_constants.py`, species branch in `app_prep_map_ui.py`, TS: `species_popup_v1` + `circle_pin` in `AllLocationsMap.tsx`. Popup shrink measure includes `.pebird-map-popup__obs-line` and species/all-visits `<summary>` rows (short location headings). Folium `build_species_overlay_map` remains for tests / legacy branch only. **Hide-only toggle:** session cache keeps **two** GeoJSON payloads (hide-only on/off) via LRU — see §13 for other cache/DRY follow-ups. E2E/perf: worth timing toggle A→B→A when adding journey tests (#205).

**Species optional polish:** §13 (deferred; not required for Species PR merge).

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

## 13. Species locations — optional polish (deferred)

From post–PR #226 code review. **Not blocking** Species merge; revisit during Family work, Folium removal, or a perf pass (#205 / §8).

### Cache banner on payload hit

**Gap:** In `app_prep_map_ui.py` (species Leaflet branch, ~954–990), `filter_species` + `compute_species_map_banner_fields` + `build_species_banner_html` run on **every** Streamlit rerun when a species is selected, even when `SPECIES_LEAFLET_PAYLOAD_CACHE_KEY` hits and GeoJSON is skipped.

**Do:** Cache banner fields or final banner HTML in the payload LRU entry (same `payload_cache_key` as GeoJSON) so warm reruns avoid repeat pandas work. Cost is smaller than GeoJSON build but noticeable if chasing “instant” revisit.

### Cache awaiting-selection empty payload

**Gap:** When no species is selected (`elif not overlay_sci`), empty `FeatureCollection` + revision hash are rebuilt each rerun; result is **not** stored in the species payload LRU (only built GeoJSON paths call `_leaflet_payload_cache_store`).

**Do:** Optional — store empty payload in the same 2-entry LRU for consistency. Cost today is tiny.

### DRY species banner stats (Folium vs Leaflet)

**Gap:** `compute_species_map_banner_fields` in `species_locations_geojson.py` parallels inline banner logic in `build_visit_overlay_map` (Folium species branch). Intentionally duplicated for this slice.

**Do:** Extract one shared helper (or have Folium call the Leaflet-oriented function) when Family lands or when Folium species path is removed — aligns with §12 “Shared Folium/GeoJSON DRY refactor”. Do **not** block Family migration on this.

---

## 11. Debug: live zoom level overlay (**retain parity**)

Production Folium builders call ``add_zoom_level_debug_overlay(...)`` when ``MAP_DEBUG_SHOW_ZOOM_LEVEL`` is true in ``explorer/app/streamlit/defaults.py`` (see ``map_renderer.py``, ``map_overlay_visit_map.py``, ``map_overlay_lifer_map.py``).

**Gap:** Custom component maps (All locations, Lifer, Species) do not yet honour that flag — no live zoom readout in the iframe.

**Do:** Pass the flag through component args (or inject the same Leaflet/HTML pattern used by ``add_zoom_level_debug_overlay``) in ``AllLocationsMap.tsx``, and replicate for future component maps so debug behaviour stays one switch in ``defaults.py``.

---

## 12. Agent handover — Family locations (start here)

*Last updated: May 2026 — PR **#226** merged to `beta-next`. New work branch: **`222-family-locations-leaflet`**.*

### State of play

| Item | Status |
|------|--------|
| Issue **#222** | **Open** — closes when Family (last map mode) is on the Leaflet component |
| Integration branch | **`beta-next`** — All locations (#224), Lifer (#225), Species (#226) |
| Remaining Folium map | None for live Map tab (Folium builders kept for tests / export until §7) |
| This TODO file | Living backlog + handover; update as Family ships |

**Note:** PR #226 merge deleted remote **`222-replace-folium-custom-component`**. Ongoing #222 work uses **`222-family-locations-leaflet`** branched from current `beta-next` (`4c5762ef` or later).

### Goal for the next agent

**Shipped on branch** `222-family-locations-leaflet`: Family locations use the Leaflet component (`family_locations_geojson.py`, `family_popup_v1`, highlight halo, viewport recipe). Merge PR to `beta-next`, dogfood, then **#222** can close (unless export/docs deferred per §7/§10).

### Where to look first (Family — Folium today)

| Area | Path | What it does |
|------|------|----------------|
| Prep / tab wiring | `explorer/app/streamlit/app_prep_map_ui.py` | `map_view_mode == "family"` → `cached_family_map_bundle`, `build_family_composition_folium_map`, banner/legend HTML (~lines 386–480). **No** `use_family_leaflet` yet. |
| Pin + banner data | `explorer/core/family_map_compute.py` | `filter_work_to_family`, `build_family_location_pins`, `compute_family_map_banner_metrics`, highlight/halo resolution |
| Folium map builder | `explorer/core/family_map_folium.py` | `build_family_composition_folium_map`, composition circles, highlight species, overlays |
| Taxonomy bundle cache | `explorer/app/streamlit/app_caches.py` | `cached_family_map_bundle` |
| Map tab embed | `explorer/app/streamlit/app_map_working_ui.py` | Family export path still Folium |

### Reference implementations (copy the pattern)

Use **Species** as the closest analogue (multiple pin roles, banner, background visit pins, hide/filter semantics). **Lifer** for simpler single-popup-type maps. **All locations** for clustering + `popup_v1` visit cards.

| Step | Species reference | Lifer | All locations |
|------|-------------------|-------|----------------|
| GeoJSON + revision | `explorer/core/species_locations_geojson.py` | `lifer_locations_geojson.py` | `all_locations_geojson.py` |
| Structured popups | `explorer/core/map_overlay_species_popups.py` | `map_overlay_lifer_popups.py` | inline `popup_v1` in geojson |
| Viewport recipe | `species_leaflet_viewport_recipe` in `map_overlay_visit_map.py` | `lifer_leaflet_viewport_recipe` in `map_overlay_lifer_map.py` | `all_locations_leaflet_viewport_recipe` |
| Prep flag + cache | `use_species_leaflet`, `SPECIES_LEAFLET_PAYLOAD_CACHE_KEY` in `app_prep_map_ui.py` / `app_constants.py` | `use_lifer_leaflet`, `LIFER_*` | `use_all_locations_leaflet`, `ALL_LOCATIONS_*` |
| TS rendering | `species_popup_v1`, `pin_role`, `circle_pin` in `AllLocationsMap.tsx` | `lifer_popup_v1` | `popup_v1`, clustering |
| Tests | `tests/explorer/test_species_locations_geojson.py` | `test_lifer_locations_geojson.py` | all-locations tests |

**Shared component entry:** `explorer/components/all_locations_map/__init__.py` → `render_all_locations_map_component`. After TS changes: `cd explorer/components/all_locations_map/frontend && npm ci && npm run build`, then commit `frontend/build/`.

### Suggested implementation order (Family)

1. Read Folium family path end-to-end (`family_map_folium.py` + prep branch) — list pin types, highlight species, composition vs visit pins, legend items.
2. Add `family_locations_geojson.py` (+ popup payload module if needed) — `revision` / `revision_extra`, per-feature `circle_pin`, structured popup JSON (not HTML×N).
3. Add `family_leaflet_viewport_recipe` (or reuse visit-map helper if framing matches).
4. Add `FAMILY_LEAFLET_PAYLOAD_CACHE_KEY` and `use_family_leaflet` in prep; mirror species LRU/cache-key pattern.
5. Extend `AllLocationsMap.tsx` for family popup template + any new `pin_role` / legend labels.
6. Unit tests in `tests/explorer/test_family_locations_geojson.py` (or extend species test file pattern).
7. One PR to `beta-next`; leave Folium builder until cutover verified; hide export on Leaflet until §7 decided.

### Session cache keys (`app_constants.py`)

- All locations: `ALL_LOCATIONS_LEAFLET_PAYLOAD_CACHE_KEY`
- Lifer: `LIFER_LEAFLET_PAYLOAD_CACHE_KEY`
- Species: `SPECIES_LEAFLET_PAYLOAD_CACHE_KEY`
- **Family:** add `FAMILY_LEAFLET_PAYLOAD_CACHE_KEY` (name TBD but follow convention)
- Cleared on dataset signature change in prep (with Folium static map cache).

### Code conventions (from recent batches)

- Module docstrings and comments should **stand alone** — do not sprinkle `#222` in inline comments (epic tracking lives here and in commit `Refs:`).
- Do **not** inject Folium `map_popup_width_fix_script` into the component iframe.
- Prefer **one map mode per PR** to `beta-next` ([CONTRIBUTING.md](../../../CONTRIBUTING.md)).

### Species batch — shipped on `beta-next` (#226)

- Leaflet species map, `species_popup_v1` / visit-only `popup_v1`, pin roles (species / lifer / last seen / default), banner + legend, hide-non-matching (2-entry payload LRU), go-to-GPS, basemap, colour scheme, popup width measure for short headings.
- Docstring cleanup commit; tests: `compute_species_map_banner_fields`, hide-only, pin roles — `tests/explorer/test_species_locations_geojson.py`.

### Species QA (optional retest on `beta-next`)

- [x] Core pins, popups, banner, legend, basemap, colour scheme
- [x] No species selected, hide-non-matching, no-sightings warning
- [ ] Mark lifer / mark last seen toggles
- [ ] Warm revisit / tab switch
- [ ] All locations popup width spot-check after shared measure change

### Deferred (OK to skip during Family migration)

- Export map HTML on Leaflet modes (§7) — Folium Family still exports until cutover.
- Zoom debug overlay on component maps (§11).
- Species cache/banner polish (§13).
- Shared Folium/GeoJSON DRY (§12 / §13).
- Perf harness (#205 / §8).
- Rename component directory from `all_locations_map` (after all maps).

### Useful docs

- [README.md](./README.md) — build, clustering, popups.
- [docs/AI_CONTEXT.md](../../../docs/AI_CONTEXT.md) — Streamlit vs core, caching, small PRs.
- `.cursor/commands/code-review.md` — naming and comment standards.
- GitHub issue **#222** — umbrella; partial PRs do not close it until Family ships.
