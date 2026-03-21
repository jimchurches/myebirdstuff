# Streamlit app (prototype)

Early **Personal eBird Explorer** UI on Streamlit. The Jupyter notebook remains the full-featured app until features are ported.

**Tracking:** [Issue #70 — Plan transition from Notebook UI to Streamlit UI](https://github.com/jimchurches/myebirdstuff/issues/70) (branch-based prototype → parallel dev → cutover when ready; Binder/notebook preserved until then).

**Landing (no CSV yet):** If disk resolution finds no file and this browser session has no cached upload yet, the app shows title + copy + **file uploader in the main column** (sidebar stays empty of data controls). After CSV load, only the **Map** sidebar + tabs appear — there is no control to swap CSV without a new session / refresh (loading APIs stay in `_load_dataframe` for future work).

## UI guidelines

- **Prefer Streamlit-native layout and widgets** — tabs, sidebar, `st.expander`, nested `st.tabs`, `st.dataframe` / `st.table`, `st.metric`, `st.columns`, and theme tweaks in `.streamlit/config.toml` (default theme uses eBird-style greens via `[theme]`). **Checklist Statistics** uses nested tabs so only one stats subsection is visible at a time (Streamlit expanders can’t be grouped as a single-open accordion). Metric tables use `st.dataframe` with **Metric** / **Value** headers (and **eBird link** for streak links). This stays aligned with Streamlit’s primitives.
- **eBird links in tables (notebook parity)** — The Jupyter UI links heavily from table cells to eBird (species, checklists, lifelists, regions). Preserve that behaviour when porting: plain `st.dataframe` cells won’t render Markdown links — use shared HTML formatters, `st.markdown` rows, `LinkColumn` for URL cells, or captions only as a fallback. See [AI_CONTEXT.md — Streamlit UI](../docs/AI_CONTEXT.md#streamlit-ui-prefer-native-components).
- **Use custom HTML/CSS sparingly** — `st.markdown(..., unsafe_allow_html=True)`, `st.html`, and large injected style blocks are acceptable when **intentional** (e.g. Folium, reusing `format_*_bundle` HTML from the notebook for parity or migration). For new features, default to native components unless there is a strong reason not to.
- **Contributors / AI assistants:** If a change could be done with native Streamlit instead of bespoke HTML, mention that tradeoff so the choice stays explicit.

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

**Map height:** The Folium iframe uses a **fixed pixel height** (streamlit-folium). Use the sidebar slider **Map height (px)** (default 720). The app passes a `key` that includes the height so the component **remounts** when you change the slider (streamlit-folium otherwise keeps the same internal identity and ignores the new height). Changing height may reset pan/zoom on the map.

**Tabs:** The main area uses Streamlit tabs with the **same labels and order** as the Jupyter notebook (`Map`, `Checklist Statistics`, …). **Map** uses **map_controller** + Folium. **Checklist Statistics** uses `compute_checklist_stats_payload` and nested `st.tabs` + tables (`checklist_stats_streamlit_native.py`). Other tabs are still placeholders.

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
3. Users upload their CSV via the app (do not commit private exports).

## Scope of this prototype

- Load CSV via `personal_ebird_explorer.data_loader.load_dataset`, map via **map_controller** + **streamlit-folium**, checklist stats tab (native Streamlit).  
- Not here yet: species filter UI, rankings/yearly/country/maintenance parity, Whoosh, date filter, etc.
