# Issue #205 — perf reference snapshot (fixture E2E)

> **Parent:** [#205](https://github.com/jimchurches/myebirdstuff/issues/205)  
> **Purpose:** Factual **single-run** numbers to compare against on later work—not targets, not guarantees.  
> Timings are **machine-dependent**; use the same repro commands on your side for before/after.

| Field | Value |
| --- | --- |
| **Recorded** | 2026-05-12 |
| **Git** | App snapshot: `65a6bc2` (Batch A). Reference doc committed as `05f6447` on `205-investigation-main`. |
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

---

## Batch A + B experimental track — summary and E2E (2026-05-13)

**Branch:** `205-investigation-main` (experimental; not the product default on `beta-next` / `main`).

**What changed (high level)**

| Item | Intent | Default in app |
| --- | --- | --- |
| **Batch A** — popup fragment cache + presentation models | Reuse visit-list / species-section / lifer-line HTML fragments on full `popup_html_cache` misses when row content is unchanged (same rich HTML as before). | On (session cache; no env flag). |
| **Batch B** — `EXPLORER_MAP_LAZY_POPUPS` | **All locations** only: tiny marker popup stubs; full HTML still built server-side and swapped in on Leaflet `popupopen`. Ignored when W2 lite popups are on. | Off (env / Streamlit secret). |

**Manual smoke (maintainer)**  
Popup behaviour looks correct after basic use; **no clear subjective win on “map loads faster”** on its own — useful mainly when combined with metrics and A/B on larger datasets.

### Automated lazy vs default (fixture E2E)

- **`test_map_perf_lazy_journey_tags_build_extra`** — runs **twice** per full `pytest tests/explorer/test_map_perf_e2e.py --perf` (child `EXPLORER_MAP_LAZY_POPUPS` **0** then **1**; **lite forced off** so lazy is not suppressed). Checks JSONL tags and loose ceilings.
- **W2 lite tests** force **`EXPLORER_MAP_LAZY_POPUPS=0`** in the child so lite A/B and lazy A/B stay isolated.
- **`prep.folium_map_to_html_bytes`** records **`extra.html_bytes_len`** (UTF-8 length of the rendered map HTML). Archive JSONL for lazy `0` vs `1`, then run `aggregate_perf_jsonl` with `--stage prep.folium_map_to_html_bytes --extra-key html_bytes_len` to compare payload size (primary objective stat for lazy popups; timing is secondary).

Archive loop (see module docstring in `tests/explorer/test_map_perf_e2e.py`).

### Full perf E2E suite (fixture CSV, default flags)

Recorded on **darwin**, **Python 3.12.3**, commit **`6f70a4b`** (count and wall time drift as tests are added; re-run locally for current numbers).

```bash
python -m pytest tests/explorer/test_map_perf_e2e.py --perf -v
```

**Result (2026-05-13 tooling):** **8 passed** in **≈ 110 s** wall time (includes W2 lite ×2, **lazy ×2**, embed rerun journey, two screenshot parity tests).

Child env unless overridden: default **lite off, lazy off**; W2 and lazy fixtures override one knob at a time.

### *n* = 1 JSONL aggregate (fixture journey only, lazy off / lite off)

Archive: `EXPLORER_E2E_PERF_JSONL_ARCHIVE=/tmp/issue-205-doc-e2e.jsonl` with  
`test_map_perf_fixture_journey_emits_prep_stages_within_loose_ceiling` only.

`aggregate_perf_jsonl` command:

```bash
python scripts/aggregate_perf_jsonl.py /tmp \
  --glob 'issue-205-doc-e2e.jsonl' \
  --stage prep.build_species_overlay_map \
  --stage prep.folium_map_to_html_bytes \
  --stage prep.map_iframe_embed \
  --stage prep.map_context_prepare \
  --stage e2e.first_paint \
  --extra-key marker_count \
  --extra-key popup_build_count \
  --extra-key popup_cache_hit_count \
  --extra-key popup_build_total_ms \
  --extra-key lite_map_popups \
  --extra-key lazy_map_popups \
  --extra-key banner_ms \
  --extra-key goto_ms \
  --extra-key html_bytes_len
```

(`html_bytes_len` is present on **`prep.folium_map_to_html_bytes`** from 2026-05-13; use it for lazy vs default payload comparisons.)

### Lazy vs default — **plain summary** (fixture, lazy fixes landed)

**Recorded:** 2026-05-13 · **Git:** `a6e2e46` · **Dataset:** `tests/fixtures/ebird_integration_fixture.csv` · **Journey:** `test_map_perf_lazy_journey_tags_build_extra` (automated; **lite off** each time).

**Important:** *one* pytest run per mode (**n = 1**). Timings and sizes are **machine-specific**; treat this as a **hint**, not a proof.

| Question | What the numbers said (this capture) |
| --- | --- |
| **Is the map HTML file smaller with lazy?** | **No here.** `prep.folium_map_to_html_bytes` **`html_bytes_len`** median was **~45.5 KB** (lazy **off**) vs **~51.7 KB** (lazy **on**). Lazy still ships **all** full popup HTML inside a **JSON blob** for the bridge, so total size can **go up** on small/medium datasets. |
| **Did the map appear faster (first banner)?** | **Maybe a little** in this single run: **`e2e.first_paint`** **~6.7 s** vs **~6.3 s** — difference is small and could be **noise**; repeat 3× per mode locally if you want confidence. |
| **Was Folium “HTML generation” much faster?** | **No.** ~**11–12 ms** per event on the fixture — noise-level. |

**Bottom line (dumbed down)**

- **Lazy popups are not showing a clear “load faster / smaller map” win** on this **fixture** run; the **byte size** of the generated HTML actually **increased**.
- **UX:** fine if you’re happy with on-open injection; that’s separate from perf.
- **Before merging lazy to a mainline for performance:** re-run the same pairing on your **real MyEBirdData CSV** (several runs each), watch **`html_bytes_len`** and **`e2e.first_paint`**. If HTML stays **larger** with lazy, the *current* lazy design is **not** a download-size optimization — a later step would be **lighter JSON + client rendering**, not “same HTML in a big object”.
- **Archives** (gitignored): `benchmarks/map_perf/snapshots/issue-205-lazy-a6e2e46/lazy-off.jsonl` and `lazy-on.jsonl`. Reproduce:

```bash
mkdir -p benchmarks/map_perf/snapshots/issue-205-lazy-a6e2e46
EXPLORER_E2E_PERF_JSONL_ARCHIVE="$PWD/benchmarks/map_perf/snapshots/issue-205-lazy-a6e2e46/lazy-off.jsonl" \
  python -m pytest 'tests/explorer/test_map_perf_e2e.py::test_map_perf_lazy_journey_tags_build_extra[0]' --perf -v
EXPLORER_E2E_PERF_JSONL_ARCHIVE="$PWD/benchmarks/map_perf/snapshots/issue-205-lazy-a6e2e46/lazy-on.jsonl" \
  python -m pytest 'tests/explorer/test_map_perf_e2e.py::test_map_perf_lazy_journey_tags_build_extra[1]' --perf -v
python scripts/aggregate_perf_jsonl.py benchmarks/map_perf/snapshots/issue-205-lazy-a6e2e46 \
  --glob '*.jsonl' \
  --stage prep.folium_map_to_html_bytes \
  --stage e2e.first_paint \
  --stage prep.build_species_overlay_map \
  --extra-key html_bytes_len --extra-key lazy_map_popups --extra-key banner_ms --extra-key goto_ms
```

Output (same capture as above; columns trimmed for reading):

```
lazy-off.jsonl   prep.folium_map_to_html_bytes   html_bytes_len.med ≈ 45521
lazy-on.jsonl    prep.folium_map_to_html_bytes   html_bytes_len.med ≈ 51674
lazy-off.jsonl   e2e.first_paint                  banner_ms.med ≈ 6739
lazy-on.jsonl    e2e.first_paint                  banner_ms.med ≈ 6303
```

### Legacy *n* = 1 table (older `issue-205-doc-e2e` capture; illustrative only)

```
group                        stage                                n_runs   total_events    med_evt/run         med_ms         p95_ms         max_ms marker_count.med marker_count.max popup_build_count.med popup_build_count.max popup_cache_hit_count.med popup_cache_hit_count.max popup_build_total_ms.med popup_build_total_ms.max lite_map_popups.med lite_map_popups.max lazy_map_popups.med lazy_map_popups.max  banner_ms.med  banner_ms.max    goto_ms.med    goto_ms.max
-----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
issue-205-doc-e2e.jsonl      e2e.first_paint                           1              1            1.0         6465.3         6465.3         6465.3              —              —              —              —              —              —              —              —            0.0            0.0            0.0            0.0         6465.3         6465.3          108.9          108.9
issue-205-doc-e2e.jsonl      prep.build_species_overlay_map              1              2            2.0           17.0           90.9           90.9           15.0           15.0           15.0           15.0            0.0            0.0            7.7           26.3            0.0            0.0            0.0            0.0              —              —              —              —
issue-205-doc-e2e.jsonl      prep.folium_map_to_html_bytes              1              2            2.0           12.5           13.1           13.1              —              —              —              —              —              —              —              —              —              —              —              —              —              —              —              —              —
issue-205-doc-e2e.jsonl      prep.map_context_prepare                  1              3            3.0           11.9           13.9           13.9              —              —              —              —              —              —              —              —              —              —              —              —              —              —              —              —              —
issue-205-doc-e2e.jsonl      prep.map_iframe_embed                     1              3            3.0           24.7           29.4           29.4              —              —              —              —              —              —              —              —              —              —              —              —              —              —              —              —              —
```

**Merge-back hygiene (for later)**

- **Batch A** (fragment cache): backend-only speedup when popups miss the full HTML cache; behaviour unchanged — strongest candidate to port if we want investigation value on `beta-next` without UX flags.
- **Batch B** (lazy popups): optional flag; **fixture A/B (`a6e2e46`) did not show smaller `html_bytes_len`** — treat as UX / architecture unless **real CSV** runs show a win; “smaller payload” likely needs **structured data + client templates** later, not inlined full HTML JSON.

## Related references (elsewhere)

- W2 lite vs rich **fixture** A/B (different question than Batch A): [`issue-205-w2-lite-ab-results.md`](issue-205-w2-lite-ab-results.md)  
- Historical batch notes: comments on [#205](https://github.com/jimchurches/myebirdstuff/issues/205) (batch 4 baselines, etc.)
