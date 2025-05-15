import sys
import requests
import pyperclip

# Assume lat/lon are passed via clipboard
text = pyperclip.paste()
try:
    lat, lon = [s.strip() for s in text.split(',')]
except ValueError:
    print("Invalid clipboard format. Expected: lat, lon")
    sys.exit(1)

try:
    from config_secret import GOOGLE_API_KEY
except ImportError:
    from config_template import GOOGLE_API_KEY


url = f"https://maps.googleapis.com/maps/api/geocode/json?latlng={lat},{lon}&key={GOOGLE_API_KEY}"
response = requests.get(url)
data = response.json()

if data['status'] == 'OK':
    components = data['results'][0]['address_components']

    preferred_types = [
        'sublocality',        
        'locality',
        'postal_town',
        'neighborhood',
        'administrative_area_level_4',
        'administrative_area_level_3',
        'administrative_area_level_2'
    ]

    locality = None
    for level in preferred_types:
        match = next((c['long_name'] for c in components if level in c['types']), None)
        if match:
            locality = match
            break

    if not locality:
        locality = "Unknown"

    formatted_name = f"{locality} ( {lat}, {lon} )"
    pyperclip.copy(formatted_name)
    print(formatted_name)
else:
    print(f"Geocoding failed: {data.get('status', 'Unknown error')}")
    sys.exit(1)

