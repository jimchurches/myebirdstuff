# Streamlit app

Primary **Personal eBird Explorer** UI. Implementation modules live in this directory (`explorer/app/streamlit/`); import as **`explorer.app.streamlit`** from tests and tooling.

**Tracking:** [Issue #70 — Plan transition from Notebook UI to Streamlit UI](https://github.com/jimchurches/myebirdstuff/issues/70).

**Run from repo root:**

```bash
streamlit run explorer/app/streamlit/app.py
```

### Map marker design utility (developers only)

A **separate** Streamlit entry point draws dummy Folium markers for every map role so you can tune colours and geometry and export paste-ready ``MapMarkerColourScheme`` snippets. It is **not** linked from the main app (no eBird data required). Run:

```bash
streamlit run explorer/app/streamlit/design_map_app.py
```

See **[docs/development.md](../../../docs/development.md#map-marker-colour-design-utility-developers)** for the file map (preview module, hex resolver, ``defaults.py``).

**Landing (no CSV yet):** If disk resolution finds no file and this browser session has no cached upload yet, the app shows title + copy + **file uploader in the main column**. The **sidebar** still shows a small text footer: **GitHub** · **eBird** · **Instagram**, and a line below with **Explorer docs** (link to `docs/explorer/README.md` on GitHub; no icons — reads better in a narrow sidebar). After CSV load, the **Map** sidebar fills in above that footer — there is no control to swap CSV without a new session / refresh (loading APIs stay in `_load_dataframe` for future work).

**Sidebar footer:** `streamlit_ui_constants` defines `GITHUB_REPO_URL`, `EBIRD_PROFILE_URL`, and `INSTAGRAM_PROFILE_URL`; `explorer_readme_github_url()` (see `explorer.core.repo_git`) builds the **Explorer docs** URL to `docs/explorer/README.md` on GitHub for the **current git branch** when running from a checkout, otherwise **`main`**. Set **`EXPLORER_README_GITHUB_BRANCH`** (e.g. in Streamlit secrets) when the deployed app has no `.git` but should link to a branch other than `main`. `sidebar_footer_links()` renders GitHub / eBird / Instagram as middot-separated links and **Explorer docs** on a second line. *Other common patterns* if you want to change it: put links only on **Settings → About**; use a **shields.io** badge in markdown; add **“Fork me on GitHub”** ribbon (CSS, more prominent); or a **footer line** in the main area with `st.caption` under specific tabs (repeats unless hoisted).

## UI guidelines

- **Layouts and simple data** — Prefer Streamlit primitives: tabs, sidebar, `st.expander`, nested `st.tabs`, `st.dataframe` / `st.table`, `st.metric`, `st.columns`, `.streamlit/config.toml` theme (eBird-adjacent greens in `[theme]`). **Checklist Statistics** uses nested `st.tabs` plus **shared HTML** tables from `checklist_stats_streamlit_tab_sections_html`. **Rankings & lists** (`rankings_streamlit_html.py`) adds another level: **Top Lists** / **Interesting Lists** nested tabs, expanders per list, HTML from `format_checklist_stats_bundle` on the full export; **Top N** / **visible rows** sliders live under **Settings → Tables & lists**. Streamlit expanders can’t act as a single-open accordion for mutually exclusive panels — nested tabs are the pattern.
- **Rich tables (rankings, “Interesting lists”, richly-linked lists)** — These are produced as **HTML** (linked species/locations/dates, bold counts, ⧉, dotted/solid link styling). **`st.dataframe` is the wrong tool** for that UX. **Use HTML from shared formatters** in `explorer/presentation/` (`checklist_stats_display`, `rankings_display`, `format_checklist_stats_bundle`, etc.) and render with **`st.markdown(..., unsafe_allow_html=True)`** or **`st.html`**. **Do not fork** duplicate table HTML in this package; extend the shared formatters instead.
- **eBird links** — Never drop deep links just to avoid HTML. See [AI_CONTEXT.md — Streamlit UI](../../../docs/AI_CONTEXT.md#streamlit-ui).
- **One-off HTML** — Ad-hoc `unsafe_allow_html` not produced by a shared formatter is a last resort; prefer extending a module helper so formatting stays aligned.
- **Contributors / AI assistants:** When choosing dataframe vs formatter HTML, **state the tradeoff** briefly so the decision is explicit.

**Console noise:** If Streamlit warns about `use_container_width`, upgrade Streamlit (`requirements.txt` pins a recent minimum) and prefer `width="stretch"` on dataframes. **streamlit-folium** may still use the old API internally for the map until that library updates.

## Run locally

From the **repository root** (after activating a Streamlit-only venv — see below). The app uses package imports (`explorer.app.streamlit.*`, `explorer.core.*`, `explorer.presentation.*`). ``app.py`` prepends the **repo root** to ``sys.path`` so imports resolve when Streamlit runs the script from ``explorer/app/streamlit/``.

```bash
pip install -r requirements.txt
streamlit run explorer/app/streamlit/app.py
```

**Terminal stays busy:** `streamlit run` is a **server** — it holds the shell until you stop it (**Ctrl+C**). Closing the browser **does not** stop the server.

**Want your prompt back?** Run in the background: `streamlit run explorer/app/streamlit/app.py &` — or use a **second terminal tab**, **`tmux`/`screen`**, or **`nohup ... &`** (see your shell docs). Stop a background server with `pkill -f "streamlit run explorer/app/streamlit/app.py"` or find its PID and `kill`.

If you see an error about **streamlit-folium**, your venv was created before that dependency was added — run `pip install -r requirements.txt` again.

### Where to put the virtualenv

The repo **`.gitignore`** ignores `.venv/`, `.venv-streamlit/`, `venv/`, and `env/` so those folders stay out of Git. You can still avoid clutter under the clone:

| Option | Example |
|--------|--------|
| **Inside repo (ignored)** | `python -m venv .venv-streamlit` — fine; won’t be committed. |
| **Next to the repo** | `cd .. && python -m venv myebirdstuff-streamlit && source myebirdstuff-streamlit/bin/activate && cd myebirdstuff` |
| **Central tools dir** | `python -m venv ~/.venvs/myebirdstuff-streamlit` then activate before `cd` into the repo |

**Pandas versions:** `requirements.txt` uses **pandas 2.x** because current Streamlit releases require `pandas<3`.

**Folium:** Required for the map (`folium`, `streamlit-folium` in `requirements.txt`). **Whoosh** is still not required — the package `__init__` lazy-loads search so CSV load stays light.

**eBird taxonomy:** Fetched once per browser session after CSV load (cached by locale). Default locale is **en_AU**; set `STREAMLIT_EBIRD_TAXONOMY_LOCALE` or `EBIRD_TAXONOMY_LOCALE` for the first-visit default, or change **Settings → Taxonomy**. The value is an eBird **locale** code (e.g. `en_AU`) — same idea as **My eBird → Preferences** for common names; [Bird names in eBird](https://support.ebird.org/en/support/solutions/articles/48000804865-bird-names-in-ebird) explains regional naming. The **taxonomy** CSV endpoint is fetched without an API key; some other reference endpoints require a key. If the fetch fails (offline, etc.), species links are skipped. Streamlit does not expose the browser language to Python.

**Map panning / grey flash:** The map is a static **HTML iframe** (same bytes as **Export map HTML**), so panning does not talk to the server. Pin **popups** still work in the browser. The design map tool (`design_map_app.py`) still uses `st_folium` where needed.

**Performance (refs #70):** **All locations** and **Lifer locations** Folium maps are **cached** in session for the same dataset + date filter + basemap so switching between those views reuses the built map (changing the date filter or CSV invalidates the cache). **Selected species** uses the **streamlit-searchbox** component inside a **`@st.fragment`** with **fragment-scoped reruns** and **debounced** input so typing in the species search does not grey out the whole app. The **Show only selected species** toggle lives **outside** the fragment so the map updates immediately when you change it.

**Map banners / legend:** Fixed overlays use the same **theme tokens** as the Streamlit app (primary green titles, panel gradient, borders) via injected CSS in ``map_overlay_theme_stylesheet`` (`explorer/presentation/map_renderer.py`; refs #70).

**Map height:** The Folium iframe uses a **fixed pixel height** via `st.components.v1.html`. Use the sidebar slider **Map height (px)** (default 720). The app passes a `st.container` **key** that includes the height so the map **remounts** when you change the slider. Changing height may reset pan/zoom on the map.

**Map sidebar (controls):** **Map view** — `All locations` | `Selected species` | `Lifer locations`. **Date filter** (non–Lifer views) — **Date filter** toggle and **date range** when on (off = all-time; **Lifer locations** ignores the map date filter but remembers your date-filter choice in session for the other views). **Lifer locations** — captions and **Show subspecies lifers** where applicable. **Group nearby pins** — Leaflet clustering on the **All locations** map (session-only; persist default under **Settings → Map display** + **Save settings**). **Selected species** — `streamlit-searchbox` + Whoosh; **Show only selected species** toggle. **Basemap** and **Map height (px)** sit below. **Export map HTML** — `st.download_button` at the bottom (bytes from `folium.Map.get_root().render()`). **Taxonomy locale** for species links: **Settings → Taxonomy**.

**Tabs:** The main area uses a classic tab order (`Map`, `Checklist Statistics`, …). **Checklist Statistics** is shared section HTML (`checklist_stats_streamlit_tab_sections_html`) with theme-scoped CSS injected via `inject_streamlit_checklist_css()` in `streamlit_theme.py` (default **green** zebra + accents; flip `USE_EBIRD_BLUE_HTML_TAB_THEME` there for **eBird-blue** across checklist-style HTML tabs). **Map** uses **map_controller** + Folium. On each full rerun, **prep** work (checklist stats payload, full-export prep, sync helpers, rankings bundle) runs in a **`st.spinner` above the main tab row** (same bird-emoji strip as the Map tab); the **Map** tab Folium build + iframe embed uses a **second** `st.spinner` inside the Map panel. Several data tabs use `@st.fragment` for partial reruns (Country, Yearly, Maintenance, Rankings, …).

## Data loading

**`config/config_template.yaml` is not used at runtime** — it is a **tracked template** to copy into
`config/config_secret.yaml` or `config/config.yaml` (both gitignored).

Disk search is **first folder that contains the CSV**, in this order:

1. **`config/config_secret.yaml`** — if it exists and defines non-empty `data_folder`, that directory is searched first. **Settings** save back into this same file under `explorer_settings` when this source wins. Typical for developers using git (file is gitignored).
2. **`config/config.yaml`** — same keys as the template; gitignored. **Settings** save back into this same file under `explorer_settings` when this source wins.
3. **Current working directory** — the directory you were in when you ran `streamlit run ...` (often the repo root). CSV can live next to your clone; **no** settings file is associated, so **Save settings** stays disabled for persistence (session-only).

| Method | When |
|--------|------|
| **File uploader** | **Landing** page (main area). Cached in session. Primary path for **Streamlit Community Cloud**. |
| **Config `data_folder`** | As above (`config_secret.yaml` → `config.yaml`). |
| **Working directory** | Put `MyEBirdData.csv` (or override basename with env **`STREAMLIT_EBIRD_DATA_FILE`**) in the directory you start Streamlit from. |

There is **no** `STREAMLIT_EBIRD_DATA_FOLDER` or Streamlit-secret data-folder override; use config files, CWD, or upload.

**Precedence (load):** A new pick from the landing uploader → **disk** (config paths + CWD) → **cached upload**. Stale upload cache is cleared when disk wins.

### Optional GitHub release notice ([#189](https://github.com/jimchurches/myebirdstuff/issues/189))

When the page host is **not** Streamlit Community Cloud (hostname does not end with `.streamlit.app`), the app may call GitHub’s public **`releases/latest`** API **at most once per 24 hours** (process cache) and show a short, non-blocking hint if a **newer** release exists than the committed id in [`explorer_build_version.txt`](explorer_build_version.txt). Offline or HTTP errors are ignored (no user-facing errors). Set **`EXPLORER_UPDATE_CHECK=0`** or **`1`** in the environment or Streamlit secrets to force-disable or force-enable. In **`config/config.yaml`** or **`config/config_secret.yaml`**, **`check_for_updates: false`** opts out.

### Performance instrumentation (Phase 0, [#179](https://github.com/jimchurches/myebirdstuff/issues/179))

**Off by default.** Set **`EXPLORER_PERF=1`** in the environment (or the same key in **Streamlit secrets** on Community Cloud) to record stage timings to session state and show a **Performance / debug** expander at the bottom of the **sidebar** (recent events table + **Download metrics (JSONL)** + clear buffer).

Optional **`EXPLORER_PERF_LOG=1`**: also emit one JSON object per line at **INFO** on the root logger (visible in Cloud **Logs**).

Implementation: `explorer/app/streamlit/perf_instrumentation.py` (`perf_span`, `perf_fragment`); hooks in `app_data_loading.py`, `app_prep_map_ui.py`, `app.py`, and tab fragments.

## Streamlit Community Cloud

**Deployed instance:** https://personal-ebird-explorer.streamlit.app

1. Connect the repo and set **Main file path** to `explorer/app/streamlit/app.py`.
2. **Python requirements file (required):** in app **Settings → Advanced settings**, set this to **`requirements.txt`** at the **repo root**.
3. Users upload their CSV via the app (do not commit private exports).

## Scope of this Streamlit app

- Load CSV via `explorer.core.data_loader.load_dataset`, map via **map_controller** + **streamlit-folium**, checklist stats tab (shared HTML + nested `st.tabs`), **Yearly Summary** (`yearly_summary_streamlit_html`: `@st.fragment` + nested tabs; `st.toggle` for recent vs full columns when year count exceeds **Settings → Yearly tables: recent year columns**, 3–25 default 10), **Country** tab (fragment + same toggle behavior), **Maintenance** tab (`maintenance_streamlit_html`: nested tabs + expanders + `maintenance_display` HTML).  
- **Rankings & lists** is migrated separately (`rankings_streamlit_html`).
