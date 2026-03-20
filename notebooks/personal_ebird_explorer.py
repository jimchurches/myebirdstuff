# ---
# jupyter:
#   jupytext:
#     formats: ipynb,py:percent
#     text_representation:
#       extension: .py
#       format_name: percent
#       format_version: '1.3'
#       jupytext_version: 1.19.1
#   kernelspec:
#     display_name: Python 3 (ipykernel)
#     language: python
#     name: python3
# ---

# %% [markdown] editable=true slideshow={"slide_type": ""} tags=["voila_hide"]
# ## 🗺️ Personal eBird Explorer
#
# Put your eBird data on a map and explore where you've been birding. No coding required — just run the notebook and use the search box and map below.
#
# **What you can do**
#
# - **See all your checklist locations** — Every place you've submitted a checklist from appears as a pin on the map (green when viewing everything).
# - **Search for a bird** — Type a species name in the search box; the map highlights where you've seen it (red pins). Your first-ever sighting (lifer) and most recent sighting can be marked with different pin colours.
# - **Focus on one species** — Optionally hide other locations so only that bird's pins show.
# - **Click a pin** — See your visits to that location, with links to each checklist on eBird and to the location's life list. If you have photos in Macaulay Library, a 📷 link appears there too.
# - **See the numbers** — The box above the map shows how many checklists, species, or individuals you're looking at (all data or for the bird you chose). Optional date filtering is available in the settings below.
# - **Other tabs** — Besides the map, you get **Checklist Statistics** (overview, protocols, time birding), **Yearly Summary** (activity by year), **Rankings** (top species, locations, months), and **Maintenance** (duplicate or nearby locations). Switch tabs above the map to explore.
#
# **What to do now**
#
# 1. Make sure your eBird export file (e.g. `MyEBirdData.csv`) is in the right folder — see **User Variables** in the next section, or the [Explorer README](docs/explorer/README.md) for where to put it.
# 2. From the menu, choose **Run → Run All Cells**. Give it a moment to load (on Binder the first map can take over a minute).
# 3. Scroll down to the **search box and map**. Use the search box to find a bird and the map updates automatically.
#
# Need install or run instructions? See [docs/explorer/README.md](docs/explorer/README.md) and [docs/explorer/install.md](docs/explorer/install.md).
#

# %% [markdown] editable=true slideshow={"slide_type": ""} tags=["voila_hide"]
# ### 🛠️ User Variables — data file, map style, pin colours, date filter, etc. Paths: `DATA_FOLDER_HARDCODED`, or `scripts/config_secret.py`, or `scripts/config_template.py`; notebook folder last. Full options: [docs/explorer/README.md](docs/explorer/README.md).

# %% editable=true slideshow={"slide_type": ""}
# --------------------------------------------
# ✅ User Variables — Change These as Needed
# --------------------------------------------

# Name of your eBird export file (in the DATA_FOLDER below)
EBIRD_DATA_FILE_NAME = "MyEBirdData.csv"

# Optional hardcoded data folder (overrides config files). Leave empty ("") to use config or fallbacks.
# macOS example: "/Users/yourname/Documents/eBird"
# Windows example: r"C:\Users\yourname\Documents\eBird" or "C:/Users/yourname/Documents/eBird"
DATA_FOLDER_HARDCODED = ""

# Where your .csv file is located, and where the output map will be saved
OUTPUT_HTML_FILE_NAME = "species_map.html"

# Map style options: "default", "satellite", "google", "carto"
MAP_STYLE = "default"

# Toggle lifer marker (first sighting in dataset)
MARK_LIFER = True

# Toggle last-seen marker (most recent sighting; ignored if same location as lifer)
MARK_LAST_SEEN = True

# Pin colours (edge, fill) — lifer, last seen, species match, default
LIFER_COLOR, LIFER_FILL = "purple", "yellow"
LAST_SEEN_COLOR, LAST_SEEN_FILL = "purple", "lightgreen"
SPECIES_COLOR, SPECIES_FILL = "purple", "red"
DEFAULT_COLOR, DEFAULT_FILL = "green", "lightgreen"

# Popup sort order: "ascending" (oldest first) or "descending" (newest first)
POPUP_SORT_ORDER = "ascending"

# Popup scroll hint when content overflows: "chevron" (▲▼), "shading" (fade gradients), or "both"
POPUP_SCROLL_HINT = "shading"

# Rankings tab: max rows per table (e.g. Top 200); tables show 16 rows visible, scroll for rest
TOP_N_TABLE_LIMIT = 200
RANKINGS_TABLE_VISIBLE_ROWS = 16

# Map maintenance tab: locations within this distance (meters) are considered "close"
CLOSE_LOCATION_METERS = 10

# eBird taxonomy locale for species links: common names in the API match your export when set.
# Examples: "en_AU" (Australian), "en_GB" (British). Leave "" for API default (en_US).
# See eBird API 2.0 reference: https://documenter.getpostman.com/view/664302/S1ENwy59
EBIRD_TAXONOMY_LOCALE = "en_AU"

# Optional date range filtering (set to False to disable)
# Note: Some eBird exports (e.g. checklists with no time, generalized locations) may use year 2026.
# If locations/species are missing, set FILTER_BY_DATE = False or extend the range.
# After changing these, re-run from the "Data prep" / load cell so the map uses the new filter.
FILTER_BY_DATE = False
FILTER_START_DATE = "2026-01-01"
FILTER_END_DATE = "2026-12-31"


# %% [markdown] editable=true slideshow={"slide_type": ""} tags=["voila_hide"]
# ### 📦 Imports and setup (dependencies, CSS, package imports in later cells).
#

# %%
# --------------------------------------------
# ✅ Check dependencies (fail fast with clear message if missing)
# --------------------------------------------
# (import_name, pip_package_name) — scikit-learn installs as "scikit-learn" but imports as "sklearn"
_REQUIRED = [
    ("pandas", "pandas"),
    ("folium", "folium"),
    ("ipywidgets", "ipywidgets"),
    ("whoosh", "whoosh"),
    ("sklearn", "scikit-learn"),
]
_missing = []
for _import_name, _pip_name in _REQUIRED:
    try:
        __import__(_import_name)
    except ImportError:
        _missing.append(_pip_name)
if _missing:
    import sys
    _kernel_py = sys.executable
    raise ImportError(
        f"Missing package(s): {', '.join(_missing)}\n\n"
        f"This kernel is using: {_kernel_py}\n"
        f"Expected (pyenv):      $HOME/.pyenv/versions/3.12.3/bin/python\n\n"
        "If they differ, Jupyter was started with a different Python. Restart Jupyter using your "
        "jlabedge script (after killing any existing Jupyter processes).\n\n"
        "Or install here:  %pip install " + " ".join(_missing)
    )

# %%
# --------------------------------------------
# ✅ Imports and Display CSS
# --------------------------------------------
import html
import os
import sys
from collections import OrderedDict
from datetime import datetime, date

import pandas as pd
import folium
from branca.element import Element
import tempfile
import threading
import importlib.util
import ipywidgets as widgets

from ipywidgets import Accordion, Box, Checkbox, HBox, VBox
from whoosh.index import create_in
from whoosh.fields import Schema, TEXT
from whoosh.analysis import StemmingAnalyzer

from IPython.display import display, HTML

display(HTML("""
<style>
.output_map iframe {
    width: 100% !important;
    height: 600px;
    min-height: 600px;
}
/* Species matches dropdown: drops neatly below input, matches app styling */
.species-matches-dropdown,
.species-matches-dropdown select,
.map-controls-panel .widget-select,
.map-controls-panel .widget-select select {
    font-size: 13px !important;
    font-weight: normal !important;
    color: #374151 !important;
    background: #fff !important;
    border: 1px solid #e5e7eb !important;
    border-radius: 6px !important;
    box-shadow: 0 1px 2px rgba(0,0,0,0.04) !important;
}
.species-matches-dropdown select,
.map-controls-panel .widget-select select {
    padding: 4px 8px !important;
    overflow: hidden !important;
}
.species-matches-dropdown {
    margin-top: 2px !important;  /* small gap below search input */
}
/* Control area: soft neutral card */
.map-controls-panel,
.widget-vbox:has(input[placeholder="Type species name..."]) {
    background: #f9fafb !important;
    border: 1px solid #e5e7eb !important;
    border-radius: 8px !important;
    box-shadow: 0 1px 3px rgba(0,0,0,0.06) !important;
    padding: 12px 16px !important;
    margin-bottom: 4px !important;
    width: 100% !important;
    max-width: 100% !important;
    box-sizing: border-box !important;
}
/* Control + map alignment: same width, no overhang */
.output_map {
    width: 100% !important;
    max-width: 100% !important;
    box-sizing: border-box !important;
}
/* Remove padding from Output widget content area so map matches control width */
.widget-output:has(.output_map),
.jp-OutputArea:has(.output_map),
.jp-OutputArea-output:has(.output_map),
*:has(> .output_map) {
    padding-left: 0 !important;
    padding-right: 0 !important;
    width: 100% !important;
    max-width: 100% !important;
    box-sizing: border-box !important;
}
/* Map tab container: no extra padding, clip overflow for alignment */
.map-tab-container,
.widget-tab-contents > .widget-vbox:first-child {
    padding-left: 0 !important;
    padding-right: 0 !important;
    overflow-x: hidden !important;
}
/* Let the dashboard output cell expand so map and tabs are visible without scrolling */
.ebird-dashboard {
    min-height: 85vh !important;
}
.jp-OutputArea-output:has(.ebird-dashboard),
.jp-OutputArea:has(.ebird-dashboard) {
    min-height: 85vh !important;
    max-height: none !important;
}
/* Classic Jupyter */
.output_area:has(.ebird-dashboard) {
    min-height: 85vh !important;
    max-height: none !important;
}

/* ---- Modern UI theme (no new libs): typography, tables, buttons, tabs ---- */
.ebird-dashboard,
.ebird-dashboard .widget-html-content,
.ebird-dashboard .p-Widget {
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif !important;
    color: #1f2937 !important;
}
/* Buttons: rounded, subtle fill, hover */
.ebird-dashboard .widget-button,
.map-controls-panel .widget-button {
    border-radius: 6px !important;
    background: #f9fafb !important;
    border: 1px solid #e5e7eb !important;
    color: #374151 !important;
    padding: 6px 12px !important;
    font-size: 13px !important;
    transition: background 0.15s ease, border-color 0.15s ease !important;
    display: inline-flex !important;
    align-items: center !important;
    justify-content: center !important;
}
.ebird-dashboard .widget-button:hover,
.map-controls-panel .widget-button:hover {
    background: #f3f4f6 !important;
    border-color: #d1d5db !important;
}
/* Tables: card-like, rounded, soft stripes */
.stats-tbl,
.maint-tbl,
.maint-pair-tbl {
    border-collapse: collapse;
    width: 100%;
    max-width: none;
    font-size: 13px;
    margin-bottom: 16px;
    border-radius: 8px;
    overflow: visible;
    box-shadow: 0 1px 3px rgba(0,0,0,0.06);
}
.stats-tbl thead tr:first-child th:first-child,
.maint-tbl thead tr:first-child th:first-child,
.maint-pair-tbl thead tr:first-child th:first-child { border-radius: 8px 0 0 0; }
.stats-tbl thead tr:first-child th:last-child,
.maint-tbl thead tr:first-child th:last-child,
.maint-pair-tbl thead tr:first-child th:last-child { border-radius: 0 8px 0 0; }
.stats-tbl tbody tr:last-child td:first-child,
.maint-tbl tbody tr:last-child td:first-child,
.maint-pair-tbl tbody tr:last-child td:first-child { border-radius: 0 0 0 8px; }
.stats-tbl tbody tr:last-child td:last-child,
.maint-tbl tbody tr:last-child td:last-child,
.maint-pair-tbl tbody tr:last-child td:last-child { border-radius: 0 0 8px 0; }
.stats-tbl th,
.maint-tbl th,
.maint-pair-tbl th {
    font-weight: 600;
    text-align: left;
    padding: 10px 14px;
    background: #f8fafc;
    border-bottom: 1px solid #e5e7eb;
    color: #374151;
}
.stats-tbl td,
.maint-tbl td,
.maint-pair-tbl td {
    padding: 10px 14px;
    border-bottom: 1px solid #f1f5f9;
}
.stats-tbl tbody tr:nth-child(odd),
.maint-tbl tbody tr:nth-child(odd) { background: #fafbfc; }
.stats-tbl tbody tr:nth-child(even),
.maint-tbl tbody tr:nth-child(even) { background: #fff; }
.maint-pair-tbl tbody tr.pair-first { background: #fafbfc; }
.maint-pair-tbl tbody tr.pair-second { background: #fff; }
.stats-tbl td:last-child,
.maint-tbl td:last-child { font-weight: 600; }
.stats-tbl th:last-child { text-align: right; }
.stats-tbl td:last-child { text-align: right; }
/* Links: subtle blue, underline on hover */
.ebird-dashboard a {
    color: #374151;
    text-decoration: underline dotted;
    text-underline-offset: 2px;
}
.ebird-dashboard a:hover {
    color: #111827;
    text-decoration-color: rgba(0,0,0,0.4);
}
.stats-tbl a,
.maint-tbl a,
.maint-pair-tbl a {
    color: #374151;
    text-decoration: underline dotted;
    text-underline-offset: 2px;
}
.stats-tbl a:hover,
.maint-tbl a:hover,
.maint-pair-tbl a:hover {
    color: #111827;
    text-decoration-color: rgba(0,0,0,0.4);
}
/* Tab bar: cleaner labels */
.p-TabBar .p-TabBar-tab,
.jupyter-widgets .p-TabBar-tab {
    border-radius: 6px 6px 0 0 !important;
    padding: 8px 14px !important;
    font-size: 13px !important;
    font-weight: 500 !important;
    color: #6b7280 !important;
}
.p-TabBar .p-TabBar-tab.p-mod-current,
.jupyter-widgets .p-TabBar-tab.p-mod-current {
    background: #f9fafb !important;
    color: #111827 !important;
}
/* Rankings & other ipywidgets Accordions: match Maintenance card style */
.jupyter-widgets .p-Accordion-tab {
    background: #f9fafb !important;
    border: 1px solid #e5e7eb !important;
    border-radius: 6px !important;
    margin-bottom: 6px !important;
    padding: 4px 10px !important;
    font-size: 13px !important;
    font-weight: 600 !important;
    color: #374151 !important;
}
/* Section headings and body text in HTML widgets */
.ebird-dashboard h4 {
    color: #111827 !important;
    border-bottom: 1px solid #e5e7eb !important;
    padding-bottom: 6px !important;
    margin-bottom: 8px !important;
    font-weight: 600 !important;
}
/* Date controls in map toolbar: match species search box font */
.map-controls-panel .widget-datepicker input,
.map-controls-panel input[type="date"] {
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif !important;
    font-size: 13px !important;
}
.map-controls-panel .widget-datepicker .widget-label {
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif !important;
    font-size: 13px !important;
}
</style>
"""))


# %% [markdown] editable=true slideshow={"slide_type": ""} tags=["voila_hide"]
# ### 🧰 Package path (repo root on sys.path for `personal_ebird_explorer`).
#

# %%
_repo_root = os.path.abspath(os.path.join(os.getcwd(), ".."))
if _repo_root not in sys.path:
    sys.path.insert(0, _repo_root)


# %% [markdown] editable=true slideshow={"slide_type": ""} tags=["voila_hide"]
# ### ⚙️ Load config and eBird data (path resolution → load_dataset → optional date filter → locations, records_by_loc, totals).
#
# 📝 **Important:**  
# - The date filter only affects the main working dataset (`df`)  
# - Lifers and last-seen are calculated from the **full dataset**, unaffected by date filtering  
# - Popups and location visits reflect the filtered `df` — not full visit history
#
#
#

# %%
# --------------------------------------------
# ✅ Configuration & Data Loading
# --------------------------------------------
# Resolve data file location: try each candidate in order until file is found.
# Fallback order: (1) hardcoded path, (2) config_secret, (3) config_template, (4) notebook folder.
# Cross-platform: works on macOS and Windows.

def _load_config_module(path):
    """Load a config module from path; return DATA_FOLDER or None."""
    if not os.path.exists(path):
        return None
    try:
        spec = importlib.util.spec_from_file_location("config", path)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        return getattr(mod, "DATA_FOLDER", None)
    except Exception:
        return None

# Notebook directory: where this .py file lives (or cwd when running as .ipynb)
try:
    _notebook_dir = os.path.dirname(os.path.abspath(__file__))
except NameError:
    _notebook_dir = os.getcwd()

# Ensure repo root is on path so personal_ebird_explorer package can be imported
_repo_root = os.path.abspath(os.path.join(_notebook_dir, ".."))
if _repo_root not in sys.path:
    sys.path.insert(0, _repo_root)

# Scripts folder (relative to notebook)
_scripts_dir = os.path.abspath(os.path.join(_notebook_dir, "..", "scripts"))
_config_secret_path = os.path.join(_scripts_dir, "config_secret.py")
_config_template_path = os.path.join(_scripts_dir, "config_template.py")

# Build candidate folders and path source labels (for Settings tab, refs #38)
_candidate_folders = []
_path_sources = []
if DATA_FOLDER_HARDCODED and str(DATA_FOLDER_HARDCODED).strip():
    _candidate_folders.append(os.path.normpath(str(DATA_FOLDER_HARDCODED).strip()))
    _path_sources.append("hardcoded")
for _config_path in (_config_secret_path, _config_template_path):
    _folder = _load_config_module(_config_path)
    if _folder and str(_folder).strip():
        _candidate_folders.append(os.path.normpath(str(_folder).strip()))
        _path_sources.append("config_secret" if _config_path == _config_secret_path else "config_template")
_candidate_folders.append(_notebook_dir)
_path_sources.append("notebook folder")

# Find data file in first candidate that has it
from personal_ebird_explorer.path_resolution import find_data_file
file_path, DATA_FOLDER = find_data_file(EBIRD_DATA_FILE_NAME, _candidate_folders)
_path_source = None
if file_path and DATA_FOLDER:
    for i, cand in enumerate(_candidate_folders):
        if os.path.normpath(cand) == os.path.normpath(DATA_FOLDER):
            _path_source = _path_sources[i]
            break
    if _path_source is None:
        _path_source = "notebook folder"

if file_path is None:
    raise FileNotFoundError(
        f"Data file not found: {EBIRD_DATA_FILE_NAME}\n\n"
        f"Tried locations:\n  " + "\n  ".join(_candidate_folders) + "\n\n"
        "Options:\n"
        "  1. Set DATA_FOLDER_HARDCODED in User Variables (e.g. macOS: \"/Users/you/Documents/eBird\"; Windows: r\"C:\\Users\\you\\Documents\\eBird\")\n"
        "  2. Create scripts/config_secret.py with DATA_FOLDER = \"your/path\"\n"
        "  3. On Binder: upload your .csv to the notebook folder (File → Upload)\n\n"
        f"Expected filename: {EBIRD_DATA_FILE_NAME}"
    )

map_output_path = os.path.join(DATA_FOLDER, OUTPUT_HTML_FILE_NAME)
os.makedirs(DATA_FOLDER, exist_ok=True)

# Load data
from personal_ebird_explorer.data_loader import load_dataset
df = load_dataset(file_path)
df_full = df.copy()  # Keep full dataset for Map maintenance tab (unaffected by date filter)

# Apply date filter if enabled
if FILTER_BY_DATE:
    try:
        start = datetime.strptime(FILTER_START_DATE, "%Y-%m-%d")
        end = datetime.strptime(FILTER_END_DATE, "%Y-%m-%d")
        assert start <= end, "Start date must be before end date"
        df = df[(df["Date"] >= start) & (df["Date"] <= end)]
    except Exception as e:
        raise ValueError(f"Invalid date filter settings: {e}")

# Exclude locations with no associated checklist in the export (e.g. orphaned from cleanup, shared-list quirks)
location_ids_with_checklists = set(df_full.dropna(subset=["Submission ID"])["Location ID"].unique())
df = df[df["Location ID"].isin(location_ids_with_checklists)]
df_full = df_full[df_full["Location ID"].isin(location_ids_with_checklists)]

# Extract location and species info
location_data = df[['Location ID', 'Location', 'Latitude', 'Longitude']].drop_duplicates()
full_location_data = df_full[['Location ID', 'Location', 'Latitude', 'Longitude']].drop_duplicates()
# Stable for session: group df by Location ID for O(1) lookup in map redraws (refs #37)
records_by_loc = {lid: grp for lid, grp in df.groupby("Location ID")}
# Per-species groupby cache for species-filtered redraws; LRU eviction when over cap; cleared when data-prep re-run (refs #37)
# Cap is arbitrary and experimental (based on author usage); adjust based on feedback and experience.
_FILTERED_BY_LOC_CACHE_MAX = 60
_filtered_by_loc_cache = OrderedDict()
# Popup HTML cache: key (location_id, selected_species or ""); cleared when data-prep re-run (refs #37)
_popup_html_cache = {}
species_list = sorted(df["Common Name"].dropna().unique().tolist())

from personal_ebird_explorer.ui_state import ExplorerState
state = ExplorerState()

# Pre-calculate totals for "all species" banner (Count can be "X" for present; treat as 1)
from personal_ebird_explorer.stats import (
    safe_count as _safe_count,
    get_sex_notation_by_year as _get_sex_notation_by_year,
)
from personal_ebird_explorer.checklist_stats_compute import compute_checklist_stats_payload
from personal_ebird_explorer.checklist_stats_display import (
    format_checklist_stats_bundle,
    format_rankings_tab_html,
)
from personal_ebird_explorer.lifer_last_seen_prep import prepare_lifer_last_seen


from personal_ebird_explorer.map_renderer import (
    format_visit_time as _format_visit_time,
    format_sighting_row as _format_sighting_row,
    popup_scroll_script as _popup_scroll_script,
    create_map as _create_map,
    build_all_species_banner_html as _build_all_species_banner_html,
    build_species_banner_html as _build_species_banner_html,
    build_legend_html as _build_legend_html,
    build_visit_info_html as _build_visit_info_html,
    build_location_popup_html as _build_location_popup_html,
    resolve_lifer_last_seen as _resolve_lifer_last_seen,
    classify_locations as _classify_locations,
)

from personal_ebird_explorer.species_logic import (
    countable_species_vectorized as _countable_species_vectorized,
    filter_species,
    base_species_for_lifer as _base_species_for_lifer,
)

total_checklists = df["Submission ID"].nunique()
total_individuals = int(df["Count"].apply(_safe_count).sum())
total_species = int(_countable_species_vectorized(df).dropna().nunique())

# When date filter is on, keep full-data structures so Reset View can show unfiltered map (refs #47)
records_by_loc_full = {}
total_checklists_full = total_checklists
total_species_full = total_species
total_individuals_full = total_individuals
_date_filter_off_for_view = False
if FILTER_BY_DATE:
    records_by_loc_full = {lid: grp for lid, grp in df_full.groupby("Location ID")}
    total_checklists_full = df_full["Submission ID"].nunique()
    total_species_full = int(_countable_species_vectorized(df_full).dropna().nunique())
    total_individuals_full = int(df_full["Count"].apply(_safe_count).sum())

# Build common → scientific name map
name_map = (
    df[['Common Name', 'Scientific Name']]
    .dropna()
    .drop_duplicates()
    .set_index('Common Name')['Scientific Name']
    .to_dict()
)

# eBird taxonomy for species links (refs #56): load once; on failure links are skipped
from personal_ebird_explorer.taxonomy import load_taxonomy, get_species_url, get_species_and_lifelist_urls
_taxonomy_loaded = load_taxonomy(locale=EBIRD_TAXONOMY_LOCALE if EBIRD_TAXONOMY_LOCALE else None)
_species_url_fn = get_species_url if _taxonomy_loaded else (lambda _: None)
_link_urls_fn = get_species_and_lifelist_urls if _taxonomy_loaded else (lambda _: (None, None))


# %% [markdown] editable=true slideshow={"slide_type": ""} tags=["voila_hide"]
# ### 🔍 Whoosh index for species autocomplete.
#

# %%
# --------------------------------------------
# ✅  Build Whoosh index for species autocomplete
# --------------------------------------------
schema = Schema(common_name=TEXT(stored=True, analyzer=StemmingAnalyzer()))
index_dir = tempfile.mkdtemp()
ix = create_in(index_dir, schema)

writer = ix.writer()
for name in species_list:
    writer.add_document(common_name=name)
writer.commit()


# %%
# --------------------------------------------
# ✅ Re-apply date filter and rebuild map data (dynamic date filter, refs #38; logic in working_set #66)
# --------------------------------------------
def _apply_date_filter_and_build_map_data():
    """Recompute df, records_by_loc, species_list, totals, and caches from df_full using current FILTER_* globals. Rebuilds Whoosh index. Call after changing date filter."""
    global df, location_data, records_by_loc, species_list
    global total_checklists, total_individuals, total_species
    global name_map, records_by_loc_full, total_checklists_full, total_species_full, total_individuals_full
    from personal_ebird_explorer.working_set import rebuild_working_set_from_date_filter

    ws = rebuild_working_set_from_date_filter(
        df_full,
        location_ids_with_checklists,
        filter_by_date=FILTER_BY_DATE,
        filter_start_date=FILTER_START_DATE,
        filter_end_date=FILTER_END_DATE,
        whoosh_index=ix,
        map_caches=(_popup_html_cache, _filtered_by_loc_cache),
    )
    if ws is None:
        return  # leave state unchanged on invalid dates
    df = ws.df
    location_data = ws.location_data
    records_by_loc = ws.records_by_loc
    species_list = ws.species_list
    total_checklists = ws.total_checklists
    total_individuals = ws.total_individuals
    total_species = ws.total_species
    name_map = ws.name_map
    records_by_loc_full = ws.records_by_loc_full
    total_checklists_full = ws.total_checklists_full
    total_species_full = ws.total_species_full
    total_individuals_full = ws.total_individuals_full


# %% [markdown] editable=true slideshow={"slide_type": ""} tags=["voila_hide"]
# ### 🗺️ Map output widgets (map lives in state; these are display containers).
#

# %%
# --------------------------------------------
# ✅ Initialise map output widgets (double-buffer for smoother redraws, refs #45)
# --------------------------------------------
_map_output_layout = widgets.Layout(min_height="500px", width="100%", min_width="0", flex="1 1 auto")
map_output_0 = widgets.Output(layout=_map_output_layout)
map_output_1 = widgets.Output(layout=_map_output_layout)
_map_outputs = [map_output_0, map_output_1]
_map_front_index = 0  # which buffer is currently shown in the map tab
output = widgets.Output()


# %% [markdown] editable=true slideshow={"slide_type": ""} tags=["voila_hide"]
# ### 🔍 Autocomplete UI (search box + matches dropdown).
#

# %%
# --------------------------------------------
# ✅ Autocomplete UI Widgets
# --------------------------------------------
# Input width: longest species name + 20%, capped (avoids full-width stretch when empty)
_max_name_len = max(len(s) for s in species_list) if species_list else 25
_species_input_ch = min(int(_max_name_len * 1.2) + 4, 52)
_species_input_width = f"{_species_input_ch}ch"
_species_label_width = "70px"  # align matches dropdown under input (not the label)

search_box = widgets.Text(placeholder="Type species name...", description="Species:")
search_box.layout = widgets.Layout(width=_species_input_width, min_width="12ch")
search_box.style.description_width = _species_label_width

matches_dropdown = widgets.Select(options=[], value=None, description="", rows=6)
matches_dropdown.layout = widgets.Layout(
    width=_species_input_width,
    min_width="12ch",
    margin=f"0 0 0 {_species_label_width}",
    display="none",  # hidden until we have suggestions
)

hide_non_matching_checkbox = Checkbox(
    value=False,
    description='Show only selected species',
    indent=False
)


# %% [markdown] editable=true slideshow={"slide_type": ""} tags=["voila_hide"]
# ### 📍 Maintenance tab HTML helpers (imported from personal_ebird_explorer; refs #69).
#

# %%
from personal_ebird_explorer.maintenance_display import (
    format_map_maintenance_html,
    format_sex_notation_maintenance_html,
    format_incomplete_checklists_maintenance_html,
)
from personal_ebird_explorer.species_search import whoosh_common_name_suggestions


# %% [markdown] editable=true slideshow={"slide_type": ""} tags=["voila_hide"]
# ### 🐣 Lifer and last-seen lookups (from full dataset; used for pin highlighting).
#

# %%
# --------------------------------------------
# ✅ Build True Lifer and Last-Seen Tables (from full dataset; refs #68)
# --------------------------------------------

# Reload full dataset to avoid filtering effects (date filter, lifer calc)
full_df = load_dataset(file_path)
# Exclude locations with no checklist (consistent with main data)
full_df = full_df[full_df["Location ID"].isin(location_ids_with_checklists)]

_lls = prepare_lifer_last_seen(full_df, base_species_fn=_base_species_for_lifer)
_lifer_lookup_df = _lls.lifer_lookup_df
true_lifer_locations = _lls.true_lifer_locations
true_last_seen_locations = _lls.true_last_seen_locations
true_lifer_locations_taxon = _lls.true_lifer_locations_taxon
true_last_seen_locations_taxon = _lls.true_last_seen_locations_taxon


# %% [markdown] editable=true slideshow={"slide_type": ""} tags=["voila_hide"]
# ### 🎛️ UI event handlers (search, dropdown, reset, toggle).
#

# %%
# --------------------------------------------
# ✅ UI Event Handlers
# --------------------------------------------

# Re-entry guards and selection state live in `state` (ExplorerState instance, created above).


def _show_matches_dropdown(show):
    """Show or hide the matches dropdown based on whether we have options."""
    matches_dropdown.layout.display = "flex" if show else "none"


def update_suggestions(change):
    """Whoosh search as user types; show/hide matches dropdown. When search is empty, reset (clear) in this context."""
    if state.skip_next_suggestion_update:
        state.skip_next_suggestion_update = False
        return
    state.updating_suggestions = True
    try:
        query = (change.get("new") or "").strip().lower()
        if query == "":
            state.skip_next_suggestion_update = True
            _clear_to_all_species()
            return
        if len(query) < 3:
            matches_dropdown.options = []
            _show_matches_dropdown(False)
            return
        opts = whoosh_common_name_suggestions(ix, query, max_options=6, min_query_len=3)
        matches_dropdown.options = opts
        matches_dropdown.value = None
        _show_matches_dropdown(len(opts) > 0)
    finally:
        state.updating_suggestions = False


def on_species_selected(change):
    """Handle dropdown selection: set species and redraw map; if dropdown and search both empty, reset to all species."""
    selected = change.get("new")
    search_text = search_box.value.strip()

    if selected is None and search_text == "":
        _clear_to_all_species()
        return
    if state.updating_suggestions:
        return
    output.clear_output()
    if selected is None:
        return
    state.selected_species_scientific = name_map.get(selected, "").strip()
    state.selected_species_common = selected
    with output:
        print(f"🔎 Selected species: {selected} → Scientific: {state.selected_species_scientific}")
    draw_map_with_species_overlay(state.selected_species_scientific, state.selected_species_common)
    state.skip_next_suggestion_update = True
    search_box.value = selected
    matches_dropdown.options = []
    _show_matches_dropdown(False)


def on_toggle_change(change):
    """Redraw map when user toggles 'Show only selected species' (no-op when suppress_toggle_redraw)."""
    if state.suppress_toggle_redraw:
        return
    with output:
        print(f"🧪 Toggle changed: {change['new']} — Current species: {state.selected_species_scientific}")
    draw_map_with_species_overlay(state.selected_species_scientific, state.selected_species_common)


def _date_filter_status_text():
    """Return short status for date filter (refs #47)."""
    if not FILTER_BY_DATE:
        return "Date filter: Off"
    if _date_filter_off_for_view:
        return "Date filter: Off (showing full data)"
    return f"Date filter: {FILTER_START_DATE} to {FILTER_END_DATE}"


def _clear_to_all_species():
    """Reset view: clear species, uncheck 'show only selected', redraw. Does not change date filter (refs #47)."""
    state.skip_next_suggestion_update = True  # avoid update_suggestions re-entering when we clear search_box
    search_box.value = ""
    matches_dropdown.options = []
    matches_dropdown.value = None
    _show_matches_dropdown(False)
    state.clear_selection()
    state.suppress_toggle_redraw = True
    hide_non_matching_checkbox.value = False
    state.suppress_toggle_redraw = False
    with output:
        output.clear_output()
        print("🧹 Reset view — showing all locations")
    draw_map_with_species_overlay("", "")


def _export_map_html():
    """Save current map HTML to file on demand (refs #47)."""
    if state.species_map is None:
        with output:
            output.clear_output()
            print("⚠️ No map to export. Open the Map tab and wait for the map to draw.")
        return
    state.species_map.save(map_output_path)
    with output:
        output.clear_output()
        print(f"✅ Map exported to {map_output_path}")


# %% [markdown] editable=true slideshow={"slide_type": ""} tags=["voila_hide"]
# ### 🧷 Register widget observers.
#

# %%
# --------------------------------------------
# ✅ Register observers
# --------------------------------------------
search_box.observe(update_suggestions, names="value")
matches_dropdown.observe(on_species_selected, names="value")
hide_non_matching_checkbox.observe(on_toggle_change, names="value")


# %% [markdown] editable=true slideshow={"slide_type": ""} tags=["voila_hide"]
# ### 🗺️ Map helpers (imported from personal_ebird_explorer.map_renderer).
#

# %%
# Map helpers are imported from personal_ebird_explorer.map_renderer
# in the cell group above (see imports after stats).


# %% [markdown] editable=true slideshow={"slide_type": ""} tags=["voila_hide"]
# ### 🗺️ Draw map (all-species or species-filtered; banners, popups, export on demand).
#

# %%
# --------------------------------------------
# ✅ Draw map with species overlay
# --------------------------------------------
def draw_map_with_species_overlay(selected_species, selected_common_name=""):
    global _map_front_index
    # When date filter was on at load and user clicked Reset View, show full data (refs #47)
    effective_use_full = bool(FILTER_BY_DATE and _date_filter_off_for_view)
    if effective_use_full:
        effective_location_data = full_location_data
        effective_records_by_loc = records_by_loc_full
        effective_totals = (total_checklists_full, total_species_full, total_individuals_full)
    else:
        effective_location_data = location_data
        effective_records_by_loc = records_by_loc
        effective_totals = (total_checklists, total_species, total_individuals)

    if selected_species:
        filtered = filter_species(df, selected_species)
        if filtered.empty:
            with output:
                output.clear_output()
                print(f"⚠️ No sightings of '{selected_species}' in current data — check date range or filters.")
            return
        seen_location_ids = set(filtered["Location ID"])
        species_locations = location_data[location_data["Location ID"].isin(seen_location_ids)]
        map_center = [species_locations["Latitude"].mean(), species_locations["Longitude"].mean()]
    else:
        map_center = [effective_location_data["Latitude"].mean(), effective_location_data["Longitude"].mean()]

    state.species_map = _create_map(map_center, MAP_STYLE)

    # records_by_loc is built once at data prep (refs #37); reused on every redraw
    if not selected_species:
        # Case 1: No species selected – draw all as green, show totals banner
        tc, ts, ti = effective_totals
        state.species_map.get_root().html.add_child(Element(
            _build_all_species_banner_html(tc, ts, ti, _date_filter_status_text())
        ))
        state.species_map.get_root().html.add_child(Element(
            _build_legend_html([(DEFAULT_COLOR, DEFAULT_FILL, "All locations")])
        ))

        popup_asc = POPUP_SORT_ORDER == "ascending"
        for _, row in effective_location_data.iterrows():
            popup_key = (row["Location ID"], "", effective_use_full)
            if popup_key not in _popup_html_cache:
                base_records = effective_records_by_loc.get(row["Location ID"], pd.DataFrame())
                visit_records = base_records.drop_duplicates(subset=["Submission ID"]).sort_values("datetime", ascending=popup_asc)
                visit_info = _build_visit_info_html(visit_records, _format_visit_time)
                _popup_html_cache[popup_key] = _build_location_popup_html(row["Location"], row["Location ID"], visit_info)
            popup_html = _popup_html_cache[popup_key]
            folium.CircleMarker(
                location=[row['Latitude'], row['Longitude']],
                radius=4,
                color=DEFAULT_COLOR,
                fill=True,
                fill_color=DEFAULT_FILL,
                fill_opacity=0.6,
                popup=folium.Popup(popup_html, max_width=800),
            ).add_to(state.species_map)

    else:
        # Case 2: Filtered by species (filtered, seen_location_ids already computed above)
        popup_asc = POPUP_SORT_ORDER == "ascending"
        if selected_species not in _filtered_by_loc_cache:
            if len(_filtered_by_loc_cache) >= _FILTERED_BY_LOC_CACHE_MAX:
                _filtered_by_loc_cache.popitem(last=False)
            _filtered_by_loc_cache[selected_species] = {lid: grp for lid, grp in filtered.groupby("Location ID")}
        else:
            _filtered_by_loc_cache.move_to_end(selected_species)
        filtered_by_loc = _filtered_by_loc_cache[selected_species]

        # Stats for banner (Count can be "X" for present; treat as 1)
        n_checklists = filtered["Submission ID"].nunique()
        n_individuals = int(filtered["Count"].apply(_safe_count).sum())
        high_count = int(filtered["Count"].apply(_safe_count).max())

        # Banner date format: dd MMM yyyy (e.g. 22 Jan 2025)
        def _banner_date(d):
            return d.strftime("%d-%b-%Y") if pd.notna(d) else "?"

        # First seen / last seen (dates only, same as lifer and last-seen pins)
        first_seen_date = ""
        last_seen_date = ""
        high_count_date = ""
        sci_parts_banner = (selected_species or "").strip().split()
        is_subspecies_banner = len(sci_parts_banner) >= 3
        taxon_key_banner = selected_species.strip().lower() if selected_species else None
        if is_subspecies_banner and taxon_key_banner:
            subset = _lifer_lookup_df[_lifer_lookup_df["_taxon"] == taxon_key_banner]
        else:
            base = _base_species_for_lifer(selected_species)
            subset = _lifer_lookup_df[_lifer_lookup_df["_base"] == base] if base else pd.DataFrame()
        if not subset.empty:
            first_rec = subset.iloc[0]
            last_rec = subset.iloc[-1]
            first_seen_date = _banner_date(first_rec["Date"])
            last_seen_date = _banner_date(last_rec["Date"])

        # Date when high count was achieved
        high_count_rows = filtered[filtered["Count"].apply(_safe_count) == high_count]
        if not high_count_rows.empty:
            high_count_date = _banner_date(high_count_rows.iloc[0]["Date"])

        state.species_map.get_root().html.add_child(Element(
            _build_species_banner_html(
                display_name=selected_common_name or selected_species,
                n_checklists=n_checklists,
                n_individuals=n_individuals,
                high_count=high_count,
                first_seen_date=first_seen_date,
                last_seen_date=last_seen_date,
                high_count_date=high_count_date,
                date_filter_status=_date_filter_status_text(),
                species_url=_species_url_fn(selected_common_name or selected_species) if _species_url_fn else None,
            )
        ))

        lifer_location, last_seen_location = _resolve_lifer_last_seen(
            selected_species,
            seen_location_ids,
            lifer_lookup=true_lifer_locations,
            last_seen_lookup=true_last_seen_locations,
            lifer_lookup_taxon=true_lifer_locations_taxon,
            last_seen_lookup_taxon=true_last_seen_locations_taxon,
            base_species_fn=_base_species_for_lifer,
            mark_lifer=MARK_LIFER,
            mark_last_seen=MARK_LAST_SEEN,
        )
        location_data_local = _classify_locations(
            location_data, seen_location_ids, lifer_location, last_seen_location,
        )

        # Pin legend: only show pin types that are actually drawn (refs #40)
        pin_types_present = set()
        for _, row in location_data_local.iterrows():
            if not row["has_species_match"] and hide_non_matching_checkbox.value:
                continue
            if row["is_lifer"]:
                pin_types_present.add("Lifer")
            elif row["is_last_seen"]:
                pin_types_present.add("Last seen")
            elif row["has_species_match"]:
                pin_types_present.add("Species")
            else:
                pin_types_present.add("Other")
        legend_order = [("Lifer", LIFER_COLOR, LIFER_FILL), ("Last seen", LAST_SEEN_COLOR, LAST_SEEN_FILL), ("Species", SPECIES_COLOR, SPECIES_FILL), ("Other", DEFAULT_COLOR, DEFAULT_FILL)]
        legend_items = [(c, f, label) for label, c, f in legend_order if label in pin_types_present]
        state.species_map.get_root().html.add_child(Element(
            _build_legend_html(legend_items)
        ))

        # Single loop for marker drawing
        for _, row in location_data_local.iterrows():
            loc_id = row["Location ID"]

            if not row["has_species_match"] and hide_non_matching_checkbox.value:
                continue

            popup_key = (loc_id, selected_species)
            if popup_key not in _popup_html_cache:
                base_records = records_by_loc.get(loc_id, pd.DataFrame())
                visit_records = base_records.drop_duplicates(subset=["Submission ID"]).sort_values("datetime", ascending=popup_asc)
                visit_info = _build_visit_info_html(visit_records, _format_visit_time)
                sightings_html = ""
                if row["has_species_match"]:
                    sub = filtered_by_loc.get(loc_id, pd.DataFrame()).sort_values("datetime", ascending=popup_asc)
                    sightings_html = "".join(_format_sighting_row(r) for _, r in sub.iterrows())
                _popup_html_cache[popup_key] = _build_location_popup_html(row["Location"], loc_id, visit_info, sightings_html)
            popup_html = _popup_html_cache[popup_key]
            popup_content = folium.Popup(popup_html, max_width=800)

            if row["is_lifer"]:
                color, fill, radius, fill_opacity = LIFER_COLOR, LIFER_FILL, 4, 0.9
            elif row["is_last_seen"]:
                color, fill, radius, fill_opacity = LAST_SEEN_COLOR, LAST_SEEN_FILL, 4, 0.9
            elif row["has_species_match"]:
                color, fill, radius, fill_opacity = SPECIES_COLOR, SPECIES_FILL, 4, 0.9
            else:
                color, fill, radius, fill_opacity = DEFAULT_COLOR, DEFAULT_FILL, 4, 0.9

            folium.CircleMarker(
                location=[row['Latitude'], row['Longitude']],
                radius=radius,
                color=color,
                fill=True,
                fill_color=fill,
                fill_opacity=fill_opacity,
                popup=popup_content
            ).add_to(state.species_map)

    scroll_popup_script = _popup_scroll_script(POPUP_SCROLL_HINT, POPUP_SORT_ORDER == "ascending")
    state.species_map.get_root().html.add_child(Element(scroll_popup_script))

    # Double-buffer: draw into the hidden output, then swap so the visible map never clears (refs #45)
    map_html = state.species_map._repr_html_()
    back_index = 1 - _map_front_index
    map_output_back = _map_outputs[back_index]
    with map_output_back:
        map_output_back.clear_output()
        display(HTML(f'<div class="output_map">{map_html}</div>'))
    map_tab_container.children = [map_controls, map_output_back]
    _map_front_index = back_index

    # Export is explicit via "Export Map HTML" button (refs #47); no automatic save on redraw



# %% [markdown] editable=true slideshow={"slide_type": ""} tags=["voila_hide"]
# ### 🧭 Display UI (dashboard in next cell).
#

# %%
# --------------------------------------------
# ✅ Display UI (controls + map/tabs combined below)
# --------------------------------------------
# Controls and map/tabs are displayed together in the next cell to avoid a gap.



# %% [markdown] editable=true slideshow={"slide_type": ""} tags=["voila_hide"]
# ### 🗺️ Dashboard (controls + map + stats tabs).
#

# %%
# --------------------------------------------
# ✅ Checklist Statistics (compute + HTML in modules; refs #68, #56)
# --------------------------------------------
def _compute_checklist_stats(df, link_urls_fn=None):
    """Compute checklist statistics from df; returns dict with stats_html, rankings sections, incomplete_by_year.

    Optional link_urls_fn(common_name) -> (species_url, lifelist_url) enables eBird links (refs #56).
    """
    payload = compute_checklist_stats_payload(df, TOP_N_TABLE_LIMIT)
    return format_checklist_stats_bundle(
        payload,
        link_urls_fn=link_urls_fn,
        scroll_hint=POPUP_SCROLL_HINT,
        visible_rows=RANKINGS_TABLE_VISIBLE_ROWS,
    )


# Stats use df_full for all-time totals (unfiltered by date). Map uses df, which may be date-filtered.
checklist_data = _compute_checklist_stats(df_full, link_urls_fn=_link_urls_fn)
checklist_stats_panel = widgets.HTML(value=checklist_data["stats_html"])

# Rankings tab: two groups (Top N + Other) with headings (refs #69: format_rankings_tab_html)
rankings_panel = widgets.HTML(
    value=format_rankings_tab_html(
        checklist_data["rankings_sections_top_n"],
        checklist_data["rankings_sections_other"],
        top_n_limit=TOP_N_TABLE_LIMIT,
    )
)


# Map maintenance tab HTML (refs #69: personal_ebird_explorer.maintenance_display)
map_maintenance_html = format_map_maintenance_html(full_location_data, CLOSE_LOCATION_METERS)

incomplete_checklists_html = format_incomplete_checklists_maintenance_html(checklist_data.get("incomplete_by_year", {}))
sex_notation_by_year = _get_sex_notation_by_year(df_full)
sex_notation_html = format_sex_notation_maintenance_html(sex_notation_by_year, species_url_fn=_species_url_fn)
map_maintenance_html_widget = widgets.HTML(value=map_maintenance_html)
_maintenance_panel_parts = [map_maintenance_html_widget]
if incomplete_checklists_html:
    _maintenance_panel_parts.append(widgets.HTML(value=incomplete_checklists_html))
if sex_notation_html:
    _maintenance_panel_parts.append(widgets.HTML(value=sex_notation_html))
map_maintenance_panel = VBox(_maintenance_panel_parts)

# --------------------------------------------
# Build map tab: date filter + species/search/buttons on one row; matches dropdown below (refs #38, #47).
# --------------------------------------------
# Date inputs: use DatePicker if available (ipywidgets 8+), else wider Text so full YYYY-MM-DD is readable
_use_date_picker = getattr(widgets, "DatePicker", None) is not None
def _date_to_str(d):
    if d is None:
        return "2026-01-01"
    if hasattr(d, "isoformat"):
        return d.isoformat()
    return str(d)
def _str_to_date(s):
    s = (s or "").strip() or "2026-01-01"
    try:
        return datetime.strptime(s, "%Y-%m-%d").date()
    except Exception:
        return date(2026, 1, 1)
if _use_date_picker:
    _start_val = _str_to_date(FILTER_START_DATE)
    _end_val = _str_to_date(FILTER_END_DATE)
    filter_start_date_widget = widgets.DatePicker(value=_start_val, description="Start", layout=widgets.Layout(width="230px"))
    filter_end_date_widget = widgets.DatePicker(value=_end_val, description="End", layout=widgets.Layout(width="230px"))
else:
    filter_start_date_widget = widgets.Text(value=FILTER_START_DATE, description="Start", placeholder="YYYY-MM-DD", layout=widgets.Layout(width="160px", min_width="14ch"))
    filter_end_date_widget = widgets.Text(value=FILTER_END_DATE, description="End", placeholder="YYYY-MM-DD", layout=widgets.Layout(width="160px", min_width="14ch"))
filter_by_date_checkbox = Checkbox(value=FILTER_BY_DATE, description="", layout=widgets.Layout(width="auto"))
date_filter_label = widgets.Label(value="Date filter", layout=widgets.Layout(margin="0 4px 0 0"))
date_filter_control = HBox([filter_by_date_checkbox, date_filter_label], layout=widgets.Layout(align_items="center"))

def _on_date_filter_change(_=None):
    """Apply date filter from widgets and redraw map (dynamic; does not reset on Reset View)."""
    global FILTER_BY_DATE, FILTER_START_DATE, FILTER_END_DATE
    FILTER_BY_DATE = filter_by_date_checkbox.value
    if _use_date_picker:
        FILTER_START_DATE = _date_to_str(filter_start_date_widget.value)
        FILTER_END_DATE = _date_to_str(filter_end_date_widget.value)
    else:
        FILTER_START_DATE = (filter_start_date_widget.value or "").strip() or "2026-01-01"
        FILTER_END_DATE = (filter_end_date_widget.value or "").strip() or "2026-12-31"
        filter_start_date_widget.value = FILTER_START_DATE
        filter_end_date_widget.value = FILTER_END_DATE
    _apply_date_filter_and_build_map_data()
    with output:
        output.clear_output()
        print("📅 Date filter updated — map redrawn.")
    draw_map_with_species_overlay(state.selected_species_scientific, state.selected_species_common)

filter_by_date_checkbox.observe(_on_date_filter_change, names="value")
filter_start_date_widget.observe(_on_date_filter_change, names="value")
filter_end_date_widget.observe(_on_date_filter_change, names="value")

_spacer = Box(layout=widgets.Layout(width="0.75em", min_width="0.75em"))
_spacer_small = Box(layout=widgets.Layout(width="0.4em", min_width="0.4em"))  # tight gap between species and date to avoid wrap
reset_view_btn = widgets.Button(description="Reset View", layout=widgets.Layout(width="100px"))
reset_view_btn.on_click(lambda _: _clear_to_all_species())
export_map_btn = widgets.Button(description="Export Map HTML", layout=widgets.Layout(width="140px"))
export_map_btn.on_click(lambda _: _export_map_html())
# Single horizontal row: species | date filter | reset | export (small spacers between sections to save space)
map_control_row = HBox(
    [
        search_box,
        _spacer,
        hide_non_matching_checkbox,
        _spacer_small,
        date_filter_control,
        filter_start_date_widget,
        filter_end_date_widget,
        _spacer_small,
        reset_view_btn,
        export_map_btn,
    ],
    layout=widgets.Layout(align_items="center", flex_flow="wrap"),
)
map_controls = VBox([map_control_row, matches_dropdown])
map_controls.layout = widgets.Layout(width="100%", min_width="0")

map_tab_container = VBox(
    [map_controls, _map_outputs[_map_front_index]],
    layout=widgets.Layout(min_height="600px", width="100%"),
)
map_tab_container.add_class("map-tab-container")

# --------------------------------------------
# Settings tab (refs #38): session-only live controls for map/list rendering; path/locale are information-only and require notebook re-run to change.
# --------------------------------------------
_NAMED_COLOURS = [
    "white", "black", "red", "lime", "blue", "yellow", "cyan", "magenta", "orange", "purple",
    "pink", "lightgreen", "lightblue", "gray", "lightgray", "darkgray", "coral", "gold", "green",
]
_path_display = (DATA_FOLDER or "(not set)") if file_path else "(data not loaded)"
_path_source_label = (_path_source or "—").replace("_", " ").title()
settings_intro = widgets.HTML(value=(
    "<div style='margin:0 0 12px 0;font-size:12px;color:#555;line-height:1.5;'>"
    "<div><strong>Note:</strong> Some Settings update immediately during this session (Map display, Tables & lists). Data & path is information-only; to persist or change those values, edit the notebook’s User Variables and re-run.</div>"
    "</div>"
))
# Data & path section (read-only info)
settings_data_header = widgets.HTML(value=(
    "<span style='color:#888;font-size:11px;'>Information only. Data path/file/locale are configured in the notebook User Variables. See docs/explorer/README.md.</span>"
))
_settings_path_table = (
    "<table style='margin:4px 0;font-size:12px;font-family:inherit;border-collapse:collapse;border:none;'>"
    f"<tr><td style='border:none;padding:2px 8px 2px 0;vertical-align:top;white-space:nowrap;'>Path:</td>"
    f"<td style='border:none;padding:2px 0;word-break:break-all;'>{_path_display}</td></tr>"
    f"<tr><td style='border:none;padding:2px 8px 2px 0;vertical-align:top;white-space:nowrap;'>Source:</td>"
    f"<td style='border:none;padding:2px 0;'>{_path_source_label}</td></tr>"
    f"<tr><td style='border:none;padding:2px 8px 2px 0;vertical-align:top;white-space:nowrap;'>File:</td>"
    f"<td style='border:none;padding:2px 0;'>{EBIRD_DATA_FILE_NAME}</td></tr>"
    f"<tr><td style='border:none;padding:2px 8px 2px 0;vertical-align:top;white-space:nowrap;'>Taxonomy locale:</td>"
    f"<td style='border:none;padding:2px 0;'>{EBIRD_TAXONOMY_LOCALE or '(API default)'}</td></tr>"
    "</table>"
)
settings_path_html = widgets.HTML(value=_settings_path_table)
settings_data_section = VBox([settings_data_header, settings_path_html], layout=widgets.Layout(width="100%"))

# Map display section
settings_display_header = widgets.HTML(value="<span style='color:#0a0;font-size:11px;'>Changes apply immediately</span>")
map_style_header = widgets.HTML(value="<strong>Map Style</strong>")
map_style_dropdown = widgets.Dropdown(options=["default", "satellite", "google", "carto"], value=MAP_STYLE, description="", layout=widgets.Layout(width="200px"))
map_style_row = HBox(
    [widgets.Label(value="Style:", layout=widgets.Layout(width="50px")), map_style_dropdown],
    layout=widgets.Layout(align_items="center", margin="2px 0 0 0"),
)
def _on_map_style_change(change):
    global MAP_STYLE
    v = change.get("new")
    if v is not None:
        MAP_STYLE = v
        draw_map_with_species_overlay(state.selected_species_scientific, state.selected_species_common)
map_style_dropdown.observe(_on_map_style_change, names="value")

def _on_pin_color_change(_=None):
    global LIFER_COLOR, LIFER_FILL, LAST_SEEN_COLOR, LAST_SEEN_FILL, SPECIES_COLOR, SPECIES_FILL, DEFAULT_COLOR, DEFAULT_FILL
    LIFER_COLOR, LIFER_FILL = lifer_color_dd.value, lifer_fill_dd.value
    LAST_SEEN_COLOR, LAST_SEEN_FILL = last_seen_color_dd.value, last_seen_fill_dd.value
    SPECIES_COLOR, SPECIES_FILL = species_color_dd.value, species_fill_dd.value
    DEFAULT_COLOR, DEFAULT_FILL = default_color_dd.value, default_fill_dd.value
    draw_map_with_species_overlay(state.selected_species_scientific, state.selected_species_common)
lifer_color_dd = widgets.Dropdown(options=_NAMED_COLOURS, value=LIFER_COLOR, description="", layout=widgets.Layout(width="150px"))
lifer_fill_dd = widgets.Dropdown(options=_NAMED_COLOURS, value=LIFER_FILL, description="", layout=widgets.Layout(width="150px"))
last_seen_color_dd = widgets.Dropdown(options=_NAMED_COLOURS, value=LAST_SEEN_COLOR, description="", layout=widgets.Layout(width="150px"))
last_seen_fill_dd = widgets.Dropdown(options=_NAMED_COLOURS, value=LAST_SEEN_FILL, description="", layout=widgets.Layout(width="150px"))
species_color_dd = widgets.Dropdown(options=_NAMED_COLOURS, value=SPECIES_COLOR, description="", layout=widgets.Layout(width="150px"))
species_fill_dd = widgets.Dropdown(options=_NAMED_COLOURS, value=SPECIES_FILL, description="", layout=widgets.Layout(width="150px"))
default_color_dd = widgets.Dropdown(options=_NAMED_COLOURS, value=DEFAULT_COLOR, description="", layout=widgets.Layout(width="150px"))
default_fill_dd = widgets.Dropdown(options=_NAMED_COLOURS, value=DEFAULT_FILL, description="", layout=widgets.Layout(width="150px"))
for _dd in [lifer_color_dd, lifer_fill_dd, last_seen_color_dd, last_seen_fill_dd, species_color_dd, species_fill_dd, default_color_dd, default_fill_dd]:
    _dd.observe(_on_pin_color_change, names="value")

mark_lifer_cb = Checkbox(value=MARK_LIFER, description="Mark lifer", layout=widgets.Layout(width="200px"))
mark_last_seen_cb = Checkbox(value=MARK_LAST_SEEN, description="Mark last-seen", layout=widgets.Layout(width="200px"))
def _on_mark_lifer_change(change):
    global MARK_LIFER
    MARK_LIFER = change.get("new", MARK_LIFER)
    draw_map_with_species_overlay(state.selected_species_scientific, state.selected_species_common)
def _on_mark_last_seen_change(change):
    global MARK_LAST_SEEN
    MARK_LAST_SEEN = change.get("new", MARK_LAST_SEEN)
    draw_map_with_species_overlay(state.selected_species_scientific, state.selected_species_common)
mark_lifer_cb.observe(_on_mark_lifer_change, names="value")
mark_last_seen_cb.observe(_on_mark_last_seen_change, names="value")

popup_sort_dd = widgets.Dropdown(options=["ascending", "descending"], value=POPUP_SORT_ORDER, description="", layout=widgets.Layout(width="170px"))
popup_scroll_dd = widgets.Dropdown(options=["chevron", "shading", "both"], value=POPUP_SCROLL_HINT, description="", layout=widgets.Layout(width="170px"))
def _on_popup_sort_change(change):
    global POPUP_SORT_ORDER
    v = change.get("new")
    if v is not None:
        POPUP_SORT_ORDER = v
        draw_map_with_species_overlay(state.selected_species_scientific, state.selected_species_common)
def _on_popup_scroll_change(change):
    global POPUP_SCROLL_HINT
    v = change.get("new")
    if v is not None:
        POPUP_SCROLL_HINT = v
        draw_map_with_species_overlay(state.selected_species_scientific, state.selected_species_common)
popup_sort_dd.observe(_on_popup_sort_change, names="value")
popup_scroll_dd.observe(_on_popup_scroll_change, names="value")
sorting_header = widgets.HTML(value="<strong>Pop-up Sorting and Scrolling</strong>")
_pin_group_layout = widgets.Layout(width="100%", margin="4px 0 0 0")
_pin_row_layout = widgets.Layout(align_items="center", margin="2px 0 0 0")
default_pin_group = VBox(
    [
        widgets.HTML(value="<strong>Default pin</strong>"),
        HBox(
            [
                widgets.Label(value="Edge:", layout=widgets.Layout(width="50px")),
                default_color_dd,
                widgets.Label(value="Fill:", layout=widgets.Layout(width="40px", margin="0 0 0 12px")),
                default_fill_dd,
            ],
            layout=_pin_row_layout,
        ),
    ],
    layout=_pin_group_layout,
)
species_pin_group = VBox(
    [
        widgets.HTML(value="<strong>Species pin</strong>"),
        HBox(
            [
                widgets.Label(value="Edge:", layout=widgets.Layout(width="50px")),
                species_color_dd,
                widgets.Label(value="Fill:", layout=widgets.Layout(width="40px", margin="0 0 0 12px")),
                species_fill_dd,
            ],
            layout=_pin_row_layout,
        ),
    ],
    layout=_pin_group_layout,
)
lifer_pin_group = VBox(
    [
        widgets.HTML(value="<strong>Lifer pin</strong>"),
        HBox(
            [
                widgets.Label(value="Edge:", layout=widgets.Layout(width="50px")),
                lifer_color_dd,
                widgets.Label(value="Fill:", layout=widgets.Layout(width="40px", margin="0 0 0 12px")),
                lifer_fill_dd,
            ],
            layout=_pin_row_layout,
        ),
    ],
    layout=_pin_group_layout,
)
last_seen_pin_group = VBox(
    [
        widgets.HTML(value="<strong>Last-seen pin</strong>"),
        HBox(
            [
                widgets.Label(value="Edge:", layout=widgets.Layout(width="50px")),
                last_seen_color_dd,
                widgets.Label(value="Fill:", layout=widgets.Layout(width="40px", margin="0 0 0 12px")),
                last_seen_fill_dd,
            ],
            layout=_pin_row_layout,
        ),
    ],
    layout=_pin_group_layout,
)
pin_visibility_header = widgets.HTML(value="<strong>Pin visibility</strong>")
settings_display_section = VBox(
    [
        settings_display_header,
        map_style_header,
        map_style_row,
        default_pin_group,
        species_pin_group,
        lifer_pin_group,
        last_seen_pin_group,
        sorting_header,
        HBox(
            [
                widgets.Label(value="Sorting:", layout=widgets.Layout(width="70px")),
                popup_sort_dd,
                widgets.Label(value="Scrolling:", layout=widgets.Layout(width="80px", margin="0 0 0 12px")),
                popup_scroll_dd,
            ],
            layout=widgets.Layout(align_items="center", margin="4px 0 0 0"),
        ),
        pin_visibility_header,
        HBox([mark_lifer_cb, mark_last_seen_cb], layout=widgets.Layout(margin="6px 0 0 0")),
    ],
    layout=widgets.Layout(width="100%"),
)

# Tables & lists section
settings_tables_header = widgets.HTML(value="<span style='color:#0a0;font-size:11px;'>Lists recalculate immediately; there may be a short delay as data is processed.</span>")
rankings_visible_int = widgets.IntText(value=RANKINGS_TABLE_VISIBLE_ROWS, description="Rankings visible rows:", layout=widgets.Layout(width="340px"))
top_n_int = widgets.IntText(value=TOP_N_TABLE_LIMIT, description="Top N table limit:", layout=widgets.Layout(width="340px"))
close_meters_int = widgets.IntText(value=CLOSE_LOCATION_METERS, description="Close location (m):", layout=widgets.Layout(width="340px"))
for _w in (rankings_visible_int, top_n_int, close_meters_int):
    _w.style.description_width = "200px"

def _refresh_rankings_panel():
    """Rebuild Rankings & lists HTML with current TOP_N_TABLE_LIMIT / RANKINGS_TABLE_VISIBLE_ROWS."""
    _data = _compute_checklist_stats(df_full, link_urls_fn=_link_urls_fn)
    rankings_panel.value = format_rankings_tab_html(
        _data["rankings_sections_top_n"],
        _data["rankings_sections_other"],
        top_n_limit=TOP_N_TABLE_LIMIT,
    )

def _refresh_map_maintenance_close_locations():
    """Update the 'close locations' panel using the latest CLOSE_LOCATION_METERS."""
    new_html = format_map_maintenance_html(full_location_data, CLOSE_LOCATION_METERS)
    # Use explicit widget reference (avoid brittle children[0] indexing).
    if getattr(map_maintenance_html_widget, "value", None) is not None:
        map_maintenance_html_widget.value = new_html

def _on_rankings_visible_change(change):
    global RANKINGS_TABLE_VISIBLE_ROWS
    v = change.get("new")
    if v is not None and v > 0:
        RANKINGS_TABLE_VISIBLE_ROWS = v
        _refresh_rankings_panel()
def _on_top_n_change(change):
    global TOP_N_TABLE_LIMIT
    v = change.get("new")
    if v is not None and v > 0:
        TOP_N_TABLE_LIMIT = v
        _refresh_rankings_panel()
def _on_close_meters_change(change):
    global CLOSE_LOCATION_METERS
    v = change.get("new")
    if v is not None and v >= 0:
        CLOSE_LOCATION_METERS = v
        _refresh_map_maintenance_close_locations()
rankings_visible_int.observe(_on_rankings_visible_change, names="value")
top_n_int.observe(_on_top_n_change, names="value")
close_meters_int.observe(_on_close_meters_change, names="value")
settings_tables_section = VBox([settings_tables_header, rankings_visible_int, top_n_int, close_meters_int], layout=widgets.Layout(width="100%"))

# Settings tab: three accordions to match Rankings/Maintenance tab behaviour and styling
settings_accordion = Accordion(
    children=[settings_display_section, settings_tables_section, settings_data_section],
    titles=("Map display", "Tables & lists", "Data & path"),
    layout=widgets.Layout(width="100%", min_width="400px"),
)
settings_accordion.add_class("ebird-settings-accordion")  # same .p-Accordion-tab CSS applies via .jupyter-widgets
settings_panel = VBox([settings_intro, settings_accordion], layout=widgets.Layout(width="100%", min_width="400px"))

# --------------------------------------------
# Build main tabs (Map, Checklist Statistics, Yearly Summary, Rankings, Maintenance, Settings) and dashboard.
# --------------------------------------------
yearly_summary_panel = widgets.HTML(value=checklist_data["yearly_summary_html"])
main_tabs = widgets.Tab(children=[map_tab_container, checklist_stats_panel, yearly_summary_panel, rankings_panel, map_maintenance_panel, settings_panel])
main_tabs.set_title(0, "Map")
main_tabs.set_title(1, "Checklist Statistics")
main_tabs.set_title(2, "Yearly Summary")
main_tabs.set_title(3, "Rankings & lists")
main_tabs.set_title(4, "Maintenance")
main_tabs.set_title(5, "Settings")
main_tabs.selected_index = 0  # Ensure map tab is visible on load
main_tabs.layout = widgets.Layout(min_width="900px", min_height="650px")  # Wide enough for full tab labels (e.g. Checklist Statistics)

# %% editable=true slideshow={"slide_type": ""}
# --------------------------------------------
# ✅ Show dashboard (controls above map, output + tabs)
# --------------------------------------------
dashboard = VBox([output, main_tabs])
dashboard.layout = widgets.Layout(min_height="900px")  # Request enough height; CSS .ebird-dashboard enforces 85vh for full viewport
dashboard.add_class("ebird-dashboard")
display(dashboard)
map_controls.add_class("map-controls-panel")
map_tab_container.add_class("map-tab-container")
matches_dropdown.add_class("species-matches-dropdown")  # after display for CSS
draw_map_with_species_overlay("", "")


# %%
