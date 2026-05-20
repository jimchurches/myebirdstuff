# Issue #222 — Performance prior art (#205, #221)

**Plain-language summary:** [`issue-222-plain-summary.md`](issue-222-plain-summary.md)  
**Measured baselines & re-run:** [`issue-222-section-8-baseline.md`](issue-222-section-8-baseline.md)

**Purpose:** Historical context and interpretation for post-Leaflet performance numbers — what #205 and #221 measured, how Folium-era stages map to Leaflet stages, and what not to re-run.

---

## Architecture (production)

| Layer | Responsibility |
|-------|----------------|
| **Python** (`app_prep_map_ui.py`, `explorer/core/*_geojson.py`) | Working set, GeoJSON + `popup_v1` (etc.), banner/legend HTML, payload LRU, `revision` |
| **Streamlit** | `declare_component` → committed `frontend/build` |
| **Client** (`AllLocationsMap.tsx`) | Leaflet, MarkerCluster, popup templates, viewport |

**Perf visibility:** `EXPLORER_PERF` + Playwright `e2e.first_paint` capture **server** stages and user-visible banner timing. Iframe parse/cluster/paint is **not** in JSONL unless added deliberately — so a fast `component_embed` row does **not** mean the map finished drawing.

---

## #205 — Folium-era Explorer performance (historical)

**Issue:** [#205](https://github.com/jimchurches/myebirdstuff/issues/205) · **Reference branch:** `205-investigation-main`  
**Older in-repo docs:** `issue-205-perf-reference.md`, `issue-205-investigation-backlog.md` — `git show origin/205-investigation-main:docs/explorer/...`

### Still relevant on `beta-next`

| Item | Notes |
|------|--------|
| **W4** map cache-key fix (#215) | Warm **All → Lifer → All** should hit payload LRU |
| **I4** E2E first-paint | `e2e.first_paint` in JSONL |
| **I5** JSONL aggregator | `scripts/aggregate_perf_jsonl.py` |
| **Batch A** popup fragment cache (#220) | Less redundant HTML fragment work on popup cache misses |

### Dropped experiments (do not re-run as product work)

| Experiment | Outcome | Lesson |
|------------|---------|--------|
| **H1** `EXPLORER_MAP_EMBED=components_html` | Dropped | Popup detach on cluster + marker DOM |
| **W1** `@st.fragment` on map embed | Dropped | Off-map `st.rerun()` still full script |
| **W2** lite popups | Measurement only | Faster build; **rich popups rejected** |
| **Batch B** lazy Folium popups | Not merged | Often **larger** HTML in JSON |
| **Batch C** structured Folium `al1` | Not merged | Led to **#221 / #222** Leaflet + `popup_v1` |

### Headline Folium numbers (narrative comparison only)

**Real CSV (~46k rows, ~5.7k pins), cold `All → Lifer → All` (#205 batch 4):**

- `e2e.first_paint` ~**25 s** (user-visible cold load)
- `prep.map_iframe_embed` ~**6.9 s** × 3 per journey (dominant warm cost)
- `prep.build_species_overlay_map` ~**3.7 s** per cache miss; **~78%** was `popup_build_total_ms`

**Fixture:** much smaller — use for CI guardrails, not “feels fast on my life list.”

### Folium → Leaflet stage mapping

| Folium-era stage | Leaflet-era stage (production) |
|------------------|--------------------------------|
| `prep.build_species_overlay_map` | `map.all_locations_leaflet.payload` (and lifer/species/family analogues) |
| `prep.folium_map_to_html_bytes` | *removed* — export uses `prep.leaflet_map_to_html_bytes` |
| `prep.map_iframe_embed` | `map.*.leaflet.component_embed` |
| `map.experimental.payload` | `map.all_locations_leaflet.payload` |
| `map.experimental.component_embed` | `map.all_locations_leaflet.component_embed` |

**Ceilings:** [`benchmarks/map_perf/stage_ceilings.json`](../../benchmarks/map_perf/stage_ceilings.json) uses Leaflet stage names.

**Post-cutover payload metrics:** `marker_count`, `popup_build_count`, `popup_build_total_ms` on `map.*.leaflet.payload` **cache misses** (I1/I2 parity with Folium-era overlay build).

---

## #221 — Custom component spike (historical)

**Issue:** [#221](https://github.com/jimchurches/myebirdstuff/issues/221) · **Spike branch:** `221-streamlit-custom-map-component-spike`  
**Spike log:** `git show origin/221-streamlit-custom-map-component-spike:docs/explorer/issue-221-map-component-spike.md`

### Validated → shipped in #222

- Streamlit custom component + Leaflet + structured **`popup_v1`** + client TS templates
- **`revision`** — client skips marker rebuild when unchanged
- Session **payload cache** — four-map LRU (`*_LEAFLET_PAYLOAD_CACHE_KEY`); spike used `EXPERIMENTAL_ALL_LOCATIONS_PAYLOAD_CACHE_KEY`
- **`payload_cache_hit`** in perf `extra` on payload spans

### Spike perf table (one session, ~5.7k pins — illustrative)

| Path | Cold (approx.) |
|------|----------------|
| Classic: overlay + popup HTML | ~7.1 s (`popup_build` ~6.5 s) |
| Classic: Folium serialize | ~3.3 s |
| Classic: iframe embed | ~6.9 s |
| Experimental: payload | ~1.6 s (compact) → **~6 s** after full visit-list parity |
| Experimental: component embed | **~14–25 ms** (Python span only) |

**Interpretation:** Server-side win vs Folium HTML + `st_folium`; **not** full browser time-to-pixels. Production LRU gives warm payload ~0 ms when inputs unchanged.

---

## #222 — Post-cutover baselines

**Issue:** [#222](https://github.com/jimchurches/myebirdstuff/issues/222)

- Four maps on Leaflet; Folium stack removed
- Rich popups, banners, export HTML, instrumentation preserved on Leaflet stages
- **Subjective (not a benchmark):** return to **All locations** on `beta-next` felt ~33% faster than `main` on Streamlit Cloud (repeated observation)

**Recorded numbers:** [`issue-222-section-8-baseline.md`](issue-222-section-8-baseline.md) · re-run: `./scripts/run_post_leaflet_perf_baseline.sh` (fixture) or `--real` for local `MyEBirdData.csv`

**Reproduce (fixture archive + aggregate):**

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

## References

- [#205](https://github.com/jimchurches/myebirdstuff/issues/205) · [#221](https://github.com/jimchurches/myebirdstuff/issues/221) · [#222](https://github.com/jimchurches/myebirdstuff/issues/222)
- [#179](https://github.com/jimchurches/myebirdstuff/issues/179) instrumentation
- [`benchmarks/map_perf/README.md`](../../benchmarks/map_perf/README.md)
- [`docs/development.md`](../development.md) — Performance Instrumentation Guardrails
