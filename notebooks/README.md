# Personal eBird Explorer

A Jupyter notebook that lets you explore your eBird data on an interactive map. Search for species, filter by date, view lifers and last-seen locations, and explore checklist details.

**You need:** Your eBird data export (CSV). Download from [eBird.org](https://ebird.org) → My eBird → Manage My Data → Download My Data. The notebook expects `MyEBirdData.csv` by default.

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
5. The map is also saved as an HTML file in the same folder — right‑click it and **Download** if you want to keep or share a view.

### Binder notes

- **Speed:** The free Binder host is slower than a fast local machine; map redraws may take a few seconds.
- **Session timeout:** The environment is not persistent and times out when idle. Relaunch when needed.
- **Occasional failures:** If the notebook fails, try **Run → Run All Cells** again. If the environment fails to build, try again later.

---

## Option B: Run locally (Jupyter or Voila)

For full installation instructions (Python, Jupyter, Voila, and dependencies on Windows and macOS), see:

**[INSTALL_EBIRD_EXPLORER.md](../INSTALL_EBIRD_EXPLORER.md)**

Local install gives you faster performance and lets you run the notebook as a Voila dashboard.

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
