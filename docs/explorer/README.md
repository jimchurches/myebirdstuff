# Personal eBird Explorer

A Jupyter notebook that lets you explore your eBird data on an interactive map. Search for species, filter by date, view lifers and last-seen locations, and explore checklist details.

## What it does

- **Map** — All checklist locations (green pins); optional species filter (red pins, lifer/last-seen highlights).
- **Search** — Type-ahead species search; “show only selected species” to hide other locations.
- **Tabs** — Map, Checklist Statistics, Yearly Summary, Rankings, Map maintenance (duplicates / close locations).
- **Export** — “Export Map HTML” saves the current map view.
- **Date filter** — Optional date range (set in the notebook’s User Variables; re-run from Data prep to apply).

**You need:** Your eBird data export (CSV). Download from [eBird.org](https://ebird.org) → My eBird → Manage My Data → Download My Data. The notebook expects `MyEBirdData.csv` by default.

## Screenshot

<!-- Placeholder: add a screenshot of the map tab (e.g. map with search and pins) when available. -->

*Screenshot placeholder — add an image of the map tab when available.*

---

## Running locally

You can run the notebook **on Binder** (no install) or **locally** (Jupyter or Voila). See below.

---

## Option A: Run on Binder (no installation)

Binder runs the notebook in the cloud. Nothing to install — just upload your data and go. It can be a bit slower than running locally.

### Quick launch

**[Launch on Binder](https://mybinder.org/v2/gh/jimchurches/myebirdstuff/main?urlpath=lab%2Ftree%2Fnotebooks%2Fpersonal_ebird_explorer.ipynb)** — opens the notebook directly.

### Manual launch

1. Go to [mybinder.org](https://mybinder.org)
2. **GitHub repository name or URL:** `https://github.com/jimchurches/myebirdstuff`
3. **File to open (in JupyterLab):** `notebooks/personal_ebird_explorer.ipynb`
4. Click **Launch**

### After the notebook opens

1. Click the **folder icon** (top left) to open the file browser.
2. **Drag and drop** your `MyEBirdData.csv` into that folder (or use Upload).
3. From the menu: **Run → Run All Cells**
4. Scroll down to the map. Use the filter box above it to search for species and redraw the map.
5. Use **Export Map HTML** above the map to save the current view as an HTML file; then right‑click it and **Download** if you want to keep or share a view.

### Binder notes

- **Speed:** The free Binder host is slower than a fast local machine; map redraws may take a few seconds. The **initial map load** can take over a minute — wait for it to finish before interacting.
- **Session timeout:** The environment is not persistent and times out when idle. Relaunch when needed.
- **Occasional failures:** If the notebook fails, try **Run → Run All Cells** again. If the environment fails to build, try again later.

---

## Option B: Run locally (Jupyter or Voila)

For full installation instructions (Python, Jupyter, Voila, and dependencies on Windows and macOS), see:

**[Installation guide](install.md)**

Local install gives you faster performance. You can run the notebook in Jupyter or as a Voila dashboard. **Note:** There is currently a known issue with Voila not working (root cause unknown); use Jupyter if you run into problems.

---

## Current project status

- **Stable:** Map, species search, stats tabs, export, reset, date filter (config in notebook). Active development is on the `refactor/modularise-core` branch; `main` tracks the current stable explorer.
- **Documentation:** This README, [install.md](install.md), [development.md](../development.md), and [AI_CONTEXT.md](../AI_CONTEXT.md) for contributors and AI-assisted work.

---

## Project structure (high level)

- **notebooks/personal_ebird_explorer.ipynb** — UI and orchestration; paired with `.py` via Jupytext.
- **personal_ebird_explorer/** — Core logic: data loading, path resolution, species logic, stats, duplicate checks, map rendering, UI state, region display (country/state names in tables).
- **docs/explorer/** — User and install docs (this file, install.md, future-ideas.md, etc.).
- **docs/development.md** — Developer guide (architecture, modules, testing, refactor and AI guardrails).
- **docs/AI_CONTEXT.md** — Context and **AI Coding Rules** for AI assistants; read before suggesting architectural changes.

For full architecture and module roles, see [docs/development.md](../development.md).

---

## Roadmap (high level)

Possible future directions (not committed):

- Easier onboarding for non-technical users (e.g. simpler install, Voila-first).
- Richer date-filter and options UI (e.g. options panel).
- Better export or standalone deployment (e.g. Voila, or self-contained HTML).
- Improved species/analysis tools.

See [future-ideas.md](future-ideas.md) for more exploratory notes.

---

## If you see "File Load Error" (notebook and .py out of sync)

This project uses [Jupytext](https://jupytext.readthedocs.io/) so `personal_ebird_explorer.ipynb` and `personal_ebird_explorer.py` stay in sync. If the dialog says the notebook is newer than the .py (or the other way around), you can fix it without losing work:

1. **Update the older file from the newer one** (recommended). From the repo root:
   ```bash
   jupytext --sync notebooks/personal_ebird_explorer.ipynb
   ```
   This makes the paired file match the one that was modified last. Then save and reopen as needed.

2. **Or** open the `.py` in an editor, make it match the notebook (or vice versa), save, and the error will go away on next open.

3. **Optional:** To make Jupytext less strict about small timing differences, add a `jupytext.toml` in the repo root with:
   ```toml
   outdated_text_notebook_margin = 5
   ```
   (default is 1 second). That only relaxes the check; it doesn’t fix real content drift, so prefer (1) when the dialog appears.
