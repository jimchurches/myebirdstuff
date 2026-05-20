# Tests

Quick guide for running test layers in this repo.

## Python environment (read this first)

Use **one** virtualenv at the repo root: **`.venv/`** (gitignored).

```bash
cd /path/to/myebirdstuff
source .venv/bin/activate    # prompt should show (.venv) — not .venv-audit-test etc.
python -c "import pandas; print(pandas.__version__)"   # must succeed

# Create or refresh .venv (Python 3.12 + all deps):
./scripts/setup_dev_venv.sh
```

CI uses Python **3.12** and `requirements.txt`. Partial venvs (audit-only, old experiments) will fail with `ModuleNotFoundError: No module named 'pandas'`.

## All locations map frontend (Jest)

CI runs Jest, TypeScript check, production dependency audit, and build for `explorer/components/all_locations_map/frontend/` (see `docs/development.md` § Leaflet map component). Locally:

```bash
cd explorer/components/all_locations_map/frontend
npm ci && npm run test:ci && npm run typecheck && npm run audit:prod
```

## Default test run (recommended day-to-day)

Run the normal unit/integration suite (**with `.venv` activated**):

```bash
pytest tests/ -v
```

This is the same core path used in CI (plus coverage there).

## Optional browser E2E examples

Browser E2E tests are intentionally opt-in and marked with `@pytest.mark.e2e`.

Run only E2E tests:

```bash
pytest -m e2e -v
```

Run only the Streamlit map example module:

```bash
pytest tests/explorer/test_streamlit_map_e2e.py -m e2e -v
```

### Playwright setup (local)

```bash
pip install playwright
python -m playwright install chromium
```

If Playwright is not installed, E2E modules skip by design.

## Map / Leaflet tests (Python, no browser)

| Module | What it covers |
|--------|----------------|
| `tests/explorer/test_leaflet_payload_cache.py` | Session LRU helpers for all four map modes (parameterized). |
| `tests/explorer/test_leaflet_geojson_build_metrics.py` | I1/I2 build metrics on GeoJSON payload misses. |
| `tests/explorer/test_app_prep_map_ui_integration.py` | Map prep spinners, dataset-signature cache clear, warm `payload_cache_hit` (Streamlit stub). |
| `tests/explorer/test_streamlit_map_prep.py` | `prepare_all_locations_map_context` on fixture CSV. |

## Optional map perf E2E (`--perf`)

Opt-in Playwright + `EXPLORER_PERF_LOG_FILE` JSONL (see `benchmarks/map_perf/README.md`):

```bash
pytest tests/explorer/test_map_perf_e2e.py --perf -v
```

Modules: `test_map_perf_fixture_journey_emits_prep_stages_within_loose_ceiling` (All → Lifer → All),
`test_map_perf_fixture_journey_species_and_family_payload_stages`. Baseline script:
`./scripts/run_post_leaflet_perf_baseline.sh`.
