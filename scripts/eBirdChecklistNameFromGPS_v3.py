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

    # Optional sanity check (helpful to catch garbage / swapped order)
    # If values look swapped (first looks like a longitude), swap them.
    if not (-90 <= lat <= 90) and (-90 <= lng <= 90) and (-180 <= lat <= 180):
        lat, lng = lng, lat
        lat_str, lng_str = lng_str, lat_str
        lat_dp, lng_dp = lng_dp, lat_dp

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


def extract_best_name(data: dict, lat: float, lng: float, debug: bool = False) -> str:
    """
    Temporary minimal implementation.
    Returns locality if present, otherwise formatted_address.
    """

    results = data.get("results", [])

    for result in results:
        for component in result.get("address_components", []):
            if "locality" in component.get("types", []):
                return component.get("long_name")

    # fallback
    if results:
        return results[0].get("formatted_address", "Unknown")

    return "Unknown"


def resolve_location(lat: float, lng: float, api_key: str, debug=False) -> str:

    data = fetch_geocode(lat, lng, api_key, debug)

    for result in data["results"]:
        for comp in result["address_components"]:

            if "locality" in comp["types"]:
                return comp["long_name"]

            if "neighborhood" in comp["types"]:
                return comp["long_name"]

    return "Unknown Location"


def resolve_location_from_data(data: dict, lat: float, lng: float, debug: bool=False) -> str:
    """
    Resolve location using already-fetched geocode JSON.
    Used by testfile mode to avoid live API calls.
    """
    return extract_best_name(data, lat, lng, debug)


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


def run_test_file(testfile: str, api_key: str, debug: bool = False, live: bool = False) -> int:
    """
    Run resolver tests from a JSON file.

    Each test case should contain:
        lat
        lng
        expected
        geocode_json (required unless --live is used)
    """
    with open(testfile, "r", encoding="utf-8") as f:
        cases = json.load(f)

    passed = 0
    failed = 0
    skipped = 0

    if not isinstance(cases, list):
        print("ERROR: Test file must contain a JSON list of test cases.")
        return 1

    for i, case in enumerate(cases, 1):
        # Basic structural validation (don’t crash on junk/blank entries)
        if not isinstance(case, dict):
            print(f"Test {i:02} ERROR test case is not an object/dict")
            failed += 1
            continue

        if "lat" not in case or "lng" not in case:
            print(f"Test {i:02} ERROR missing 'lat' and/or 'lng' in test case")
            failed += 1
            continue

        lat = case["lat"]
        lng = case["lng"]
        expected = case.get("expected")

        try:
            if live:
                # --live means: always call the API, ignore embedded geocode_json
                name = resolve_location(lat, lng, api_key, debug)

            else:
                # non-live means: must have embedded geocode_json
                geocode_json = case.get("geocode_json")
                if not geocode_json:
                    print(f"Test {i:02} ERROR missing 'geocode_json' (run with --live to fetch from API)")
                    failed += 1
                    continue

                name = resolve_location_from_data(
                    geocode_json,
                    lat,
                    lng,
                    debug
                )

        except Exception as e:
            print(f"Test {i:02} ERROR resolving location: {e}")
            failed += 1
            continue

        if expected is None:
            print(f"Test {i:02} SKIP (no expected value)")
            skipped += 1
            continue

        if name == expected:
            print(f"Test {i:02} PASS  {name}")
            passed += 1
        else:
            print(f"Test {i:02} FAIL  got='{name}' expected='{expected}'")
            failed += 1

    print()
    print(f"Summary: {passed} passed, {failed} failed, {skipped} skipped")
    return failed


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
    parser.add_argument("--live", action="store_true", help="For --testfile runs, ignore embedded geocode_json and fetch live from the API.",
)

    args, extras = parser.parse_known_args()

    api_key = load_api_key()

    if args.testfile:
        raise SystemExit(
            run_test_file(
                args.testfile,
                api_key=api_key,
                debug=args.debug,
                live=args.live
            )
        )

    # 1) Get coordinate text from clipboard or argv tokens
    if args.clipboard:
        coord_text = pyperclip.paste()
    else:
        coord_text = " ".join(list(args.coords) + list(extras))

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