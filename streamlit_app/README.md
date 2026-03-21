# Streamlit app (prototype)

Early **Personal eBird Explorer** UI on Streamlit. The Jupyter notebook remains the full-featured app until features are ported.

**Tracking:** [Issue #70 — Plan transition from Notebook UI to Streamlit UI](https://github.com/jimchurches/myebirdstuff/issues/70) (branch-based prototype → parallel dev → cutover when ready; Binder/notebook preserved until then).

**Landing (no CSV yet):** If disk resolution finds no file and the user has not uploaded one, the app shows a simple title + instructions in the main area and only **Data** (plus an optional expander for local/Cloud setup) in the sidebar. Map controls, taxonomy fetch, and tabs appear after data loads.

## UI guidelines

- **Prefer Streamlit-native layout and widgets** — tabs, sidebar, `st.expander` (accordions), `st.dataframe` / `st.table`, `st.metric`, `st.columns`, and theme tweaks in `.streamlit/config.toml`. This stays aligned with Streamlit’s theming and future releases.
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

**Tabs:** The main area uses Streamlit tabs with the **same labels and order** as the Jupyter notebook (`Map`, `Checklist Statistics`, …). **Map** uses **map_controller** + Folium. **Checklist Statistics** uses `compute_checklist_stats_payload` and native widgets (`checklist_stats_streamlit_native.py`). Other tabs are still placeholders.

## Data loading (same ideas as the notebook)

| Method | When |
|--------|------|
| **File uploader** | In the **sidebar** under *Data* (drag-and-drop or browse). Best for **Streamlit Community Cloud**. |
| **CSV in this folder** | Put `MyEBirdData.csv` (or name from `STREAMLIT_EBIRD_DATA_FILE`) in `streamlit_app/`. |
| **`STREAMLIT_EBIRD_DATA_FOLDER`** | Env var: directory containing the CSV (like notebook `DATA_FOLDER_HARDCODED`). |
| **`scripts/config_secret.py`** | `DATA_FOLDER = "..."` — same as the notebook. |
| **Streamlit secret `EBIRD_DATA_FOLDER`** | Optional; same as hardcoded folder if you use Cloud secrets. |

Uploader wins over disk if a file is selected.

## Streamlit Community Cloud

1. Connect the repo and set **Main file path** to `streamlit_app/app.py`.
2. **Python requirements:** point to `requirements-streamlit.txt` (app settings).
3. Users upload their CSV via the app (do not commit private exports).

## Scope of this prototype

- Load CSV via `personal_ebird_explorer.data_loader.load_dataset`.
- Deduplicate by **Location ID** and show points with `st.map`.

Not here yet: species filter, Folium popups, stats tabs, Whoosh, date filter, etc.
