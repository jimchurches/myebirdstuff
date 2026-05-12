# W2 — Lite map popups A/B (fixture dataset)

GitHub note: [comment on #205](https://github.com/jimchurches/myebirdstuff/issues/205#issuecomment-4427368612).

Parent: [#205](https://github.com/jimchurches/myebirdstuff/issues/205). **W2** adds `EXPLORER_MAP_LITE_POPUPS` (measurement / debug UX); product default stays rich popups.

## Protocol

| Item | Value |
| --- | --- |
| **When** | 2026-05-12 (local run) |
| **Dataset** | `tests/fixtures/ebird_integration_fixture.csv` (not `EXPLORER_E2E_DATASET_CSV`) |
| **Design** | 3 runs × 2 modes (`EXPLORER_MAP_LITE_POPUPS` off vs on in the Streamlit **child** only) |
| **Journey** | `test_map_perf_fixture_journey_emits_prep_stages_within_loose_ceiling` — cold load, record `e2e.first_paint`, **All locations → Lifer locations → All locations** |
| **Archive** | `benchmarks/map_perf/snapshots/issue-205-w2/w2-fixture-lite{0,1}-r{1,2,3}.jsonl` (directory is **gitignored**; re-capture locally to reproduce exact bytes) |

### Reproduce captures + table

```bash
mkdir -p benchmarks/map_perf/snapshots/issue-205-w2
for lite in 0 1; do for run in 1 2 3; do
  EXPLORER_E2E_PERF_JSONL_ARCHIVE="$PWD/benchmarks/map_perf/snapshots/issue-205-w2/w2-fixture-lite${lite}-r${run}.jsonl" \
  EXPLORER_E2E_MAP_LITE_POPUPS=$lite \
    python -m pytest tests/explorer/test_map_perf_e2e.py::test_map_perf_fixture_journey_emits_prep_stages_within_loose_ceiling --perf -v
done; done

python scripts/aggregate_perf_jsonl.py benchmarks/map_perf/snapshots/issue-205-w2 \
  --glob 'w2-fixture-lite*.jsonl' \
  --group-regex 'w2-fixture-lite(?P<lite>[01])-r\d+' \
  --stage prep.build_species_overlay_map \
  --stage prep.folium_map_to_html_bytes \
  --stage prep.map_iframe_embed \
  --stage e2e.first_paint \
  --extra-key marker_count \
  --extra-key popup_build_count \
  --extra-key popup_build_total_ms \
  --extra-key popup_cache_hit_count \
  --extra-key banner_ms \
  --extra-key goto_ms
```

`EXPLORER_E2E_MAP_LITE_POPUPS` is read by the perf Streamlit fixture (default `0`) so the child does not inherit a stray parent-shell `EXPLORER_MAP_LITE_POPUPS`.

## Aggregated results (`aggregate_perf_jsonl`, text output)

<!-- snapshot from 2026-05-12 local run -->

```
group                        stage                                n_runs   total_events    med_evt/run         med_ms         p95_ms         max_ms marker_count.med marker_count.max popup_build_count.med popup_build_count.max popup_cache_hit_count.med popup_cache_hit_count.max popup_build_total_ms.med popup_build_total_ms.max  banner_ms.med  banner_ms.max    goto_ms.med    goto_ms.max
---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
lite=0                       e2e.first_paint                           3              3            1.0         6149.2         6169.2         6169.2              —              —              —              —              —              —              —              —         6149.2         6169.2          109.7          110.1
lite=0                       prep.build_species_overlay_map              3              6            2.0           15.6           93.7           93.7           15.0           15.0           15.0           15.0            0.0            0.0            6.2           27.9              —              —              —              —
lite=0                       prep.folium_map_to_html_bytes              3              6            2.0           12.1           13.2           13.2              —              —              —              —              —              —              —              —              —              —              —              —
lite=0                       prep.map_iframe_embed                     3              9            3.0           24.7           26.2           26.2              —              —              —              —              —              —              —              —              —              —              —              —
lite=1                       e2e.first_paint                           3              3            1.0         6186.2         6202.3         6202.3              —              —              —              —              —              —              —              —         6186.2         6202.3          115.5          118.2
lite=1                       prep.build_species_overlay_map              3              6            2.0            9.3           81.0           81.0           15.0           15.0           15.0           15.0            0.0            0.0            0.1            0.1              —              —              —              —
lite=1                       prep.folium_map_to_html_bytes              3              6            2.0           11.4           13.5           13.5              —              —              —              —              —              —              —              —              —              —              —              —
lite=1                       prep.map_iframe_embed                     3              9            3.0           25.3           28.7           28.7              —              —              —              —              —              —              —              —              —              —              —              —
```

## Summary (fixture CSV)

- **`popup_build_total_ms`** (median over all `prep.build_species_overlay_map` samples): **~6.2 ms → ~0.1 ms** with lite on — confirms I1’s split: on this tiny map, almost all “popup work” is the rich HTML path.
- **`prep.build_species_overlay_map`** wall time: **~15.6 ms → ~9.3 ms** median — ~40% reduction on the fixture; **marker_count** unchanged (15), as expected.
- **`prep.folium_map_to_html_bytes`**: small drop (**~12.1 ms → ~11.4 ms** med) — consistent with less popup HTML in the document; swamped by noise on this scale.
- **`prep.map_iframe_embed`** and **`e2e.first_paint`**: **no meaningful change** on the integration fixture — cold load is dominated by other work; **real CSV** is still the right place to judge user-visible first paint.

**Conclusion:** Lite mode does what we instrumented for: it slashes popup assembly cost on the overlay build. Keep it **off by default**; use it for A/B and future trade-off discussion. Optional follow-up: repeat this protocol with `EXPLORER_E2E_DATASET_CSV` pointed at a large export (same 3×2 design) if we need wall-clock confirmation on production-shaped data.
