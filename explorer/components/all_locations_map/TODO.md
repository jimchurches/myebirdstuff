# All locations Leaflet map — backlog (#222)

Living checklist for the Streamlit **custom component** path (`declare_component` + committed `frontend/build`).  
Update this file as items ship so the backlog stays visible outside chat history.

**Related:** [README.md](./README.md) (build, clustering, banner/legend, popups).

**Working principles:** Production Map tab uses **only** the Leaflet component. Folium / `streamlit-folium` / `map_controller` were removed on branch **`222-folium-removal`** (May 2026).

**Leaflet payload cache contract (all four maps):** Session LRU via `_leaflet_payload_cache_lookup` / `_store` in `app_prep_map_ui.py`. Each entry holds `revision`, `geojson`, and (where applicable) `banner_html`, `legend_html`, plus mode-specific fields (`framing_pairs`, `pin_roles`, …). Warm reruns skip GeoJSON and overlay HTML rebuilds. LRU sizes: all-locations **4**, lifer **2**, species **2**, family **4** — sized for common toggle pairs (cluster, hide-non-matching, subspecies, highlight).

---

### #222 status and rollout (source narrative)

**Where we are (May 2026):** All four Map-tab modes on **Leaflet** on `beta-next`. Folium stack **removed** (#232). **§17** popup parity **done** (#233 + `222-optional-polish-maps`). **§13–§15** four-map payload cache **done** on **`222-optional-polish-maps`** (PR → `beta-next`). **#222** stays **open** for **§8** (testing, client/CI, server perf — #205 / #221 context) and **§10** docs. Branch **`222-test-performance-review`**. Experimental spike branch retirement is **out of scope** for #222 (separate issues).

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

## 8. Testing & performance (#222 / #205 / #221)

**Branch:** `222-test-performance-review` · **Refs:** #222, #205, #221, #179.

**Architecture (why this batch has two halves):** Production maps are a **Streamlit custom component** — Python prepares GeoJSON, `revision`, banner/legend HTML, and calls `declare_component`; **React + Leaflet** in the committed `frontend/build` iframe renders markers, clustering, and popups. **Server** perf (`EXPLORER_PERF`, Playwright E2E) measures prep + embed; **client** perf (parse, cluster, first paint inside the iframe) is largely invisible to today’s stages unless we add it deliberately.

**Where metrics and baselines live (do not duplicate blindly):**

| Location | Use |
|----------|-----|
| [`benchmarks/map_perf/README.md`](../../../benchmarks/map_perf/README.md) | Committed **stage ceilings** (`stage_ceilings.json`); how to tune guardrails |
| `benchmarks/map_perf/snapshots/` (gitignored) | Local dated JSON snapshots via `scripts/snapshot_explorer_perf_log.py` |
| Issue/PR notes (#179, #205, #222) | Human **before/after** medians; not committed |
| [`docs/development.md`](../../../docs/development.md) § Performance Instrumentation Guardrails | `EXPLORER_PERF`, E2E `--perf`, JSONL archive env vars |
| [`explorer/app/streamlit/README.md`](../../app/streamlit/README.md) | Sidebar perf panel, `EXPLORER_PERF_LOG_FILE` |
| [`docs/explorer/regression-checklist.md`](../../../docs/explorer/regression-checklist.md) | Manual Map-tab smoke (complements automated tests) |
| GitHub **#205** / **#221** / **#222** comments | Durable narrative + tables (Folium-era baselines, spike JSONL, subjective cloud notes) |
| [`docs/explorer/issue-222-section-8-prior-art.md`](../../../docs/explorer/issue-222-section-8-prior-art.md) | **§8.0 mined summary** (stage mapping, shipped vs dropped) |
| [`docs/explorer/issue-222-section-8-baseline.md`](../../../docs/explorer/issue-222-section-8-baseline.md) | **§8.5** fixture + real CSV tables; re-run via `scripts/run_post_leaflet_perf_baseline.sh` |
| [`docs/explorer/issue-222-plain-summary.md`](../../../docs/explorer/issue-222-plain-summary.md) | **Plain-language** wins / trade-offs (also on GitHub #222) |
| [`docs/explorer/issue-222-section-8-weak-test-triage.md`](../../../docs/explorer/issue-222-section-8-weak-test-triage.md) | **§8.6** weak-test SKIP vs FOLLOW-UP decisions |
| Branches `205-investigation-main`, `221-streamlit-custom-map-component-spike` | Older detail: `issue-205-perf-reference.md`, `issue-205-investigation-backlog.md`, `issue-221-map-component-spike.md` — `git show origin/<branch>:docs/explorer/...` |

**Already done (keep out of checklist):** Leaflet export HTML cache — `LEAFLET_EXPORT_HTML_CACHE_KEY` LRU.

### 8.0 Prior art — mine before re-measuring (#205, #221, #222) — **done (2026-05-20)**

**Output:** [`docs/explorer/issue-222-section-8-prior-art.md`](../../../docs/explorer/issue-222-section-8-prior-art.md) (carry-forward table at bottom).

- [x] **#205 (Folium-era Explorer perf)** — issue comments (batches 1–4) + `205-investigation-main` docs:
  - [x] **Still relevant on `beta-next`:** W4 / #215; I4 first-paint + I5 `aggregate_perf_jsonl` / #217; Batch A fragment cache / #220; **I6** lesson; `All → Lifer → All` journey; `stage_ceilings.json` uses Leaflet stages.
  - [x] **Historical / superseded:** Folium stages; H1, W1, W2 product paths; Folium lazy/structured batches — **do not re-run**.
  - [x] **Headline Folium finding:** ~78% of overlay build was popup HTML; H2 → **#221 / #222** Leaflet component.
  - [x] **Gap → §8.4:** I1/I2 restored on `map.*.leaflet.payload` misses (`marker_count`, `popup_build_*`).
- [x] **#221 (component spike)** — `issue-221-map-component-spike.md` on `221-streamlit-custom-map-component-spike`:
  - [x] Spike JSONL table captured in prior-art doc (classic vs experimental ms).
  - [x] Production: four-map payload LRU + `payload_cache_hit` in perf `extra`.
  - [x] `popup_v1` + TS templates **shipped**.
- [x] **#222** — issue body + comments mined (parity, perf, subjective Cloud note).
- [x] **Post-Leaflet measured baseline** — §8.5: fixture + real `MyEBirdData.csv`; comments on #222; `issue-222-section-8-baseline.md` + plain summary.

**Next (human):** merge **PR #236** → `beta-next` → manual smoke → close **#222** for §8 scope (**§10** docs separate).

### 8.1 Test suite review (post–Folium / Leaflet refactor) — **done (2026-05-20)**

**Log:** [`docs/explorer/issue-222-section-8-prior-art.md`](../../../docs/explorer/issue-222-section-8-prior-art.md) §8.1.

- [x] Run full suite — **557 passed**, **4 skipped** (3 E2E: no Playwright Chromium; 1 perf: needs `--perf`).
- [x] **Orphaned coverage** — no deleted-module imports under `tests/`.
- [x] **Stale test intent** — Folium wording updated in 4 test/helper files.
- [x] **E2E / journeys** — selectors use `pebird-map-banner` / iframe scan (Leaflet). **I6** cluster+popup parity → §8.2.
- [x] **Gaps — Python map path** (partial):
  - [x] Leaflet payload LRU helpers — `tests/explorer/test_leaflet_payload_cache.py` (banner/legend/geojson on hit).
  - [x] Viewport / GeoJSON builders — existing `test_all_locations_viewport.py`, `test_*_locations_geojson.py`.
  - [x] Moved to **§8.1 nice-to-have** (discuss at §8.6).
- [x] **Gaps — component / export** — existing modules present; no new TS API churn requiring tests this pass.
  - [x] Moved **accuracy** audit to **§8.1 nice-to-have**.
- [x] **CI (Python)** — matches `pytest tests/` + 65% cov; E2E/perf opt-in per `tests/README.md`.

### 8.1 nice-to-have — §8.6 decisions (2026-05-20)

Not required to close **#222** for testing/perf. Use **Your call** when creating (or ignoring) GitHub issues.

| Item | §8.6 decision | Your call (pick one) | If you open an issue, use |
|------|---------------|----------------------|-------------------------|
| **Per-mode LRU session keys** | **FOLLOW-UP** | Create issue **/ Drop** / Do someday without issue | Draft **A** below |
| **`app_prep_map_ui.py` integration** | **Done** (#222 branch) | — | `tests/explorer/test_app_prep_map_ui_integration.py` |
| **Accuracy audit** | **Done on #222** | N/A — triage doc + 3 tightened tests | [`issue-222-section-8-weak-test-triage.md`](../../../docs/explorer/issue-222-section-8-weak-test-triage.md) |

E2E smokes and `streamlit_map_working` tests: **SKIP #222** (intentional light coverage) — see triage doc.

### 8.2 Client-side testing & performance (component / iframe) — **done (2026-05-20)**

**Log:** [`docs/explorer/issue-222-section-8-prior-art.md`](../../../docs/explorer/issue-222-section-8-prior-art.md) §8.2 · component [README.md](./README.md) “Client performance”.

**Testing**

- [x] **Inventory** — `mapComponentParsers.test.ts` added; `npm run test:ci` (7 tests); wired in CI (§8.3).
- [x] **Unit-level** — `parseViewportV1` extracted to `mapComponentParsers.ts` (more parsers later if useful).
- [x] **Integration** — **I6** ported: `test_all_locations_cluster_popup_parity` in `test_streamlit_map_e2e.py` (runs with `pytest -m e2e`; needs Playwright Chromium).
- [x] **Build contract** — `npm run build` green; commit updated `frontend/build/` after TS change.

**Performance (client)**

- [x] **Feasibility** — browser `performance.mark` possible; wiring to Python JSONL **not** worth v1 cost.
- [x] **Decision for #222:** **server** `EXPLORER_PERF` + Playwright `e2e.first_paint` are the supported metrics; no new client perf flag this batch.
- [x] **Re-measure post-cutover** — §8.5: fixture + real CSV; embed ~ms vs payload seconds documented in baseline + plain summary.

### 8.3 CI hygiene — JavaScript / TypeScript (parity with Python jobs)

**CI (`.github/workflows/tests.yml`):** job `all-locations-map-frontend` (*All locations map (frontend CI)*) runs after `npm ci`: `npm test -- --watchAll=false`, `npx tsc --noEmit`, `npm audit --omit=dev`, `npm run build`. Python CI still has Ruff, pip-audit, pytest+coverage, gitleaks separately.

- [x] **Gap analysis** — mirrored for the component frontend:
  - [x] **`npm audit --omit=dev`** — production/runtime deps only (0 vulns as of §8.3); aligns with pip-audit (fail on prod vulns). Full `npm audit` reports `react-scripts`/webpack-dev-server dev advisories — out of scope until CRA upgrade.
  - [x] **`npm test`** — Jest via `npm run test:ci` after `npm ci` (`CI=true` in Actions).
  - [x] **Typecheck** — explicit `npx tsc --noEmit` (+ `npm run typecheck` locally); CRA `build` still runs ESLint on compile.
  - [x] **Lockfile discipline** — `package-lock.json` committed; review npm lock updates like `requirements.txt` (no Dependabot job yet).
- [x] **Implement** — CI steps + `docs/development.md` + component README pre-push commands; `package.json` scripts `test:ci`, `typecheck`, `audit:prod`.
- [x] **Out of scope unless needed:** bundle-size budget, Lighthouse in CI, separate Node version matrix (Node 20 is enough for now).

### 8.4 Server-side performance instrumentation (#179 / #205)

- [x] **Audit** — `perf_instrumentation.py` unchanged; call sites in `app_prep_map_ui.py` / `app_data_loading.py` / tab fragments use Leaflet stages (`map.*.leaflet.payload`, `map.*.leaflet.component_embed`, `prep.leaflet_map_to_html_bytes`, `prep.map_context_prepare`, …). No Folium stage names in code.
- [x] **Restore I1/I2** — GeoJSON builders return `LeafletGeoJsonBuildMetrics`; merged into perf `extra` on payload **misses** for all four maps (`explorer/core/leaflet_geojson_build_metrics.py`).
- [x] **Docs** — `docs/development.md` spinner narrative → Leaflet-first; perf section documents I1/I2 on payload spans; `aggregate_perf_jsonl.py` example updated for Leaflet stages.
- [x] **Payload cache** — `payload_cache_hit` already on `_perf_*` dicts; build metrics only on miss (zeros on empty family/species payloads).
- [x] **Tests** — `test_leaflet_geojson_build_metrics.py`; `test_map_perf_e2e.py` asserts `marker_count` on cold payload miss; existing perf/aggregate tests pass.
- [x] **Ceilings tune** — §8.5: fixture + real CSV runs passed existing `stage_ceilings.json`; no tighten needed yet.
- [x] **Optional Folium vs Leaflet table** — §8.5: narrative in `issue-222-section-8-baseline.md`, plain summary, #222 comments (not production targets).

### 8.5 Capture & document metrics (for future regressions)

- [x] **Documented journey** — `./scripts/run_post_leaflet_perf_baseline.sh` (Playwright `test_map_perf_e2e` + `EXPLORER_PERF_LOG_FILE`). Covers **All** + **Lifer** on fixture; Species/Family manual steps in [`docs/explorer/issue-222-section-8-baseline.md`](../../../docs/explorer/issue-222-section-8-baseline.md).
- [x] **Archive** — `benchmarks/map_perf/snapshots/post-leaflet-fixture-r1.jsonl` + dated snapshot via `snapshot_explorer_perf_log.py` (gitignored).
- [x] **Summary table** — `issue-222-section-8-baseline.md`; posted to #222 (fixture + real CSV + plain summary comments).
- [x] **Ceilings** — unchanged after fixture run (all stages within `stage_ceilings.json`; tune on real CSV if needed).
- [x] **Regression checklist** — optional perf note added (fixture journey + manual Species/Family).

### 8.6 Close-out for §8 — **done on branch (2026-05-20); close #222 after PR #236 merge**

**Remaining for you:** merge **PR #236**, manual smoke, then close GitHub **#222** for §8 scope. **§10** full doc pass stays open.

- [x] **§8.1 nice-to-have** — decisions table above; accuracy audit closed; LRU + prep integration → optional follow-up drafts (not #222 blockers).
- [x] **§8.0–§8.5** — all substantive items done or documented (prior-art, baseline, plain summary, triage, CI, I1/I2, ceilings unchanged).
- [x] **Tests / Folium wording** — §8.1: no orphaned deleted-module imports; Folium wording cleaned in tests/helpers; shared HTML builder tests kept on purpose.
- [x] **§8 checklist** — this file updated; stale “Next: §8.3” lines removed.
- [x] **PR opened** — [#236](https://github.com/jimchurches/myebirdstuff/pull/236) (`222-test-performance-review` → `beta-next`).
- [x] **#222 close-out comment posted** (2026-05-20) — §8 summary + links; issue stays open until merge + smoke.

**After PR #236 merge — close #222 with (short):**  
“§8 testing/perf on `beta-next` (§8.0–§8.6). See issue comments + `docs/explorer/issue-222-plain-summary.md`. §10 docs tracked in component TODO §10.”

---

### §8 follow-up issues (optional backlog — create, drop, or park)

Copy a draft into a **new GitHub issue** only if you want it tracked. Otherwise check **Drop** and forget.

| ID | Drop? | Priority hint | Title |
|----|-------|---------------|-------|
| **A** | ☑ | Low — pattern exists for All locations | Done — parameterized `test_leaflet_payload_cache.py` |
| **B** | ☐ | Medium — catches prep regressions | Integration tests for map prep spinners and payload cache invalidation |
| **C** | ☑ | Low — perf only | Done — `test_map_perf_fixture_journey_species_and_family_payload_stages` |
| **D** | ☑ | Low — docs/clarity | Renamed → `leaflet_payload_cache_key` in `app_caches.py` |
| **E** | ☐ | Very low | Upgrade Create React App / address dev-only `npm audit` noise |

#### Draft A — Per-mode Leaflet payload LRU tests ✅

**Shipped:** `tests/explorer/test_leaflet_payload_cache.py` — parameterized all / lifer / species / family session keys; hit restores mode fields (`framing_pairs`, `pin_roles`, `highlight_framed`, …); LRU eviction + MRU tests per key.

---

#### Draft B — `app_prep_map_ui` integration tests ✅

**Problem:** Map prep (spinners, mode switch, payload cache miss vs hit) is only covered indirectly by E2E and unit GeoJSON builders.

**Shipped (#222 branch):**

- `apply_dataset_signature_for_map_caches()` — signature change clears Leaflet LRU + popup/export caches; unchanged signature preserves LRU.
- Revision-extra / cluster toggle → distinct payload cache keys (miss on toggle).
- `render_prep_spinner_and_map_tab` stubbed path: `MAP_PREP_SPINNER_TEXT` + `TAB_PREP_SPINNER_TEXT`; `payload_cache_hit` false → true on second All-locations prep with same inputs.
- `EXPLORER_PERF` off: prep path still completes.

**Tests:** `tests/explorer/test_app_prep_map_ui_integration.py` (shared Streamlit stub: `st.spinner`, `st.empty`, sidebar context).

**References:** `app_prep_map_ui.py`, `perf_instrumentation.py`, §8.4 I1/I2 extras.

---

#### Draft C — Species / Family automated perf journey ✅

**Shipped:**

- `test_map_perf_fixture_journey_species_and_family_payload_stages` — Species + Family map modes; asserts `map.species_leaflet.payload` / `map.family_leaflet.payload` cold misses in JSONL.
- `e2e_support.choose_first_recorded_family` (sidebar Family selectbox); `choose_species_by_common_name` helper for future journey tests (searchbox is Base Web combobox).
- `stage_ceilings.json` — species/family payload + embed stages (loose caps).
- `./scripts/run_post_leaflet_perf_baseline.sh` runs both perf E2E tests.

---

#### Draft D — `leaflet_payload_cache_key` (renamed from `static_map_cache_key`) ✅

**Shipped:** `leaflet_payload_cache_key` in `app_caches.py` — stable tuple for Leaflet GeoJSON payload LRU (view, filters, species/GPS toggles); paired with `revision_extra` in `app_prep_map_ui`.

---

#### Draft E — Frontend toolchain (CRA)

**Problem:** Full `npm audit` reports dev-toolchain advisories (`react-scripts` / `webpack-dev-server`). CI uses `npm audit --omit=dev` only (0 prod vulns as of §8.3).

**Done when:** Planned upgrade or migration; not urgent for Explorer users.

---

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

*Last updated: May 2026 — branch **`222-test-performance-review`** (§8.0–§8.2 done; next §8.3).*

### Shipped on this branch

- **§13** — Species payload LRU: banner/legend on hit; empty awaiting-selection payload cached.
- **§14** — Family payload LRU: empty payloads; composition + banner/legend only on cache miss.
- **§15** — All-locations + lifer: same LRU helper + banner/legend on hit (four-map contract at top of this file).
- **§17 export** — Lifer export popup HTML matches live map (no `Visited:` section label).

### PR smoke (after merge to `beta-next`)

- Map tab: switch all four **Map view** modes; repeat visit same mode — no unnecessary spinner from banner/geojson rebuild when inputs unchanged.
- Species: no species selected → repeat rerun; family: no family selected → repeat rerun (empty map cached).
- Export map HTML: open exported file; lifer pin popup — no `Visited:` label above species lines.

### Recommended next work (**#222** open until §8 merge + smoke)

1. **§8** — merge **PR #236**; manual smoke per regression checklist.
2. Close **#222** for §8 scope after merge + smoke (§10 not required for §8 close).
3. **§10** — documentation pass (Folium → Leaflet architecture), can follow §8 close.

**Recover lost §17 detail:** `git show bdfa70f1^:explorer/components/all_locations_map/TODO.md` (section “## 15. Popup typography…” before Folium-removal commit collapsed it; current **§15** is payload cache).
