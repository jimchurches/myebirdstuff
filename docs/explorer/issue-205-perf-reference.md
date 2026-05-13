# Issue #205 — perf reference snapshot (fixture E2E)

> **Parent:** [#205](https://github.com/jimchurches/myebirdstuff/issues/205)  
> **Purpose:** Factual **single-run** numbers to compare against on later work—not targets, not guarantees.  
> Timings are **machine-dependent**; use the same repro commands on your side for before/after.

| Field | Value |
| --- | --- |
| **Recorded** | 2026-05-12 |
| **Git** | `205-investigation-main` @ `65a6bc2` (includes Batch A fragment cache + popup models) |
| **Dataset** | Default E2E: `tests/fixtures/ebird_integration_fixture.csv` (not `EXPLORER_E2E_DATASET_CSV`) |
| **Journey** | `test_map_perf_fixture_journey_emits_prep_stages_within_loose_ceiling` — cold load, `e2e.first_paint`, All → Lifer → All |
| **Runs** | *n = 1* (illustrative only) |

## `aggregate_perf_jsonl` (text)

Command used:

```bash
python scripts/aggregate_perf_jsonl.py . \
  --glob '.perf-ref-issue-205.jsonl' \
  --stage prep.build_species_overlay_map \
  --stage prep.folium_map_to_html_bytes \
  --stage prep.map_iframe_embed \
  --stage prep.map_context_prepare \
  --stage e2e.first_paint \
  --extra-key marker_count \
  --extra-key popup_build_count \
  --extra-key popup_cache_hit_count \
  --extra-key popup_build_total_ms \
  --extra-key banner_ms \
  --extra-key goto_ms
```

Output (same machine as the capture below):

```
group                        stage                                n_runs   total_events    med_evt/run         med_ms         p95_ms         max_ms marker_count.med marker_count.max popup_build_count.med popup_build_count.max popup_cache_hit_count.med popup_cache_hit_count.max popup_build_total_ms.med popup_build_total_ms.max  banner_ms.med  banner_ms.max    goto_ms.med    goto_ms.max
---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
.perf-ref-issue-205.jsonl    e2e.first_paint                           1              1            1.0         6896.6         6896.6         6896.6              —              —              —              —              —              —              —              —         6896.6         6896.6          160.8          160.8
.perf-ref-issue-205.jsonl    prep.build_species_overlay_map              1              2            2.0           16.8           91.5           91.5           15.0           15.0           15.0           15.0            0.0            0.0            8.0           27.2              —              —              —              —
.perf-ref-issue-205.jsonl    prep.folium_map_to_html_bytes              1              2            2.0           12.1           13.3           13.3              —              —              —              —              —              —              —              —              —              —              —              —
.perf-ref-issue-205.jsonl    prep.map_context_prepare                  1              3            3.0           11.9           13.0           13.0              —              —              —              —              —              —              —              —              —              —              —              —
.perf-ref-issue-205.jsonl    prep.map_iframe_embed                     1              3            3.0           23.7           26.3           26.3              —              —              —              —              —              —              —              —              —              —              —              —              —
```

## Reproduce capture

From repo root (writes one JSONL next to cwd; adjust path as needed):

```bash
EXPLORER_E2E_PERF_JSONL_ARCHIVE="$PWD/.perf-ref-issue-205.jsonl" \
  python -m pytest tests/explorer/test_map_perf_e2e.py::test_map_perf_fixture_journey_emits_prep_stages_within_loose_ceiling --perf -v
```

Then point `aggregate_perf_jsonl` at the directory containing that file (see command above). Delete the JSONL after recording if you do not want a local artifact.

## Related references (elsewhere)

- W2 lite vs rich **fixture** A/B (different question than Batch A): [`issue-205-w2-lite-ab-results.md`](issue-205-w2-lite-ab-results.md)  
- Historical batch notes: comments on [#205](https://github.com/jimchurches/myebirdstuff/issues/205) (batch 4 baselines, etc.)
