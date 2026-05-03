# Tests

Quick guide for running test layers in this repo.

## Default test run (recommended day-to-day)

Run the normal unit/integration suite:

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
