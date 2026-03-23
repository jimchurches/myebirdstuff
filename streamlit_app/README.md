# Streamlit app (prototype)

Early **Personal eBird Explorer** UI on Streamlit. The Jupyter notebook remains the full-featured app until features are ported.

**Tracking:** [Issue #70 — Plan transition from Notebook UI to Streamlit UI](https://github.com/jimchurches/myebirdstuff/issues/70) (branch-based prototype → parallel dev → cutover when ready; Binder/notebook preserved until then).

**Landing (no CSV yet):** If disk resolution finds no file and this browser session has no cached upload yet, the app shows title + copy + **file uploader in the main column**. The **sidebar** still shows a small **GitHub** link (icon + “Source”) at the bottom. After CSV load, the **Map** sidebar fills in above that footer — there is no control to swap CSV without a new session / refresh (loading APIs stay in `_load_dataframe` for future work).

**GitHub link:** `app.py` sets `GITHUB_REPO_URL` and renders `_sidebar_github_footer()` after the sidebar controls (and after the optional map export button). *Other common patterns* if you want to change it: put the link only on **Settings → About**; use a **shields.io** badge in markdown; add **“Fork me on GitHub”** ribbon (CSS, more prominent); or a **footer line** in the main area with `st.caption` under specific tabs (repeats unless hoisted).

## UI guidelines

- **Layouts and simple data** — Prefer Streamlit primitives: tabs, sidebar, `st.expander`, nested `st.tabs`, `st.dataframe` / `st.table`, `st.metric`, `st.columns`, `.streamlit/config.toml` theme (eBird-adjacent greens in `[theme]`). **Checklist Statistics** uses nested `st.tabs` plus **shared HTML** tables from `checklist_stats_streamlit_tab_sections_html` (same source as the notebook stats columns). **Rankings & lists** (`rankings_streamlit_html.py`) adds another level: **Top Lists** / **Interesting Lists** nested tabs, expanders per list, HTML from `format_checklist_stats_bundle` on the full export; **Top N** / **visible rows** sliders live under **Settings → Tables & lists**. Streamlit expanders can’t act as a single-open accordion for mutually exclusive panels — nested tabs are the pattern.
- **Rich tables (rankings, “Interesting lists”, notebook-style lists)** — Jupyter builds these as **HTML** (linked species/locations/dates, bold counts, ⧉, dotted/solid link styling). **`st.dataframe` is the wrong tool** for that parity. **Use HTML from shared formatters** in `personal_ebird_explorer/` (`checklist_stats_display`, `rankings_display`, `format_checklist_stats_bundle`, etc.) and render with **`st.markdown(..., unsafe_allow_html=True)`** or **`st.html`**. **Do not fork** duplicate table HTML in `streamlit_app/`. Same trust model as Folium popups: escape in formatters.
- **eBird links** — Never drop deep links just to avoid HTML; match the notebook’s linking behaviour. See [AI_CONTEXT.md — Streamlit UI](../docs/AI_CONTEXT.md#streamlit-ui).
- **One-off HTML** — Ad-hoc `unsafe_allow_html` not produced by a shared formatter is a last resort; prefer extending a module helper so notebook and Streamlit stay aligned.
- **Contributors / AI assistants:** When choosing dataframe vs formatter HTML, **state the tradeoff** briefly so the decision is explicit.

**Console noise:** If Streamlit warns about `use_container_width`, upgrade Streamlit (`requirements-streamlit.txt` pins a recent minimum) and prefer `width="stretch"` on dataframes. **streamlit-folium** may still use the old API internally for the map until that library updates.

## Run locally

From the **repository root** (after activating a Streamlit-only venv — see below):

```bash
pip install -r requirements-streamlit.txt
streamlit run streamlit_app/app.py
```

**Terminal stays busy:** `streamlit run` is a **server** — it holds the shell until you stop it (**Ctrl+C**). Closing the browser **does not** stop the server.

**Want your prompt back?** Run in the background: `streamlit run streamlit_app/app.py &` — or use a **second terminal tab**, **`tmux`/`screen`**, or **`nohup ... &`** (see your shell docs). Stop a background server with `pkill -f "streamlit run streamlit_app/app.py"` or find its PID and `kill`.

If you see an error about **streamlit-folium**, your venv was created before that dependency was added — run `pip install -r requirements-streamlit.txt` again.

### Where to put the virtualenv

The repo **`.gitignore`** ignores `.venv/`, `.venv-streamlit/`, `venv/`, and `env/` so those folders stay out of Git. You can still avoid clutter under the clone:

| Option | Example |
|--------|--------|
| **Inside repo (ignored)** | `python -m venv .venv-streamlit` — fine; won’t be committed. |
| **Next to the repo** | `cd .. && python -m venv myebirdstuff-streamlit && source myebirdstuff-streamlit/bin/activate && cd myebirdstuff` |
| **Central tools dir** | `python -m venv ~/.venvs/myebirdstuff-streamlit` then activate before `cd` into the repo |

**Pandas vs Jupyter:** `requirements-streamlit.txt` uses **pandas 2.x** because current Streamlit releases require `pandas<3`. The notebook stack (`requirements-explorer.txt`) uses **pandas 3.x**. Use a **dedicated venv** for Streamlit so you don’t fight pip over pandas versions.

**Folium:** Required for the map (`folium`, `streamlit-folium` in `requirements-streamlit.txt`). **Whoosh** is still not required — the package `__init__` lazy-loads search so CSV load stays light.

**eBird taxonomy:** Fetched once per browser session after CSV load (cached by locale). Default locale is **en_AU**; set `STREAMLIT_EBIRD_TAXONOMY_LOCALE` or `EBIRD_TAXONOMY_LOCALE` for the first-visit default, or change the sidebar *Taxonomy locale* field. If the fetch fails (offline, etc.), species links in popups are skipped. Streamlit does not provide the browser’s language to Python automatically; auto-locale would need a query param, custom JS/component, or heuristics from the CSV (e.g. dominant `Country`) — not implemented yet.

**Map panning / grey flash:** The app calls `st_folium(..., returned_objects=[], return_on_hover=False)` so panning does not trigger a full Streamlit rerun (the default would return bounds/zoom and redraw the iframe). Pin **popups** still work in the browser; only server-side “read what was clicked” is disabled.

**Performance (refs #70):** **All locations** and **Lifer locations** Folium maps are **cached** in session for the same dataset + date filter + basemap so switching between those views reuses the built map (changing the date filter or CSV invalidates the cache). **Selected species** uses the **streamlit-searchbox** component inside a **`@st.fragment`** with **fragment-scoped reruns** and **debounced** input so typing in the species search does not grey out the whole app. The **Show only selected species** toggle lives **outside** the fragment so the map updates immediately when you change it.

**Map banners / legend:** Fixed overlays use the same **theme tokens** as the Streamlit app (primary green titles, panel gradient, borders) via injected CSS in ``map_overlay_theme_stylesheet`` (`personal_ebird_explorer/map_renderer.py`; refs #70).

**Map height:** The Folium iframe uses a **fixed pixel height** (streamlit-folium). Use the sidebar slider **Map height (px)** (default 720). The app passes a `key` that includes the height so the component **remounts** when you change the slider (streamlit-folium otherwise keeps the same internal identity and ignores the new height). Changing height may reset pan/zoom on the map.

**Map sidebar (controls):** **Map view** — `All locations` | `Selected species` | `Lifer locations` (notebook parity). **Date** — **Date filter** applies to **All locations** and **Selected species** (off = all-time; on = **date range**, default inception → today). **Lifer locations** ignores the date filter for the map; your date choice is **remembered in session** when you return to the other views. **Selected species** — single **search-as-you-type** field (`streamlit-searchbox` + Whoosh on common and scientific names); **Show only selected species** toggle (all pins vs species-only). **Basemap** and **Map height (px)** sit below Date and species. **Export map HTML** — `st.download_button` at the bottom (bytes from `folium.Map.get_root().render()`). **Taxonomy locale** for species links: **Settings → Species links**.

**Tabs:** The main area matches the Jupyter notebook tab order (`Map`, `Checklist Statistics`, …). **Checklist Statistics** is shared section HTML (`checklist_stats_streamlit_tab_sections_html`) with theme-scoped CSS (default **green** zebra + accents, `CHECKLIST_STATS_STREAMLIT_HTML_TAB_CSS`; optional **eBird-blue** via `CHECKLIST_STATS_STREAMLIT_HTML_TAB_CSS_BLUE` + `_USE_EBIRD_BLUE_HTML_TAB_THEME` in `checklist_stats_streamlit_html.py`), injected once. **Map** uses **map_controller** + Folium. Checklist stats are computed once right under the main tab row (`st.spinner`), so the loading line appears whichever tab is open. Other tabs are still placeholders.

## Data loading (same ideas as the notebook)

| Method | When |
|--------|------|
| **File uploader** | On the **landing** page only (main area). Upload is cached in session for reruns. Best for **Streamlit Community Cloud**. |
| **CSV in this folder** | Put `MyEBirdData.csv` (or name from `STREAMLIT_EBIRD_DATA_FILE`) in `streamlit_app/`. |
| **`STREAMLIT_EBIRD_DATA_FOLDER`** | Env var: directory containing the CSV (like notebook `DATA_FOLDER_HARDCODED`). |
| **`scripts/config_secret.py`** | `DATA_FOLDER = "..."` — same as the notebook. |
| **Streamlit secret `EBIRD_DATA_FOLDER`** | Optional; same as hardcoded folder if you use Cloud secrets. |

**Precedence:** A new pick from the landing uploader → **disk** (if resolvable) → **cached upload** for this session. Stale cache is cleared when disk wins.

## Streamlit Community Cloud

1. Connect the repo and set **Main file path** to `streamlit_app/app.py`.
2. **Python requirements file (required):** in app **Settings → Advanced settings**, set this to  
   **`requirements-streamlit.txt`** (repo root) **or** **`streamlit_app/requirements.txt`**.  
   If you leave the default **`requirements.txt`**, the build only installs the **Jupyter** stack — you will get **Missing streamlit-folium** at runtime.  
   **`requirements-streamlit.txt`** includes **scikit-learn** (Maintenance close-location BallTree) and **pycountry** (Country tab / ISO → names). Without them, Cloud can fail on `sklearn` or show raw codes like `AU` instead of `Australia`.
3. Users upload their CSV via the app (do not commit private exports).

## Scope of this prototype

- Load CSV via `personal_ebird_explorer.data_loader.load_dataset`, map via **map_controller** + **streamlit-folium**, checklist stats tab (shared HTML + nested `st.tabs`), **Country** tab (fragment + shared HTML), **Maintenance** tab (`maintenance_streamlit_html`: nested tabs + expanders + `maintenance_display` HTML).  
- Not here yet: rankings/yearly parity, etc.
