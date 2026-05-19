# All locations Leaflet map — backlog (#222)

Living checklist for the Streamlit **custom component** path (`declare_component` + committed `frontend/build`).  
Update this file as items ship so the backlog stays visible outside chat history.

**Related:** [README.md](./README.md) (build, clustering, banner/legend, popups).

**Working principles:** Production Map tab uses **only** the Leaflet component. Folium / `streamlit-folium` / `map_controller` were removed on branch **`222-folium-removal`** (May 2026).

**Leaflet payload cache contract (all four maps):** Session LRU via `_leaflet_payload_cache_lookup` / `_store` in `app_prep_map_ui.py`. Each entry holds `revision`, `geojson`, and (where applicable) `banner_html`, `legend_html`, plus mode-specific fields (`framing_pairs`, `pin_roles`, …). Warm reruns skip GeoJSON and overlay HTML rebuilds. LRU sizes: all-locations **4**, lifer **2**, species **2**, family **4** — sized for common toggle pairs (cluster, hide-non-matching, subspecies, highlight).

---

### #222 status and rollout (source narrative)

**Where we are (May 2026):** All four Map-tab modes on **Leaflet** on `beta-next`. Folium stack **removed** (#232). **§17** popup parity **done** (#233 + `222-optional-polish-maps`). **§13–§15** four-map payload cache **done** on **`222-optional-polish-maps`** (PR → `beta-next`). **#222** stays **open** for **§8** perf/instrumentation (#205) and **§10** docs (planned after merge). Experimental spike branch retirement is **out of scope** for #222 (separate issues).

| Map mode / workstream | Status | PR (approx.) |
|-----------------------|--------|----------------|
| **All locations** | **Done** — §1–5 | #224 |
| **Lifer locations** | **Done** — §6 (lifer row) | #225 |
| **Species locations** | **Done** — §6 (species row) | #226 |
| **Family locations** | **Done** — §6 (family row) | #228 |
| **Design utility (preview)** | **Done** — §16 | — |
| **Export HTML — popup parity (§7)** | **Done** | `222-export-html-ux` |
| **Export HTML — button UX (§18)** | **Done** | `222-export-html-ux` |
| **Popup template parity (§17)** | **Done** | #233, `222-optional-polish-maps` |
| **Leaflet payload cache — all four maps (§13–§15)** | **Done** | `222-optional-polish-maps` |

### §17 status — **done**

Popup parity accepted for #222 (better than legacy Folium). Remaining visual nits (e.g. species **6px** vs **4px** heading margin, mode-specific section chrome) may be tuned **outside #222** if they show up in use.

**Integrate onto `beta-next` in batches:** Prefer **several small PRs into `beta-next` only** (per [CONTRIBUTING.md](../../../CONTRIBUTING.md)).

---

## 1. Viewport / focus / zoom parity with legacy Folium — **done (initial)**

**Shipped:** `all_locations_leaflet_viewport_recipe` in `explorer/core/map_leaflet_viewport.py` (scope pairs, centre-of-gravity, single-point `fitBounds`, padding px, max zoom caps, **go-to-GPS** framing). Applied via `revision_bundle` / `revision_extra` in `app_prep_map_ui.py`; iframe: `parseViewportV1` / `applyAllLocationsViewport` in `AllLocationsMap.tsx`.

**Follow-ups:** Re-verify acceptance with full datasets + edge cases (country focus, empty pairs).

---

## 2. Go to GPS — red temporary marker (Folium parity) — **done**

Implemented in `AllLocationsMap.tsx` + `AllLocationsMapPopup.css` when `viewport.mode === "go_to_gps"`.

---

## 3. Base map / layer control — **done (initial)**

**Shipped:** Sidebar `map_style` → `AllLocationsMap.tsx` (`default` / `google` / `carto`). Basemap swap without GeoJSON rebuild when `revision` unchanged.

---

## 4. Popup open — map motion / width / visit layout — **done**

Width finalized in TS only (`AllLocationsMap.tsx` + `AllLocationsMapPopup.css`). Theme from `map_overlay_theme_stylesheet()` in `map_renderer.py`.

---

## 5. Attribution / iframe chrome — **done**

---

## 6. Other map modes — Folium → Leaflet component (#222) — **done**

| Mode | Status | Key modules |
|------|--------|-------------|
| **All locations** | **Done** | `all_locations_geojson.py`, `map_leaflet_viewport.py` |
| **Lifer** | **Done** | `lifer_locations_geojson.py` |
| **Species** | **Done** | `species_locations_geojson.py` |
| **Family** | **Done** | `family_locations_geojson.py`, `family_map_overlays.py` |

**Family QA (May 2026):** Complete — pins, popups, banner, legend, basemap, colour scheme, highlight species, no-family hint, family/highlight warm cache.

---

## 7. Export map HTML — **done**

**Shipped:** `leaflet_map_to_html_bytes` — standalone HTML with CDN Leaflet + MarkerCluster (#230). Export popup HTML tests (#233). **`visited_truncated` trunc-hint** in export path matches live map (`popup_v1_export_html`, `visit_trunc_hint_html` on `LocationPopupModel`) — `222-export-html-ux`.

**Do (export popup HTML):**

- [x] Tests for `lifer_popup_v1`, `family_popup_v1`, and `species_popup_v1` via `popup_export_html_from_properties` (#233).
- [x] Export `visited_truncated` trunc-hint parity with live map (`222-export-html-ux`).
- **Optional:** Assert banner/legend fragments in exported HTML.

---

## 8. Performance / benchmarks (#205)

- Optional: extend map perf harness for Leaflet payload vs old Folium HTML size.
- **Leaflet export HTML cache:** **Done** — `LEAFLET_EXPORT_HTML_CACHE_KEY` LRU.

---

## 10. Repository documentation — custom map architecture

**When:** After `222-folium-removal` merges.

**Do:** Audit root README, `explorer/app/streamlit/README.md`, `docs/development.md`, `.cursor` rules — remove Folium/`map_controller` references; document component build, cache/revision contract, prep → iframe flow. (Partial drive-by may land on the Folium-removal PR; full pass still tracked here.)

---

## 11. Debug: live zoom level overlay — **done**

`MAP_DEBUG_SHOW_ZOOM_LEVEL` → `AllLocationsMap.tsx` (`.ebird-zoom-debug-overlay`).

---

## 12. Folium removal — **done (222-folium-removal)**

**Removed:**

- `map_controller.py`, `map_overlay_visit_map.py`, `map_overlay_lifer_map.py`, `map_overlay_theme.py`, `family_map_folium.py`
- Folium `create_map`, `map_popup_width_fix_script`, `folium` / `streamlit-folium` from `requirements.txt`
- Folium embed path in `app_prep_map_ui.py`, `FOLIUM_STATIC_MAP_CACHE_KEY`
- Tests: `test_map_controller.py`, `test_family_map_folium.py`, `test_map_render_cache.py`, Folium cases in `test_map_renderer` / `test_streamlit_map_working`

**Kept / moved:**

- Viewport + cluster styling → `explorer/core/map_leaflet_viewport.py`
- Family banner/legend/pin styling → `explorer/core/family_map_overlays.py`
- Popup/banner HTML builders → `explorer/presentation/map_renderer.py`
- Design utility: Leaflet live preview + export (`design_map_preview.py`, §16)

---

## 16. Map marker design utility — live preview parity — **done**

**Shipped:** `build_design_preview_leaflet_bundle` + `render_all_locations_map_component` in `design_map_app.py` (Canberra zoom 5, role markers, SEQ cluster tier demo, legend). No `folium` / `streamlit-folium`.

**Acceptance:** [x] Update map per scope · [x] colours match sidebar/export · [x] `docs/development.md` updated.

---

## 17. Popup template parity across all map modes — **done**

Audit (May 2026): all four Leaflet modes share `map_overlay_theme_stylesheet()` injected into the iframe plus `AllLocationsMapPopup.css` (`.pebird-map-popup` base **0.8125rem**, green headings, green links). Structured payloads (`popup_v1`, `species_popup_v1`, `lifer_popup_v1`, `family_popup_v1`) are rendered by **one TS layout per mode** in `AllLocationsMap.tsx`; export uses `popup_v1_export_html.py` with the same BEM classes (standalone export also embeds `AllLocationsMapPopup.css`).

**Headings aligned** via `pebird-map-popup__location-heading` + `map_popup_heading_text.prevent_orphan_closing_punctuation` (Python + TS).

### Architecture (target)

| Layer | Role |
|-------|------|
| Python | Facts + URLs only in GeoJSON properties (no per-pin HTML in production) |
| `map_renderer.py` | `map_popup_theme_stylesheet()` — canonical CSS tokens (`EXPLORER_UI_*`) |
| `AllLocationsMapPopup.css` | Mirror of popup rules in the component (keep in sync with Python) |
| `AllLocationsMap.tsx` | Layout functions: all / species / lifer / family |
| `popup_v1_export_html.py` | Same class names for downloaded HTML |

See [README.md](./README.md) — “Popup anchor vs iframe size” and structured `popup_v1` notes.

### Shipped in prior backlog (keep)

- **Family body text:** Species rows → `pebird-map-popup__species-line`; empty state → `pebird-map-popup__summary-line`.
- **Family width cap:** Removed `max-width:22rem`; species names `nowrap` + horizontal scroll on overflow (visit-list pattern).

### Shipped

| Item | Maps | Notes |
|------|------|--------|
| **Species-only CSS in component CSS file** | Species | `AllLocationsMapPopup.css` mirrors `map_popup_theme_stylesheet` (#233). |
| **Long location heading** | All 4 | `__heading-row` clearance + orphan punctuation (Python + TS) (#233). |
| **Export popup HTML parity** | All 4 | `popup_v1_export_html.py` + tests; trunc-hint (§7). |
| **Lifer export layout (no `Visited:` label)** | Lifer export | `222-optional-polish-maps` — matches `popupHtmlLiferLayout`. |

**Accepted for #222 (change only if noticed in use):** species heading margin **6px** vs **4px** elsewhere; lifer/family content-driven blocks without all-locations `Visited:` chrome; lifer `Species : date` line shape.

**Files:** `AllLocationsMap.tsx`, `AllLocationsMapPopup.css`, `map_renderer.py`, `popup_v1_export_html.py`, `map_popup_models.py`, `map_overlay_species_popups.py`, `map_overlay_family_popups.py`, geojson builders under `explorer/core/`.

**Related:** §7 export popup tests · `docs/explorer/regression-checklist.md` (Map — popups / links).

---

## 13. Species locations — optional polish — **done**

From post–PR #226. **Not blocking** merge.

### Cache banner on payload hit — **done**

**Shipped:** `banner_html` and `legend_html` stored in `SPECIES_LEAFLET_PAYLOAD_CACHE_KEY` LRU entries and restored on payload cache hit (no banner recompute on warm rerun).

### Cache awaiting-selection empty payload — **done**

**Shipped:** Empty GeoJSON + awaiting-selection banner stored in the 2-entry species payload LRU when no species is selected.

### DRY species banner stats

**Done (Folium removed):** `compute_species_map_banner_fields` is the single path; no Folium duplicate left.

---

## 14. Family locations — optional polish — **done**

From PR #228. **Not blocking** merge.

### Cache empty / awaiting-selection payloads — **done**

**Shipped:** Empty family GeoJSON (no family selected / invalid family) stored in `FAMILY_LEAFLET_PAYLOAD_CACHE_KEY` 4-entry LRU.

### Cache banner + composition on payload hit — **done**

**Shipped:** Family pin composition, banner, and legend run only on cache miss; full entries include `banner_html` / `legend_html` restored on hit.

---

## 15. Leaflet payload cache — all four maps — **done (`222-optional-polish-maps`)**

Aligns warm-rerun behaviour across modes (builds on §13–§14).

| Map | LRU | Banner / legend on payload hit | Empty / awaiting-selection cached |
|-----|-----|--------------------------------|-----------------------------------|
| **All locations** | 4 entries (`_leaflet_payload_cache_*`) | **Done** | N/A |
| **Lifer** | 2 entries | **Done** | N/A |
| **Species** | 2 entries | **Done** (§13) | **Done** (§13) |
| **Family** | 4 entries | **Done** (§14) | **Done** (§14) |

**Shipped:** All-locations and lifer migrated from legacy single-slot session dicts to shared `_leaflet_payload_cache_lookup` / `_store`; `banner_html` + `legend_html` stored and restored on hit (same contract as species/family).

**Files:** `app_prep_map_ui.py` (`_ALL_LOCATIONS_*`, `_LIFER_*`, `_SPECIES_*`, `_FAMILY_*` max entry constants).

**Out of scope (future enhancement):** Per-mode **camera** memory when switching Map view (pan/zoom); payload cache does not remount iframe or preserve user framing.

---

## 18. Export map HTML — button UX — **done**

**Shipped (`222-export-html-ux`):** One sidebar `st.button` (“Export map HTML”). On click: build if needed (spinner; session/LRU skip rebuild), `st.rerun()`, `st.download_button` + parent-frame JS auto-click. One user click on typical desktop browsers (maintainer-tested Safari/macOS); lazy recipe sync unchanged.

**Alternative (if exports fail in the field):** Two-button Prepare + Download UX — see [`docs/explorer/map-html-export-ux-alternative.md`](../../../docs/explorer/map-html-export-ux-alternative.md).

**Files:** `app_prep_map_ui.py`, `app_map_ui.py` (`inject_auto_click_streamlit_download_js`), `app_constants.py`.

---

## Agent handover

*Last updated: May 2026 — branch **`222-optional-polish-maps`** (PR → `beta-next`, Refs #222).*

### Shipped on this branch

- **§13** — Species payload LRU: banner/legend on hit; empty awaiting-selection payload cached.
- **§14** — Family payload LRU: empty payloads; composition + banner/legend only on cache miss.
- **§15** — All-locations + lifer: same LRU helper + banner/legend on hit (four-map contract at top of this file).
- **§17 export** — Lifer export popup HTML matches live map (no `Visited:` section label).

### PR smoke (after merge to `beta-next`)

- Map tab: switch all four **Map view** modes; repeat visit same mode — no unnecessary spinner from banner/geojson rebuild when inputs unchanged.
- Species: no species selected → repeat rerun; family: no family selected → repeat rerun (empty map cached).
- Export map HTML: open exported file; lifer pin popup — no `Visited:` label above species lines.

### Recommended next work (post-merge; **#222** remains open)

1. **§8** — perf harness / instrumentation (#205).
2. **§10** — documentation pass (Folium → Leaflet architecture), last.
3. Close **#222** when §8 + §10 + smoke are satisfied.

**Recover lost §17 detail:** `git show bdfa70f1^:explorer/components/all_locations_map/TODO.md` (section “## 15. Popup typography…” before Folium-removal commit collapsed it; current **§15** is payload cache).
