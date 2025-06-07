# ---
# jupyter:
#   jupytext:
#     formats: ipynb,py:percent
#     text_representation:
#       extension: .py
#       format_name: percent
#       format_version: '1.3'
#       jupytext_version: 1.17.2
#   kernelspec:
#     display_name: Python 3 (ipykernel)
#     language: python
#     name: python3
# ---

# %% [markdown]
# ## 🗺️ Explore Your eBird Data on a Map
#
# This notebook lets you explore your personal eBird records in an interactive, visual way.
#
# Once you’ve downloaded your full eBird data export, this tool maps every location you’ve submitted a checklist from — whether it’s a hotspot or a personal location. You can search for a species, filter by date, highlight lifers, and explore your birding history on a map.
#
# ### ✅ What This Notebook Does
#
# - Loads your eBird data export (CSV format)
# - Draws a map of all checklist locations (green by default)
# - Highlights locations where a selected species was seen (red)
# - Optionally marks your lifer location for that species (blue)
# - Lets you hide non-matching locations
# - Offers type-ahead search that mimics eBird’s own species search behaviour
# - Supports date-range filtering
# - Adds detailed popups showing:
#   - All visits to each location
#   - Sightings of the selected species (if relevant)
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
# Once up and running, the menu items **Run All Cells** and **Restart Kernel and Clear Outputs of All Cells** are your friends.
#
# ---
#
# ### ⚙️ One Small Setup Note
#
# By default, the notebook expects your eBird data file to be named `MyEBirdData.csv`. This is controlled by a variable in the first code cell — you can change it if needed.
#
# Folder paths and output settings are pulled from a small config file used elsewhere in the codebase. You might need to **create or update that config file in the `scripts` folder**.  You could even just hack the code in the third code cell and hard code some paths.  Depends on what you are comfortable with.
#
# Other than that, just run the notebook from top to bottom — it should work straight away.
#

# %% [markdown]
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
# - `MARK_LIFER`:  
#   - `True` — highlights your first sighting of each species with a blue marker  
#   - `False` — all sightings use red markers
# - `FILTER_BY_DATE`:  
#   - `True` — only show locations and sightings within the specified date range  
#   - `False` — include all data
# - `FILTER_START_DATE`, `FILTER_END_DATE`: format as `YYYY-MM-DD`  
#   These only apply if `FILTER_BY_DATE` is `True`.
#
# > NOTE: Paths (not file names) are stored in the config files in the scritps folder of the code repo.  You can easily move paths here if you wish.

# %%
# --------------------------------------------
# ✅ User Variables — Change These as Needed
# --------------------------------------------

# Name of your eBird export file (in the DATA_FOLDER below)
EBIRD_DATA_FILE_NAME = "MyEBirdData.csv"

# Where your .csv file is located, and where the output map will be saved
OUTPUT_HTML_FILE_NAME = "species_map.html"
EXPORT_HTML = True  # Save HTML file each time map is updated

# Map style options: "default", "satellite", "google", "carto"
MAP_STYLE = "default"

# Toggle lifer marker (first sighting in dataset gets blue marker)
MARK_LIFER = True

# Optional date range filtering (set to False to disable)
FILTER_BY_DATE = False
FILTER_START_DATE = "2025-01-01"
FILTER_END_DATE = "2025-12-31"

# %% [markdown]
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
# ✅ Imports and Display CSS
# --------------------------------------------
import os
import sys
import pandas as pd
import folium
import tempfile  
import threading
import ipywidgets as widgets

from datetime import datetime
from ipywidgets import Checkbox, VBox
from whoosh.index import create_in
from whoosh.fields import Schema, TEXT
from whoosh.analysis import StemmingAnalyzer
from whoosh.qparser import QueryParser, OrGroup

from IPython.display import display, HTML

display(HTML("""
<style>
.output_map iframe {
    width: 100% !important;
    height: 100%;
}
</style>
"""))

# %% [markdown]
# ## ⚙️ Load Config and eBird Data
#
# This cell handles the initial setup and data loading:
#
# - Adds the `scripts` folder to the Python path
# - Loads folder paths from either `config_secret.py` or `config_template.py`
# - Builds the full path to your eBird data file and output map file
# - Loads the CSV and parses the "Date" column into proper datetime objects
# - Optionally filters the data by a specified date range
# - Extracts a list of unique locations and species for later use
# - Builds a dictionary that maps common names to scientific names
#
# > 📝 The date filter (enabled by `FILTER_BY_DATE = True`) ensures all map features — including species lists, lifer logic, and visibility — only use data within the selected range. However, popups still show full history from that location.
#

# %%
# --------------------------------------------
# ✅ Configuration & Data Loading
# --------------------------------------------

scripts_path = os.path.abspath("../scripts")
sys.path.append(scripts_path)

# Load secret or fallback config
try:
    from config_secret import DATA_FOLDER
except ImportError:
    from config_template import DATA_FOLDER

# Build full file path
file_path = os.path.join(DATA_FOLDER, EBIRD_DATA_FILE_NAME)
map_output_path = os.path.join(DATA_FOLDER, OUTPUT_HTML_FILE_NAME)
os.makedirs(DATA_FOLDER, exist_ok=True)

# Load data
df = pd.read_csv(file_path)
df["Date"] = pd.to_datetime(df["Date"], errors="coerce")

# Apply date filter if enabled
if FILTER_BY_DATE:
    try:
        start = datetime.strptime(FILTER_START_DATE, "%Y-%m-%d")
        end = datetime.strptime(FILTER_END_DATE, "%Y-%m-%d")
        assert start <= end, "Start date must be before end date"
        df = df[(df["Date"] >= start) & (df["Date"] <= end)]
        #print(f"📅 Filtered data rows: {len(df)} from {start.date()} to {end.date()}")
    except Exception as e:
        raise ValueError(f"Invalid date filter settings: {e}")

# Extract location and species info
location_data = df[['Location ID', 'Location', 'Latitude', 'Longitude']].drop_duplicates()
species_list = sorted(df["Common Name"].dropna().unique().tolist())
selected_species_name = ""

#print(f"📋 Species list (count: {len(species_list)}): {species_list[:5]}...")

# Build common → scientific name map
name_map = (
    df[['Common Name', 'Scientific Name']]
    .dropna()
    .drop_duplicates()
    .set_index('Common Name')['Scientific Name']
    .to_dict()
)


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
# ✅ Initialise global map objects
# --------------------------------------------
species_map = None
map_output = widgets.Output()
output = widgets.Output()



# --------------------------------------------
# ✅ Autocomplete UI Widgets
# --------------------------------------------
search_box = widgets.Text(placeholder="Type species name...", description="Search:")
dropdown = widgets.Select(options=[], value=None, description="Matches:", rows=10)
hide_non_matching_checkbox = Checkbox(
    value=False,
    description='Show only selected species',
    indent=False
)


# %%
# --------------------------------------------
# ✅ Species Filter (for subspecies / slashes)
# --------------------------------------------

def filter_species(df, base_species):
    base_species = base_species.lower().strip()
    if "/" in base_species:
        return df[df["Scientific Name"].str.lower() == base_species]
    filtered_df = df[df["Scientific Name"].fillna("").str.lower().str.startswith(base_species)]
    return filtered_df[~filtered_df["Scientific Name"].str.contains("/", regex=False)]


# %%
# --------------------------------------------
# ✅ Build True Lifer Table (from full dataset)
# --------------------------------------------

# Reload full dataset to avoid filtering effects
full_df = pd.read_csv(file_path)
full_df["Date"] = pd.to_datetime(full_df["Date"], errors="coerce")
full_df["Time"] = full_df["Time"].fillna("00:00")

# Combine Date and Time safely
# Combine Date and Time safely
df["datetime"] = pd.to_datetime(
    df["Date"].astype(str) + " " + df["Time"],
    errors="coerce"
)
full_df["datetime"] = pd.to_datetime(
    full_df["Date"].astype(str) + " " + full_df["Time"],
    errors="coerce"
)


# Build lifer location dictionary: scientific name → first seen location
true_lifer_locations = (
    full_df.sort_values("datetime")
    .dropna(subset=["Scientific Name", "Location ID"])
    .groupby("Scientific Name")
    .first()["Location ID"]
    .to_dict()
)


# %%
# --------------------------------------------
# ✅ UI Event Handlers
# --------------------------------------------

# ✅ Called when a dropdown species is selected
def on_species_selected(change):
    global selected_species_name
    output.clear_output()

    selected = change.get("new")
    search_text = search_box.value.strip()

    #print(f"🧩 Dropdown changed: '{selected}'")
    #print(f"🔡 Search box text: '{search_text}'")

    # Show full map if search fully cleared
    if selected is None and search_text == "":
        selected_species_name = ""
        hide_non_matching_checkbox.value = False
        with output:
            print("🧹 Search truly cleared — showing all locations")
        draw_map_with_species_overlay("")
        return

    # Don't trigger if no species selected
    if selected is None:
        print("🚫 No selection — skipping map draw")
        return

    # Lookup scientific name
    selected_species_name = name_map.get(selected, "").strip()
    print(f"✅ Selected scientific name: {selected_species_name}")

    with output:
        print(f"🔎 Selected species: {selected} → Scientific: {selected_species_name}")
    draw_map_with_species_overlay(selected_species_name)


# ✅ Called when the "hide non-matching" checkbox is toggled
def on_toggle_change(change):
    global selected_species_name
    with output:
        print(f"🧪 Toggle changed: {change['new']} — Current species: {selected_species_name}")
    if selected_species_name:
        draw_map_with_species_overlay(selected_species_name)


# ✅ Called when search box is cleared (after short debounce)
def on_search_box_cleared(change):
    global debounce_timer

    old_val = change.get("old", "").strip()
    new_val = change.get("new", "").strip()

    if old_val and not new_val:
        if debounce_timer:
            debounce_timer.cancel()

        def handle_clear():
            if search_box.value.strip() == "":
                dropdown.options = []
                dropdown.value = None
                hide_non_matching_checkbox.value = False
                with output:
                    output.clear_output()
                    print("🧹 Search cleared — showing all locations")
                draw_map_with_species_overlay("")

        debounce_timer = threading.Timer(debounce_delay, handle_clear)
        debounce_timer.start()



# %%
# --------------------------------------------
# ✅ Autocomplete Setup + Observers
# --------------------------------------------

# ✅ Set up fuzzy search engine (Whoosh)
schema = Schema(common_name=TEXT(stored=True, analyzer=StemmingAnalyzer()))
index_dir = tempfile.mkdtemp()
ix = create_in(index_dir, schema)
writer = ix.writer()
for name in species_list:
    writer.add_document(common_name=name)
writer.commit()

# ✅ Handle search input and suggest species
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

# ✅ Register observers
search_box.observe(update_suggestions, names="value")
search_box.observe(on_search_box_cleared, names="value")
dropdown.observe(on_species_selected, names="value")
hide_non_matching_checkbox.observe(on_toggle_change, names="value")


# %%
# --------------------------------------------
# ✅ Map Creation and Redraws
# --------------------------------------------

# ✅ Create base map with selected tile style
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

# ✅ Draw map with species overlay
def draw_map_with_species_overlay(selected_species):
    global species_map
    #print(f"🔍 Drawing map for species: '{selected_species}'")
    #print(f"📌 Total rows in df: {len(df)}")
    #print(f"📌 Unique species in df: {df['Common Name'].nunique()}")
    #print(f"📌 Unique locations: {df['Location ID'].nunique()}")

    map_center = [location_data['Latitude'].mean(), location_data['Longitude'].mean()]
    species_map = create_map(map_center)

    if not selected_species:
        # Case 1: All locations (green)
        for _, row in location_data.iterrows():
            base_records = df[df['Location ID'] == row['Location ID']]
            visit_info = "<br>".join(
                f"{d.strftime('%Y-%m-%d')} {str(t) if pd.notna(t) else 'unknown'}"
                for d, t in sorted(
                    {(d, str(t) if pd.notna(t) else 'unknown') for d, t in zip(base_records["Date"], base_records["Time"])}
                    if not base_records.empty else []
                )
            )

            popup = folium.Popup(f"<b>{row['Location']}</b><br><b>Visited:</b><br>{visit_info}", max_width=800)
            folium.CircleMarker(
                location=[row['Latitude'], row['Longitude']],
                radius=4,
                color="green",
                fill=True,
                fill_color="lightgreen",
                fill_opacity=0.6,
                popup=popup
            ).add_to(species_map)

    else:
        # Case 2: Filtered by species
        filtered = filter_species(df, selected_species)
        #print(f"🔎 Matching observations for '{selected_species}': {len(filtered)}")
        #print(f"🧭 Locations with this species: {filtered['Location ID'].nunique()}")

        seen_location_ids = set(filtered['Location ID'])

        if filtered.empty:
            with output:
                output.clear_output()
                print(f"⚠️ No sightings of '{selected_species}' in current data — check date range or filters.")
            return

        # ✅ Lifer logic
        lifer_location = None
        if MARK_LIFER and not filtered.empty:
            true_lifer_loc = true_lifer_locations.get(selected_species)
            if true_lifer_loc in filtered['Location ID'].values:
                lifer_location = true_lifer_loc

        # Pass 1: green non-matching markers
        for _, row in location_data.iterrows():
            loc_id = row['Location ID']
            if loc_id in seen_location_ids or hide_non_matching_checkbox.value:
                continue
            base_records = df[df['Location ID'] == loc_id]
            visit_info = "<br>".join(
                f"{d} {str(t) if pd.notna(t) else 'unknown'}"
                for d, t in sorted(
                    {(d, str(t) if pd.notna(t) else 'unknown') for d, t in zip(base_records["Date"], base_records["Time"])}
                )
            )
            popup = folium.Popup(f"<b>{row['Location']}</b><br><b>Visited:</b><br>{visit_info}", max_width=800)
            folium.CircleMarker(
                location=[row['Latitude'], row['Longitude']],
                radius=4,
                color="green",
                fill=True,
                fill_color="lightgreen",
                fill_opacity=0.6,
                popup=popup
            ).add_to(species_map)

        # Pass 2: red/blue species markers
        for _, row in location_data.iterrows():
            loc_id = row['Location ID']
            if loc_id not in seen_location_ids:
                continue

            base_records = df[df['Location ID'] == loc_id]
            visit_info = "<br>".join(
                f"{d} {str(t) if pd.notna(t) else 'unknown'}"
                for d, t in sorted(
                    {(d, str(t) if pd.notna(t) else 'unknown') for d, t in zip(base_records["Date"], base_records["Time"])}
                )
            )
            base_popup = f"<b>{row['Location']}</b><br><b>Visited:</b><br>{visit_info}"
            sub = filtered[filtered['Location ID'] == loc_id]
            obs_details = "".join(
                f"<br>{r['Date'].strftime('%Y-%m-%d') if pd.notna(r['Date']) else 'unknown'} {r['Time']} — {r['Common Name']} ({r['Count']})"
                for _, r in sub.iterrows()
            )
            popup_content = folium.Popup(base_popup + "<br><b>Seen:</b>" + obs_details, max_width=800)

            if MARK_LIFER and loc_id == lifer_location:
                color, fill = "blue", "blue"
            else:
                color, fill = "red", "red"

            folium.CircleMarker(
                location=[row['Latitude'], row['Longitude']],
                radius=4,
                color=color,
                fill=True,
                fill_color=fill,
                fill_opacity=0.6,
                popup=popup_content
            ).add_to(species_map)

    with map_output:
        map_output.clear_output()
        display(HTML("<div class='output_map'>"))
        display(species_map)
        display(HTML("</div>"))
        if EXPORT_HTML:
            species_map.save(map_output_path)
        display(HTML("""
        <script>
        setTimeout(() => {
          const iframe = document.querySelector('.output_map iframe');
          if (iframe) {
            iframe.style.minHeight = '600px';
            iframe.parentElement.style.minHeight = '600px';
          }
        }, 100);
        </script>
        """))



# %%
# --------------------------------------------
# ✅ Display UI and Draw Initial Map
# --------------------------------------------

# ✅ Display the UI
display(VBox([search_box, dropdown, hide_non_matching_checkbox, output]))

# ✅ Draw initial map (no filters applied)
draw_map_with_species_overlay("")

# ✅ Force minimum height for map display
with map_output:
    display(HTML("""
    <script>
    setTimeout(() => {
      const iframe = document.querySelector('.output_map iframe');
      if (iframe) {
        iframe.style.minHeight = '600px';
        iframe.parentElement.style.minHeight = '600px';
      }
    }, 100);
    </script>
    """))


# %%
# --------------------------------------------
# ✅ Show interactive output area (map + messages)
# --------------------------------------------
display(map_output)

