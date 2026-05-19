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
