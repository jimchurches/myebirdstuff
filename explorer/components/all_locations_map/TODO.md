# All locations Leaflet map — backlog (#222)

Living checklist for the Streamlit **custom component** path (`declare_component` + committed `frontend/build`).  
Update this file as items ship so the backlog stays visible outside chat history.

**Related:** [README.md](./README.md) (build, clustering, banner/legend, popups).

**Working principles (#222):** All four Map-tab modes now use the Leaflet component in production prep. Legacy Folium builders remain for **unit tests only** until Folium removal — **not** for production map display or export (§7 rules out a parallel Folium export stack). Defer cross-stack DRY and deep edge-case polish until Folium is removed.

---

### #222 status and rollout (source narrative)

**Where we are (May 2026):** All four Map-tab modes are on the **Leaflet custom component**. All locations, Lifer, and Species are merged to **`beta-next`**; **Family** is migrated on branch **`222-family-locations-leaflet`** (PR to `beta-next` pending):

| Map mode | Status | PR (approx.) |
|----------|--------|----------------|
| **All locations** | **Done** — §1–5 | #224 |
| **Lifer locations** | **Done** — §6 (lifer row) | #225 |
| **Species locations** | **Done** — §6 (species row) | #226 |
| **Family locations** | **Done** — §6 (family row) | PR pending → `beta-next` |

**#222** can close after Family PR merges and dogfoods on `beta-next` (unless you keep it open for §7 export, Folium removal, or §10 docs).

**Integrate onto `beta-next` in batches:** Prefer **several small PRs into `beta-next` only** (per [CONTRIBUTING.md](../../../CONTRIBUTING.md)), **not** one monolith and **not** landing on **`main`** until promotion.

**Next work (post–§6 migration):** §11 zoom debug overlay, §7 export decision, §8 perf (#205), §10 documentation pass, Folium stack removal / DRY.

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

**Status:** Closed for all component map modes; reopen only if attribution clips on a new basemap or Streamlit iframe theme change.

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

**Family implementation pointers:** `explorer/core/family_locations_geojson.py`, `explorer/core/map_overlay_family_popups.py`, `family_leaflet_viewport_recipe` in `map_overlay_visit_map.py`, `FAMILY_LEAFLET_PAYLOAD_CACHE_KEY` in `app_constants.py`, family branch in `app_prep_map_ui.py` (`use_family_leaflet`), TS: `family_popup_v1` + `circle_pin` + highlight halo in `AllLocationsMap.tsx`. Banner/legend reuse `build_family_map_banner_overlay_html` / `build_family_map_legend_overlay_html_for_pins` from `family_map_folium.py`. **Payload cache:** 4-entry LRU (family + highlight-species variants). **Export:** cleared on Leaflet family path (§7). Folium `build_family_composition_folium_map` remains for tests. Tests: `tests/explorer/test_family_locations_geojson.py`.

---

## 7. Export map HTML — **done (single-stack HTML)**

**Shipped (branch ``222-export-map-html``):** Leaflet maps export via ``leaflet_map_to_html_bytes`` — standalone HTML with CDN Leaflet 1.9.4 + MarkerCluster, same GeoJSON/theme/banner/legend as the live component. Popups pre-rendered in Python (``popup_v1_export_html``) into ``export_popup_html`` on each feature; viewer in ``explorer/presentation/static/leaflet_map_export.js``. Prep sets ``EXPLORER_MAP_HTML_BYTES_KEY`` for all four Leaflet modes (sidebar **Export map HTML** visible again).

**Constraints:** Downloaded file needs network for tiles + CDN scripts. Not fully offline.

**No dual stack:** Folium builders are not run for export on Leaflet paths.

---

## 8. Performance / benchmarks (#205)

- Optional: extend map perf harness / snapshots for the component path vs Folium HTML size and interaction.

---

## 9. Branch / spike cleanup

- When #222 is landed to your satisfaction, retire or archive branch `221-streamlit-custom-map-component-spike` per original plan.

---

## 10. Repository documentation — custom map architecture

The repo describes Streamlit and caps how much “new stack” we add; all four map modes on the **declare_component + committed `frontend/build`** path is materially new vs the prior Folium + `st_folium` mental model.

**When:** After Family PR is on `beta-next` and dogfooded (§6 complete).

**Do:** Audit and refresh **relevant docs** — e.g. root `README` / explorer README, developer guides, `.cursor` commands or rules if they cite Folium-only maps, map build instructions. Replace or branch narrative (Folium vs component), document the component build, cache/revision contract, and where `defaults.py` / prep UI feed the iframe.

---

## 15. Popup typography parity across map modes (deferred)

Audit (May 2026): all four Leaflet modes share `map_popup_theme_stylesheet()` + `AllLocationsMapPopup.css` (`.pebird-map-popup` base **0.8125rem**, green headings, green links). **Headings are aligned** via `pebird-map-popup__location-heading`. Remaining gaps are mostly spacing and Family-specific chrome — not a blocker for #222 close.

### Shipped in this backlog

- **Family body text (§15 item 2):** Species list rows use `pebird-map-popup__species-line` (inherit base size); empty state uses `pebird-map-popup__summary-line` (muted). Folium `format_family_location_popup_html` + TS `popupHtmlFamilyLayout` updated.
- **Family species line wrap (§15 width cap):** Removed `max-width:22rem` card cap; species lines use `white-space: nowrap` + horizontal scroll on overflow (visit-list pattern). Popup width grows via shrink-wrap measure.

### Still deferred (design / cross-mode pass)

| Item | Maps | Notes |
|------|------|--------|
| **Heading margin below title** | All 4 | All/Lifer/Family **4px**; Species **6px** (intentional in Folium). Lifer Folium used **2px** — Leaflet Lifer still **4px**. Pick one default or document exceptions. |
| ~~**Family popup width cap**~~ | Family | **Done** — removed 22rem cap; species names nowrap (May 2026). |
| **Section labels** | Lifer, Family | No `Visited:` / `<details>` chrome (content-driven); All + Species use `__section-label`. OK structurally; revisit if we want uniform “data block” labels. |
| **Species-only CSS in TS file** | Species | `obs-line`, `species-seen`, chevrons live in Python `map_popup_theme_stylesheet` only; component relies on injected theme. Copy into `AllLocationsMapPopup.css` when Folium is removed. |
| **Lifer line format** | Lifer | `Species : date` in one link vs All locations visit rows — content, not typography. |
| **Species map — long location heading** | Species | **Reported May 2026** (e.g. Hooded Robin at “Nombinnie Nature Reserve (East)--Euabalong-Mount Hope Rd …”): location title uses `pebird-map-popup__location-heading` with `white-space: nowrap` and shrink-wrap width; very long names run to the popup edge / under the close control with little or no visible right margin — no wrap. Revisit with cross-map heading rules: optional wrap, stronger `padding-right` on `__heading-row`, or horizontal scroll on the title row (All locations already scrolls the heading row in some cases). Not a Family-map issue. |

**Files:** `AllLocationsMap.tsx` (layouts), `AllLocationsMapPopup.css`, `map_renderer.py` (`map_popup_theme_stylesheet`), `family_map_compute.py`, `map_popup_models.py` (Species margin default 6).

---

## 14. Family locations — optional polish (deferred)

From PR #228 code review. **Not blocking** merge.

### Cache empty / awaiting-selection payloads

**Gap:** When no family is selected or taxonomy is unavailable, prep rebuilds an empty `FeatureCollection` each rerun without storing it in `FAMILY_LEAFLET_PAYLOAD_CACHE_KEY` (same pattern as Species §13).

**Do:** Optional — store empty payloads in the 4-entry LRU for warm reruns when toggling family/highlight.

### Rebuild frontend after TS one-liners

Any change to `AllLocationsMap.tsx` requires `npm run build` in `frontend/` and committing `frontend/build/` before merge.

---

## 13. Species locations — optional polish (deferred)

From post–PR #226 code review. **Not blocking** merge; revisit during Folium removal or a perf pass (#205 / §8).

### Cache banner on payload hit

**Gap:** In `app_prep_map_ui.py` (species Leaflet branch, ~954–990), `filter_species` + `compute_species_map_banner_fields` + `build_species_banner_html` run on **every** Streamlit rerun when a species is selected, even when `SPECIES_LEAFLET_PAYLOAD_CACHE_KEY` hits and GeoJSON is skipped.

**Do:** Cache banner fields or final banner HTML in the payload LRU entry (same `payload_cache_key` as GeoJSON) so warm reruns avoid repeat pandas work. Cost is smaller than GeoJSON build but noticeable if chasing “instant” revisit.

### Cache awaiting-selection empty payload

**Gap:** When no species is selected (`elif not overlay_sci`), empty `FeatureCollection` + revision hash are rebuilt each rerun; result is **not** stored in the species payload LRU (only built GeoJSON paths call `_leaflet_payload_cache_store`).

**Do:** Optional — store empty payload in the same 2-entry LRU for consistency. Cost today is tiny.

### DRY species banner stats (Folium vs Leaflet)

**Gap:** `compute_species_map_banner_fields` in `species_locations_geojson.py` parallels inline banner logic in `build_visit_overlay_map` (Folium species branch). Intentionally duplicated for this slice.

**Do:** Extract one shared helper (or have Folium call the Leaflet-oriented function) when Folium species path is removed — aligns with §12 “Shared Folium/GeoJSON DRY refactor”.

---

## 11. Debug: live zoom level overlay — **done**

**Shipped:** ``render_all_locations_map_component`` passes ``show_zoom_debug`` from ``MAP_DEBUG_SHOW_ZOOM_LEVEL`` (``defaults.py``). ``AllLocationsMap.tsx`` adds the same bottom-right Leaflet control as Folium ``add_zoom_level_debug_overlay`` (``.ebird-zoom-debug-overlay``). Applies to all four Map-tab Leaflet modes (single component embed).

---

## 12. Agent handover (post–§6 migration)

*Last updated: May 2026 — **Family locations migrated** on `222-family-locations-leaflet` (PR to `beta-next` pending).*

### State of play

| Item | Status |
|------|--------|
| Issue **#222** | **Ready to close** after Family PR merges to `beta-next` and dogfoods (all four map modes on Leaflet component) |
| Integration branch | **`beta-next`** — All locations (#224), Lifer (#225), Species (#226); Family PR pending |
| Live Map tab | **All modes Leaflet** via `render_all_locations_map_component` |
| Folium map builders | Kept for unit tests; not used in production prep for Map tab |
| Working branch | **`222-family-locations-leaflet`** |

### §6 migration — complete

| Mode | Leaflet | Key files |
|------|---------|-----------|
| All locations | Yes | `all_locations_geojson.py`, `use_all_locations_leaflet` |
| Lifer | Yes | `lifer_locations_geojson.py`, `use_lifer_leaflet` |
| Species | Yes | `species_locations_geojson.py`, `use_species_leaflet` |
| Family | Yes | `family_locations_geojson.py`, `use_family_leaflet` |

**Shared:** `explorer/components/all_locations_map/`, `map_overlay_theme_stylesheet()` in `map_renderer.py`, prep in `app_prep_map_ui.py`. After TS changes: `npm run build` in `frontend/`, commit `frontend/build/`.

### Session cache keys (`app_constants.py`)

- `ALL_LOCATIONS_LEAFLET_PAYLOAD_CACHE_KEY`
- `LIFER_LEAFLET_PAYLOAD_CACHE_KEY`
- `SPECIES_LEAFLET_PAYLOAD_CACHE_KEY` (2-entry LRU for hide-only toggle)
- `FAMILY_LEAFLET_PAYLOAD_CACHE_KEY` (4-entry LRU for family + highlight variants)

### Family batch — shipped on branch

- Leaflet family map: density-band pins, highlight species + halo, `family_popup_v1`, banner + legend (green species links, no underline — Folium parity), viewport with highlight max-zoom, basemap, colour scheme, awaiting-selection / empty states.
- Banner link CSS fix in `map_banner_and_legend_theme_stylesheet()`.
- Tests: `tests/explorer/test_family_locations_geojson.py`.

### Family QA (before/after PR merge)

- [x] Pins, popups, banner, legend, basemap, colour scheme, highlight species
- [x] Banner/legend species hyperlink styling (green, no underline)
- [ ] No family selected → blank + hint
- [ ] Family change + highlight-species toggle (warm cache)
- [ ] Spot-check other map modes after shared CSS change

### Suggested next tasks (after Family on `beta-next`)

1. Merge **`222-family-locations-leaflet`** → `beta-next`, dogfood, close **#222** (or keep open for cleanup epic).
2. ~~§11 — zoom debug overlay on component maps.~~ **Done** on ``222-zoom-debug-overlay``.
3. ~~§7 — export strategy for Leaflet modes.~~ **Done** on ``222-export-map-html``.
4. §10 — documentation pass; optional rename of `all_locations_map` component directory.
5. Remove or gate Folium map builders; §13–§14 cache polish; §15 popup typography pass; §8 perf (#205).
6. Standalone comments: remaining `refs #NNN` in `map_renderer.py` docstrings (popup HTML builders) — batch cleanup.

### Useful docs

- [README.md](./README.md) — build, clustering, popups.
- [docs/AI_CONTEXT.md](../../../docs/AI_CONTEXT.md) — Streamlit vs core, caching, small PRs.
- `.cursor/commands/code-review.md` — naming and comment standards.
- GitHub issue **#222** — umbrella for the Folium → Leaflet migration.
