# All locations Leaflet map — backlog (#222)

Living checklist for the Streamlit **custom component** path (`declare_component` + committed `frontend/build`).  
Update this file as items ship so the backlog stays visible outside chat history.

**Related:** [README.md](./README.md) (build, clustering, banner/legend, popups).

**Working principles:** Production Map tab uses **only** the Leaflet component. Folium / `streamlit-folium` / `map_controller` were removed on branch **`222-folium-removal`** (May 2026).

---

### #222 status and rollout (source narrative)

**Where we are (May 2026):** All four Map-tab modes on **Leaflet** on `beta-next`. Folium stack **removed** (#232). **§17 Fix now** popup parity **shipped** (#233). Optional **§17 full pass** (design-review table) and **§10** docs remain.

| Map mode | Status | PR (approx.) |
|----------|--------|----------------|
| **All locations** | **Done** — §1–5 | #224 |
| **Lifer locations** | **Done** — §6 (lifer row) | #225 |
| **Species locations** | **Done** — §6 (species row) | #226 |
| **Family locations** | **Done** — §6 (family row) | #228 |
| **Design utility (preview)** | **Done** — §16 | — |
| **Popup template — Fix now (§17)** | **Done** | #233 |
| **Popup template — full pass (§17)** | **Optional** — product choices | — |

### §17 status

**Fix now (#233):** Species rules mirrored in `AllLocationsMapPopup.css`; location headings wrap with `__heading-row` clearance (all modes); export popups use same BEM + `popup_v1_export_html.py` tests for all four payload types.

**Optional full pass:** Heading margin 4px vs 6px (species), section-label uniformity, lifer line shape, manual cross-mode checklist — see §17 table below. Not blocking **#222** closure.

**#222** can close after brief smoke on `beta-next` if you are satisfied with map parity; keep open only if you want the §17 full-pass checklist done first.

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

## 7. Export map HTML — **done (single-stack HTML)**

**Shipped:** `leaflet_map_to_html_bytes` — standalone HTML with CDN Leaflet + MarkerCluster.

**Do (export popup HTML):**

- [x] Tests for `lifer_popup_v1`, `family_popup_v1`, and `species_popup_v1` via `popup_export_html_from_properties` (#233).
- [x] Export `visited_truncated` trunc-hint parity with live map (`popup_v1_export_html`, `visit_trunc_hint_html` on `LocationPopupModel`).
- **Optional:** Assert banner/legend fragments in exported HTML.

**Follow-up:** §18 — export button UX (single click, clear feedback).

---

## 8. Performance / benchmarks (#205)

- Optional: extend map perf harness for Leaflet payload vs old Folium HTML size.
- **Leaflet export HTML cache:** **Done** — `LEAFLET_EXPORT_HTML_CACHE_KEY` LRU.

---

## 9. Branch / spike cleanup

- When #222 is landed, retire branch `221-streamlit-custom-map-component-spike` per original plan.

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

## 17. Popup template parity across all map modes — **Fix now done (#233); full pass optional**

Audit (May 2026): all four Leaflet modes share `map_overlay_theme_stylesheet()` injected into the iframe plus `AllLocationsMapPopup.css` (`.pebird-map-popup` base **0.8125rem**, green headings, green links). Structured payloads (`popup_v1`, `species_popup_v1`, `lifer_popup_v1`, `family_popup_v1`) are rendered by **one TS layout per mode** in `AllLocationsMap.tsx`; export uses `popup_v1_export_html.py` with the same BEM classes (standalone export also embeds `AllLocationsMapPopup.css`).

**Headings aligned** via `pebird-map-popup__location-heading` + `map_popup_heading_text.prevent_orphan_closing_punctuation` (Python + TS). Optional full pass: spacing choices, section chrome, manual cross-mode checklist.

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

### Fix now — **done (#233)**

| Item | Maps | Status |
|------|------|--------|
| **Species-only CSS in component CSS file** | Species | **Done** — `obs-line`, `species-seen`, `all-visits`, chevrons, `media-link` in `AllLocationsMapPopup.css` (mirrors `map_popup_theme_stylesheet`). |
| **Long location heading** | All 4 | **Done** — `white-space: normal` on `__location-heading`; `__heading-row` `padding-right: 2.25rem`; orphan punctuation helper (Python + TS). |
| **Export popup HTML parity** | All 4 | **Done** — `popup_v1_export_html.py` + tests; export bundles `AllLocationsMapPopup.css`; trunc-hint when visits capped (§7). |

### Full pass (design review — optional)

| Item | Maps | Notes |
|------|------|--------|
| **Heading margin below title** | All 4 | All/Lifer/Family **4px**; Species **6px** (legacy Folium). Pick one default or document exceptions in `map_popup_models.py` / TS constants. |
| **Section labels** | Lifer, Family | No `Visited:` / `<details>` chrome (content-driven); All + Species use `__section-label`. Revisit if we want uniform “data block” labels. |
| **Lifer line format** | Lifer | `Species : date` in one link vs All locations visit rows — **content** shape, not font size; only change if product wants structural parity. |
| **Cross-mode checklist** | All 4 + export | Open the same location/species on each map mode; compare font size, link colour, bold, truncation hints, scroll regions, popup max width. Update regression checklist Map section if needed. |

**Files:** `AllLocationsMap.tsx`, `AllLocationsMapPopup.css`, `map_renderer.py`, `popup_v1_export_html.py`, `map_popup_models.py`, `map_overlay_species_popups.py`, `map_overlay_family_popups.py`, geojson builders under `explorer/core/`.

**Related:** §7 export popup tests · `docs/explorer/regression-checklist.md` (Map — popups / links).

---

## 13. Species locations — optional polish (deferred)

From post–PR #226. **Not blocking** merge.

### Cache banner on payload hit

**Gap:** Species Leaflet branch recomputes banner HTML on every rerun even when `SPECIES_LEAFLET_PAYLOAD_CACHE_KEY` hits.

**Do:** Cache banner fields or HTML in the payload LRU entry.

### Cache awaiting-selection empty payload

**Gap:** Empty GeoJSON when no species selected is rebuilt each rerun; not stored in species payload LRU.

**Do:** Optional — store in 2-entry LRU.

### DRY species banner stats

**Done (Folium removed):** `compute_species_map_banner_fields` is the single path; no Folium duplicate left.

---

## 14. Family locations — optional polish (deferred)

From PR #228. **Not blocking** merge.

### Cache empty / awaiting-selection payloads

**Gap:** Empty family payloads rebuilt each rerun; not stored in `FAMILY_LEAFLET_PAYLOAD_CACHE_KEY`.

**Do:** Optional — store in 4-entry LRU.

---

## 18. Export map HTML — button UX — **done**

**Shipped:** One sidebar `st.button` (“Export map HTML”). On click: build if needed (spinner; session/LRU skip rebuild), `st.rerun()`, hidden `st.download_button` with bytes, parent-frame JS auto-clicks it (iframe Blob downloads do not work). One user click; lazy recipe sync unchanged.

**Files:** `app_prep_map_ui.py`, `app_map_ui.py` (`inject_auto_click_streamlit_download_js`), `app_constants.py`.

---

## Agent handover

*Last updated: May 2026 — **§7 + §18 export HTML done** on `222-export-html-ux`; optional §17 full pass + §10 docs next.*

**Smoke (before closing #222):** Design utility + Map tab — regression checklist Map section.

**Branch `222-export-html-ux`:** §7 + §18 export HTML work.

**Recommended next work (after export PR):**

1. §10 — documentation pass (Folium → Leaflet architecture).
2. Close **#222** after smoke on `beta-next` (optional §17 full-pass checklist first).
3. §13–§14 — cache polish (optional).
4. §8 — perf (#205).

**Recover lost §17 detail:** `git show bdfa70f1^:explorer/components/all_locations_map/TODO.md` (section “## 15. Popup typography…” before Folium-removal commit collapsed it).
