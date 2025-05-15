import sys
import requests
import pyperclip

# Get GPS from clipboard
text = pyperclip.paste()
try:
    lat, lon = [s.strip() for s in text.split(',')]
except ValueError:
    print("Invalid clipboard format. Expected: lat, lon")
    sys.exit(1)

# Load API key
try:
    from config_secret import GOOGLE_API_KEY
except ImportError:
    from config_template import GOOGLE_API_KEY

# Preferred types in order
preferred_types = [
    'sublocality',
    'locality',
    'postal_town',
    'neighborhood',
    'administrative_area_level_4',
    'administrative_area_level_3',
    'administrative_area_level_2'
]

# Call Google Maps API
url = f"https://maps.googleapis.com/maps/api/geocode/json?latlng={lat},{lon}&key={GOOGLE_API_KEY}"
response = requests.get(url)
data = response.json()

# Extract location
location_name = None
if data.get('status') == 'OK':
    for result in data.get('results', []):
        components = result.get('address_components', [])
        for level in preferred_types:
            match = next((c['long_name'] for c in components if level in c['types']), None)
            if match:
                location_name = match
                break
        if location_name:
            break

if not location_name:
    location_name = "Unknown"

# Format and copy result
final_name = f"{location_name} ( {lat}, {lon} )"
print(final_name)
pyperclip.copy(final_name)
