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
# ## 🗺️ Explore Your eBird Data on a Map
#
# This notebook lets you explore your personal eBird records in an interactive, visual way.
#
# Once you’ve downloaded your full eBird data export, this tool maps every location you’ve submitted a checklist from — whether it’s a hotspot or a personal location. You can search for a species, filter by date, highlight lifers and last-seen locations, and explore your birding history on a map.
#
# ### ✅ What This Notebook Does 
#
# - Loads your eBird data export (CSV format)
# - Draws a map of all checklist locations (green by default)
# - Highlights locations where a selected species was seen (currently purple)
# - Marks your lifer (first-ever) and last-seen location for that species with distinct pin colours
# - Shows stats banners: all-species totals when viewing all, or species-specific (checklists, individuals, high count) when filtering
# - Lets you hide non-matching locations
# - Offers type-ahead search that mimics eBird’s own species search behaviour
# - Supports date-range filtering
# - Adds detailed popups with links:
#   - Location names link to your eBird life list for that place
#   - Visit dates/times link to each checklist
#   - Media icon (📷) links to Macaulay Library when available
#
# > 📍 You’ll find the interactive **search box and map display towards the end of the notebook**. Once everything’s loaded, scroll down to use it.
#
# ---
#
# ### 🚀 Getting Started
#
# To run this notebook, you’ll need:
#
# - Python
# - Jupyter Notebook or JupyterLab
#
# It works on macOS, Windows, or Linux.
#
# Jupyter notebooks are interactive coding environments used for working with data — this one is designed specifically to help you explore your birding records.
#
# If you haven’t set up Python or Jupyter before, don’t worry — just ask ChatGPT, Microsoft Copilot, or your favourite chat bot to walk you through it.  Hey, you could even use a Google search.  
#
# You'll probably need to install some Python modules also.  These modules will include:  `ipywidgets`, `pandas`, `whoosh`, `folium`, and `scikit-learn`.
#
# Once up and running, the menu items **Run All Cells** and **Restart Kernel and Clear Outputs of All Cells** are your friends.
#
# ---
#
# ### ⚙️ One Small Setup Note
#
# By default, the notebook expects your eBird data file to be named `MyEBirdData.csv`. This is controlled by a variable in the first code cell — you can change it if needed.
#
# Folder paths can be set in several ways: a hardcoded path in the User Variables cell, or a config file in the `scripts` folder. The notebook tries each location in order until it finds your data file; the notebook folder is tried last (e.g. for Binder uploads).
#
# Other than that, just run the notebook from top to bottom — it should work straight away.
#
# ### 🎩✨ Voila
#
# Yes, this should work with voila.  Tested for about five minutes after figuring out how to hide all the doco.  Voila let's you see this notebook as a dashboard with just the input UI elements and the map.  The code and the docoumentation is hidden.  Launch viola from the notebooks folder and configuration in `voila.json` will hide the markdown documentation cells so just the search box and map will display.  You don't need to do this, this notebook works nicely here in Jupyter Labs also if you don't mind the clutter.
#

# %% [markdown] editable=true slideshow={"slide_type": ""} tags=["voila_hide"]
# ### 🛠️ User Configuration
#
# Set these variables to control how the map behaves.
#
# - `EBIRD_DATA_FILE_NAME`: the name of your eBird export file (must be in the same folder).
# - `OUTPUT_HTML_FILE_NAME`: name of the saved HTML map file (overwritten each update).
# - `EXPORT_HTML`:  
#   - `True` — the map is saved to HTML each time it updates  
#   - `False` — no HTML export
# - `MAP_STYLE`: choose from `"default"`, `"satellite"`, `"google"`, or `"carto"`.
# - `MARK_LIFER`: `True` — highlights your first-ever sighting (lifer) with a distinct pin
# - `MARK_LAST_SEEN`: `True` — highlights your most recent sighting with a distinct pin (skipped if same as lifer)
# - `LIFER_COLOR`, `LIFER_FILL`, `LAST_SEEN_COLOR`, `LAST_SEEN_FILL`, etc. — pin colours (see User Variables cell)
# - `FILTER_BY_DATE`:  
#   - `True` — only show locations and sightings within the specified date range  
#   - `False` — include all data
# - `FILTER_START_DATE`, `FILTER_END_DATE`: format as `YYYY-MM-DD`  
#   These only apply if `FILTER_BY_DATE` is `True`.
# - `POPUP_SORT_ORDER`: `"ascending"` (oldest first) or `"descending"` (newest first) for visit/species lists in popups.
# - `POPUP_SCROLL_HINT`: when popup content overflows, show `"chevron"` (▲▼), `"shading"` (fade gradients), or `"both"` to compare.
# - `TOP_N_TABLE_LIMIT`: max rows per rankings table (e.g. 200); tables are scrollable.
# - `RANKINGS_TABLE_VISIBLE_ROWS`: rows visible before scrolling (e.g. 16).
# - `CLOSE_LOCATION_METERS`: distance (m) below which locations are considered "close" in the Map maintenance tab.
#
# > NOTE: Paths can be set in three ways: (1) `DATA_FOLDER_HARDCODED` in this cell, (2) `scripts/config_secret.py`, or (3) `scripts/config_template.py`. The notebook tries each in order until the data file is found; the notebook folder is tried last (e.g. for Binder uploads).
#
# #### Pin colour reference (named colours for Folium)
#
# Use these names in `LIFER_COLOR`, `LIFER_FILL`, etc. (HTML/CSS named colours):
#
# - **Basic:** black, white, gray, silver
# - **Reds / pinks:** red, crimson, darkred, firebrick, salmon, coral, tomato, hotpink, pink
# - **Oranges / yellows:** orange, darkorange, gold, goldenrod, yellow, lightyellow
# - **Greens:** green, darkgreen, lightgreen, lime, olive, seagreen
# - **Blues:** blue, navy, darkblue, dodgerblue, skyblue, steelblue, cornflowerblue
# - **Purples:** purple, indigo, darkviolet, blueviolet, mediumpurple, orchid, violet
# - **Browns / neutrals:** brown, saddlebrown, chocolate, tan, wheat, beige, khaki

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
EXPORT_HTML = True  # Save HTML file each time map is updated

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

# Optional date range filtering (set to False to disable)
# Note: Some eBird exports (e.g. checklists with no time, generalized locations) may use year 2026.
# If locations/species are missing, set FILTER_BY_DATE = False or extend the range.
FILTER_BY_DATE = False
FILTER_START_DATE = "2025-01-01"
FILTER_END_DATE = "2025-12-31"

# %% [markdown] editable=true slideshow={"slide_type": ""} tags=["voila_hide"]
# ### 📦 Imports and Setup
#
# This cell loads all the required Python libraries:
#
# - **pandas**, **folium** – for data handling and map rendering  
# - **ipywidgets** – for interactive dropdowns, checkboxes, and layout  
# - **Whoosh** – for fast fuzzy text search on species names  
# - **IPython.display** – to control how HTML and maps are shown in the notebook  
# - **tempfile**, **threading**, **os**, **sys**, **datetime** – used for behind-the-scenes file and thread management
#
# It also applies some custom CSS to make the output map stretch to full width.
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
from datetime import datetime

import pandas as pd
import folium
from branca.element import Element
import tempfile
import threading
import importlib.util
import ipywidgets as widgets

from ipywidgets import Accordion, Checkbox, VBox
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
</style>
"""))


# %% [markdown] editable=true slideshow={"slide_type": ""} tags=["voila_hide"]
# ### 🧰 Date/Time Helper Function
#
# This utility function ensures consistency in handling date and time columns:
# - Parses `Date` to proper datetime objects
# - Fills missing `Time` values with `"12:00 AM"` (so they parse when mixed with AM/PM times)
# - Combines both into a new `datetime` column
#
# Used for sorting lifer and last-seen locations, and for chronological ordering in popups.
#

# %%
# --------------------------------------------
# ✅ Helper: Add datetime column from Date + Time
# --------------------------------------------
def add_datetime_column(df):
    df["Date"] = pd.to_datetime(df["Date"], errors="coerce")
    df["Time"] = df["Time"].fillna("00:00")
    # Normalize "00:00" to "12:00 AM" so it parses when mixed with AM/PM times (e.g. "08:30 AM")
    time_str = df["Time"].astype(str).replace("00:00", "12:00 AM")
    date_str = df["Date"].apply(lambda x: x.strftime("%Y-%m-%d") if pd.notna(x) else "")
    df["datetime"] = pd.to_datetime(date_str + " " + time_str, errors="coerce")
    return df


# %% [markdown] editable=true slideshow={"slide_type": ""} tags=["voila_hide"]
# ### ⚙️ Load Config and eBird Data
#
# This cell handles the core setup and data load:
#
# - Resolves data file location by trying, in order: hardcoded path, config_secret, config_template, notebook folder  
# - Cross-platform (macOS and Windows); falls through to next location if file not found  
# - Loads the CSV and parses the `"Date"` column  
# - Optionally filters the **main dataset (`df`)** by a specified date range  
# - Excludes locations with no associated checklist (orphaned from cleanup, shared-list quirks)
# - Extracts a unique set of locations and species from the filtered data  
# - Builds a lookup map from common names → scientific names
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

# Try each candidate until we find the data file
file_path = None
DATA_FOLDER = None
for _folder in _candidate_folders:
    _candidate_path = os.path.join(_folder, EBIRD_DATA_FILE_NAME)
    if os.path.exists(_candidate_path):
        file_path = _candidate_path
        DATA_FOLDER = _folder
        break

if file_path is None:
    _tried = ", ".join(_candidate_folders)
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
df = pd.read_csv(file_path)
df = add_datetime_column(df)
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

# Exclude locations with no associated checklist (e.g. orphaned from cleanup, shared-list quirks)
location_ids_with_checklists = set(df_full.dropna(subset=["Submission ID"])["Location ID"].unique())
all_locations_from_csv = df_full[["Location ID", "Location", "Latitude", "Longitude"]].drop_duplicates(subset=["Location ID"])
df = df[df["Location ID"].isin(location_ids_with_checklists)]
df_full = df_full[df_full["Location ID"].isin(location_ids_with_checklists)]

# Locations without checklists (excluded from map and other tabs)
locations_without_checklists = all_locations_from_csv[~all_locations_from_csv["Location ID"].isin(location_ids_with_checklists)]

# Extract location and species info
location_data = df[['Location ID', 'Location', 'Latitude', 'Longitude']].drop_duplicates()
full_location_data = df_full[['Location ID', 'Location', 'Latitude', 'Longitude']].drop_duplicates()
species_list = sorted(df["Common Name"].dropna().unique().tolist())
selected_species_scientific = ""
selected_species_common = ""

# Pre-calculate totals for "all species" banner (Count can be "X" for present; treat as 1)
def _safe_count(x):
    if pd.isna(x):
        return 0
    try:
        return int(x)
    except (ValueError, TypeError):
        return 1


def _format_sighting_row(r):
    """Format a single sighting row for popup HTML: date, time, species, count, checklist link, optional media link."""
    date_str = r["Date"].strftime("%Y-%m-%d") if pd.notna(r["Date"]) else "unknown"
    time_str = str(r["Time"]) if pd.notna(r["Time"]) else "unknown"
    text = f"{date_str} {time_str} — {r['Common Name']} ({r['Count']})"
    cid = r.get("Submission ID", "")
    checklist_url = f"https://ebird.org/checklist/{cid}" if cid else "#"
    media_html = ""
    ml = r.get("ML Catalog Numbers")
    if pd.notna(ml) and str(ml).strip():
        first_ml = str(ml).strip().split()[0]
        media_html = f' <a href="https://macaulaylibrary.org/asset/{first_ml}" target="_blank" title="View media">📷</a>'
    return f'<br><a href="{checklist_url}" target="_blank">{text}</a>{media_html}'


def _base_species_for_count(row):
    """Normalize to countable species (used for filter_species / single-row lookups)."""
    sci = (row.get("Scientific Name") or "").strip()
    common = (row.get("Common Name") or "").strip()
    if not sci:
        return None
    if " sp." in sci or sci.lower().endswith(" sp"):
        return None  # spuh
    if " x " in sci or "(hybrid)" in common.lower():
        return None  # hybrid
    if "Domestic" in common or "(Domestic type)" in common:
        return None
    parts = sci.split()
    if len(parts) < 2:
        return None
    if "/" in parts[1]:
        return None  # species-level slash (not countable)
    return f"{parts[0]} {parts[1]}".lower()

def _countable_species_vectorized(df):
    """Vectorized species count: exclude spuhs, slashes, hybrids, domestic; roll up subspecies."""
    sci = df["Scientific Name"].fillna("").astype(str).str.strip()
    common = df["Common Name"].fillna("").astype(str).str.strip()
    spuh = sci.str.contains(r" sp\.", case=False, na=False) | sci.str.lower().str.endswith(" sp")
    hybrid = sci.str.contains(" x ", na=False) | common.str.lower().str.contains(r"\(hybrid\)", na=False)
    domestic = common.str.contains("Domestic", na=False) | common.str.contains(r"\(Domestic type\)", na=False)
    parts = sci.str.split(expand=True)
    slash = parts[1].str.contains("/", na=False) if 1 in parts.columns else pd.Series(False, index=df.index)
    too_short = parts[0].isna() | parts[1].isna() if 1 in parts.columns else parts[0].isna()
    exclude = spuh | hybrid | domestic | slash | too_short
    base = parts[0].str.lower() + " " + parts[1].str.lower()
    return base.where(~exclude)

total_checklists = df["Submission ID"].nunique()
total_individuals = int(df["Count"].apply(_safe_count).sum())
total_species = int(_countable_species_vectorized(df).dropna().nunique())

# Build common → scientific name map
name_map = (
    df[['Common Name', 'Scientific Name']]
    .dropna()
    .drop_duplicates()
    .set_index('Common Name')['Scientific Name']
    .to_dict()
)



# %% [markdown] editable=true slideshow={"slide_type": ""} tags=["voila_hide"]
# ### 🔍 Build Whoosh Index for Species Autocomplete
#
# Creates an in-memory search index of species names for fast, fuzzy autocomplete.
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
# ### 🗺️ Initialise Global Map Objects
#
# Sets up the global map and output widgets used for rendering and interaction.
#

# %%
# --------------------------------------------
# ✅ Initialise global map objects
# --------------------------------------------
species_map = None
map_output = widgets.Output(layout=widgets.Layout(min_height="500px", width="100%"))
output = widgets.Output()


# %% [markdown] editable=true slideshow={"slide_type": ""} tags=["voila_hide"]
# ### 🔍 Autocomplete UI Widgets
#
# Defines the text input, dropdown list, and checkbox used for species search and filtering.
#

# %%
# --------------------------------------------
# ✅ Autocomplete UI Widgets
# --------------------------------------------
debounce_delay = 0.3  # seconds to wait after search box cleared before resetting
debounce_timer = None
search_box = widgets.Text(placeholder="Type species name...", description="Search:")
dropdown = widgets.Select(options=[], value=None, description="Matches:", rows=10)
hide_non_matching_checkbox = Checkbox(
    value=False,
    description='Show only selected species',
    indent=False
)


# %% [markdown] editable=true slideshow={"slide_type": ""} tags=["voila_hide"]
# ### 🧪 Species Filter (handles slashes and subspecies)
#
# Filters the dataset for a given base species name, excluding subspecies and slash group variants unless explicitly searched.
#

# %%
# --------------------------------------------
# ✅ Species Filter (for subspecies / slashes)
# --------------------------------------------

def filter_species(df, base_species):
    base_species = base_species.lower().strip()
    if "/" in base_species:
        return df[df["Scientific Name"].str.lower() == base_species]
    filtered_df = df[df["Scientific Name"].fillna("").str.lower().str.startswith(base_species)]

    # Exclude only species-level slash groups (e.g. Anas gracilis/castanea), not subspecies with
    # slash (e.g. Tyto tenebricosa tenebricosa/arfaki). A slash at the boundary after our prefix
    # indicates a species-level split; a slash later (in subspecies) we include.
    def is_species_level_slash(sci_name):
        sn = (sci_name or "").lower()
        if "/" not in sn:
            return False
        rest = sn[len(base_species) :].lstrip()
        return rest.startswith("/")

    mask = filtered_df["Scientific Name"].fillna("").apply(
        lambda s: not is_species_level_slash(s)
    )
    return filtered_df[mask]


# %% [markdown] editable=true slideshow={"slide_type": ""} tags=["voila_hide"]
# ### 📍 Map Maintenance Data (duplicates, close locations)
#
# Used by the Map maintenance tab to find exact duplicates and near-duplicate locations.
#

# %%
def _get_map_maintenance_data(loc_df, threshold_m):
    """Return (exact_dup_rows, near_pairs) for Map maintenance tab.
    - exact_dup_rows: list of (location_name, location_id, count) for duplicates table
    - near_pairs: list of [(loc_id1, loc_name1), (loc_id2, loc_name2)] for close-location pairs
    """
    if "Location" not in loc_df.columns:
        return [], []
    one_per_loc = loc_df[["Location ID", "Location", "Latitude", "Longitude"]].drop_duplicates(subset=["Location ID"], keep="first")
    one_per_loc = one_per_loc.copy()
    one_per_loc["Latitude"] = pd.to_numeric(one_per_loc["Latitude"], errors="coerce")
    one_per_loc["Longitude"] = pd.to_numeric(one_per_loc["Longitude"], errors="coerce")
    one_per_loc = one_per_loc.dropna(subset=["Latitude", "Longitude"])

    if len(one_per_loc) < 2:
        return [], []

    import numpy as np
    from sklearn.neighbors import BallTree

    id_to_name = dict(zip(one_per_loc["Location ID"], one_per_loc["Location"]))
    id_to_coords = dict(zip(one_per_loc["Location ID"], zip(one_per_loc["Latitude"], one_per_loc["Longitude"])))

    # Exact duplicates: group by coords. If same name appears multiple times, list once; if different names, list each.
    coord_cols = ["Latitude", "Longitude"]
    dup_coords = one_per_loc[coord_cols].round(6).duplicated(keep=False)
    dup_df = one_per_loc.loc[dup_coords]
    exact_dup_rows = []
    if not dup_df.empty:
        grouped = dup_df.groupby(dup_df[coord_cols].round(6).apply(tuple, axis=1))
        for _, grp in grouped:
            count = len(grp)
            # Dedupe by name: same name -> one row; different names -> separate rows
            by_name = grp.drop_duplicates(subset=["Location"], keep="first")
            for _, r in by_name.iterrows():
                lat, lon = r["Latitude"], r["Longitude"]
                exact_dup_rows.append((r["Location"], r["Location ID"], count, lat, lon))

    # Near duplicates: collect pairs (treat as pairs even if cluster has >2)
    coords = np.radians(one_per_loc[["Latitude", "Longitude"]].values)
    ids = one_per_loc["Location ID"].tolist()
    earth_radius = 6_371_000
    radius_rad = threshold_m / earth_radius
    tree = BallTree(coords, metric="haversine")
    indices, distances = tree.query_radius(coords, r=radius_rad, return_distance=True)

    seen_pairs = set()
    near_pairs = []
    for i, (neighbors, dists) in enumerate(zip(indices, distances)):
        for k, j in enumerate(neighbors):
            if i != j and dists[k] * earth_radius > 0.01:
                pair = tuple(sorted([ids[i], ids[j]]))
                if pair not in seen_pairs:
                    seen_pairs.add(pair)
                    coords_i = id_to_coords.get(ids[i], (None, None))
                    coords_j = id_to_coords.get(ids[j], (None, None))
                    near_pairs.append([
                        (ids[i], id_to_name.get(ids[i], ids[i]), coords_i[0], coords_i[1]),
                        (ids[j], id_to_name.get(ids[j], ids[j]), coords_j[0], coords_j[1]),
                    ])
    return exact_dup_rows, near_pairs


# %% [markdown] editable=true slideshow={"slide_type": ""} tags=["voila_hide"]
# ### 🐣 Build True Lifer and Last-Seen Tables
#
# Creates lookup dictionaries for lifer (first-ever) and last-seen (most recent) locations per species:
#
# - Reloading the full dataset to avoid effects of any active filters
# - Excluding locations with no checklist (consistent with main data)
# - Parsing and combining dates and times into full datetime objects
# - Sorting the full data chronologically
# - Finding the first-ever sighting (lifer) and most recent sighting (last-seen) per species
#
# Used to correctly mark lifer and last-seen pins regardless of current date filters.
#

# %%
# --------------------------------------------
# ✅ Build True Lifer and Last-Seen Tables (from full dataset)
# --------------------------------------------

# Reload full dataset to avoid filtering effects (date filter, lifer calc)
full_df = pd.read_csv(file_path)
full_df = add_datetime_column(full_df)
# Exclude locations with no checklist (consistent with main data)
full_df = full_df[full_df["Location ID"].isin(location_ids_with_checklists)]

# Build lifer location dictionary: base species (genus + species) → first seen location.
# Uses base species so subspecies (e.g. Tyto javanica [javanica Group]) roll up to the
# same lifer as the nominate (Tyto javanica) — the chronologically first record wins.
def _base_species_for_lifer(sci_name):
    if pd.isna(sci_name) or not str(sci_name).strip():
        return None
    parts = str(sci_name).strip().split()
    if len(parts) < 2:
        return None
    return f"{parts[0]} {parts[1]}".lower()

_lifer_lookup_df = (
    full_df.sort_values("datetime")
    .dropna(subset=["Scientific Name", "Location ID", "datetime"])
    .assign(_base=lambda x: x["Scientific Name"].apply(_base_species_for_lifer))
)
_lifer_lookup_df = _lifer_lookup_df[_lifer_lookup_df["_base"].notna()]
true_lifer_locations = _lifer_lookup_df.groupby("_base").first()["Location ID"].to_dict()
true_last_seen_locations = _lifer_lookup_df.groupby("_base").last()["Location ID"].to_dict()


# %% [markdown] editable=true slideshow={"slide_type": ""} tags=["voila_hide"]
# ### 🎛️ UI Event Handlers
#
# Handles user interaction with species search and filter controls:
#
# - `on_species_selected`: 
#   - Updates the selected species when a dropdown item is clicked
#   - Looks up the scientific name from the common name
#   - Draws the species map
#   - Clears the map if the search box and dropdown are both empty
#
# - `on_toggle_change`: 
#   - Redraws the map when the "hide non-matching" checkbox is toggled
#   - Only has an effect if a species is currently selected
#
# - `on_search_box_cleared`: 
#   - Waits briefly after clearing the search box (debounce)
#   - If still empty, resets the dropdown, checkbox, and full map view
#
# These handlers drive the main species filtering logic and keep the map UI reactive.
#

# %%
# --------------------------------------------
# ✅ UI Event Handlers
# --------------------------------------------

# ✅ Called when a dropdown species is selected
def on_species_selected(change):
    global selected_species_scientific, selected_species_common
    output.clear_output()

    selected = change.get("new")
    search_text = search_box.value.strip()

    # Show full map if search fully cleared
    if selected is None and search_text == "":
        selected_species_scientific = ""
        selected_species_common = ""
        hide_non_matching_checkbox.value = False
        with output:
            print("🧹 Search truly cleared — showing all locations")
        draw_map_with_species_overlay("", "")
        return

    # Don't trigger if no species selected
    if selected is None:
        print("🚫 No selection — skipping map draw")
        return

    # Lookup scientific name
    selected_species_scientific = name_map.get(selected, "").strip()
    selected_species_common = selected or ""
    print(f"✅ Selected scientific name: {selected_species_scientific}")

    with output:
        print(f"🔎 Selected species: {selected} → Scientific: {selected_species_scientific}")
    draw_map_with_species_overlay(selected_species_scientific, selected_species_common)


# ✅ Called when the "hide non-matching" checkbox is toggled (species filter only)
def on_toggle_change(change):
    global selected_species_scientific, selected_species_common
    with output:
        print(f"🧪 Toggle changed: {change['new']} — Current species: {selected_species_scientific}")
    if selected_species_scientific:
        draw_map_with_species_overlay(selected_species_scientific, selected_species_common)


# ✅ Called when search box is cleared (after short debounce)
def on_search_box_cleared(change):
    global debounce_timer

    old_val = change.get("old", "").strip()
    new_val = change.get("new", "").strip()

    if old_val and not new_val:
        if debounce_timer:
            debounce_timer.cancel()

        def handle_clear():
            global selected_species_scientific, selected_species_common
            if search_box.value.strip() == "":
                dropdown.options = []
                dropdown.value = None
                hide_non_matching_checkbox.value = False
                selected_species_scientific = ""
                selected_species_common = ""
                with output:
                    output.clear_output()
                    print("🧹 Search cleared — showing all locations")
                draw_map_with_species_overlay("", "")

        debounce_timer = threading.Timer(debounce_delay, handle_clear)
        debounce_timer.start()



# %% [markdown] editable=true slideshow={"slide_type": ""} tags=["voila_hide"]
# ### 🔡 Autocomplete Search Logic
#
# This function handles fuzzy autocomplete updates when the user types in the search box:
#
# - Ignores input shorter than 3 characters
# - Uses Whoosh to run a partial (wildcard) search across species names
# - Parses and scores matches, giving a bonus to names that start with the first typed token
# - Updates the dropdown with the top 10 most relevant matches
#
# 📌 Keeps suggestions focused and relevant as the user types, even with typos or partial input.
#

# %%
# --------------------------------------------
# ✅ Autocomplete Search Logic 
# --------------------------------------------
def update_suggestions(change):
    print(f"✍️ Search changed: '{change['new']}'")
    query = change["new"].strip().lower()
    if len(query) < 3:
        dropdown.options = []
        return
    with ix.searcher() as searcher:
        qp = QueryParser("common_name", ix.schema, group=OrGroup)
        tokens = query.split()
        try:
            q = qp.parse(" ".join(f"{t}*" for t in tokens))
        except Exception:
            dropdown.options = []
            return
        results = searcher.search(q, limit=None)

        def score(r):
            name = r["common_name"].lower()
            base = 100 - r.rank
            if name.startswith(tokens[0]):
                base += 50
            return base

        ranked = sorted(results, key=score, reverse=True)
        #print(f"🎯 Search matches found: {[r['common_name'] for r in ranked[:10]]}")
        dropdown.options = [r["common_name"] for r in ranked[:10]]



# %% [markdown] editable=true slideshow={"slide_type": ""} tags=["voila_hide"]
# ### 🧷 Register Widget Observers
#
# Connects UI elements to their respective callback functions:
#
# - `search_box`: updates suggestions and clears search
# - `dropdown`: triggers map redraw on selection
# - `hide_non_matching_checkbox`: toggles visibility of non-matching markers
#
# 📌 Enables real-time interaction between widgets and map updates.
#

# %%
# --------------------------------------------
# ✅ Register observers
# --------------------------------------------
search_box.observe(update_suggestions, names="value")
search_box.observe(on_search_box_cleared, names="value")
dropdown.observe(on_species_selected, names="value")
hide_non_matching_checkbox.observe(on_toggle_change, names="value")


# %% [markdown] editable=true slideshow={"slide_type": ""} tags=["voila_hide"]
# ### 🗺️ Create Base Map with Tile Style
#
# Initialises the Folium map using the selected `MAP_STYLE`:
#
# - `"default"`: Standard OpenStreetMap tiles
# - `"satellite"`: Esri WorldImagery (aerial view)
# - `"google"`: Google satellite tiles (unofficial)
# - `"carto"`: CartoDB Positron (clean, minimalist look)
#
# Used as the foundation for all map rendering.
#

# %%
# --------------------------------------------
# ✅ Create base map with selected tile style
# --------------------------------------------
def _popup_scroll_script(scroll_hint, scroll_to_bottom):
    """Return HTML script for popup scroll hints (chevrons/shading). Runs in map iframe."""
    hint_js = repr(scroll_hint)
    to_bottom_js = "true" if scroll_to_bottom else "false"
    return f"""
<script>
(function() {{
  var HINT = {hint_js};
  var SCROLL_TO_BOTTOM = {to_bottom_js};

  function updateHints(scrollable, wrapper) {{
    var st = scrollable.scrollTop;
    var maxScroll = scrollable.scrollHeight - scrollable.clientHeight;
    var hasMoreAbove = st > 0;
    var hasMoreBelow = st < maxScroll;

    if (HINT === 'chevron' || HINT === 'both') {{
      var upEl = wrapper.querySelector('.popup-scroll-up');
      var downEl = wrapper.querySelector('.popup-scroll-down');
      if (upEl) upEl.style.visibility = hasMoreAbove ? 'visible' : 'hidden';
      if (downEl) downEl.style.visibility = hasMoreBelow ? 'visible' : 'hidden';
    }}
    if (HINT === 'shading' || HINT === 'both') {{
      var topShade = wrapper.querySelector('.popup-scroll-shade-top');
      var botShade = wrapper.querySelector('.popup-scroll-shade-bot');
      if (topShade) topShade.style.visibility = hasMoreAbove ? 'visible' : 'hidden';
      if (botShade) botShade.style.visibility = hasMoreBelow ? 'visible' : 'hidden';
    }}
  }}

  function setupPopup(scrollable, wrapper) {{
    var hasOverflow = scrollable.scrollHeight > scrollable.clientHeight;
    if (!hasOverflow) return;

    scrollable.scrollTop = SCROLL_TO_BOTTOM ? scrollable.scrollHeight : 0;

    var scrollTop = scrollable.offsetTop;
    if (HINT === 'chevron' || HINT === 'both') {{
      var up = document.createElement('div');
      up.className = 'popup-scroll-up';
      up.style.cssText = 'position:absolute;top:' + scrollTop + 'px;left:50%;transform:translateX(-50%);font-size:10px;color:#888;pointer-events:none;z-index:10;';
      up.textContent = '\\u25B2';
      var down = document.createElement('div');
      down.className = 'popup-scroll-down';
      down.style.cssText = 'position:absolute;bottom:8px;left:50%;transform:translateX(-50%);font-size:10px;color:#888;pointer-events:none;z-index:10;';
      down.textContent = '\\u25BC';
      wrapper.appendChild(up);
      wrapper.appendChild(down);
    }}
    if (HINT === 'shading' || HINT === 'both') {{
      var topShade = document.createElement('div');
      topShade.className = 'popup-scroll-shade-top';
      topShade.style.cssText = 'position:absolute;top:' + scrollTop + 'px;left:0;right:0;height:24px;pointer-events:none;z-index:5;background:linear-gradient(to bottom,rgba(255,255,255,0.95),transparent);';
      var botShade = document.createElement('div');
      botShade.className = 'popup-scroll-shade-bot';
      botShade.style.cssText = 'position:absolute;bottom:0;left:0;right:0;height:24px;pointer-events:none;z-index:5;background:linear-gradient(to top,rgba(255,255,255,0.95),transparent);';
      wrapper.appendChild(topShade);
      wrapper.appendChild(botShade);
    }}

    updateHints(scrollable, wrapper);
    scrollable.addEventListener('scroll', function() {{ updateHints(scrollable, wrapper); }});
  }}

  function onPopupOpen() {{
    setTimeout(function() {{
      var scrollable = document.querySelector('.leaflet-popup-content div[style*="overflow-y"]');
      if (!scrollable) return;
      var wrapper = scrollable.parentElement;
      if (wrapper.dataset.popupSetup) return;
      wrapper.dataset.popupSetup = '1';
      setupPopup(scrollable, wrapper);
    }}, 100);
  }}

  var observer = new MutationObserver(function(mutations) {{
    for (var i = 0; i < mutations.length; i++) {{
      for (var j = 0; j < mutations[i].addedNodes.length; j++) {{
        var node = mutations[i].addedNodes[j];
        if (node.nodeType === 1 && node.classList && node.classList.contains('leaflet-popup')) {{
          onPopupOpen();
          return;
        }}
      }}
    }}
  }});
  observer.observe(document.body, {{ childList: true, subtree: true }});
}})();
</script>
"""


def create_map(map_center):
    if MAP_STYLE == "default":
        return folium.Map(location=map_center, zoom_start=6)
    elif MAP_STYLE == "satellite":
        return folium.Map(location=map_center, zoom_start=6, tiles="Esri WorldImagery", attr="Esri")
    elif MAP_STYLE == "google":
        return folium.Map(
            location=map_center,
            zoom_start=6,
            tiles="https://mt1.google.com/vt/lyrs=y&x={x}&y={y}&z={z}",
            attr="Google"
        )
    elif MAP_STYLE == "carto":
        return folium.Map(location=map_center, zoom_start=6, tiles="CartoDB Positron", attr="CartoDB")
    else:
        return folium.Map(location=map_center, zoom_start=6)


# %% [markdown] editable=true slideshow={"slide_type": ""} tags=["voila_hide"]
# ### 🗺️ Draw Map with Species Overlay
#
# Creates and displays the interactive map with observation markers.
#
# Handles two main cases:
#
# - **No species selected**:  
#   - Places **green** markers at all locations in the dataset  
#   - Shows **all-species banner** (checklists, species count, individuals)
#   - Popups show visit history with links to each checklist and to the location's eBird life list page
#
# - **Species selected**:  
#   - Filters dataset using `filter_species()`, centres map on species locations
#   - Adds **red** markers at locations where species was seen  
#   - Optionally adds distinct pins for **lifer** (first-ever) and **last-seen** (most recent) — colours configurable
#   - Shows **species-specific banner** (checklists, individuals, high count)
#   - Green markers for locations with no sightings unless the checkbox hides them
#   - Popups include checklist links, Macaulay Library media links (📷) when available, and location links
#
# Extra features:
# - Map centres on species locations when filtering; on all locations when viewing "All species"
# - Saves map as HTML if `EXPORT_HTML = True`
#

# %%
# --------------------------------------------
# ✅ Draw map with species overlay (refactored for lifer-on-top and single loop)
# --------------------------------------------
def draw_map_with_species_overlay(selected_species, selected_common_name=""):
    global species_map

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
        map_center = [location_data["Latitude"].mean(), location_data["Longitude"].mean()]

    species_map = create_map(map_center)

    # Pre-group by Location ID to avoid repeated full DataFrame scans (O(1) lookup vs O(n) per location)
    records_by_loc = {lid: grp for lid, grp in df.groupby("Location ID")}

    if not selected_species:
        # Case 1: No species selected – draw all as green, show totals banner
        banner_html = f"""
        <div style="position:fixed;top:10px;right:10px;z-index:1000;background:rgba(255,255,255,0.95);
                    padding:10px 14px;border-radius:6px;box-shadow:0 2px 10px rgba(0,0,0,0.2);
                    font-family:sans-serif;font-size:13px;line-height:1.5;">
            <b>All species</b><br>
            {total_checklists} checklist{total_checklists != 1 and 's' or ''} &nbsp;|&nbsp;
            {total_species} species &nbsp;|&nbsp;
            {total_individuals} individual{total_individuals != 1 and 's' or ''}
        </div>
        """
        species_map.get_root().html.add_child(Element(banner_html))

        popup_asc = POPUP_SORT_ORDER == "ascending"
        for _, row in location_data.iterrows():
            base_records = records_by_loc.get(row["Location ID"], pd.DataFrame())
            visit_records = base_records.drop_duplicates(subset=["Submission ID"]).sort_values(["Date", "Time"], ascending=[popup_asc, popup_asc])
            visit_info = "<br>".join(
                f'<a href="https://ebird.org/checklist/{r["Submission ID"]}" target="_blank">{r["Date"].strftime("%Y-%m-%d") if pd.notna(r["Date"]) else "?"} {str(r["Time"]) if pd.notna(r["Time"]) else "unknown"}</a>'
                for _, r in visit_records.iterrows()
            ) if not visit_records.empty else ""
            loc_id = row["Location ID"]
            loc_url = f"https://ebird.org/lifelist/{loc_id}"
            loc_link = f'<a href="{loc_url}" target="_blank">{row["Location"]}</a>'
            popup_html = f'<div class="popup-scroll-wrapper" style="position:relative;"><div style="margin-bottom:6px;"><b>{loc_link}</b></div><div style="max-height:300px;overflow-y:auto;"><b>Visited:</b><br>{visit_info}</div></div>'
            popup = folium.Popup(popup_html, max_width=800)
            color, fill = DEFAULT_COLOR, DEFAULT_FILL
            folium.CircleMarker(
                location=[row['Latitude'], row['Longitude']],
                radius=4,
                color=color,
                fill=True,
                fill_color=fill,
                fill_opacity=0.6,
                popup=popup
            ).add_to(species_map)

    else:
        # Case 2: Filtered by species (filtered, seen_location_ids already computed above)
        popup_asc = POPUP_SORT_ORDER == "ascending"
        filtered_by_loc = {lid: grp for lid, grp in filtered.groupby("Location ID")}

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
        base = _base_species_for_lifer(selected_species)
        if base:
            subset = _lifer_lookup_df[_lifer_lookup_df["_base"] == base]
            if not subset.empty:
                first_rec = subset.iloc[0]
                last_rec = subset.iloc[-1]
                first_seen_date = _banner_date(first_rec["Date"])
                last_seen_date = _banner_date(last_rec["Date"])

        # Date when high count was achieved
        high_count_rows = filtered[filtered["Count"].apply(_safe_count) == high_count]
        if not high_count_rows.empty:
            high_count_date = _banner_date(high_count_rows.iloc[0]["Date"])

        sep = " &nbsp;|&nbsp; "
        line2 = f"{n_checklists} checklist{n_checklists != 1 and 's' or ''}{sep}{n_individuals} individual{n_individuals != 1 and 's' or ''}"
        line3_parts = []
        if first_seen_date:
            line3_parts.append(f"First seen: {first_seen_date}")
        if last_seen_date:
            line3_parts.append(f"Last seen: {last_seen_date}")
        line3 = sep.join(line3_parts)
        line4 = f"High count: {high_count_date} ({high_count})"

        banner_html = f"""
        <div style="position:fixed;top:10px;right:10px;z-index:1000;background:rgba(255,255,255,0.95);
                    padding:10px 14px;border-radius:6px;box-shadow:0 2px 10px rgba(0,0,0,0.2);
                    font-family:sans-serif;font-size:13px;line-height:1.5;">
            <b>{selected_common_name or selected_species}</b><br>
            {line2}<br>
            {line3}<br>
            {line4}
        </div>
        """
        species_map.get_root().html.add_child(Element(banner_html))

        lifer_location = None
        last_seen_location = None
        if MARK_LIFER:
            base = _base_species_for_lifer(selected_species)
            true_lifer_loc = true_lifer_locations.get(base) if base else None
            if true_lifer_loc in seen_location_ids:
                lifer_location = true_lifer_loc
        if MARK_LAST_SEEN:
            base = _base_species_for_lifer(selected_species)
            true_last_loc = true_last_seen_locations.get(base) if base else None
            if true_last_loc in seen_location_ids and true_last_loc != lifer_location:
                last_seen_location = true_last_loc

        # Prepare classification flags
        location_data_local = location_data.copy()
        location_data_local["has_species_match"] = location_data_local["Location ID"].isin(seen_location_ids)
        location_data_local["is_lifer"] = location_data_local["Location ID"] == lifer_location
        location_data_local["is_last_seen"] = location_data_local["Location ID"] == last_seen_location

        # Sort so lifer drawn last (on top), then last seen, then species, then non-matching
        location_data_local = location_data_local.sort_values(
            by=["has_species_match", "is_lifer", "is_last_seen"], ascending=[True, True, True]
        )

        # Single loop for marker drawing
        for _, row in location_data_local.iterrows():
            loc_id = row["Location ID"]

            if not row["has_species_match"] and hide_non_matching_checkbox.value:
                continue

            base_records = records_by_loc.get(loc_id, pd.DataFrame())
            visit_records = base_records.drop_duplicates(subset=["Submission ID"]).sort_values(["Date", "Time"], ascending=[popup_asc, popup_asc])
            visit_info = "<br>".join(
                f'<a href="https://ebird.org/checklist/{r["Submission ID"]}" target="_blank">{r["Date"].strftime("%Y-%m-%d") if pd.notna(r["Date"]) else "?"} {str(r["Time"]) if pd.notna(r["Time"]) else "unknown"}</a>'
                for _, r in visit_records.iterrows()
            ) if not visit_records.empty else ""
            loc_url = f"https://ebird.org/lifelist/{loc_id}"
            loc_link = f'<a href="{loc_url}" target="_blank">{row["Location"]}</a>'
            if row["has_species_match"]:
                sub = filtered_by_loc.get(loc_id, pd.DataFrame()).sort_values(["Date", "Time"], ascending=[popup_asc, popup_asc])
                obs_details = "".join(_format_sighting_row(r) for _, r in sub.iterrows())
                popup_html = f'<div class="popup-scroll-wrapper" style="position:relative;"><div style="margin-bottom:6px;"><b>{loc_link}</b></div><div style="max-height:300px;overflow-y:auto;"><b>Visited:</b><br>{visit_info}<br><b>Seen:</b>{obs_details}</div></div>'
            else:
                popup_html = f'<div class="popup-scroll-wrapper" style="position:relative;"><div style="margin-bottom:6px;"><b>{loc_link}</b></div><div style="max-height:300px;overflow-y:auto;"><b>Visited:</b><br>{visit_info}</div></div>'
            popup_content = folium.Popup(popup_html, max_width=800)

            if row["is_lifer"]:
                color, fill, radius, fill_opacity = LIFER_COLOR, LIFER_FILL, 5, 0.9
            elif row["is_last_seen"]:
                color, fill, radius, fill_opacity = LAST_SEEN_COLOR, LAST_SEEN_FILL, 5, 0.9
            elif row["has_species_match"]:
                color, fill, radius, fill_opacity = SPECIES_COLOR, SPECIES_FILL, 4, 0.8
            else:
                color, fill, radius, fill_opacity = DEFAULT_COLOR, DEFAULT_FILL, 4, 0.6

            folium.CircleMarker(
                location=[row['Latitude'], row['Longitude']],
                radius=radius,
                color=color,
                fill=True,
                fill_color=fill,
                fill_opacity=fill_opacity,
                popup=popup_content
            ).add_to(species_map)

    # Scroll popup: chevrons/shading hints; runs in map iframe
    scroll_popup_script = _popup_scroll_script(POPUP_SCROLL_HINT, POPUP_SORT_ORDER == "ascending")
    species_map.get_root().html.add_child(Element(scroll_popup_script))

    with map_output:
        map_output.clear_output()
        map_html = species_map._repr_html_()
        display(HTML(f'<div class="output_map">{map_html}</div>'))

    if EXPORT_HTML:
        species_map.save(map_output_path)



# %% [markdown] editable=true slideshow={"slide_type": ""} tags=["voila_hide"]
# ### 🧭 Display UI
#
# Placeholder — the full dashboard (controls + map/tabs) is displayed in the next section
# so controls and map stay together with no gap.
#

# %%
# --------------------------------------------
# ✅ Display UI (controls + map/tabs combined below)
# --------------------------------------------
# Controls and map/tabs are displayed together in the next cell to avoid a gap.



# %% [markdown] editable=true slideshow={"slide_type": ""} tags=["voila_hide"]
# ### 🗺️ Dashboard: Controls + Map + Stats
#
# Controls and map/tabs are in one `VBox` so they stay together with no gap.
# Map is the primary tab. Checklist Statistics shows real data from your export.
#

# %%
# --------------------------------------------
# ✅ Helper: Longest consecutive-day streak
# --------------------------------------------
def _longest_streak(unique_dates, cl):
    """Find longest streak of consecutive days with a checklist. Returns (streak, start_date, start_loc, start_sid, end_date, end_loc, end_sid)."""
    import numpy as np

    streak = 0
    streak_start_date = ""
    streak_start_loc = ""
    streak_start_sid = ""
    streak_end_date = ""
    streak_end_loc = ""
    streak_end_sid = ""
    if len(unique_dates) == 0:
        return streak, streak_start_date, streak_start_loc, streak_start_sid, streak_end_date, streak_end_loc, streak_end_sid

    arr = np.asarray(pd.to_datetime(unique_dates)).astype("datetime64[D]")
    day_ints = np.unique(arr.view("int64"))
    diffs = np.diff(day_ints)
    gaps = np.where(diffs > 1)[0]
    best_start, best_end = day_ints[0], day_ints[-1]

    if len(gaps) == 0:
        streak = len(day_ints)
        if streak > 0:
            streak_start_date = pd.Timestamp(day_ints[0], unit="D").strftime("%d %b %Y")
            streak_end_date = pd.Timestamp(day_ints[-1], unit="D").strftime("%d %b %Y")
    else:
        indices = np.arange(len(diffs))
        segments = np.split(indices, gaps + 1)
        best_len = 0
        for i, seg in enumerate(segments):
            seg = list(seg)
            if i == 0 and len(seg) > 0 and seg[-1] in gaps:
                seg = seg[:-1]
            n = len(seg) + 1 if len(seg) > 0 else 1
            if n > best_len:
                best_len = n
                start_idx = seg[0] if seg else 0
                end_idx = (seg[-1] + 1) if seg else 0
                best_start = day_ints[start_idx]
                best_end = day_ints[min(end_idx, len(day_ints) - 1)]
        streak = best_len
        if best_start is not None and best_end is not None:
            streak_start_date = pd.Timestamp(best_start, unit="D").strftime("%d %b %Y")
            streak_end_date = pd.Timestamp(best_end, unit="D").strftime("%d %b %Y")

    # Look up locations for streak start/end
    if streak > 0 and "Date" in cl.columns:
        first_day = best_start if len(gaps) > 0 else day_ints[0]
        last_day = best_end if len(gaps) > 0 else day_ints[-1]
        first_d = pd.Timestamp(first_day, unit="D").normalize()
        last_d = pd.Timestamp(last_day, unit="D").normalize()
        cl_copy = cl.copy()
        cl_copy["_d"] = pd.to_datetime(cl_copy["Date"]).dt.normalize()
        start_m = cl_copy[cl_copy["_d"] == first_d]
        end_m = cl_copy[cl_copy["_d"] == last_d]
        if not start_m.empty:
            start_row = start_m.iloc[0]
            streak_start_loc = start_row.get("Location", "")
            streak_start_sid = str(start_row.get("Submission ID", ""))
        if not end_m.empty:
            end_row = end_m.iloc[-1]
            streak_end_loc = end_row.get("Location", "")
            streak_end_sid = str(end_row.get("Submission ID", ""))

    return streak, streak_start_date, streak_start_loc, streak_start_sid, streak_end_date, streak_end_loc, streak_end_sid


def _rankings_scroll_wrapper(table_html, scroll_hint, visible_rows):
    """Wrap table HTML in scrollable div with shading hints. Uses pure CSS (ipywidgets HTML does not run scripts)."""
    max_h = visible_rows * 38  # ~38px per row
    # Match popup gradient: fade to white/light. ipywidgets strips scripts, so we use static CSS overlays.
    shade_css = "position:absolute;left:0;right:0;height:24px;pointer-events:none;z-index:5;"
    top_shade = f'<div class="rankings-scroll-shade-top" style="{shade_css}top:0;background:linear-gradient(to bottom,rgba(255,255,255,0.95),transparent);"></div>'
    bot_shade = f'<div class="rankings-scroll-shade-bot" style="{shade_css}bottom:0;background:linear-gradient(to top,rgba(255,255,255,0.95),transparent);"></div>'
    show_shade = scroll_hint in ("shading", "both")
    shades = (top_shade + bot_shade) if show_shade else ""
    return f"""
<div class="rankings-scroll-wrapper" style="position:relative;">
  <div class="rankings-scroll-inner" style="max-height:{max_h}px;overflow-y:auto;">
    {table_html}
  </div>
  {shades}
</div>"""


def _rankings_by_value(df_sub, value_col, date_col, loc_col, loc_id_col, sid_col, fmt, limit):
    """Top N by value desc, date asc; ties show oldest. Location links to lifelist, date/time links to checklist."""
    if df_sub.empty or value_col not in df_sub.columns:
        return []
    use_col = "datetime" if "datetime" in df_sub.columns else date_col
    cols = [use_col, loc_col, sid_col, value_col]
    if loc_id_col and loc_id_col in df_sub.columns:
        cols.append(loc_id_col)
    d = df_sub[cols].dropna(subset=[value_col]).drop_duplicates()
    d = d.sort_values(by=[value_col, use_col], ascending=[False, True]).head(limit)
    rows = []
    for _, r in d.iterrows():
        dt = r[use_col]
        dt_str = pd.Timestamp(dt).strftime("%d %b %Y %H:%M") if pd.notna(dt) else "—"
        loc = r.get(loc_col, "")
        sid = r.get(sid_col, "")
        lid = r.get(loc_id_col, "")
        val = fmt(r[value_col])
        loc_link = f'<a href="https://ebird.org/lifelist/{lid}" target="_blank">{loc}</a>' if lid else loc
        dt_link = f'<a href="https://ebird.org/checklist/{sid}" target="_blank">{dt_str}</a>' if sid else dt_str
        rows.append((loc_link, dt_link, val))
    return rows


def _rankings_by_location(df_obs, cl_sub, mode, fmt, limit):
    """Top N locations by total species or individuals. mode: 'species' or 'individuals'. Ties by first visit date."""
    if df_obs.empty or cl_sub.empty:
        return []
    if mode == "species":
        agg = df_obs.groupby("Location ID", group_keys=False).apply(
            lambda g: _countable_species_vectorized(g).dropna().nunique(),
            include_groups=False,
        ).reset_index(name="_val")
    else:
        agg = df_obs.groupby("Location ID", group_keys=False).apply(
            lambda g: g["Count"].apply(_safe_count).sum(),
            include_groups=False,
        ).reset_index(name="_val")
    dt_col = "datetime" if "datetime" in cl_sub.columns else "Date"
    loc_info = cl_sub.groupby("Location ID").agg(
        Location=("Location", "first"),
        Checklists=("Submission ID", "nunique"),
    ).reset_index()
    first_dates = cl_sub.groupby("Location ID")[dt_col].min().reset_index().rename(columns={dt_col: "_first"})
    merged = agg.merge(loc_info, on="Location ID", how="inner").merge(first_dates, on="Location ID", how="left")
    merged = merged.sort_values(by=["_val", "_first", "Location"], ascending=[False, True, True]).head(limit)
    rows = []
    for _, r in merged.iterrows():
        lid = r["Location ID"]
        loc_link = f'<a href="https://ebird.org/lifelist/{lid}" target="_blank">{r["Location"]}</a>' if lid else r["Location"]
        rows.append((loc_link, f"{int(r['Checklists']):,}", fmt(r["_val"])))
    return rows


def _rankings_by_individuals(df_obs, limit):
    """Top N species by total individuals. Subspecies rolled into main species (like map)."""
    if df_obs.empty:
        return []
    df_s = df_obs.copy()
    df_s["_base"] = _countable_species_vectorized(df_s)
    df_s = df_s.dropna(subset=["_base"])
    df_s["_count"] = df_s["Count"].apply(_safe_count)
    by_base = df_s.groupby("_base").agg(
        total=("_count", "sum"),
        common_name=("Common Name", lambda s: s.value_counts().index[0] if len(s) > 0 else ""),
    ).reset_index()
    by_base = by_base.sort_values(by=["total", "_base"], ascending=[False, True]).head(limit)
    rows = []
    for _, r in by_base.iterrows():
        name = r["common_name"] if pd.notna(r["common_name"]) else r["_base"]
        rows.append((str(name), "—", f"{int(r['total']):,}"))
    return rows


def _rankings_by_checklists(df_obs, limit):
    """Top N species by number of checklists. Subspecies rolled into main species (like map)."""
    if df_obs.empty:
        return []
    df_s = df_obs.copy()
    df_s["_base"] = _countable_species_vectorized(df_s)
    df_s = df_s.dropna(subset=["_base"])
    by_base = df_s.groupby("_base").agg(
        n_checklists=("Submission ID", "nunique"),
        common_name=("Common Name", lambda s: s.value_counts().index[0] if len(s) > 0 else ""),
    ).reset_index()
    by_base = by_base.sort_values(by=["n_checklists", "_base"], ascending=[False, True]).head(limit)
    rows = []
    for _, r in by_base.iterrows():
        name = r["common_name"] if pd.notna(r["common_name"]) else r["_base"]
        rows.append((str(name), "—", f"{int(r['n_checklists']):,}"))
    return rows


def _rankings_seen_once(df_obs, limit=None):
    """Species in exactly 1 checklist. Returns (species, location_link, date_time_link, count). No limit by default."""
    if df_obs.empty:
        return []
    df_s = df_obs.copy()
    df_s["_base"] = _countable_species_vectorized(df_s)
    df_s = df_s.dropna(subset=["_base"])
    df_s["_count"] = df_s["Count"].apply(_safe_count)
    dt_col = "datetime" if "datetime" in df_s.columns else "Date"
    by_base = df_s.groupby("_base").agg(
        n_checklists=("Submission ID", "nunique"),
        checklist_count=("_count", "sum"),
        common_name=("Common Name", lambda s: s.value_counts().index[0] if len(s) > 0 else ""),
        Location=("Location", "first"),
        Location_ID=("Location ID", "first"),
        Submission_ID=("Submission ID", "first"),
        _dt=(dt_col, "first"),
    ).reset_index()
    seen_once = by_base[by_base["n_checklists"] == 1].sort_values("common_name")
    if limit is not None:
        seen_once = seen_once.head(limit)
    rows = []
    for _, r in seen_once.iterrows():
        name = r["common_name"] if pd.notna(r["common_name"]) else r["_base"]
        lid = r.get("Location_ID")
        loc = r.get("Location", "")
        sid = r.get("Submission_ID")
        dt = r.get("_dt")
        dt_str = pd.Timestamp(dt).strftime("%d %b %Y %H:%M") if pd.notna(dt) else "—"
        loc_link = f'<a href="https://ebird.org/lifelist/{lid}" target="_blank">{loc}</a>' if lid else loc
        dt_link = f'<a href="https://ebird.org/checklist/{sid}" target="_blank">{dt_str}</a>' if sid else dt_str
        rows.append((str(name), loc_link, dt_link, f"{int(r['checklist_count']):,}"))
    return rows


def _rankings_by_visits(cl_sub, limit):
    """Top N most visited locations; ties by oldest first. Location→lifelist; first/last→checklists."""
    if cl_sub.empty:
        return []
    dt_col = "datetime" if "datetime" in cl_sub.columns else "Date"
    first_idx = cl_sub.groupby("Location ID")[dt_col].idxmin()
    last_idx = cl_sub.groupby("Location ID")[dt_col].idxmax()
    first_rows = cl_sub.loc[first_idx, ["Location ID", "Location", dt_col, "Submission ID"]].rename(
        columns={dt_col: "First", "Submission ID": "First_SID"}
    )
    last_rows = cl_sub.loc[last_idx, ["Location ID", "Location", dt_col, "Submission ID"]].rename(
        columns={dt_col: "Last", "Submission ID": "Last_SID"}
    )
    vc = cl_sub.groupby("Location ID").agg(Count=("Submission ID", "nunique")).reset_index()
    vc = vc.merge(first_rows, on="Location ID").merge(last_rows[["Location ID", "Last", "Last_SID"]], on="Location ID")
    vc = vc.sort_values(by=["Count", "First"], ascending=[False, True]).head(limit)
    rows = []
    for _, r in vc.iterrows():
        loc = r["Location"]
        lid = r["Location ID"]
        first_str = pd.Timestamp(r["First"]).strftime("%d %b %Y %H:%M") if pd.notna(r["First"]) else "—"
        last_str = pd.Timestamp(r["Last"]).strftime("%d %b %Y %H:%M") if pd.notna(r["Last"]) else "—"
        first_sid = r.get("First_SID")
        last_sid = r.get("Last_SID")
        first_link = f'<a href="https://ebird.org/checklist/{first_sid}" target="_blank">{first_str}</a>' if pd.notna(first_sid) and first_sid else first_str
        last_link = f'<a href="https://ebird.org/checklist/{last_sid}" target="_blank">{last_str}</a>' if pd.notna(last_sid) and last_sid else last_str
        loc_link = f'<a href="https://ebird.org/lifelist/{lid}" target="_blank">{loc}</a>' if lid else loc
        rows.append((loc_link, first_link, last_link, f"{int(r['Count']):,}"))
    return rows


def _compute_rankings(df, cl, limit, dur_col, dist_col):
    """Compute all Top N rankings data. Returns dict of section key → list of row tuples."""
    cl_with_dur = cl.dropna(subset=[dur_col]).copy() if dur_col else pd.DataFrame()
    if dur_col and not cl_with_dur.empty:
        cl_with_dur["_dur"] = pd.to_numeric(cl_with_dur[dur_col], errors="coerce").fillna(0)
    cl_with_dist = cl.dropna(subset=[dist_col]).copy() if dist_col else pd.DataFrame()
    if dist_col and not cl_with_dist.empty:
        cl_with_dist["_dist"] = pd.to_numeric(cl_with_dist[dist_col], errors="coerce").fillna(0)
    species_per_cl = df.groupby("Submission ID", group_keys=False).apply(
        lambda g: _countable_species_vectorized(g).dropna().nunique(),
        include_groups=False,
    ).reset_index(name="_nsp")
    ind_per_cl = df.groupby("Submission ID", group_keys=False).apply(
        lambda g: g["Count"].apply(_safe_count).sum(),
        include_groups=False,
    ).reset_index(name="_nind")
    cl_species = cl.merge(species_per_cl, on="Submission ID", how="inner")
    cl_individuals = cl.merge(ind_per_cl, on="Submission ID", how="inner")

    return {
        "time": _rankings_by_value(cl_with_dur, "_dur", "Date", "Location", "Location ID", "Submission ID", lambda x: f"{int(round(x))} min", limit) if dur_col and not cl_with_dur.empty else [],
        "dist": _rankings_by_value(cl_with_dist, "_dist", "Date", "Location", "Location ID", "Submission ID", lambda x: f"{x:,.2f} km", limit) if dist_col and not cl_with_dist.empty else [],
        "species": _rankings_by_value(cl_species, "_nsp", "Date", "Location", "Location ID", "Submission ID", lambda x: f"{int(x):,}", limit) if not cl_species.empty else [],
        "individuals": _rankings_by_value(cl_individuals, "_nind", "Date", "Location", "Location ID", "Submission ID", lambda x: f"{int(x):,}", limit) if not cl_individuals.empty else [],
        "species_loc": _rankings_by_location(df, cl, "species", lambda x: f"{int(x):,}", limit),
        "individuals_loc": _rankings_by_location(df, cl, "individuals", lambda x: f"{int(x):,}", limit),
        "visited": _rankings_by_visits(cl, limit),
        "species_individuals": _rankings_by_individuals(df, limit),
        "species_checklists": _rankings_by_checklists(df, limit),
        "seen_once": _rankings_seen_once(df, limit=None),  # No limit; show all species seen only once
    }


# %%
# --------------------------------------------
# ✅ Checklist Statistics (computed from data)
# --------------------------------------------
def _compute_checklist_stats(df):
    """Compute checklist statistics from df; returns dict with stats_html and rankings_sections."""
    import html

    if df.empty:
        return "<p>No data.</p>"

    # Checklist-level data (one row per checklist)
    cl = df.drop_duplicates(subset=["Submission ID"]).copy()
    cl["Date"] = pd.to_datetime(cl["Date"], errors="coerce")
    dur_col = "Duration (Min)" if "Duration (Min)" in df.columns else None
    dist_col = "Distance Traveled (km)" if "Distance Traveled (km)" in df.columns else None

    # Overview
    n_checklists = cl["Submission ID"].nunique()
    n_species = int(_countable_species_vectorized(df).dropna().nunique())
    n_individuals = int(df["Count"].apply(_safe_count).sum())

    # Completed checklists (All Obs Reported)
    n_completed = "—"
    if "All Obs Reported" in df.columns:
        completed = cl.dropna(subset=["All Obs Reported"])
        if not completed.empty:
            reported = completed["All Obs Reported"].astype(str).str.upper().isin(["1", "TRUE", "YES", "Y"])
            n_completed = f"{(reported).sum():,}"

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
            excl = timed["Protocol"].str.strip().str.lower().str.contains("incidental|historical", na=False, regex=True)
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

    _table_css = """
    .stats-info-icon { position:relative; display:inline-block; margin-left:4px; }
    .stats-info-glyph { cursor:help; opacity:0.7; }
    .stats-info-tooltip { position:absolute; top:100%; left:0; margin-top:6px; padding:10px 14px; background:#333; color:#fff; font-size:12px; font-weight:normal; line-height:1.5; white-space:normal; max-width:min(380px,90vw); min-width:200px; border-radius:6px; box-shadow:0 2px 8px rgba(0,0,0,0.2); opacity:0; visibility:hidden; transition:opacity 0.05s; pointer-events:none; z-index:9999; }
    .stats-info-icon:hover .stats-info-tooltip { opacity:1; visibility:visible; }
    .stats-tbl { border-collapse:collapse; width:100%; max-width:100%; font-size:13px; }
    .stats-tbl th { font-weight:bold; text-align:left; padding:8px 12px; border-bottom:1px solid #ddd; background:#fff; }
    .stats-tbl th:last-child { text-align:right; }
    .stats-tbl td { padding:8px 12px; border-bottom:1px solid #e8e8e8; }
    .stats-tbl td:last-child { text-align:right; font-weight:bold; }
    .stats-tbl tbody tr:nth-child(odd) { background:#f8f8f8; }
    .stats-tbl tbody tr:nth-child(even) { background:#fff; }
    .stats-tbl-3 th:nth-child(2), .stats-tbl-3 td:nth-child(2) { text-align:center; }
    .rankings-tbl td:first-child { font-weight:normal; }
    .stats-tbl a, .rankings-tbl a { text-decoration:underline dotted; text-decoration-color:rgba(0,0,0,0.22); text-underline-offset:2px; }
    .stats-tbl a:hover, .rankings-tbl a:hover { text-decoration-color:rgba(0,0,0,0.45); }
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
  <h4 style="margin-top:{mt};margin-bottom:8px;padding-bottom:4px;border-bottom:1px solid #ddd;">{title}{info}</h4>
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
  ], first=True, info_title=time_hint)}

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

    def _rankings_table(title, headers, rows, include_heading=True, scroll_hint="shading", visible_rows=16):
        """Build a rankings table with scrollable body. Uses shared scroll-wrapper for chevrons/shading."""
        if not rows:
            no_data = "<p style='margin:4px 0;color:#666;'>No data.</p>"
            return f"<h4 style='margin:0 0 8px;'>{title}</h4>{no_data}" if include_heading else no_data
        body = "".join(
            f"<tr><td>{r[0]}</td><td>{r[1]}</td><td style='text-align:right;font-weight:bold;'>{r[2]}</td></tr>"
            for r in rows
        )
        tbl = f"<table class='stats-tbl rankings-tbl'><thead><tr><th>{headers[0]}</th><th>{headers[1]}</th><th>{headers[2]}</th></tr></thead><tbody>{body}</tbody></table>"
        scroll_wrapper = _rankings_scroll_wrapper(tbl, scroll_hint, visible_rows)
        content = f"<h4 style='margin:0 0 8px;'>{title}</h4>{scroll_wrapper}" if include_heading else scroll_wrapper
        return content

    def _rankings_visited_table(rows, include_heading=True, scroll_hint="shading", visible_rows=16):
        """4-column table: Location | First visit | Last visit | Visits."""
        if not rows:
            no_data = "<p style='margin:4px 0;color:#666;'>No data.</p>"
            return f"<h4 style='margin:0 0 8px;'>Most visited locations</h4>{no_data}" if include_heading else no_data
        body = "".join(
            f"<tr><td>{r[0]}</td><td>{r[1]}</td><td>{r[2]}</td><td style='text-align:right;font-weight:bold;'>{r[3]}</td></tr>" for r in rows
        )
        tbl = f"<table class='stats-tbl rankings-tbl'><thead><tr><th>Location</th><th>First visit</th><th>Last visit</th><th>Visits</th></tr></thead><tbody>{body}</tbody></table>"
        scroll_wrapper = _rankings_scroll_wrapper(tbl, scroll_hint, visible_rows)
        return f"<h4 style='margin:0 0 8px;'>Most visited locations</h4>{scroll_wrapper}" if include_heading else scroll_wrapper

    def _rankings_seen_once_table(rows, include_heading=True, scroll_hint="shading", visible_rows=16, note_text=None):
        """4-column table: Species | Location | Visited date/time | Count. Optional note above table."""
        import html as _html
        if not rows:
            no_data = "<p style='margin:4px 0;color:#666;'>No data.</p>"
            return f"<h4 style='margin:0 0 8px;'>Species: Seen only once</h4>{no_data}" if include_heading else no_data
        body = "".join(
            f"<tr><td>{r[0]}</td><td>{r[1]}</td><td>{r[2]}</td><td style='text-align:right;font-weight:bold;'>{r[3]}</td></tr>" for r in rows
        )
        tbl = f"<table class='stats-tbl rankings-tbl'><thead><tr><th>Species</th><th>Location</th><th>Visited date/time</th><th>Count</th></tr></thead><tbody>{body}</tbody></table>"
        scroll_wrapper = _rankings_scroll_wrapper(tbl, scroll_hint, visible_rows)
        note_html = ""
        if note_text:
            esc = _html.escape(note_text, quote=True)
            note_html = f"""<p class="rankings-note" style="margin:0 0 6px;font-size:11px;color:#888;line-height:1.4;">
  <span class="stats-info-glyph" style="margin-right:4px;">&#9432;</span>{esc}
</p>"""
        return f"{note_html}{scroll_wrapper}"

    # Rankings sections for accordion (content only, no heading - accordion provides title)
    scroll_hint = POPUP_SCROLL_HINT
    visible_rows = RANKINGS_TABLE_VISIBLE_ROWS
    rankings_sections = [
        ("Checklist: Longest by time", _rankings_table("Checklist: Longest by time", ["Location", "Visited date/time", "Time"], rankings["time"], include_heading=False, scroll_hint=scroll_hint, visible_rows=visible_rows)),
        ("Checklist: Longest by distance", _rankings_table("Checklist: Longest by distance", ["Location", "Visited date/time", "Distance"], rankings["dist"], include_heading=False, scroll_hint=scroll_hint, visible_rows=visible_rows)),
        ("Checklist: Most species", _rankings_table("Checklist: Most species", ["Location", "Visited date/time", "Species"], rankings["species"], include_heading=False, scroll_hint=scroll_hint, visible_rows=visible_rows)),
        ("Checklist: Most individuals", _rankings_table("Checklist: Most individuals", ["Location", "Visited date/time", "Count"], rankings["individuals"], include_heading=False, scroll_hint=scroll_hint, visible_rows=visible_rows)),
        ("Location: Most species", _rankings_table("Location: Most species", ["Location", "Checklists", "Species"], rankings["species_loc"], include_heading=False, scroll_hint=scroll_hint, visible_rows=visible_rows)),
        ("Location: Most individuals", _rankings_table("Location: Most individuals", ["Location", "Checklists", "Count"], rankings["individuals_loc"], include_heading=False, scroll_hint=scroll_hint, visible_rows=visible_rows)),
        ("Location: Most visited", _rankings_visited_table(rankings["visited"], include_heading=False, scroll_hint=scroll_hint, visible_rows=visible_rows)),
        ("Species: Most individuals", _rankings_table("Species: Most individuals", ["Species", "", "Individuals"], rankings["species_individuals"], include_heading=False, scroll_hint=scroll_hint, visible_rows=visible_rows)),
        ("Species: Most checklists", _rankings_table("Species: Most checklists", ["Species", "", "Checklists"], rankings["species_checklists"], include_heading=False, scroll_hint=scroll_hint, visible_rows=visible_rows)),
        ("Species: Seen only once", _rankings_seen_once_table(rankings["seen_once"], include_heading=False, scroll_hint=scroll_hint, visible_rows=visible_rows, note_text=f"All species, not limited to {TOP_N_TABLE_LIMIT}.")),
    ]

    stats_html = f"""
<style>{_table_css}</style>
<div class="stats-layout" style="font-family:sans-serif;font-size:13px;line-height:1.6;width:100%;max-width:1400px;display:flex;flex-wrap:wrap;gap:clamp(24px,4vw,48px);justify-content:flex-start;padding:0 clamp(16px,3vw,32px);box-sizing:border-box;">
  <div class="stats-col" style="flex:1 1 320px;min-width:280px;max-width:480px;padding:16px;box-sizing:border-box;">{left_col}</div>
  <div class="stats-col" style="flex:1 1 320px;min-width:280px;max-width:480px;padding:16px;box-sizing:border-box;">{right_col}</div>
</div>
"""
    return {"stats_html": stats_html, "rankings_sections": rankings_sections}


# Stats use df_full for all-time totals (unfiltered by date). Map uses df, which may be date-filtered.
checklist_data = _compute_checklist_stats(df_full)
checklist_stats_panel = widgets.HTML(value=checklist_data["stats_html"])

# Rankings tab: accordion so lists are collapsible, each takes full width when expanded
_rankings_css = """
.stats-info-icon { position:relative; display:inline-block; margin-left:4px; }
.stats-info-glyph { cursor:help; opacity:0.7; }
.stats-info-tooltip { position:absolute; top:100%; left:0; margin-top:6px; padding:10px 14px; background:#333; color:#fff; font-size:12px; font-weight:normal; line-height:1.5; white-space:normal; max-width:min(380px,90vw); min-width:200px; border-radius:6px; box-shadow:0 2px 8px rgba(0,0,0,0.2); opacity:0; visibility:hidden; transition:opacity 0.05s; pointer-events:none; z-index:9999; }
.stats-info-icon:hover .stats-info-tooltip { opacity:1; visibility:visible; }
.stats-tbl { border-collapse:collapse; width:100%; max-width:none; font-size:13px; }
.stats-tbl th { font-weight:bold; text-align:left; padding:8px 12px; border-bottom:1px solid #ddd; }
.stats-tbl th:last-child { text-align:right; }
.stats-tbl td { padding:8px 12px; border-bottom:1px solid #e8e8e8; }
.stats-tbl td:nth-child(2), .stats-tbl td:nth-child(3) { white-space:nowrap; }
.stats-tbl td:last-child { text-align:right; font-weight:bold; }
.stats-tbl tbody tr:nth-child(odd) { background:#f8f8f8; }
.stats-tbl tbody tr:nth-child(even) { background:#fff; }
.stats-tbl a { text-decoration:underline dotted; text-decoration-color:rgba(0,0,0,0.22); }
"""
rankings_accordion = Accordion(
    children=[widgets.HTML(value=f"<style>{_rankings_css}</style>{html}") for _, html in checklist_data["rankings_sections"]],
    selected_index=None,  # All collapsed by default; expand to view
)
for i, (title, _) in enumerate(checklist_data["rankings_sections"]):
    rankings_accordion.set_title(i, title)


# Map maintenance tab: duplicate, close-location, and orphaned data
# Link format for maintenance: edit page (merge/delete), not lifelist
_MAINT_LOC_URL = "https://ebird.org/mylocations/edit/"


def _compute_map_maintenance_html(loc_df, threshold_m, orphaned_df):
    """Build HTML for Map maintenance tab: orphaned, exact duplicates, close-location pairs."""
    exact_rows, near_pairs = _get_map_maintenance_data(loc_df, threshold_m)
    css = """
    .maint-tbl { border-collapse:collapse; width:100%; max-width:none; font-size:13px; margin-bottom:16px; }
    .maint-tbl th { font-weight:bold; text-align:left; padding:8px 12px; border-bottom:1px solid #ddd; }
    .maint-tbl td { padding:8px 12px; border-bottom:1px solid #e8e8e8; }
    .maint-tbl td:last-child { text-align:right; font-weight:bold; }
    .maint-tbl td:nth-child(2) { white-space:nowrap; }
    .maint-tbl.maint-single-col td { text-align:left; font-weight:normal; }
    .maint-tbl tbody tr:nth-child(odd) { background:#f8f8f8; }
    .maint-tbl tbody tr:nth-child(even) { background:#fff; }
    .maint-tbl a { text-decoration:underline dotted; text-decoration-color:rgba(0,0,0,0.22); }
    .maint-pair-tbl { border-collapse:collapse; width:100%; max-width:600px; font-size:13px; margin-bottom:12px; }
    .maint-pair-tbl th { font-weight:bold; text-align:left; padding:6px 10px; border-bottom:1px solid #e8e8e8; }
    .maint-pair-tbl td { padding:6px 10px; border-bottom:1px solid #e8e8e8; }
    .maint-pair-tbl tbody tr.pair-first { background:#f8f8f8; }
    .maint-pair-tbl tbody tr.pair-second { background:#fff; }
    .maint-pair-tbl tbody tr.maint-spacer { background:transparent; }
    .maint-pair-tbl td:nth-child(2) { white-space:nowrap; }
    .maint-pair-tbl a { text-decoration:underline dotted; text-decoration-color:rgba(0,0,0,0.22); }
    """
    # Table 0: Locations without checklists
    orphaned_body = ""
    if not orphaned_df.empty:
        for _, r in orphaned_df.iterrows():
            link = f'<a href="{_MAINT_LOC_URL}{r["Location ID"]}" target="_blank">{r["Location"]}</a>' if pd.notna(r.get("Location ID")) else str(r.get("Location", ""))
            orphaned_body += f"<tr><td>{link}</td></tr>"
        orphaned_table = f"""
  <h4 style="margin-top:20px;margin-bottom:8px;padding-bottom:4px;border-bottom:1px solid #ddd;">Locations without checklists</h4>
  <p style="margin:4px 0 8px;color:#666;font-size:12px;">These locations have no attached checklists and are excluded from the map and other tabs.</p>
  <table class="maint-tbl maint-single-col">
    <thead><tr><th>Location</th></tr></thead>
    <tbody>{orphaned_body}</tbody>
  </table>"""
    else:
        orphaned_table = """
  <h4 style="margin-top:20px;margin-bottom:8px;padding-bottom:4px;border-bottom:1px solid #ddd;">Locations without checklists</h4>
  <p style="margin:4px 0;color:#666;">None.</p>"""

    # Table 1: Exact duplicates (Location | Lat/Long | Number of duplicates)
    dup_body = ""
    if exact_rows:
        for loc_name, loc_id, count, lat, lon in exact_rows:
            link = f'<a href="{_MAINT_LOC_URL}{loc_id}" target="_blank">{loc_name}</a>' if loc_id else loc_name
            coords = f"({lat:.6f}, {lon:.6f})" if pd.notna(lat) and pd.notna(lon) else "—"
            dup_body += f"<tr><td>{link}</td><td>{coords}</td><td>{count}</td></tr>"
        dup_table = f"""
  <h4 style="margin-top:0;margin-bottom:8px;padding-bottom:4px;border-bottom:1px solid #ddd;">Exact duplicates</h4>
  <p style="margin:4px 0 8px;color:#666;font-size:12px;">Different Location IDs at the same coordinates. Same name listed once; different names listed separately.</p>
  <table class="maint-tbl">
    <thead><tr><th>Location</th><th>Latitude/Longitude</th><th>Number of duplicates</th></tr></thead>
    <tbody>{dup_body}</tbody>
  </table>"""
    else:
        dup_table = """
  <h4 style="margin-top:20px;margin-bottom:8px;padding-bottom:4px;border-bottom:1px solid #ddd;">Exact duplicates</h4>
  <p style="margin:4px 0;color:#666;">None detected.</p>"""

    # Table 2: Close locations (one heading, pairs separated by spacer rows)
    near_section = ""
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
        near_section = f"""
  <h4 style="margin-top:20px;margin-bottom:8px;padding-bottom:4px;border-bottom:1px solid #ddd;">Close locations</h4>
  <p style="margin:4px 0 12px;color:#666;font-size:12px;">Locations within {threshold_m} m of each other (excluding exact duplicates).</p>
  <table class="maint-pair-tbl">
    <thead><tr><th>Location</th><th>Latitude/Longitude</th></tr></thead>
    <tbody>{all_rows}</tbody>
  </table>"""
    else:
        near_section = f"""
  <h4 style="margin-top:20px;margin-bottom:8px;padding-bottom:4px;border-bottom:1px solid #ddd;">Close locations</h4>
  <p style="margin:4px 0;color:#666;">None detected within the current threshold ({threshold_m} m).</p>"""

    explanation = """
  <div style="margin-top:24px;max-width:600px;display:flex;gap:8px;box-sizing:border-box;">
    <span style="flex-shrink:0;display:inline-flex;align-items:center;justify-content:center;width:16px;height:16px;border-radius:50%;background:#5a7ab8;color:white;font-size:10px;font-weight:600;font-family:sans-serif;line-height:1;">?</span>
    <div style="flex:1;min-width:0;color:#555;font-size:12px;font-weight:normal;line-height:1.6;text-align:left;overflow-wrap:break-word;word-break:break-word;">
      This data is provided to help you keep your eBird locations in good order. It may not be that useful if you use a lot of hotspots and don't create many new locations. However, for those who create locations and build a large catalogue of them, this data can help you clean up duplicates or locations that are very close to each other.<br><br>
      On the eBird website there are options to merge locations. Duplicates can be tricky to merge directly, so often the easiest approach is to move a checklist to the other duplicate location, then delete the now-empty one. See eBird for more details.
    </div>
  </div>"""

    return f"""
<style>{css}</style>
<div style="font-family:sans-serif;font-size:13px;line-height:1.6;max-width:800px;">
{dup_table}
{near_section}
{orphaned_table}
{explanation}
</div>"""


map_maintenance_html = _compute_map_maintenance_html(full_location_data, CLOSE_LOCATION_METERS, locations_without_checklists)
map_maintenance_panel = widgets.HTML(value=map_maintenance_html)

# Tabs: Map, Checklist Statistics, Rankings (Top N), Map maintenance
main_tabs = widgets.Tab(children=[map_output, checklist_stats_panel, rankings_accordion, map_maintenance_panel])
main_tabs.set_title(0, "🗺️ Map")
main_tabs.set_title(1, "📊 Checklist Statistics")
main_tabs.set_title(2, f"🏆 Top {TOP_N_TABLE_LIMIT}")
main_tabs.set_title(3, "🔧 Map maintenance")
main_tabs.selected_index = 0  # Ensure map tab is visible on load
main_tabs.layout = widgets.Layout(min_width="420px", min_height="650px")  # Fit tab name; reserve space for map

# %% editable=true slideshow={"slide_type": ""}
# --------------------------------------------
# ✅ Show dashboard (controls + map/tabs together)
# --------------------------------------------
dashboard = VBox([search_box, dropdown, hide_non_matching_checkbox, output, main_tabs])
dashboard.layout = widgets.Layout(min_height="750px")  # Ensure map + controls visible without expanding
display(dashboard)
draw_map_with_species_overlay("", "")


# %%
