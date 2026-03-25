# Getting started — Personal eBird Explorer

The Personal eBird Explorer is a **Streamlit app** for exploring your personal eBird export (CSV) on an interactive map with summary tabs.

## Try it first (recommended): Streamlit Community Cloud

If you just want to try it without installing anything locally, use the hosted app:

- **Streamlit Community Cloud app**: `<TBA>`

**Trade-offs vs local run**

- **Pros**: no local install, easy “try before installing”
- **Cons**: slower than local for large exports; no offline use; you’ll need to re-upload the CSV when the session resets

## Run locally

You need **Python** installed. We assume you already have it (install via your OS app store / package manager / python.org — any of those are fine).

From the repo root, follow the Streamlit app README:

- [`streamlit_app/README.md`](../../streamlit_app/README.md)

## Download / update the app code

- **Option A (simplest)**: download a ZIP from GitHub and unzip it somewhere
- **Option B (developer)**: clone with Git if you already use Git

If you downloaded a ZIP and want to update later, the simplest approach is to download a new ZIP and replace your old folder (keeping your `scripts/config_secret.py`).

## Data loading and config files

The app loads your CSV in this order:

1. **Upload in the app** (best for Streamlit Community Cloud)
2. **Disk discovery** (local runs): it searches for the CSV in:
   - `scripts/config_secret.py` (`DATA_FOLDER`)
   - `scripts/config.py` (`DATA_FOLDER`)
   - the **working directory** where you ran `streamlit run ...`

### Why `config_secret.py`?

If you use Git, `scripts/config_secret.py` is the place for **your local paths and settings** because it is **gitignored** (so you don’t accidentally commit private filesystem paths).

