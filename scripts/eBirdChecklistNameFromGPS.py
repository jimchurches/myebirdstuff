#!/usr/bin/env python3

import os
import sys
import json
import requests
import pyperclip

# Flags
debug_mode = '--debug' in sys.argv
rich_output = '--rich' in sys.argv

# Load GPS from clipboard
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

# API call
url = f'https://maps.googleapis.com/maps/api/geocode/json?latlng={lat},{lon}&key={GOOGLE_API_KEY}'
response = requests.get(url)
data = response.json()

if debug_mode:
    print(json.dumps(data, indent=2))
    sys.exit(0)

# Suburb and override logic for Canberra
CanberraFocus = True
canberra_regions = ['Belconnen', 'Canberra Central', 'Gungahlin', 'Molonglo Valley', 'Tuggeranong', 'Woden Valley', 'Weston Creek']
canberra_suburbs = ['Acton', 'Ainslie', 'Amaroo', 'Aranda', 'Banks', 'Barton', 'Belconnen', 'Bonner', 'Braddon', 'Bruce', 'Calwell',
    'Campbell', 'Chapman', 'Charnwood', 'Chifley', 'Conder', 'Cook', 'Curtin', 'Deakin', 'Dickson', 'Downer', 'Duffy',
    'Dunlop', 'Evatt', 'Fadden', 'Farrer', 'Fisher', 'Florey', 'Flynn', 'Forde', 'Forrest', 'Franklin', 'Fraser', 'Garran',
    'Gilmore', 'Giralang', 'Gordon', 'Gowrie', 'Greenway', 'Griffith', 'Hackett', 'Harrison', 'Hawker', 'Higgins', 'Holder',
    'Holt', 'Hughes', 'Isaacs', 'Isabella Plains', 'Kaleen', 'Kambah', 'Kingston', 'Latham', 'Lawson', 'Lyneham', 'Lyons',
    'Macarthur', 'Macgregor', 'Macquarie', 'Majura', 'Manuka', 'Mawson', 'McKellar', 'Melba', 'Monash', 'Narrabundah',
    'Ngunnawal', 'Nicholls', "O'Connor", "O'Malley", 'Oxley', 'Page', 'Palmerston', 'Parkes', 'Pearce', 'Phillip', 'Red Hill',
    'Reid', 'Rivett', 'Scullin', 'Spence', 'Stirling', 'Taylor', 'Tharwa', 'Theodore', 'Torrens', 'Turner', 'Watson',
    'Weetangera', 'Weston', 'Wright', 'Wanniassa', 'Yarralumla']
misfire_names = {
    # 'Uriarra Village': 'Coree',
}

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
chosen_suburb = None
chosen_region = None

for result in data.get("results", []):
    for component in result.get("address_components", []):
        name = component.get("long_name")
        types = component.get("types", [])
        seen_types.update(types)

        if 'locality' in types and name in canberra_suburbs:
            chosen_suburb = name
        if 'neighborhood' in types and name in canberra_regions:
            chosen_region = name

        for p_type in preferred_types:
            if p_type in types:
                candidates.append((preferred_types.index(p_type), name, p_type))
                break

if CanberraFocus and chosen_suburb and chosen_region:
    chosen_name = chosen_suburb
    override_note = f"🎯 Canberra override: using suburb '{chosen_suburb}' instead of region '{chosen_region}'"
else:
    candidates.sort(key=lambda x: x[0])
    candidate_name = candidates[0][1] if candidates else "Unknown"
    chosen_name = misfire_names.get(candidate_name, candidate_name)
    override_note = ""

# Output block
if rich_output:
    print("📦 Candidate address components:")
    for i, (rank, name, tag) in enumerate(candidates):
        print(f" {i+1:>2}. {name:<25} ({tag})")
    if override_note:
        print(override_note)
    print("")

output = f"{chosen_name} ( {lat}, {lon} )"
pyperclip.copy(output)
print(output)
