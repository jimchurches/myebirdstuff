# All locations Leaflet map — backlog (#222)

Living checklist for the Streamlit **custom component** path (`declare_component` + committed `frontend/build`).  
Update this file as items ship so the backlog stays visible outside chat history.

**Related:** [README.md](./README.md) (build, clustering, banner/legend, popups).

**Working principles:** Production Map tab uses **only** the Leaflet component. Folium / `streamlit-folium` / `map_controller` were removed on branch **`222-folium-removal`** (May 2026).

---

### #222 status and rollout (source narrative)

**Where we are (May 2026):** All four Map-tab modes are on the **Leaflet custom component** on `beta-next`. Family map **dogfood QA complete**. On **`222-folium-removal`**: production Folium stack removed; **do not merge to `beta-next` until §16 (design utility preview parity)** — otherwise we replace the working Folium-based design tool with export-only.

| Map mode | Status | PR (approx.) |
|----------|--------|----------------|
| **All locations** | **Done** — §1–5 | #224 |
| **Lifer locations** | **Done** — §6 (lifer row) | #225 |
| **Species locations** | **Done** — §6 (species row) | #226 |
| **Family locations** | **Done** — §6 (family row) | #228 |
| **Design utility (preview)** | **Not done** — §16 (merge blocker on this branch) | — |

**#222** can close after `222-folium-removal` merges (production maps + export + §16) and brief smoke on `beta-next`.

**Integrate onto `beta-next` in batches:** Prefer **several small PRs into `beta-next` only** (per [CONTRIBUTING.md](../../../CONTRIBUTING.md)).

**Working branch:** **`222-folium-removal`** (from `beta-next`) — rolls Folium removal **and** §16 design utility restore.

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

- Add tests for `lifer_popup_v1`, `family_popup_v1`, and `species_popup_v1` via `popup_export_html_from_properties`.
- **Optional:** Assert banner/legend fragments in exported HTML.

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
- Design utility: export tab only until **§16** ships (Folium preview removed from `design_map_app.py` on this branch)

---

## 16. Map marker design utility — live preview parity — **not done (merge blocker)**

**Do not merge `222-folium-removal` to `beta-next` until this is resolved.** Today’s `beta-next` still has a working developer tool:

```bash
streamlit run explorer/app/streamlit/design_map_app.py
```

**Legacy behaviour (pre-removal, still on `beta-next`):**

- **Map preview** tab: dummy Folium map centred near Canberra (`build_design_preview_map` in `design_map_preview.py`) with one marker per map role (all locations, species, lifer, family bands), bottom-left legend, optional SEQ MarkerCluster demo for all-locations scope, **Update map** driven by sidebar sliders.
- **Export to defaults.py** tab: paste-ready `MapMarkerColourScheme` snippets (`design_map_export.py`).

**Gap on `222-folium-removal`:** Folium + `build_design_preview_map` were removed with the production stack. Preview tab is an `st.info` placeholder; **export still works** via `scheme_seed_config` / `DesignMapPreviewConfig`.

**Target (parity, single stack):** Restore **live preview** without bringing Folium back. Prefer reusing the production Leaflet path:

| Piece | Notes |
|-------|--------|
| Config | Keep `DesignMapPreviewConfig` + `scheme_seed_config` (`design_map_preview.py`) |
| Dummy map data | Build minimal GeoJSON (or reuse component APIs) for each **Preview scope** — same roles as `PREVIEW_MARKER_ROWS` / legend labels |
| Embed | `render_all_locations_map_component` (or a thin design-only wrapper) with resolved colours from sidebar, not eBird CSV |
| Cluster demo | All-locations scope: optional synthetic cluster tier demo (was SEQ anchors in Folium) |
| Export tab | Unchanged |

**Reference on `beta-next` (before merge):** `git show beta-next:explorer/presentation/design_map_preview.py` (`build_design_preview_map`), `design_map_app.py` preview tab (`st_folium`).

**Acceptance:**

- [ ] **Update map** shows pins + legend for each preview scope (all / per-map-mode).
- [ ] Colours match sidebar + `map_marker_colour_resolve` (same as export tab would emit).
- [ ] No `folium` / `streamlit-folium` dependency reintroduced.
- [ ] `docs/development.md` § “Map marker colour design utility” updated (Leaflet preview, not Folium).

**Files (likely):** `explorer/app/streamlit/design_map_app.py`, `explorer/presentation/design_map_preview.py` (dummy payload builder), possibly `explorer/components/all_locations_map/` if preview shares component embed.

---

## 13–15. Deferred polish

See prior §13 (species banner cache), §14 (family empty LRU), §15 (popup typography). Not blocking merge if §16 is done.

---

## Agent handover

*Last updated: May 2026 — **Folium removed** on `222-folium-removal`; Family QA complete; **§16 blocks merge**.*

**Before merge to `beta-next`:** Complete **§16** (design utility Leaflet preview).

**After merge:** §7 export popup tests, §10 docs pass, §8 perf (#205), optional §13–§15 polish, close **#222**.
