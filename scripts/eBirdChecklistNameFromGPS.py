#!/usr/bin/env python3

import os
import sys
import json
import requests
import pyperclip

# Get GPS from clipboard
gps = pyperclip.paste()
try:
    lat, lon = [s.strip() for s in gps.split(',')]
except ValueError:
    print("❌ Invalid clipboard format. Expected: lat, lon")
    sys.exit(1)

# Load API key
try:
    from config_secret import GOOGLE_API_KEY
except ImportError:
    from config_template import GOOGLE_API_KEY

# Optional debug flag
debug_mode = '--debug' in sys.argv

url = f'https://maps.googleapis.com/maps/api/geocode/json?latlng={lat},{lon}&key={GOOGLE_API_KEY}'

# Perform the API request
response = requests.get(url)
data = response.json()

if debug_mode:
    print(json.dumps(data, indent=2))
    sys.exit(0)

# Preferred types to search for, in order
preferred_types = [
    'neighborhood',
    'sublocality',
    'locality',
    'postal_town',
    'administrative_area_level_4',
    'administrative_area_level_3',
    'administrative_area_level_2'
]

candidates = []
seen_types = set()

# Search through all address components
for result in data.get("results", []):
    for component in result.get("address_components", []):
        types = component.get("types", [])
        seen_types.update(types)
        for p_type in preferred_types:
            if p_type in types:
                candidates.append((preferred_types.index(p_type), component.get("long_name")))
                break  # Only record the first match from this component

# Decide on name
if candidates:
    candidates.sort(key=lambda x: x[0])  # sort by preferred_types index
    name = candidates[0][1]
else:
    print("⚠️ No preferred type match found. Types seen:")
    for t in sorted(seen_types):
        print(f" - {t}")
    name = "Unknown"

# Format output
output = f"{name} ( {lat}, {lon} )"
pyperclip.copy(output)
print(output)
