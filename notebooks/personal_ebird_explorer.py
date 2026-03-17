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
from datetime import datetime

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
from whoosh.qparser import QueryParser, OrGroup

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

# Build candidate folders in fallback order
_candidate_folders = []
if DATA_FOLDER_HARDCODED and str(DATA_FOLDER_HARDCODED).strip():
    _candidate_folders.append(os.path.normpath(str(DATA_FOLDER_HARDCODED).strip()))
for _config_path in (_config_secret_path, _config_template_path):
    _folder = _load_config_module(_config_path)
    if _folder and str(_folder).strip():
        _candidate_folders.append(os.path.normpath(str(_folder).strip()))
_candidate_folders.append(_notebook_dir)

# Find data file in first candidate that has it
from personal_ebird_explorer.path_resolution import find_data_file
file_path, DATA_FOLDER = find_data_file(EBIRD_DATA_FILE_NAME, _candidate_folders)

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
    longest_streak as _longest_streak,
    compute_rankings as _compute_rankings,
    yearly_summary_stats as _yearly_summary_stats,
    get_sex_notation_by_year as _get_sex_notation_by_year,
)


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

from personal_ebird_explorer.rankings_display import (
    rankings_table_location_5col,
    rankings_table_with_rank,
    rankings_visited_table,
    rankings_seen_once_table,
    rankings_subspecies_hierarchical_table,
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
from personal_ebird_explorer.taxonomy import load_taxonomy, get_species_url, get_species_lifelist_url
_taxonomy_loaded = load_taxonomy(locale=EBIRD_TAXONOMY_LOCALE if EBIRD_TAXONOMY_LOCALE else None)
_species_url_fn = get_species_url if _taxonomy_loaded else (lambda _: None)
_lifelist_url_fn = get_species_lifelist_url if _taxonomy_loaded else (lambda _: None)


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
# ### 📍 Map maintenance data (duplicates / close locations via duplicate_checks).
#

# %%
from personal_ebird_explorer.duplicate_checks import (
    get_map_maintenance_data as _get_map_maintenance_data,
)


# %% [markdown] editable=true slideshow={"slide_type": ""} tags=["voila_hide"]
# ### 🐣 Lifer and last-seen lookups (from full dataset; used for pin highlighting).
#

# %%
# --------------------------------------------
# ✅ Build True Lifer and Last-Seen Tables (from full dataset)
# --------------------------------------------

# Reload full dataset to avoid filtering effects (date filter, lifer calc)
full_df = load_dataset(file_path)
# Exclude locations with no checklist (consistent with main data)
full_df = full_df[full_df["Location ID"].isin(location_ids_with_checklists)]

# Build lifer location dictionary: base species (genus + species) → first seen location.
# Uses base species so subspecies (e.g. Tyto javanica [javanica Group]) roll up to the
# same lifer as the nominate (Tyto javanica) — the chronologically first record wins.
# _base_species_for_lifer imported from species_logic (see species-logic import cell above).

_lifer_lookup_df = (
    full_df.sort_values("datetime")
    .dropna(subset=["Scientific Name", "Location ID", "datetime"])
    .assign(
        _base=lambda x: x["Scientific Name"].apply(_base_species_for_lifer),
        _taxon=lambda x: x["Scientific Name"].str.strip().str.lower(),
    )
)
_lifer_lookup_df = _lifer_lookup_df[_lifer_lookup_df["_base"].notna()]
# Base species (genus + species): for parent selection, first/last across all subspecies
true_lifer_locations = _lifer_lookup_df.groupby("_base").first()["Location ID"].to_dict()
true_last_seen_locations = _lifer_lookup_df.groupby("_base").last()["Location ID"].to_dict()
# Taxon (full scientific name): for subspecies selection, first/last of that taxon only
true_lifer_locations_taxon = _lifer_lookup_df.groupby("_taxon").first()["Location ID"].to_dict()
true_last_seen_locations_taxon = _lifer_lookup_df.groupby("_taxon").last()["Location ID"].to_dict()


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
        with ix.searcher() as searcher:
            qp = QueryParser("common_name", ix.schema, group=OrGroup)
            tokens = query.split()
            try:
                q = qp.parse(" ".join(f"{t}*" for t in tokens))
            except Exception:
                matches_dropdown.options = []
                _show_matches_dropdown(False)
                return
            results = searcher.search(q, limit=None)

            def score(r):
                name = r["common_name"].lower()
                base = 100 - r.rank
                if name.startswith(tokens[0]):
                    base += 50
                return base

            ranked = sorted(results, key=score, reverse=True)
            opts = [r["common_name"] for r in ranked[:6]]  # match rows=6, no scrollbar
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
# ✅ Checklist Statistics (computed from data; table HTML from rankings_display)
# --------------------------------------------
def _compute_checklist_stats(df, species_url_fn=None, lifelist_url_fn=None):
    """Compute checklist statistics from df; returns dict with stats_html, rankings_sections_top_n, rankings_sections_other.

    Optional species_url_fn(common_name) and lifelist_url_fn(common_name) enable eBird species/lifelist links (refs #56).
    """
    import html

    if df.empty:
        return "<p>No data.</p>"

    # Checklist-level data (one row per checklist)
    cl = df.drop_duplicates(subset=["Submission ID"]).copy()
    dur_col = "Duration (Min)" if "Duration (Min)" in df.columns else None
    dist_col = "Distance Traveled (km)" if "Distance Traveled (km)" in df.columns else None

    # Overview
    n_checklists = cl["Submission ID"].nunique()
    n_species = int(_countable_species_vectorized(df).dropna().nunique())
    n_individuals = int(df["Count"].apply(_safe_count).sum())

    # Completed checklists (All Obs Reported: 1/1.0 = complete, 0 = incomplete; also TRUE/YES/Y)
    n_completed = "—"
    if "All Obs Reported" in df.columns:
        a = cl["All Obs Reported"]
        reported = a.notna() & (
            (pd.to_numeric(a, errors="coerce") == 1) |
            (a.astype(str).str.strip().str.upper().isin(["TRUE", "YES", "Y"]))
        )
        n_completed = f"{reported.sum():,}"

    # Protocol counts — all types with zero, roll unknown into Other
    PROTOCOL_ORDER = ["Traveling", "Stationary", "Incidental", "Pelagic Protocol", "Historical", "Other"]
    PROTOCOL_MAP = {
        "traveling": "Traveling", "travelling": "Traveling", "traveling count": "Traveling",
        "ebird - traveling count": "Traveling",
        "stationary": "Stationary", "stationary count": "Stationary",
        "ebird - stationary count": "Stationary",
        "incidental": "Incidental", "incidental observation": "Incidental",
        "ebird - casual observation": "Incidental", "casual observation": "Incidental",
        "pelagic": "Pelagic Protocol", "pelagic protocol": "Pelagic Protocol",
        "historical": "Historical", "historical checklist": "Historical",
    }
    protocol_counts = {p: 0 for p in PROTOCOL_ORDER}
    if "Protocol" in df.columns:
        proto_df = cl.dropna(subset=["Protocol"])
        for _, row in proto_df.iterrows():
            p = str(row["Protocol"]).strip().lower()
            if not p:
                continue
            disp = PROTOCOL_MAP.get(p, "Other")
            protocol_counts[disp] = protocol_counts.get(disp, 0) + 1
    protocol_rows = [(k, f"{v:,}") for k, v in protocol_counts.items()]
    protocol_rows.append(("Completed checklists", n_completed))

    # Time eBirded (excludes incidental, historical, other for total time)
    total_minutes = 0.0
    if dur_col:
        timed = cl.dropna(subset=[dur_col]).copy()
        if "Protocol" in timed.columns:
            excl = timed["Protocol"].str.strip().str.lower().str.contains("incidental|historical|casual observation", na=False, regex=True)
            timed = timed[~excl]
        total_minutes = pd.to_numeric(timed[dur_col], errors="coerce").fillna(0).sum()
    total_hours = total_minutes / 60
    total_days_dec = total_minutes / (60 * 24)
    total_months = total_minutes / (60 * 24 * 30.44)
    total_years = total_minutes / (60 * 24 * 365.25)
    dates = cl.dropna(subset=["Date"])["Date"]
    unique_dates = dates.dt.normalize().unique()
    n_days_with_checklist = len(unique_dates)

    # Shared checklists and time with others
    n_shared = 0
    shared_minutes = 0.0
    n_days_birding_with_others = 0
    if "Number of Observers" in df.columns:
        shared_cl = cl.dropna(subset=["Number of Observers"])
        shared_mask = shared_cl["Number of Observers"].astype(float) > 1
        n_shared = int(shared_mask.sum())
        if n_shared > 0:
            shared_ids = set(shared_cl.loc[shared_mask, "Submission ID"])
            shared_subset = cl[cl["Submission ID"].isin(shared_ids)]
            if "Date" in shared_subset.columns:
                n_days_birding_with_others = shared_subset["Date"].dt.normalize().nunique()
            if dur_col:
                shared_dur = shared_subset.dropna(subset=[dur_col])
                shared_minutes = pd.to_numeric(shared_dur[dur_col], errors="coerce").fillna(0).sum()
    shared_hours = shared_minutes / 60

    # Total distance
    total_km = 0.0
    if dist_col:
        total_km = pd.to_numeric(cl[dist_col], errors="coerce").fillna(0).sum()
    parkruns = total_km / 5
    marathons = total_km / 42.195
    equator_km = 40_075
    times_equator = total_km / equator_km
    godwit_km = 13_560
    times_godwit = total_km / godwit_km

    # Longest streak and start/end
    streak, streak_start_date, streak_start_loc, streak_start_sid, streak_end_date, streak_end_loc, streak_end_sid = _longest_streak(unique_dates, cl)

    # Top N rankings data (limit from TOP_N_TABLE_LIMIT)
    rankings = _compute_rankings(df, cl, TOP_N_TABLE_LIMIT, dur_col, dist_col)

    # Yearly summary: static table (includes Traveling/Stationary count rows), then accordions with detail tables
    years_list, yearly_rows, incomplete_by_year = _yearly_summary_stats(df, cl, dur_col, dist_col)
    yearly_table_html = ""
    if years_list and yearly_rows:
        def _any_value(vals):
            return any(v != "—" for v in vals)
        # Only detail rows (label starts with "Traveling checklist:" or "Stationary checklist:") go to accordions; count rows stay in main table
        static_rows = []
        traveling_detail = []
        stationary_detail = []
        traveling_count_vals = None
        stationary_count_vals = None
        for label, vals in yearly_rows:
            ls = label.strip()
            if ls.startswith("Traveling checklist:"):
                traveling_detail.append((label, vals))
            elif ls.startswith("Stationary checklist:"):
                stationary_detail.append((label, vals))
            else:
                static_rows.append((label, vals))
                if ls.startswith("Traveling checklists") and "Traveling checklist: " not in ls:
                    traveling_count_vals = vals
                if ls.startswith("Stationary checklists") and "Stationary checklist: " not in ls:
                    stationary_count_vals = vals
        visible_static = [(label, vals) for label, vals in static_rows if _any_value(vals)]
        year_headers = "".join(f"<th style='text-align:right;'>{y}</th>" for y in years_list)
        yearly_css = """
    .yearly-maint-section { margin-bottom:8px; border:1px solid #e5e7eb; border-radius:6px; background:#f9fafb; padding:4px 10px; }
    .yearly-maint-section > summary { font-weight:600; padding:6px 0; color:#374151; cursor:pointer; }
"""
        _yearly_comment_style = "margin:4px 0 8px;color:#6b7280;font-size:12px;line-height:1.5;"
        _traveling_comment = "Incomplete checklists not counted."
        _stationary_comment = "Incomplete checklists not counted."
        # Short display names for accordion tables (strip "Traveling checklist: " / "Stationary checklist: " and any (i) HTML)
        _traveling_order = ["Total distance (km)", "Average distance (km)", "Total hours", "Average minutes", "Average species", "Average individuals"]
        _stationary_order = ["Total hours", "Average minutes", "Average species", "Average individuals"]
        def _short_name(full_label, prefix):
            # Strip prefix and any trailing HTML (e.g. info icon)
            name = full_label.strip()
            if name.startswith(prefix):
                name = name[len(prefix):].strip()
            # Drop trailing info-icon span (starts with " <span")
            if " <span" in name:
                name = name.split(" <span")[0].strip()
            return name or full_label
        def _ordered_detail_rows(detail_rows, order_list, prefix):
            by_suffix = {}
            for label, vals in detail_rows:
                short = _short_name(label, prefix)
                by_suffix[short] = vals
            return [(name, by_suffix.get(name, ["—"] * len(years_list))) for name in order_list if name in by_suffix]
        parts = []
        if visible_static:
            body_rows = "".join(
                f"<tr><td>{label}</td>" + "".join(f"<td style='text-align:right;'>{v}</td>" for v in vals) + "</tr>"
                for label, vals in visible_static
            )
            parts.append(f"""
  <h4 style="margin-top:24px;margin-bottom:8px;padding-bottom:6px;border-bottom:1px solid #e5e7eb;">Yearly Summary Statistics</h4>
  <div style="overflow-x:auto;">
  <table class="stats-tbl" style="min-width:400px;">
    <thead><tr><th>Statistic</th>{year_headers}</tr></thead>
    <tbody>{body_rows}</tbody>
  </table>
  </div>""")
        elif traveling_detail or stationary_detail:
            parts.append("\n  <h4 style=\"margin-top:24px;margin-bottom:8px;padding-bottom:6px;border-bottom:1px solid #e5e7eb;\">Yearly Summary Statistics</h4>")
        def _yearly_accordion_body(comment_text, total_checklists_vals, ordered_detail_rows):
            rows_html = []
            if total_checklists_vals is not None:
                rows_html.append(f"<tr><td>Total checklists</td>" + "".join(f"<td style='text-align:right;'>{v}</td>" for v in total_checklists_vals) + "</tr>")
            for name, vals in ordered_detail_rows:
                rows_html.append(f"<tr><td>{name}</td>" + "".join(f"<td style='text-align:right;'>{v}</td>" for v in vals) + "</tr>")
            if not rows_html:
                return ""
            body = "\n    ".join(rows_html)
            return f"""  <p style="{_yearly_comment_style}">{comment_text}</p>
  <div style="overflow-x:auto;">
  <table class="stats-tbl" style="min-width:400px;">
    <thead><tr><th>Statistic</th>{year_headers}</tr></thead>
    <tbody>
    {body}
    </tbody>
  </table>
  </div>"""
        if traveling_detail or traveling_count_vals is not None:
            ordered_trav = _ordered_detail_rows(traveling_detail, _traveling_order, "Traveling checklist:")
            if ordered_trav or traveling_count_vals is not None:
                body = _yearly_accordion_body(_traveling_comment, traveling_count_vals, ordered_trav)
                if body:
                    parts.append(f"""
  <details class="yearly-maint-section">
    <summary>Traveling checklists</summary>
{body}  </details>""")
        if stationary_detail or stationary_count_vals is not None:
            ordered_stat = _ordered_detail_rows(stationary_detail, _stationary_order, "Stationary checklist:")
            if ordered_stat or stationary_count_vals is not None:
                body = _yearly_accordion_body(_stationary_comment, stationary_count_vals, ordered_stat)
                if body:
                    parts.append(f"""
  <details class="yearly-maint-section">
    <summary>Stationary checklists</summary>
{body}  </details>""")
        if parts:
            yearly_table_html = f"""
  <style>{yearly_css}</style>
  <div style="width:100%;max-width:1400px;padding:0 clamp(16px,3vw,32px) 24px;box-sizing:border-box;">
{"".join(parts)}
  </div>"""

    _table_css = """
    .stats-info-icon { position:relative; display:inline-block; margin-left:4px; }
    .stats-info-glyph { cursor:help; opacity:0.7; }
    .stats-info-tooltip { position:absolute; bottom:100%; top:auto; margin-bottom:6px; margin-top:0; padding:10px 14px; background:#374151; color:#fff; font-size:12px; font-weight:normal; line-height:1.5; white-space:normal; max-width:min(320px,85vw); min-width:180px; border-radius:6px; box-shadow:0 4px 12px rgba(0,0,0,0.15); opacity:0; visibility:hidden; transition:opacity 0.15s; pointer-events:none; z-index:9999; right:0; left:auto; }
    .stats-info-icon:hover .stats-info-tooltip { opacity:1; visibility:visible; }
    /* Left column: tooltip extends left into the page */
    .stats-col:first-child .stats-info-tooltip { right:0; left:auto; }
    /* Right column: tooltip extends right into the page */
    .stats-col:last-child .stats-info-tooltip { left:0; right:auto; }
    .stats-tbl-3 th:nth-child(2), .stats-tbl-3 td:nth-child(2) { text-align:center; }
    .rankings-tbl td:first-child { font-weight:normal; }
    """

    def _row(label, value):
        return f"<tr><td>{label}</td><td>{value}</td></tr>"

    def _info_icon(title):
        """Return HTML for info icon with tooltip."""
        import html as _html
        esc = _html.escape(title, quote=True)
        return f' <span class="stats-info-icon"><span class="stats-info-glyph">&#9432;</span><span class="stats-info-tooltip">{esc}</span></span>'

    def _table(title, rows, first=False, info_title=None, show_header=False, header_left="", header_right=""):
        """Build a stats table. If show_header is False, no thead row (for Overview, Time eBirded, etc.)."""
        info = f" {_info_icon(info_title)}" if info_title else ""
        body = "".join(_row(label, value) for label, value in rows)
        mt = "0" if first else "16px"
        thead = f"<thead><tr><th>{header_left}</th><th>{header_right}</th></tr></thead>" if show_header else ""
        return f"""
  <h4 style="margin-top:{mt};margin-bottom:8px;padding-bottom:6px;border-bottom:1px solid #e5e7eb;">{title}{info}</h4>
  <table class="stats-tbl">
    {thead}<tbody>{body}</tbody>
  </table>"""

    time_hint = "Incidental, historical and other untimed checklists don't count towards total time, but do count towards Days with a checklist."
    godwit_hint = "4BBRW: Bar-tailed Godwit, Alaska→Tasmania, ~13,560 km nonstop (2022). 11 days without landing."
    godwit_link = '<a href="https://www.audubon.org/news/these-mighty-shorebirds-keep-breaking-flight-records-and-you-can-follow-along" target="_blank">4BBRW</a>'

    streak_start_link = f'<a href="https://ebird.org/checklist/{streak_start_sid}" target="_blank">{streak_start_loc}</a>' if streak_start_sid else streak_start_loc
    streak_end_link = f'<a href="https://ebird.org/checklist/{streak_end_sid}" target="_blank">{streak_end_loc}</a>' if streak_end_sid else streak_end_loc

    left_col = f"""
  {_table("Overview", [
    ("Total checklists", f"{n_checklists:,}"),
    ("Total species", f"{n_species:,}"),
    ("Total individuals", f"{n_individuals:,}"),
  ], first=True)}

  {_table("Checklist types", protocol_rows)}

  {_table("Total Distance", [
    ("Kilometers traveled", f"{total_km:,.2f}"),
    ("Parkruns (5 km)", f"{parkruns:,.2f}"),
    ("Marathons (42.195 km)", f"{marathons:,.2f}"),
    (f"Longest Flight ({godwit_link}){_info_icon(godwit_hint)}", f"{times_godwit:,.2f}"),
    ("Times around the equator", f"{times_equator:,.2f}"),
  ])}
"""

    right_col = f"""
  {_table("Time eBirded", [
    ("Total minutes", f"{total_minutes:,.2f}"),
    ("Total hours", f"{total_hours:,.2f}"),
    ("Total days", f"{total_days_dec:,.2f}"),
    ("Months", f"{total_months:,.2f}"),
    ("Total years", f"{total_years:,.2f}"),
    ("Days with a checklist", f"{n_days_with_checklist:,}"),
  ], first=True)}
  <p style="margin:4px 0 0;color:#6b7280;font-size:12px;line-height:1.5;">
    {time_hint}
  </p>

  {_table("eBirding with Others", [
    ("Shared checklists", f"{n_shared:,}"),
    ("Minutes eBirding with others", f"{shared_minutes:,.0f}"),
    ("Hours eBirding with others", f"{shared_hours:,.2f}"),
    ("Days birding with others", f"{n_days_birding_with_others:,}"),
  ])}

  {_table("Checklist Streak", [
    ("Longest streak (consecutive days)", str(streak)),
    ("Start date", streak_start_date),
    ("Start location", streak_start_link),
    ("End date", streak_end_date),
    ("End location", streak_end_link),
  ])}
"""

    # Rankings sections: Top N (limit 200) vs other (full/unlimited lists)
    scroll_hint = POPUP_SCROLL_HINT
    visible_rows = RANKINGS_TABLE_VISIBLE_ROWS
    rankings_sections_top_n = [
        ("Checklist: Longest by time", rankings_table_location_5col("Checklist: Longest by time", ["Location", "State", "Country", "Visited date/time", "Time"], rankings["time"], include_heading=False, scroll_hint=scroll_hint, visible_rows=visible_rows)),
        ("Checklist: Longest by distance", rankings_table_location_5col("Checklist: Longest by distance", ["Location", "State", "Country", "Visited date/time", "Distance"], rankings["dist"], include_heading=False, scroll_hint=scroll_hint, visible_rows=visible_rows)),
        ("Checklist: Most species", rankings_table_location_5col("Checklist: Most species", ["Location", "State", "Country", "Visited date/time", "Species"], rankings["species"], include_heading=False, scroll_hint=scroll_hint, visible_rows=visible_rows)),
        ("Checklist: Most individuals", rankings_table_location_5col("Checklist: Most individuals", ["Location", "State", "Country", "Visited date/time", "Count"], rankings["individuals"], include_heading=False, scroll_hint=scroll_hint, visible_rows=visible_rows)),
        ("Location: Most species", rankings_table_location_5col("Location: Most species", ["Location", "State", "Country", "Checklists", "Species"], rankings["species_loc"], include_heading=False, scroll_hint=scroll_hint, visible_rows=visible_rows)),
        ("Location: Most individuals", rankings_table_location_5col("Location: Most individuals", ["Location", "State", "Country", "Checklists", "Count"], rankings["individuals_loc"], include_heading=False, scroll_hint=scroll_hint, visible_rows=visible_rows)),
        ("Location: Most visited", rankings_visited_table(rankings["visited"], include_heading=False, scroll_hint=scroll_hint, visible_rows=visible_rows)),
    ]
    rankings_sections_other = [
        ("Species: Most individuals", rankings_table_with_rank("Species: Most individuals", ["Species", "", "Individuals"], rankings["species_individuals"], include_heading=False, scroll_hint=scroll_hint, visible_rows=visible_rows, species_url_fn=species_url_fn)),
        ("Species: Most checklists", rankings_table_with_rank("Species: Most checklists", ["Species", "", "Checklists"], rankings["species_checklists"], include_heading=False, scroll_hint=scroll_hint, visible_rows=visible_rows, species_url_fn=species_url_fn, lifelist_url_fn=lifelist_url_fn)),
        ("Species: Subspecies occurrence", rankings_subspecies_hierarchical_table("Species: Subspecies occurrence", rankings["subspecies"], include_heading=False, scroll_hint=scroll_hint, visible_rows=visible_rows)),
        ("Species: Seen only once", rankings_seen_once_table(rankings["seen_once"], include_heading=False, scroll_hint=scroll_hint, visible_rows=visible_rows, species_url_fn=species_url_fn)),
    ]

    stats_html = f"""
<style>{_table_css}</style>
<div class="stats-layout" style="font-family:sans-serif;font-size:13px;line-height:1.6;width:100%;max-width:1400px;display:flex;flex-wrap:wrap;gap:clamp(24px,4vw,48px);justify-content:flex-start;padding:0 clamp(16px,3vw,32px);box-sizing:border-box;">
  <div class="stats-col" style="flex:1 1 320px;min-width:280px;max-width:480px;padding:16px;box-sizing:border-box;">{left_col}</div>
  <div class="stats-col" style="flex:1 1 320px;min-width:280px;max-width:480px;padding:16px;box-sizing:border-box;">{right_col}</div>
</div>
"""
    yearly_summary_html = f"<style>{_table_css}</style>{yearly_table_html}" if yearly_table_html else "<p style='font-family:sans-serif;color:#666;padding:16px;'>No yearly data.</p>"
    return {"stats_html": stats_html, "yearly_summary_html": yearly_summary_html, "rankings_sections_top_n": rankings_sections_top_n, "rankings_sections_other": rankings_sections_other, "incomplete_by_year": incomplete_by_year}


# Stats use df_full for all-time totals (unfiltered by date). Map uses df, which may be date-filtered.
checklist_data = _compute_checklist_stats(df_full, species_url_fn=_species_url_fn, lifelist_url_fn=_lifelist_url_fn)
checklist_stats_panel = widgets.HTML(value=checklist_data["stats_html"])

# Rankings tab: two groups (Top N + Other) with headings, each group an accordion
_rankings_heading_style = "font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif;font-size:15px;font-weight:600;margin:0 0 8px;padding:0;color:#111827;"

def _build_rankings_panel_html(sections_top_n, sections_other):
    """Build HTML for Rankings & lists tab using <details> accordions (matching Maintenance style)."""
    def _details_block(title, html_body):
        return f"""
<details class="maint-section">
  <summary>{title}</summary>
  <div style="margin-top:8px;">
{html_body}
  </div>
</details>"""

    top_html = "".join(_details_block(title, html) for title, html in sections_top_n)
    other_html = "".join(_details_block(title, html) for title, html in sections_other)

    return f"""
<style>
.maint-section {{
  margin-bottom:8px;
  border:1px solid #e5e7eb;
  border-radius:6px;
  background:#f9fafb;
  padding:4px 10px;
}}
.maint-section > summary {{
  font-weight:600;
  padding:6px 0;
  color:#374151;
  cursor:pointer;
}}
</style>
<div style="font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif;font-size:13px;line-height:1.6;width:100%;max-width:1400px;padding:0 clamp(16px,3vw,32px);box-sizing:border-box;">
  <h3 style="{_rankings_heading_style}">Top {TOP_N_TABLE_LIMIT}</h3>
  {top_html}
  <h3 style="margin-top:24px;{_rankings_heading_style.split('margin:0 0 8px;')[0]}">Interesting Lists</h3>
  {other_html}
</div>
"""


rankings_panel = widgets.HTML(
    value=_build_rankings_panel_html(
        checklist_data["rankings_sections_top_n"],
        checklist_data["rankings_sections_other"],
    )
)


# Map maintenance tab: exact duplicates and close-location pairs
# Link format for maintenance: edit page (merge/delete), not lifelist
_MAINT_LOC_URL = "https://ebird.org/mylocations/edit/"


def _compute_map_maintenance_html(loc_df, threshold_m):
    """Build HTML for Map maintenance tab: exact duplicates and close-location pairs."""
    exact_rows, near_pairs = _get_map_maintenance_data(loc_df, threshold_m)
    css = """
    .maint-tbl.maint-single-col td { text-align:left; font-weight:normal; }
    .maint-pair-tbl { max-width:600px; }
    .maint-pair-tbl tbody tr.maint-spacer { background:transparent; }
    .maint-section {
      margin-bottom:8px;
      border:1px solid #e5e7eb;
      border-radius:6px;
      background:#f9fafb;
      padding:4px 10px;
    }
    .maint-section > summary {
      font-weight:600;
      padding:6px 0;
      color:#374151;
      cursor:pointer;
    }
    .maint-subsection { margin-top:8px; margin-bottom:4px; margin-left:8px; }
    .maint-subsection > summary {
      font-weight:600;
      padding:4px 0;
      color:#374151;
      cursor:pointer;
      font-size:13px;
    }
    """
    # Table 1: Exact duplicates (inner accordion)
    dup_body = ""
    if exact_rows:
        for loc_name, loc_id, count, lat, lon in exact_rows:
            link = f'<a href="{_MAINT_LOC_URL}{loc_id}" target="_blank">{loc_name}</a>' if loc_id else loc_name
            coords = f"({lat:.6f}, {lon:.6f})" if pd.notna(lat) and pd.notna(lon) else "—"
            dup_body += f"<tr><td>{link}</td><td>{coords}</td><td>{count}</td></tr>"
        exact_dup_content = f"""
  <p style="margin:4px 0 8px;color:#6b7280;font-size:13px;">Different Location IDs at the same coordinates. Same name listed once; different names listed separately.</p>
  <table class="maint-tbl">
    <thead><tr><th>Location</th><th>Latitude/Longitude</th><th>Number of duplicates</th></tr></thead>
    <tbody>{dup_body}</tbody>
  </table>"""
    else:
        exact_dup_content = """
  <p style="margin:4px 0;color:#6b7280;">None detected.</p>"""

    # Table 2: Close locations (inner accordion)
    if near_pairs:
        all_rows = ""
        for i, pair in enumerate(near_pairs):
            pair_rows = "".join(
                (f'<tr class="pair-first"><td><a href="{_MAINT_LOC_URL}{lid}" target="_blank">{name}</a></td><td>{f"({lat:.6f}, {lon:.6f})" if pd.notna(lat) and pd.notna(lon) else "—"}</td></tr>'
                 if idx == 0 else
                 f'<tr class="pair-second"><td><a href="{_MAINT_LOC_URL}{lid}" target="_blank">{name}</a></td><td>{f"({lat:.6f}, {lon:.6f})" if pd.notna(lat) and pd.notna(lon) else "—"}</td></tr>')
                for idx, (lid, name, lat, lon) in enumerate(pair)
            )
            all_rows += pair_rows
            if i < len(near_pairs) - 1:
                all_rows += '<tr class="maint-spacer"><td colspan="2" style="height:12px;border:none;background:transparent;"></td></tr>'
        close_loc_content = f"""
  <p style="margin:4px 0 12px;color:#6b7280;font-size:13px;">Locations within {threshold_m} m of each other (excluding exact duplicates).</p>
  <table class="maint-pair-tbl">
    <thead><tr><th>Location</th><th>Latitude/Longitude</th></tr></thead>
    <tbody>{all_rows}</tbody>
  </table>"""
    else:
        close_loc_content = f"""
  <p style="margin:4px 0;color:#6b7280;">None detected within the current threshold ({threshold_m} m).</p>"""

    explanation = """
  <div style="margin-top:0;margin-bottom:16px;max-width:600px;box-sizing:border-box;color:#6b7280;font-size:13px;font-weight:normal;line-height:1.6;text-align:left;overflow-wrap:break-word;word-break:break-word;">
    These tables highlight duplicate locations and locations that are very close to each other (within the configured distance) to help you keep your personal eBird locations organised. This is most useful if you regularly create new locations and build a large catalogue of them; if you mainly use hotspots it may be less relevant. Locations can be merged on the eBird website, though directly merging duplicates can sometimes be awkward. Often the simplest approach is to move checklists to the preferred location and then delete the now-empty duplicate. See eBird for details.
  </div>"""

    return f"""
<style>{css}</style>
<div style="font-family:sans-serif;font-size:13px;line-height:1.6;max-width:800px;">
<details class="maint-section">
  <summary>Location Maintenance</summary>
{explanation}
  <details class="maint-subsection">
    <summary>Exact duplicates</summary>
{exact_dup_content}
  </details>
  <details class="maint-subsection">
    <summary>Close locations</summary>
{close_loc_content}
  </details>
</details>
</div>"""


map_maintenance_html = _compute_map_maintenance_html(full_location_data, CLOSE_LOCATION_METERS)


def _compute_sex_notation_html(sex_notation_by_year, species_url_fn=None):
    """Build HTML for Maintenance tab: sex-notation strings in checklist comments, grouped by year.

    Optional species_url_fn(common_name) -> url enables eBird species links in Species column (refs #56).
    """
    import html as _html
    if not sex_notation_by_year:
        return ""
    css = """
    details { margin-bottom:8px; }
    summary { cursor:pointer; font-weight:600; padding:6px 0; color:#374151; }
    .maint-section {
      margin-bottom:8px;
      border:1px solid #e5e7eb;
      border-radius:6px;
      background:#f9fafb;
      padding:4px 10px;
    }
    .maint-section > summary {
      font-weight:600;
      padding:6px 0;
      color:#374151;
      cursor:pointer;
    }
    """
    explanation = """
  <div style="margin-top:0;margin-bottom:16px;max-width:600px;box-sizing:border-box;color:#6b7280;font-size:13px;font-weight:normal;line-height:1.6;text-align:left;overflow-wrap:break-word;word-break:break-word;">
    Some checklists contain shorthand sex or age notation (for example <code>MF</code>, <code>MFFF</code>, or <code>MMF??F</code>) entered in the field notes. These should ideally be converted into the structured Age/Sex table on the eBird website. The following lists identify checklists where this shorthand was detected.
  </div>"""
    sections = []
    for y in sorted(sex_notation_by_year.keys(), reverse=True):
        items = sex_notation_by_year[y]
        rows = []
        for sid, date_str, loc, species, protocol, notation in items:
            loc_esc = _html.escape(loc, quote=True)
            date_esc = _html.escape(date_str, quote=True)
            species_esc = _html.escape(species, quote=True)
            protocol_esc = _html.escape(protocol, quote=True)
            notation_esc = _html.escape(notation, quote=True)
            species_url = species_url_fn(species) if species_url_fn else None
            species_cell = f"<a href=\"{_html.escape(species_url, quote=True)}\" target=\"_blank\" rel=\"noopener\">{species_esc}</a>" if species_url else species_esc
            url = f"https://ebird.org/checklist/{sid}" if sid else "#"
            loc_link = f"<a href=\"{url}\" target=\"_blank\">{loc_esc}</a>" if url != "#" else loc_esc
            rows.append(f"<tr><td>{date_esc}</td><td>{protocol_esc}</td><td>{species_cell}</td><td>{notation_esc}</td><td>{loc_link}</td></tr>")
        table_body = "".join(rows)
        table = f"<table class=\"maint-tbl\"><thead><tr><th>Date</th><th>Protocol</th><th>Species</th><th>Sex Notation</th><th>Location</th></tr></thead><tbody>{table_body}</tbody></table>"
        sections.append(f"<details><summary>{y} ({len(items)})</summary>{table}</details>")
    return f"""
<style>{css}</style>
<div style="font-family:sans-serif;font-size:13px;line-height:1.6;max-width:800px;">
<details class="maint-section">
  <summary>Sex notation in checklist comments</summary>
{explanation}
  <div style="margin-top:16px;">
{"".join(sections)}
  </div>
</details>
</div>"""


def _compute_incomplete_checklists_html(incomplete_by_year):
    """Build HTML for Maintenance tab: explanation + accordion (details/summary) of incomplete checklists by year in tables."""
    import html as _html
    if not incomplete_by_year:
        return ""
    css = """
    details { margin-bottom:8px; }
    summary { cursor:pointer; font-weight:600; padding:6px 0; color:#374151; }
    .maint-section {
      margin-bottom:8px;
      border:1px solid #e5e7eb;
      border-radius:6px;
      background:#f9fafb;
      padding:4px 10px;
    }
    .maint-section > summary {
      font-weight:600;
      padding:6px 0;
      color:#374151;
      cursor:pointer;
    }
    """
    explanation = """
  <div style="margin-top:0;margin-bottom:16px;max-width:600px;box-sizing:border-box;color:#6b7280;font-size:13px;font-weight:normal;line-height:1.6;text-align:left;overflow-wrap:break-word;word-break:break-word;">
    Incomplete travelling and stationary checklists often occur when submitting a checklist in the eBird mobile app. The default setting is incomplete, and if you move quickly through the submission prompts you may accidentally answer "No" to the question asking whether the list is complete.<br><br>
    Incomplete checklists can certainly be intentional and acceptable (for example, when other species were present but not recorded). These checklists tables below are provided so you can review your data for checklists that may have been marked incomplete by mistake. Incidental checklists are not included.<br><br>
    Reference: <a href="https://support.ebird.org/en/support/solutions/articles/48000950859-guide-to-ebird-protocols" target="_blank">Guide to eBird Protocols</a>
  </div>"""
    sections = []
    for y in sorted(incomplete_by_year.keys(), reverse=True):
        items = incomplete_by_year[y]
        rows = []
        for sid, date_str, loc in items:
            loc_esc = _html.escape(loc, quote=True)
            date_esc = _html.escape(date_str, quote=True)
            url = f"https://ebird.org/checklist/{sid}" if sid else "#"
            rows.append(f"<tr><td>{date_esc}</td><td><a href=\"{url}\" target=\"_blank\">{loc_esc}</a></td></tr>")
        table_body = "".join(rows)
        table = f"<table class=\"maint-tbl\"><thead><tr><th>Date</th><th>Location</th></tr></thead><tbody>{table_body}</tbody></table>"
        sections.append(f"<details><summary>{y} ({len(items)})</summary>{table}</details>")
    return f"""
<style>{css}</style>
<div style="font-family:sans-serif;font-size:13px;line-height:1.6;max-width:800px;">
<details class="maint-section">
  <summary>Incomplete checklists (Traveling or Stationary)</summary>
{explanation}
  <div style="margin-top:16px;">
{"".join(sections)}
  </div>
</details>
</div>"""


incomplete_checklists_html = _compute_incomplete_checklists_html(checklist_data.get("incomplete_by_year", {}))
sex_notation_by_year = _get_sex_notation_by_year(df_full)
sex_notation_html = _compute_sex_notation_html(sex_notation_by_year, species_url_fn=_species_url_fn)
_maintenance_panel_parts = [widgets.HTML(value=map_maintenance_html)]
if incomplete_checklists_html:
    _maintenance_panel_parts.append(widgets.HTML(value=incomplete_checklists_html))
if sex_notation_html:
    _maintenance_panel_parts.append(widgets.HTML(value=sex_notation_html))
map_maintenance_panel = VBox(_maintenance_panel_parts)

# --------------------------------------------
# Build map tab: single control row (search, checkbox, reset, export) + matches dropdown. Date filter shown in banner only (refs #47).
# --------------------------------------------
_spacer = Box(layout=widgets.Layout(width="0.75em", min_width="0.75em"))
reset_view_btn = widgets.Button(description="Reset View", layout=widgets.Layout(width="100px"))
reset_view_btn.on_click(lambda _: _clear_to_all_species())
export_map_btn = widgets.Button(description="Export Map HTML", layout=widgets.Layout(width="140px"))
export_map_btn.on_click(lambda _: _export_map_html())
search_row = HBox(
    [search_box, _spacer, hide_non_matching_checkbox, _spacer, reset_view_btn, export_map_btn],
    layout=widgets.Layout(align_items="center"),
)
map_controls = VBox([search_row, matches_dropdown])
map_controls.layout = widgets.Layout(width="100%", min_width="0")

map_tab_container = VBox(
    [map_controls, _map_outputs[_map_front_index]],
    layout=widgets.Layout(min_height="600px", width="100%"),
)
map_tab_container.add_class("map-tab-container")

# --------------------------------------------
# Build main tabs (Map, Checklist Statistics, Rankings, Map maintenance) and dashboard.
# --------------------------------------------
yearly_summary_panel = widgets.HTML(value=checklist_data["yearly_summary_html"])
main_tabs = widgets.Tab(children=[map_tab_container, checklist_stats_panel, yearly_summary_panel, rankings_panel, map_maintenance_panel])
main_tabs.set_title(0, "Map")
main_tabs.set_title(1, "Checklist Statistics")
main_tabs.set_title(2, "Yearly Summary")
main_tabs.set_title(3, "Rankings & lists")
main_tabs.set_title(4, "Maintenance")
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
