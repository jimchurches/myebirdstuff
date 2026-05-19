# Issue #222 — §8 prior art (#205, #221, #222)

**Purpose:** Consolidated mining of exploratory perf/testing work so §8.1–§8.6 do not repeat dropped experiments or Folium-only protocols.  
**Recorded:** 2026-05-20 · **Branch:** `222-test-performance-review`  
**Living checklist:** [`explorer/components/all_locations_map/TODO.md`](../../explorer/components/all_locations_map/TODO.md) §8

---

## Architecture (current production)

| Layer | Responsibility |
|-------|----------------|
| **Python** (`app_prep_map_ui.py`, `explorer/core/*_geojson.py`) | Working set, GeoJSON + `popup_v1` (etc.), banner/legend HTML, payload LRU, `revision` |
| **Streamlit** | `declare_component` → committed `frontend/build` |
| **Client** (`AllLocationsMap.tsx`) | Leaflet, MarkerCluster, popup templates, viewport |

**Perf visibility today:** `EXPLORER_PERF` + Playwright `e2e.first_paint` see **server** stages; iframe parse/cluster/paint is **not** instrumented unless we add it (§8.2).

---

## #205 — Folium-era Explorer performance (exploratory)

**Issue:** [#205](https://github.com/jimchurches/myebirdstuff/issues/205) · **Branch (reference):** `205-investigation-main`  
**In-repo docs (not on `beta-next`):** `docs/explorer/issue-205-perf-reference.md`, `issue-205-investigation-backlog.md`, `issue-205-w2-lite-ab-results.md` — use `git show origin/205-investigation-main:docs/explorer/...` or GitHub.

### Shipped to `beta-next` (still use)

| Item | PR/issue | Notes |
|------|----------|--------|
| **W4** map LRU cache-key fix | #215 | `prep.map_cache_hit` / miss; All→Lifer→All should get hits on return |
| **I4** E2E first-paint | #217 | `measure_first_paint_ms` → `e2e.first_paint` in JSONL |
| **I5** JSONL aggregator | #217 | `scripts/aggregate_perf_jsonl.py` + unit tests |
| **Batch A** popup fragment cache | #220 | `POPUP_FRAGMENT_CACHE_KEY` — still in session wiring; reduces redundant HTML fragment work on popup cache misses |

### Dropped or not promoted (do not re-run as product work)

| Experiment | Outcome | Lesson |
|------------|---------|--------|
| **H1** `EXPLORER_MAP_EMBED=components_html` | **Dropped** | #190-style popup detach on All-locations **cluster + Marker** DOM |
| **W1** `@st.fragment` on map embed | **Dropped** | Off-map `st.rerun()` still runs full script; ~0 ms embed savings |
| **W2** lite popups | **Measurement only** | ~40% faster overlay build on fixture; **UX rejected** — keep rich popups |
| **Batch B** lazy Folium popups | Not merged | Often **larger** `html_bytes_len` (HTML still in JSON) |
| **Batch C** structured Folium `al1` | Not merged as Folium path | Led to **#221 / #222** Leaflet + `popup_v1` instead |

### Headline Folium numbers (historical — compare narrative only)

**Real CSV (~46k rows, ~5.7k pins), cold `All → Lifer → All` (issue comments, batch 4):**

- `e2e.first_paint` ~**25 s** (user-visible cold load)
- `prep.map_iframe_embed` ~**6.9 s** × 3 events per journey (dominant warm cost)
- `prep.build_species_overlay_map` ~**3.7 s** per cache miss; **~78%** was `popup_build_total_ms` (I1/I2)

**Fixture:** much smaller; use for CI guardrails only.

### Folium → Leaflet stage mapping (for #222 comments)

| Folium-era stage | Leaflet-era stage (production) |
|------------------|--------------------------------|
| `prep.build_species_overlay_map` | `map.all_locations_leaflet.payload` (and lifer/species/family analogues) |
| `prep.folium_map_to_html_bytes` | *removed* — export uses `prep.leaflet_map_to_html_bytes` |
| `prep.map_iframe_embed` | `map.*.leaflet.component_embed` |
| `map.experimental.payload` | → `map.all_locations_leaflet.payload` |
| `map.experimental.component_embed` | → `map.all_locations_leaflet.component_embed` |

**Ceilings:** [`benchmarks/map_perf/stage_ceilings.json`](../../benchmarks/map_perf/stage_ceilings.json) already uses Leaflet stage names.

### Gap after Folium removal (→ §8.4)

- **I1/I2 `metrics_sink`** (`popup_build_total_ms`, `marker_count` on overlay build) lived on **`prep.build_species_overlay_map`**, which no longer exists. `aggregate_perf_jsonl` still supports those extra keys, but **current JSONL will not emit them** unless we add counters to GeoJSON builders or `build_all_locations_geojson_payload`.
- **I6** Playwright test `test_map_embed_all_locations_cluster_popup_parity_screenshot` was on `205-investigation-main`; **not present** on `beta-next` today — only `test_map_perf_fixture_journey_emits_prep_stages_within_loose_ceiling` (→ §8.2).

### Local archives (gitignored)

`benchmarks/map_perf/snapshots/issue-205-batch-{1,3,4}/`, `issue-205-w2/`, etc. — regenerate with `EXPLORER_PERF_LOG_FILE` + `snapshot_explorer_perf_log.py` if needed.

---

## #221 — Custom component spike

**Issue:** [#221](https://github.com/jimchurches/myebirdstuff/issues/221) · **Branch:** `221-streamlit-custom-map-component-spike` (do not delete until #222 closed)  
**Spike log:** `git show origin/221-streamlit-custom-map-component-spike:docs/explorer/issue-221-map-component-spike.md`

### Validated (now #222 production)

- Streamlit custom component + Leaflet + structured **`popup_v1`** + client TS templates
- **`revision`** — client skips marker rebuild when unchanged
- Session **payload cache** — production: four-map Leaflet LRU (§13–§15 in component TODO); spike used `EXPERIMENTAL_ALL_LOCATIONS_PAYLOAD_CACHE_KEY`
- **`payload_cache_hit`** in perf `extra` on `map.all_locations_leaflet.payload` spans

### Spike perf table (one session, ~5.7k pins — illustrative)

| Path | Cold (approx.) |
|------|----------------|
| Classic: overlay + popup HTML | ~7.1 s (`popup_build` ~6.5 s) |
| Classic: Folium serialize | ~3.3 s |
| Classic: iframe embed | ~6.9 s |
| Experimental: payload | ~1.6 s (compact popups) → **~6 s** after full visit-list parity |
| Experimental: component embed | **~14–25 ms** (Python span only) |

**Interpretation:** Server-side win vs Folium HTML + `st_folium`; **not** full browser time-to-pixels. After visit parity, warm Folium could reuse HTML while experimental still rebuilt payload until cache landed — **production LRU addresses that**.

### Deferred from spike (optional later)

- Lazy popup sections on open (without Streamlit rerun per click)
- Cluster icon tier parity vs old Folium
- Client-side perf marks (§8.2)

---

## #222 — Production cutover

**Issue:** [#222](https://github.com/jimchurches/myebirdstuff/issues/222)

### Acceptance themes (from issue + comments)

- Four maps on Leaflet; Folium stack removed (#232)
- Parity: popups, banners, sidebar, colours, viewport, export HTML
- Perf: warm revisit when inputs unchanged; instrumentation preserved/improved
- Tests: same **journeys**, updated selectors/DOM

### Subjective note (not a benchmark)

Streamlit Cloud: return to **All locations** on `beta-next` felt ~**33% faster** than `main` (repeated observation; resource contention possible). **Needs Leaflet-era JSONL** for durable record (§8.5).

### Post-Leaflet baseline status

| Item | Status |
|------|--------|
| `stage_ceilings.json` Leaflet stages | **Done** (committed) |
| Median table on #222 (fixture + optional real CSV) | **Not done** → §8.5 |
| Folium vs Leaflet comparison comment | **Optional** one-time in §8.5 |

**Reproduce command (fixture):**

```bash
EXPLORER_E2E_PERF_JSONL_ARCHIVE="$PWD/benchmarks/map_perf/snapshots/post-leaflet-fixture-r1.jsonl" \
  pytest tests/explorer/test_map_perf_e2e.py::test_map_perf_fixture_journey_emits_prep_stages_within_loose_ceiling --perf -v
python scripts/aggregate_perf_jsonl.py benchmarks/map_perf/snapshots \
  --glob 'post-leaflet-*.jsonl' \
  --stage map.all_locations_leaflet.payload \
  --stage map.all_locations_leaflet.component_embed \
  --stage map.lifer_leaflet.component_embed \
  --stage prep.map_context_prepare \
  --stage e2e.first_paint \
  --extra-key payload_cache_hit \
  --extra-key banner_ms
```

---

## §8.1 test suite review (2026-05-20)

**Run:** `pytest tests/ -v` on `222-test-performance-review` → **557 passed**, **4 skipped** (~21 s).

| Skip | Reason |
|------|--------|
| `test_map_perf_e2e.py` (1) | Opt-in `@pytest.mark.perf` (needs `--perf`) |
| `test_streamlit_map_e2e.py` (2), `test_streamlit_journeys_e2e.py` (1) | Playwright Chromium not installed locally (`python -m playwright install chromium`) |

**Orphans:** No `folium`, `map_controller`, `family_map_folium`, or `map_render_cache` imports under `tests/`. Removed test modules stay deleted (§12).

**Stale wording fixed:** `e2e_support.py`, `test_streamlit_ui_helpers.py`, `test_all_locations_map_component.py`, `colour_scheme_test_utils.py`.

**E2E / Leaflet:** Map smoke/journey modules already target `pebird-map-banner` in component iframes (`e2e_support.wait_for_pebird_map_markup`). **I6** cluster+popup parity test from #205 investigation **not** on this branch → §8.2.

**Added tests:** `tests/explorer/test_leaflet_payload_cache.py` — LRU hit restores `revision` / `geojson` / `banner_html` / `legend_html`; eviction + MRU.

**Existing coverage (no change needed):** `test_all_locations_viewport.py`, `test_lifer_locations_geojson.py`, `test_species_locations_geojson.py`, `test_family_locations_geojson.py`, popup/export/component tests.

**Gaps (defer):** Parameterized LRU tests per session key (lifer/species/family); full `app_prep_map_ui` integration with stubbed prep; tighten weak assertions audit.

**CI (Python):** `.github/workflows/tests.yml` runs `pytest tests/ -v --cov=explorer --cov-fail-under=65` (no `-m e2e`, no `--perf`). E2E/perf documented in `tests/README.md` + `docs/development.md`.

---

## §8.2 client-side testing & performance (2026-05-20)

**Testing**

- Extracted `parseViewportV1` → `frontend/src/mapComponentParsers.ts` + **7** Jest tests (`npm test -- --watchAll=false`).
- Ported **I6**: `tests/explorer/test_streamlit_map_e2e.py::test_all_locations_cluster_popup_parity` — cluster frame, Leaflet API popup open, content/tip + banner width asserts; optional screenshot under `benchmarks/map_perf/snapshots/issue-222-cluster-popup-parity/`.
- `tsconfig.json` excludes `*.test.ts(x)` from production `npm run build`.

**Client performance decision (for #222 close-out)**

| Approach | Verdict |
|----------|---------|
| `performance.mark` in iframe | Possible for dev profiling; **not** wired to `EXPLORER_PERF` in v1 |
| React Profiler | Dev-only |
| **Supported metrics** | Python `EXPLORER_PERF` stages + Playwright `e2e.first_paint` (§8.5 baselines) |

**Deferred:** post-cutover embed vs payload comparison → §8.5.

---

## Carry-forward into §8.1–§8.6

| Section | Action from this doc |
|---------|----------------------|
| **8.1** | **Done** — see §8.1 block above |
| **8.2** | **Done** — see §8.2 block above |
| **8.3** | CI: `npm ci` → test, `tsc --noEmit`, `audit --omit=dev`, build; docs + `test:ci`/`typecheck`/`audit:prod` scripts |
| **8.4** | Rename stale docs (Folium spinners); consider **popup/geojson build metrics** to replace I1/I2; verify `payload_cache_hit` in journeys |
| **8.5** | Run reproduce block above; paste summary to #222; optional real CSV |
| **8.6** | Close §8 when checklist + issue comment done |

---

## References

- [#205](https://github.com/jimchurches/myebirdstuff/issues/205) · [#221](https://github.com/jimchurches/myebirdstuff/issues/221) · [#222](https://github.com/jimchurches/myebirdstuff/issues/222)
- [#179](https://github.com/jimchurches/myebirdstuff/issues/179) instrumentation · [#190](https://github.com/jimchurches/myebirdstuff/issues/190) popup regression history
- [`benchmarks/map_perf/README.md`](../../benchmarks/map_perf/README.md)
- [`docs/development.md`](../development.md) — Performance Instrumentation Guardrails
