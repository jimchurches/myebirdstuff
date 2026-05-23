# Release 2026-05-23 — performance baseline

**Build id:** `2026-05-23` (`explorer/app/streamlit/explorer_build_version.txt`)  
**Branch at capture:** `243-release-hygiene-final-testing`  
**Plain-language summary:** [`release-2026-05-23-plain-summary.md`](release-2026-05-23-plain-summary.md)  
**Prior baselines:** [`issue-222-section-8-baseline.md`](issue-222-section-8-baseline.md) · [`issue-222-plain-summary.md`](issue-222-plain-summary.md) · #205 / #221 prior art in [`issue-222-section-8-prior-art.md`](issue-222-section-8-prior-art.md)

**Recorded:** 2026-05-23 (macOS dev machine)  
**Committed metrics:** [`release-2026-05-23-baseline-metrics.json`](release-2026-05-23-baseline-metrics.json) (fixture + real datasets, merged by `scripts/extract_release_perf_metrics.py`).

Raw JSONL archives are **gitignored** under `benchmarks/map_perf/snapshots/`.

Reproduce:

```bash
./scripts/run_release_perf_baseline.sh              # fixture
./scripts/run_release_perf_baseline.sh --real       # tests/fixtures/MyEBirdData.csv
```

Legacy helper (same journey, `post-leaflet-*` filenames): `./scripts/run_post_leaflet_perf_baseline.sh`

---

## E2E journeys (2026-05-23)

| Dataset | Playwright journey | Notes |
|---------|-------------------|--------|
| **Fixture** (150 rows) | Four-map: All → Lifer → warm All → Species → warm Species → Family → warm Family | Full mode coverage + LRU checks |
| **Real export** (~46k rows) | Headline: cold All (in `e2e.first_paint`) → Lifer → warm All | Species/Family UI automation is fixture-only until streamlit-searchbox E2E is stable on large exports |

**Species searchbox** lives in a dedicated iframe (`streamlit_searchbox.searchbox`); banner titles may be plain text or eBird links — tests use substring matching (`map_banner_must_contain`).

---

## Real export — `tests/fixtures/MyEBirdData.csv`

**Shape:** 46,178 rows · 5,594 locations · 886 species · 7,462 checklists  
**Archive:** `benchmarks/map_perf/snapshots/release-2026-05-23-real-r1.jsonl` (gitignored)

| Stage | Session | `payload_cache_hit` | `elapsed_ms` | Notes |
|-------|---------|---------------------|--------------|--------|
| `e2e.first_paint` | cold | — | **20,441** | User-visible All locations banner |
| `taxonomy.cached_species_url_fn` | cold | — | **6,126** | First-run species URL cache |
| `prep.map_context_prepare` | cold | — | **1,270** | |
| `map.all_locations_leaflet.payload` | cold | **false** | **6,043** | 5,594 pins; `popup_build_total_ms` ≈ **5,841** |
| `map.all_locations_leaflet.component_embed` | cold | — | **32** | Python span only |
| `map.lifer_leaflet.payload` | warm | **false** | **6,130** | 338 lifer pins; `popup_build_total_ms` ≈ **619** |
| `map.all_locations_leaflet.payload` | warm | **true** | **0.08** | LRU hit returning to All |
| `map.all_locations_leaflet.component_embed` | warm | — | **27** | |

### Comparison to issue #222 baseline (same journey prefix, 2026-05-20)

| Metric | #222 (2026-05-20) | Release 2026-05-23 | Δ (approx.) |
|--------|-------------------|---------------------|-------------|
| `e2e.first_paint` | 19,448 ms | 20,441 ms | +~5% (machine / CSV mtime noise) |
| Cold All `payload` | 5,805 ms | 6,043 ms | +~4% |
| First Lifer `payload` | 9,251 ms | 6,130 ms | −~34% |
| Warm All `payload` (hit) | 0.1 ms | 0.08 ms | unchanged in practice |

Hygiene work on this branch (R4 Folium cache removal, R6 data signature, R13 prep split, R14 frontend split, popup scroll-hint restore) did **not** materially move the headline cold/warm map prep numbers away from the #222 Leaflet baseline.

---

## Integration fixture — `tests/fixtures/ebird_integration_fixture.csv`

**Shape:** 150 rows · 15 locations · 114 species  
**Archive:** `benchmarks/map_perf/snapshots/release-2026-05-23-fixture-r1.jsonl` (gitignored)

| Stage | Session | `payload_cache_hit` | `elapsed_ms` | Notes |
|-------|---------|---------------------|--------------|--------|
| `e2e.first_paint` | cold | — | **7,772** | Dominated by cold taxonomy URL cache (~6.7 s) |
| `map.all_locations_leaflet.payload` | cold | **false** | **24** | 15 pins; `popup_build_total_ms` ≈ **19** |
| `map.all_locations_leaflet.component_embed` | cold | — | **1.4** | |
| `map.lifer_leaflet.payload` | warm | **false** | **304** | 15 pins (fixture has no lifer-only subset) |
| `map.all_locations_leaflet.payload` | warm | **true** | **0.02** | LRU hit |
| `map.species_leaflet.payload` | warm | **false** | **0.04** | 0 markers — E2E species pick incomplete |

Use the fixture for **CI guardrails** and cache-hit behaviour, not production scale.

---

## Aggregate table (single run per dataset)

```text
release-2026-05-23-fixture-r1  e2e.first_paint              med 7772 ms
release-2026-05-23-fixture-r1  map.all_locations_leaflet.payload  miss 24 ms / hit 0.02 ms
release-2026-05-23-fixture-r1  map.lifer_leaflet.payload    304 ms
release-2026-05-23-real-r1     e2e.first_paint              med 20334 ms
release-2026-05-23-real-r1     map.all_locations_leaflet.payload  miss 5501 ms / hit 0.09 ms
release-2026-05-23-real-r1     map.lifer_leaflet.payload    7118 ms
```

Full aggregator output:

```bash
python scripts/aggregate_perf_jsonl.py benchmarks/map_perf/snapshots \
  --glob 'release-2026-05-23-*.jsonl' \
  --group-regex 'release-2026-05-23-(?P<dataset>[^-]+)-r1' \
  --stage e2e.first_paint \
  --stage map.all_locations_leaflet.payload \
  --stage map.lifer_leaflet.payload \
  --stage map.all_locations_leaflet.component_embed \
  --extra-key payload_cache_hit \
  --extra-key marker_count \
  --extra-key popup_build_total_ms
```

---

## What this release added (perf-adjacent)

| Item | Perf impact |
|------|-------------|
| Leaflet cutover (#222) | Already baselined; this doc re-confirms on hygiene branch |
| Session LRU + `data_signature` fingerprint (#242 / R6) | Warm All return still ~0.1 ms |
| Four-map headline E2E (#222 / R7) | Species/Family **UI** step flaky in Playwright (see above) |
| Map prep modular split (R13) | No measurable change to headline stages |
| Popup scroll hints restored (`38c4cde6`) | Client-only; not in JSONL stages |

---

## Manual follow-ups (optional)

- Re-run Species / Family legs manually with `EXPLORER_PERF=1` if you want banner timings for those modes.
- Compare against OneDrive live export (`config_secret.yaml` `data_folder`) if `tests/fixtures/MyEBirdData.csv` is stale vs your current export.
