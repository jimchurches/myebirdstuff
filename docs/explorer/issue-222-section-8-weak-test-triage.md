# Issue #222 — §8.6 weak-test accuracy triage

**Purpose:** Decide what to do with tests that mostly prove “didn’t crash” vs contracts worth locking before closing #222.  
**Date:** 2026-05-20 · **Branch:** `222-test-performance-review`

**Legend**

| Decision | Meaning |
|----------|---------|
| **TIGHTEN_NOW** | Small assert added on this branch (or already strong enough) |
| **SKIP #222** | Accept as intentional smoke; no issue |
| **FOLLOW-UP** | New GitHub issue; out of scope for #222 close-out |

---

## Already strong (no change)

| Test / area | Why |
|-------------|-----|
| `test_species_locations_geojson.py` | Pin roles, popup shapes, hide-non-matching, banner field counts |
| `test_family_locations_geojson.py` | Species URL lines, highlight framing, `family_popup_v1` structure |
| `test_leaflet_map_html_export.py` | HTML contains export shell, popup types, lifer/family/species blocks |
| `test_map_renderer.py` (popup/banner) | Substring + structure contracts on HTML builders |
| `test_all_locations_map_component.py` | Asserts `show_zoom_debug` passed to component |
| `test_streamlit_map_e2e::test_all_locations_cluster_popup_parity` | Popup open, tip, banner width (#205 I6) |
| `test_streamlit_ui_helpers::test_leaflet_payload_cache_key_*` | Cache keys differ when inputs differ (Leaflet payload LRU identity) |
| `test_leaflet_payload_cache.py` | LRU hit restores revision/geojson/banner/legend |
| `test_leaflet_geojson_build_metrics.py` | Marker counts + merge into perf extra |
| `test_map_perf_e2e.py` | Stages, ceilings, `marker_count` on payload miss |

---

## TIGHTEN_NOW (done or trivial on this branch)

| Test | Was weak | Action |
|------|----------|--------|
| `test_lifer_locations_geojson::test_build_lifer_geojson_minimal` | `len(features) >= 1`, keys only | Assert exactly one feature, `location_id`, non-empty `lifer_popup_v1.lines` |
| `test_family_map_compute::test_merge_taxonomy_detail_for_family_map_smoke` | Only `"group_name" in columns` | Assert row count matches input taxonomy |
| `test_design_map_preview::test_build_design_preview_leaflet_bundle_revision_*` | `assert a["legend_html"]` truthy | Assert non-empty legend HTML string |

---

## SKIP #222 (intentional smoke — document only)

| Test | Why skip |
|------|----------|
| `test_streamlit_map_e2e::test_map_default_view_*` | E2E smoke: app boots, sidebar labels, banner appears |
| `test_streamlit_map_e2e::test_all_locations_map_shows_legend_*` | Legend presence via `wait_for_pebird_map_markup` + substring |
| `test_streamlit_journeys_e2e::test_journey_switch_*` | Journey smoke: banner title changes per mode |
| `test_streamlit_map_working.py` (4 tests) | Working-set wiring; `ws is not None` + status substring is enough for fixture |
| `test_streamlit_map_prep.py` | Small fixture context; totals and signatures are already specific |
| `test_design_map_preview::test_build_design_preview_leaflet_bundle_cluster_enabled_*` | Single flag check; preview tool not production path |
| `test_map_perf_e2e.py` (ceilings) | Guardrail against hangs, not UX benchmark |

---

## FOLLOW-UP (new issue — not #222)

| Item | Why defer | Suggested issue title |
|------|-----------|------------------------|
| **Per-mode Leaflet LRU tests** | Same helper pattern as all-locations; need four session keys + eviction cases | “Test Leaflet payload LRU for lifer/species/family session keys” |
| **`app_prep_map_ui` integration** | Needs Streamlit stub + spinners + mode switch + cache invalidation | “Integration tests for map prep spinners and payload cache invalidation” |
| **Species/Family E2E perf journey** | Playwright must drive searchbox / family selectbox | “E2E perf journey for Species and Family map modes” |
| **`leaflet_payload_cache_key` rename** | Was `static_map_cache_key` (Folium-era name) | **Done** — renamed in `app_caches.py` |
| **Broad “import module” smokes** | e.g. `test_streamlit_tab_modules_import_without_runtime` | Low value unless import regression recurs — optional backlog |

---

## Not weak (false alarms from audit wording)

| Item | Note |
|------|------|
| GeoJSON `assert rev is not None` | Paired with feature counts, popup `v: 1`, and role sets elsewhere |
| `test_prepare_all_locations_map_context_has_location_totals` | Asserts `effective_totals` and `records_by_loc` membership |
| Folium HTML popup tests in `test_map_renderer.py` | Still valid for shared HTML builders used in export/banners |

---

## §8.6 decision for #222

**Accuracy audit:** **Closed on #222** with three cheap tightenings (table above) and this triage doc. Remaining items are **SKIP** (smoke) or **FOLLOW-UP** (separate issues). No blocker to closing #222 testing/perf scope.
