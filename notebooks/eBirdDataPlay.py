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

# %%

# %%
import os
import sys
import pandas as pd
import folium
import tempfile 
import asyncio
import ipywidgets as widgets

from whoosh.fields import Schema, TEXT
from whoosh.analysis import StemmingAnalyzer
from whoosh.index import create_in
from whoosh.qparser import QueryParser, OrGroup
from ipywidgets import Checkbox, VBox

from IPython.display import display, HTML
display(HTML("<style>.output_map iframe {width: 100% !important; height: 100%;}</style>"))


# --------------------------------------------
# ✅ Configuration & Paths
# --------------------------------------------
MAP_STYLE = "default"
MARK_LIFER = True   # Toggle to mark lifer record with a different colour (currently blue) when viewing species
EXPORT_HTML = False  # Set to True to write map HTML after each draw

scripts_path = os.path.abspath("../scripts")
sys.path.append(scripts_path)

try:
    from config_secret import DATA_FOLDER
except ImportError:
    from config_template import DATA_FOLDER

csv_output_path = os.path.join(DATA_FOLDER, "ebird_locations.csv")
map_output_path = os.path.join(DATA_FOLDER, "ebird_map.html")
os.makedirs(DATA_FOLDER, exist_ok=True)

# --------------------------------------------
# ✅ Load and Prepare Data
# --------------------------------------------

file_path = os.path.join(DATA_FOLDER, "MyEBirdData.csv")
df = pd.read_csv(file_path)

location_data = df[['Location ID', 'Location', 'Latitude', 'Longitude']].drop_duplicates()
species_list = sorted(df["Common Name"].dropna().unique().tolist())
selected_species_name = ""

# Build mapping from Common Name to Scientific Name
name_map = (
    df[['Common Name', 'Scientific Name']]
    .dropna()
    .drop_duplicates()
    .set_index('Common Name')['Scientific Name']
    .to_dict()
)

# --------------------------------------------
# ✅ Species Filter (for subspecies / slashes)
# --------------------------------------------

def filter_species(df, base_species):
    base_species = base_species.lower().strip()
    if "/" in base_species:
        return df[df["Scientific Name"].str.lower() == base_species]
    filtered_df = df[df["Scientific Name"].fillna("").str.lower().str.startswith(base_species)]
    return filtered_df[~filtered_df["Scientific Name"].str.contains("/", regex=False)]

# --------------------------------------------
# ✅ Autocomplete UI Setup
# --------------------------------------------

schema = Schema(common_name=TEXT(stored=True, analyzer=StemmingAnalyzer()))
index_dir = tempfile.mkdtemp()
ix = create_in(index_dir, schema)
writer = ix.writer()
for name in species_list:
    writer.add_document(common_name=name)
writer.commit()

search_box = widgets.Text(placeholder="Type species name...", description="Search:")
dropdown = widgets.Select(options=[], description="Matches:", rows=10)
output = widgets.Output()
hide_non_matching_checkbox = Checkbox(
    value=False,
    description='Hide locations where species was not seen',
    indent=False
)

def update_suggestions(change):
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
        dropdown.options = [r["common_name"] for r in ranked[:10]]

search_box.observe(update_suggestions, names="value")


# --------------------------------------------
# ✅ Map Drawing Function (called dynamically)
# --------------------------------------------
species_map = None
last_search_task = None
map_output = widgets.Output()
debounce_delay = 0.5   # Delay time for debounce (in seconds)

def on_species_selected(change):
    global selected_species_name
    output.clear_output()
    selected_species_name = name_map.get(change['new'], "").strip()
    with output:
        print(f"🔎 Selected species: {change['new']} → Scientific: {selected_species_name}")
    draw_map_with_species_overlay(selected_species_name)

def on_toggle_change(change):
    global selected_species_name
    with output:
        print(f"🧪 Toggle changed: {change['new']} — Current species: {selected_species_name}")
    if selected_species_name:
        draw_map_with_species_overlay(selected_species_name)

def on_search_box_cleared(change):
    global last_search_task

    search_value = change["new"].strip()

    # Cancel any previous redraw task
    if last_search_task and not last_search_task.done():
        last_search_task.cancel()

    # If truly cleared — reset toggle and show all
    if search_value == "":
        dropdown.options = []
        dropdown.value = None
        hide_non_matching_checkbox.value = False
        output.clear_output()
        with output:
            print("🧹 Search cleared — showing all locations")
        draw_map_with_species_overlay("")
    else:
        # Debounce redraw to avoid slowing down typing
        async def delayed_search():
            try:
                await asyncio.sleep(debounce_delay)
                # Do not trigger map redraw unless dropdown value has changed
                if dropdown.value:
                    draw_map_with_species_overlay(selected_species_name)
            except asyncio.CancelledError:
                pass  # Cancelled due to more typing

        last_search_task = asyncio.create_task(delayed_search())


''''
def create_map(map_center):
    """Create a Folium map with the selected MAP_STYLE."""
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

def draw_map_with_species_overlay(selected_species):
    global species_map
    map_center = [location_data['Latitude'].mean(), location_data['Longitude'].mean()]
    species_map = create_map(map_center)

    if not selected_species:
        for _, row in location_data.iterrows():
            base_records = df[df['Location ID'] == row['Location ID']]
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
    else:
        filtered = filter_species(df, selected_species)
        seen_location_ids = set(filtered['Location ID'])

        # Determine lifer (first observation by date+time)
        lifer_location = None
        if MARK_LIFER and not filtered.empty:
            filtered['datetime'] = pd.to_datetime(filtered['Date'] + ' ' + filtered['Time'])
            lifer_location = filtered.sort_values('datetime').iloc[0]['Location ID']

        for _, row in location_data.iterrows():
            loc_id = row['Location ID']
            is_species_location = loc_id in seen_location_ids

            if hide_non_matching_checkbox.value and not is_species_location:
                continue

            base_records = df[df['Location ID'] == loc_id]
            visit_info = "<br>".join(
                f"{d} {str(t) if pd.notna(t) else 'unknown'}"
                for d, t in sorted(
                    {(d, str(t) if pd.notna(t) else 'unknown') for d, t in zip(base_records["Date"], base_records["Time"])}
                )
            )
            base_popup = f"<b>{row['Location']}</b><br><b>Visited:</b><br>{visit_info}"

            if is_species_location:
                sub = filtered[filtered['Location ID'] == loc_id]
                obs_details = "".join(
                    f"<br>{r['Date']} {r['Time']} — {r['Common Name']} ({r['Count']})" for _, r in sub.iterrows()
                )
                popup_content = folium.Popup(base_popup + "<br><b>Seen:</b>" + obs_details, max_width=800)

                if MARK_LIFER and loc_id == lifer_location:
                    color, fill = "blue", "blue"
                else:
                    color, fill = "red", "red"
            else:
                popup_content = folium.Popup(base_popup, max_width=800)
                color, fill = "green", "lightgreen"

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
'''

# --------------------------------------------
# ✅ Observers for UI Interactions
# --------------------------------------------

def on_species_selected(change):
    global selected_species_name
    output.clear_output()
    selected_species_name = name_map.get(change['new'], "").strip()
    with output:
        print(f"🔎 Selected species: {change['new']} → Scientific: {selected_species_name}")
    draw_map_with_species_overlay(selected_species_name)

def on_toggle_change(change):
    global selected_species_name
    with output:
        print(f"🧪 Toggle changed: {change['new']} — Current species: {selected_species_name}")
    if selected_species_name:
        draw_map_with_species_overlay(selected_species_name)

def on_search_box_cleared(change):
    if change["new"].strip() == "":
        dropdown.options = []
        dropdown.value = None
        hide_non_matching_checkbox.value = False  # Reset toggle
        with output:
            output.clear_output()
            print("🧹 Search cleared — showing all locations")
        draw_map_with_species_overlay("")

dropdown.observe(on_species_selected, names='value')
hide_non_matching_checkbox.observe(on_toggle_change, names='value')
search_box.observe(on_search_box_cleared, names="value")

# %%
# Show the map in its own cell
# Initial map load (all green markers)

draw_map_with_species_overlay("")
display(map_output)



# %%
