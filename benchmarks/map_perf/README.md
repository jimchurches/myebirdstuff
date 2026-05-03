# Map performance baselines (#179)

This folder holds **versioned ceilings** used by opt-in **`pytest --perf`** tests so catastrophic
slowdowns or hangs regressions are noticeable without baking flaky millisecond timings into CI.

## What gets stored

| File | Purpose |
|------|---------|
| `stage_ceilings.json` | Very loose per-stage **milliseconds** caps (cold laptop / CI-ish). Tune intentionally when speeding up mapped paths. |

Historical **absolute** timings are not committed: they vary by machine, load, and Python/Streamlit
versions. The useful part is **stage names + relative before/after** from your own runs (issue/PR
notes) and these **guardrail ceilings**.

## Feasibility / relevance

- **Feasible:** small JSON blobs, no binary logs.
- **Relevant:** keeps `prep.*` / `dataset.load` instrumentation honest when refactoring embeds (#190)
  or cache keys.
- **Worth doing:** lightweight; complements human-reported timings. Replace or tighten ceilings when
  you intentionally improve hotspots.

## How to regenerate ceilings (rare)

1. Run a local journey with logging (see **`docs/development.md`** § performance / E2E).
2. If all runs comfortably under current caps, optionally **lower** the JSON values to tighten the
   guardrail (leave headroom for CI variability).
3. Commit with the behaviour change PR so future regressions surface quickly.

---

## Local snapshots (not committed — single-machine history)

Capture runs with **`EXPLORER_PERF_LOG_FILE`** (see **`explorer/app/streamlit/README.md`**) pointing at a
writable path, reproduce the journey, then archive the JSONL into **gitignored**

`benchmarks/map_perf/snapshots/YYYY-MM-DDTHH-MM-SSZ_<label>.json`

(one pretty-printed JSON file with hostname, source path, and parsed ``events``):

```bash
python scripts/snapshot_explorer_perf_log.py /path/to/perf.jsonl --label post-embed-tweak
```

The directory stays local so you can diff before/after or attach excerpts to issues without fighting
hardware variance on other machines.
