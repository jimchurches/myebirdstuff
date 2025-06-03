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
import os
import sys
import pandas as pd
import folium
from rapidfuzz import fuzz
import ipywidgets as widgets
from rapidfuzz import process
from IPython.display import display, HTML


# --------------------------------------------
# ✅ Configuration & Paths
# --------------------------------------------

MAP_STYLE = "default"          # Options: 'default', 'satellite', 'google', 'carto'
EXPORT_GOOGLE_CSV = False      # If True, export CSV for Google Maps
DISPLAY_SPECIES_LIST = False   # Show a list of found species in eBird data
TEST_SEARCH = False            # Here for some testing and probably remove later

# Get absolute path to scripts folder
scripts_path = os.path.abspath("../scripts")  # Move up one level from notebooks/
sys.path.append(scripts_path)  # Add scripts folder to Python module search path

# Try importing config file, fallback to template
try:
    from config_secret import DATA_FOLDER  
except ImportError:
    from config_template import DATA_FOLDER  # Example file for GitHub

# Output paths
csv_output_path = os.path.join(DATA_FOLDER, "ebird_locations.csv")
map_output_path = os.path.join(DATA_FOLDER, "ebird_map.html")

# Ensure data folder exists
os.makedirs(DATA_FOLDER, exist_ok=True)

# --------------------------------------------
# ✅ Load CSV Data & Extract Key Fields
# --------------------------------------------

file_path = os.path.join(DATA_FOLDER, "MyEBirdData.csv")
df = pd.read_csv(file_path)

# Extract unique locations
location_data = df[['Location ID', 'Location', 'Latitude', 'Longitude']].drop_duplicates()

# Extract unique species (sorted alphabetically)
species_list = sorted(df["Common Name"].unique().tolist())

# --------------------------------------------
# ✅ Species Filtering Function (Case-insensitive + Slash Handling)
# --------------------------------------------

def filter_species(df, base_species):
    """Filters the dataset for a selected species or subspecies."""
    base_species = base_species.lower().strip()  # Normalize input

    if "/" in base_species:
        # User selected a slash species → Return exact matches only
        return df[df["Scientific Name"].str.lower() == base_species]
    
    # Normal filtering → Finds parent species but excludes slash species
    filtered_df = df[df["Scientific Name"].fillna("").str.lower().str.startswith(base_species)]
    return filtered_df[~filtered_df["Scientific Name"].str.contains("/", regex=False)]

# --------------------------------------------
# ✅ Interactive Map Creation
# --------------------------------------------

# Determine map center
map_center = [location_data['Latitude'].mean(), location_data['Longitude'].mean()]

# Map style options
tile_options = {
    "default": "OpenStreetMap",
    "satellite": "Esri WorldImagery",
    "google": "https://mt1.google.com/vt/lyrs=y&x={x}&y={y}&z={z}",
    "carto": "CartoDB Positron"
}

# Create base map
m = folium.Map(location=map_center, zoom_start=6, tiles=tile_options.get(MAP_STYLE, "OpenStreetMap"))

# Add markers for each location
for _, row in location_data.iterrows():
    visited_dates = df[df["Location ID"] == row["Location ID"]]["Date"].unique()
    visited_text = "<br>".join(visited_dates) if visited_dates.size > 0 else "No recorded visits"

    popup_content = folium.Popup(
        f"<b>{row['Location']}</b><br><b>Visited:</b><br>{visited_text}",
        max_width=800  # Adjust for wider popups
    )

    folium.CircleMarker(
        location=[row['Latitude'], row['Longitude']],
        radius=4,
        color="green",
        fill=True,
        fill_color="lightgreen",
        fill_opacity=0.6,
        popup=popup_content
    ).add_to(m)

# --------------------------------------------
# ✅ Optional: Display Species List
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

# --------------------------------------------
# ✅ Export Google CSV (If Enabled)
# --------------------------------------------

if EXPORT_GOOGLE_CSV:
    location_data.to_csv(csv_output_path, index=False)
    print("✍️ Google CSV export written to your data folder.")

# Save the map (if needed externally)
m.save(map_output_path)
print(f"✍️ Mapping file saved to your data folder named '{os.path.basename(os.path.normpath(DATA_FOLDER))}'")

# --------------------------------------------
# ✅ Interactive Fuzzy Search UI for Species Selection
# --------------------------------------------

# Create a search box
search_box = widgets.Text(placeholder="Type species name...", description="Search:")
output = widgets.Output()

# Function to update search suggestions as clickable buttons
def improved_species_match(query, species_list, limit=10):
    tokens = query.lower().split()
    scores = []

    for species in species_list:
        name = species.lower()
        words = name.split()

        token_score = 0
        matched_tokens = 0

        for token in tokens:
            if any(word.startswith(token) for word in words):
                token_score += 25  # strong prefix match
                matched_tokens += 1
            elif token in name:
                token_score += 10  # weak anywhere match
                matched_tokens += 1

        if matched_tokens == 0:
            continue

        fuzzy_score = fuzz.partial_ratio(query, name)
        common_penalty = 10 if any(c in name for c in ["black", "white", "common", "sp."]) else 0

        total_score = token_score + fuzzy_score - common_penalty
        scores.append((species, total_score))

    scores.sort(key=lambda x: x[1], reverse=True)
    return [s[0] for s in scores[:limit]]






search_box.observe(update_suggestions, names="value")

#update_suggestions({"new": "alb"})


# Display the search UI
display(search_box, output)

# --------------------------------------------
# ✅ Test Species Filtering on a Sample Input
# --------------------------------------------
if TEST_SEARCH:
    selected_species = "Tachyspiza cirrocephala/fasciata"  # Example selection
    filtered_data = filter_species(df, selected_species)

    # Display filtered results, sorting by Common Name → Date → Time (if available)
    print(filtered_data[["Common Name", "Date", "Time", "Location"]]
          .sort_values(["Common Name", "Date", "Time"], ascending=[True, True, True])
          .to_string(index=False))

