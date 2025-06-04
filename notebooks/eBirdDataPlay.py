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

import os
import sys
import pandas as pd
import folium
import ipywidgets as widgets
from IPython.display import display, HTML

from whoosh.fields import Schema, TEXT
from whoosh.analysis import StemmingAnalyzer
from whoosh.index import create_in
from whoosh.qparser import QueryParser, OrGroup
import tempfile

# --------------------------------------------
# ✅ Configuration & Paths
# --------------------------------------------

MAP_STYLE = "default"
EXPORT_GOOGLE_CSV = False
DISPLAY_SPECIES_LIST = False

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

# --------------------------------------------
# ✅ Filter Function for Subspecies / Slash Logic
# --------------------------------------------

def filter_species(df, base_species):
    base_species = base_species.lower().strip()
    if "/" in base_species:
        return df[df["Scientific Name"].str.lower() == base_species]
    filtered_df = df[df["Scientific Name"].fillna("").str.lower().str.startswith(base_species)]
    return filtered_df[~filtered_df["Scientific Name"].str.contains("/", regex=False)]

# --------------------------------------------
# ✅ Build Interactive Map
# --------------------------------------------

map_center = [location_data['Latitude'].mean(), location_data['Longitude'].mean()]
tile_options = {
    "default": "OpenStreetMap",
    "satellite": "Esri WorldImagery",
    "google": "https://mt1.google.com/vt/lyrs=y&x={x}&y={y}&z={z}",
    "carto": "CartoDB Positron"
}
m = folium.Map(location=map_center, zoom_start=6, tiles=tile_options.get(MAP_STYLE, "OpenStreetMap"))

for _, row in location_data.iterrows():
    visited_dates = df[df["Location ID"] == row["Location ID"]]["Date"].unique()
    visited_text = "<br>".join(visited_dates) if visited_dates.size > 0 else "No recorded visits"
    popup_content = folium.Popup(f"<b>{row['Location']}</b><br><b>Visited:</b><br>{visited_text}", max_width=800)
    folium.CircleMarker(
        location=[row['Latitude'], row['Longitude']],
        radius=4,
        color="green",
        fill=True,
        fill_color="lightgreen",
        fill_opacity=0.6,
        popup=popup_content
    ).add_to(m)

m.save(map_output_path)
print(f"✍️ Mapping file saved to your data folder named '{os.path.basename(os.path.normpath(DATA_FOLDER))}'")

# --------------------------------------------
# ✅ Display Optional Species Table
# --------------------------------------------

if DISPLAY_SPECIES_LIST:
    table_html = "<table style='border-collapse: collapse;'><tr>"
    for i, species in enumerate(species_list):
        table_html += f"<td style='padding: 5px; border: 1px solid #ccc;'>{species}</td>"
        if (i + 1) % 5 == 0:
            table_html += "</tr><tr>"
    table_html += "</tr></table>"
    print("✍️ List of species found in your eBird data")
    display(HTML(table_html))

if EXPORT_GOOGLE_CSV:
    location_data.to_csv(csv_output_path, index=False)
    print("✍️ Google CSV export written to your data folder.")

# --------------------------------------------
# ✅ Setup Whoosh Index for Autocomplete
# --------------------------------------------

schema = Schema(common_name=TEXT(stored=True, analyzer=StemmingAnalyzer()))
index_dir = tempfile.mkdtemp()
ix = create_in(index_dir, schema)
writer = ix.writer()
for name in species_list:
    writer.add_document(common_name=name)
writer.commit()

# --------------------------------------------
# ✅ Autocomplete UI with Priority Ranking
# --------------------------------------------

search_box = widgets.Text(placeholder="Type species name...", description="Search:")
dropdown = widgets.Select(options=[], description="Matches:", rows=10)
output = widgets.Output()

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

def on_select(change):
    with output:
        output.clear_output()
        print(f"🔎 You selected: {change['new']}")

search_box.observe(update_suggestions, names="value")
dropdown.observe(on_select, names="value")

display(search_box, dropdown, output)
