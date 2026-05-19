# Issue #222 — §8.5 post-Leaflet perf baseline

**Plain-language summary:** [`issue-222-plain-summary.md`](issue-222-plain-summary.md)

**Recorded:** 2026-05-20 · **Branch:** `222-test-performance-review`  
**Dataset:** `tests/fixtures/ebird_integration_fixture.csv` (150 rows, 15 locations, 114 species)  
**Journey:** Playwright `test_map_perf_fixture_journey` — cold **All locations** → **Lifer locations** → warm **All locations** (return).

Raw JSONL archives are **gitignored** under `benchmarks/map_perf/snapshots/`. Reproduce locally:

```bash
./scripts/run_post_leaflet_perf_baseline.sh
```

**Real export (recommended for scale):** copy your file to gitignored `tests/fixtures/MyEBirdData.csv`, then:

```bash
./scripts/run_post_leaflet_perf_baseline.sh --real
```

Or any path: `./scripts/run_post_leaflet_perf_baseline.sh /path/to/MyEBirdData.csv`

---

## Real CSV journey — `tests/fixtures/MyEBirdData.csv` (2026-05-20)

**Shape:** 46,178 rows · 5,594 locations · 886 species · 7,462 checklists  
**Journey:** same Playwright script (cold All → Lifer → warm All).

| Stage | Session | `payload_cache_hit` | `elapsed_ms` | Notes |
|-------|---------|---------------------|--------------|--------|
| `e2e.first_paint` | cold | — | **19,448** | User-visible banner; vs Folium-era ~25 s on similar scale |
| `taxonomy.cached_species_url_fn` | cold | — | **4,809** | First-run taxonomy URL cache |
| `prep.map_context_prepare` | cold | — | **1,269** | |
| `map.all_locations_leaflet.payload` | cold | **false** | **5,805** | 5,594 pins; `popup_build_total_ms` ≈ **5,605** |
| `map.all_locations_leaflet.component_embed` | cold | — | **29** | Python span (client cluster/paint extra) |
| `map.lifer_leaflet.payload` | warm | **false** | **9,251** | 338 lifer pins |
| `map.all_locations_leaflet.payload` | warm | **true** | **0.1** | LRU hit returning to All |
| `map.all_locations_leaflet.component_embed` | warm | — | **28** | |

Archive: `benchmarks/map_perf/snapshots/post-leaflet-real-r1.jsonl` (gitignored).

**Folium comparison (#205, same ballpark dataset):** `prep.build_species_overlay_map` ~3.7 s with ~78% popup HTML; Leaflet cold payload ~5.8 s building structured `popup_v1` for every pin — different work, but same order of magnitude. Folium `prep.map_iframe_embed` ~6.9 s is **not** comparable to Leaflet `component_embed` (~29 ms Python); user time is closer to `e2e.first_paint`.

---

## Fixture journey — representative medians (single run, macOS dev)

Absolute milliseconds vary by machine; use **relative** comparisons and **cache hit** flags for regressions.

| Stage | Session | `payload_cache_hit` | `elapsed_ms` | Notes |
|-------|---------|---------------------|--------------|--------|
| `e2e.first_paint` | cold | — | **6305** | Browser banner visible; includes cold taxonomy URL cache (~5s on first run) |
| `map.all_locations_leaflet.payload` | cold | **false** | **19** | 15 pins; `popup_build_total_ms` ≈ 14 |
| `map.all_locations_leaflet.component_embed` | cold | — | **1** | Python embed span only (not full iframe paint) |
| `map.lifer_leaflet.payload` | warm | **false** | **292** | First lifer build; 15 pins |
| `map.lifer_leaflet.component_embed` | warm | — | **1** | |
| `map.all_locations_leaflet.payload` | warm | **true** | **0.02** | LRU hit on return to All |
| `map.all_locations_leaflet.component_embed` | warm | — | **0.5** | |

**I1/I2 on payload miss (All locations, cold):** `marker_count=15`, `popup_build_count=15`, `popup_build_total_ms≈14`.

---

## Folium-era context (#205 — do not use as Leaflet targets)

Historical real CSV (~5.7k pins), cold `All → Lifer → All`:

| Folium stage | ~median | Leaflet analogue |
|--------------|---------|------------------|
| `e2e.first_paint` | ~25 s | `e2e.first_paint` |
| `prep.build_species_overlay_map` | ~3.7 s | `map.*.leaflet.payload` (miss) |
| `prep.map_iframe_embed` | ~6.9 s | *removed* — embed span ~1 ms; client paint not in Python JSONL |

Fixture is **tiny**; use it for CI guardrails and cache-hit behaviour, not production scale.

---

## Species / Family map modes

Automated perf journey today covers **All locations** + **Lifer locations** only. For **Species locations** and **Family locations**, run manually with `EXPLORER_PERF=1` and `EXPLORER_PERF_LOG_FILE`, then:

```bash
python scripts/snapshot_explorer_perf_log.py /path/to/perf.jsonl --label post-leaflet-species-manual
python scripts/aggregate_perf_jsonl.py benchmarks/map_perf/snapshots \
  --glob 'post-leaflet-*.jsonl' \
  --stage map.species_leaflet.payload \
  --stage map.family_leaflet.payload \
  --extra-key payload_cache_hit --extra-key marker_count --extra-key popup_build_total_ms
```

---

## GitHub #222 comment (paste-ready)

```markdown
### §8.5 — Post-Leaflet perf baseline (fixture)

**Journey:** cold All → Lifer → warm All (`pytest …/test_map_perf_e2e.py --perf`).

| Stage | Cache hit | ms (representative) |
|-------|-----------|---------------------|
| `e2e.first_paint` | — | ~6300 (fixture; cold taxonomy dominates) |
| `map.all_locations_leaflet.payload` | miss | ~19 |
| `map.all_locations_leaflet.payload` | **hit** | **~0.02** |
| `map.lifer_leaflet.payload` | miss | ~292 |
| `map.*.leaflet.component_embed` | — | ~1 (Python span) |

I1/I2 on cold All payload: 15 markers, `popup_build_total_ms` ~14 ms.

Details: `docs/explorer/issue-222-section-8-baseline.md`. Species/Family: manual perf run documented there.

Folium-era ~25 s first paint / ~7 s embed on real CSV — narrative only; see `docs/explorer/issue-222-section-8-prior-art.md`.
```
