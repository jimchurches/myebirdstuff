#!/usr/bin/env python3

"""
eBirdChecklistNameFromGPS_v3.py

Resolves GPS coordinates into an eBird-friendly location name.

Output format:
    Location Name ( lat, lng )

Supports input from:
    command line
    clipboard
    test file

Examples:
    script.py -35.327454,148.860410
    script.py -35.327454 148.860410
    script.py "--clipboard"
    script.py --testfile test.json
"""

import argparse
import json
import re
import sys
import requests
import pyperclip
from typing import Tuple, List


# ------------------------------------------------------------
# API key loader
# ------------------------------------------------------------


def load_api_key() -> str:
    try:
        from config_secret import GOOGLE_API_KEY
    except ImportError:
        from config_template import GOOGLE_API_KEY

    if not GOOGLE_API_KEY or GOOGLE_API_KEY == "YOUR_API_KEY_HERE":
        raise RuntimeError("Google API key not configured.")

    return GOOGLE_API_KEY


# ------------------------------------------------------------
# Coordinate parsing
# ------------------------------------------------------------


def parse_coords_from_text(text: str) -> Tuple[float, float, int, int]:
    """
    Extract the first two numbers from arbitrary text and treat them as lat/lng.

    Accepts:
      - "-35.327454,148.860410"
      - "-35.327454, 148.860410"
      - "-35.327454 148.860410"
      - "Uriarra Village ( -35.327454, 148.860410 )"
      - any other text containing at least two numbers

    Returns: (lat, lng, lat_dp, lng_dp)
    """
    text = (text or "").strip()
    if not text:
        raise ValueError("No coordinates provided.")

    # Find ints or decimals with optional sign
    nums = re.findall(r"[+-]?\d{1,3}(?:\.\d+)?", text)
    if len(nums) < 2:
        raise ValueError(f"Could not find two numbers to use as coordinates in: {text!r}")

    lat_str, lng_str = nums[0], nums[1]

    lat = float(lat_str)
    lng = float(lng_str)

    lat_dp = len(lat_str.split(".", 1)[1]) if "." in lat_str else 0
    lng_dp = len(lng_str.split(".", 1)[1]) if "." in lng_str else 0

    # Optional sanity check (helpful to catch garbage)
    if not (-90 <= lat <= 90 and -180 <= lng <= 180):
        raise ValueError(f"Extracted values out of range: lat={lat}, lng={lng} from {text!r}")

    return lat, lng, lat_dp, lng_dp


# ------------------------------------------------------------
# Geocode fetch
# ------------------------------------------------------------


def fetch_geocode(lat: float, lng: float, api_key: str, debug=False):

    url = "https://maps.googleapis.com/maps/api/geocode/json"

    params = {
        "latlng": f"{lat},{lng}",
        "key": api_key,
    }

    response = requests.get(url, params=params)
    data = response.json()

    if debug:
        print(json.dumps(data, indent=2))

    if data["status"] != "OK":
        raise RuntimeError(f"Geocode failed: {data['status']}")

    return data


# ------------------------------------------------------------
# Naming logic (simple baseline)
# ------------------------------------------------------------


def resolve_location(lat: float, lng: float, api_key: str, debug=False) -> str:

    data = fetch_geocode(lat, lng, api_key, debug)

    for result in data["results"]:
        for comp in result["address_components"]:

            if "locality" in comp["types"]:
                return comp["long_name"]

            if "neighborhood" in comp["types"]:
                return comp["long_name"]

    return "Unknown Location"


# ------------------------------------------------------------
# Output formatting
# ------------------------------------------------------------


def format_location_string(
    name: str,
    lat: float,
    lng: float,
    lat_dp: int,
    lng_dp: int
) -> str:

    lat_str = f"{lat:.{lat_dp}f}"
    lng_str = f"{lng:.{lng_dp}f}"

    return f"{name} ( {lat_str}, {lng_str} )"


# ------------------------------------------------------------
# Clipboard output
# ------------------------------------------------------------


def copy_to_clipboard(text: str):
    pyperclip.copy(text)


# ------------------------------------------------------------
# Test file runner
# ------------------------------------------------------------


def run_test_file(path: str, api_key: str, debug=False):

    with open(path) as f:
        tests = json.load(f)

    passed = 0

    for test in tests:

        lat = test["lat"]
        lng = test["lng"]
        expected = test["expected"]

        name = resolve_location(lat, lng, api_key, debug)

        if name == expected:
            passed += 1
        else:
            print(f"FAIL: {lat},{lng}")
            print(f"Expected: {expected}")
            print(f"Got: {name}")

    print(f"{passed}/{len(tests)} passed")


# ------------------------------------------------------------
# Main
# ------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Resolve a GPS point to an eBird-friendly location name."
    )

    parser.add_argument(
        "coords",
        nargs="*",
        help="Coordinates: lat,lng or lat lng (quotes optional). Also accepts full formatted text."
    )
    parser.add_argument("--clipboard", action="store_true", help="Read coordinates from clipboard.")
    parser.add_argument("--debug", action="store_true", help="Enable debug output.")
    parser.add_argument("--testfile", help="Run a JSON test file.")

    args = parser.parse_args()

    api_key = load_api_key()

    if args.testfile:
        raise SystemExit(run_test_file(args.testfile, api_key=api_key, debug=args.debug))

    # 1) Get coordinate text from clipboard or argv tokens
    if args.clipboard:
        coord_text = pyperclip.paste()
    else:
        coord_text = " ".join(args.coords).replace(",", " ")

    # 2) Parse coordinates (robust to commas/spaces/formatted strings)
    lat, lng, lat_dp, lng_dp = parse_coords_from_text(coord_text)

    # 3) Resolve + format output
    name = resolve_location(lat, lng, api_key=api_key, debug=args.debug)
    output = format_location_string(name, lat, lng, lat_dp, lng_dp)

    print(output)
    copy_to_clipboard(output)


# ------------------------------------------------------------

if __name__ == "__main__":
    main()