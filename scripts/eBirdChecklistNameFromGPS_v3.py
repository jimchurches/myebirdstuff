#!/usr/bin/env python3

"""
eBirdChecklistNameFromGPS_v3.py

Resolves GPS coordinates into an eBird-friendly location name.
Output is printed to the console and copied to the clipboard (for UI.Vision macros).

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

ACT (Australian Capital Territory): In Google data, suburbs are 'locality' and
districts are 'neighborhood' (reversed from most jurisdictions). The script
prefers the geographically best-matching result, then uses locality (suburb)
if present else neighborhood (district). Results that are only plus_code (grid
cells) are deprioritised in ACT so that when a point is in open land (e.g. a
reserve in Belconnen district, 50m from Whitlam suburb), we take the street/area
result (Belconnen) rather than the plus_code cell that is centred on the point
but labelled with the neighbouring suburb (Whitlam).

Jurisdictions:
  The code has a Canberra/ACT-focused section because that is the primary
  use case and Google's reverse-geocode data for the ACT has specific quirks
  (district vs suburb, plus_code cells on borders, etc.). Other areas use
  generic logic: country detection, type-priority by country (e.g. Spain,
  Indonesia), and a common sort by containment, area, and distance. There are
  no separate "Canberra modules"—just an ACT branch in the sort key and
  naming logic. To support more jurisdictions (e.g. USA with state-level
  differences), a future refactor could introduce a configuration file
  (e.g. JSON) that maps country/state to rules (type priority, thresholds,
  when to prefer district over locality, plus_code handling). That is not
  implemented yet and is not required for current use.

Development:
  This script was written extensively with Cursor (https://cursor.com), an
  AI-powered code editor that helps with editing, refactoring, and debugging
  in the IDE. If you find this code useful and want similar assistance for
  your own projects, Cursor is free to try and works with your existing
  editor workflow.
"""

import argparse
import json
import re
import sys
import requests
import pyperclip
from typing import Tuple, List, Optional


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
# Geometry helpers (for ranking which result best matches the point)
# ------------------------------------------------------------

def _bounds_contain_point(bounds: dict, lat: float, lng: float) -> bool:
    """True if (lat, lng) is inside bounds (northeast/southwest)."""
    if not bounds:
        return False
    ne = bounds.get("northeast", {})
    sw = bounds.get("southwest", {})
    try:
        ne_lat = float(ne.get("lat"))
        sw_lat = float(sw.get("lat"))
        ne_lng = float(ne.get("lng"))
        sw_lng = float(sw.get("lng"))
    except (TypeError, ValueError):
        return False
    return sw_lat <= lat <= ne_lat and sw_lng <= lng <= ne_lng


def _bounds_area(bounds: dict) -> float:
    """Approximate area (lat span * lng span). Smaller = more specific."""
    if not bounds:
        return float("inf")
    ne = bounds.get("northeast", {})
    sw = bounds.get("southwest", {})
    try:
        lat_span = abs(float(ne.get("lat") or 0) - float(sw.get("lat") or 0))
        lng_span = abs(float(ne.get("lng") or 0) - float(sw.get("lng") or 0))
    except (TypeError, ValueError):
        return float("inf")
    return lat_span * lng_span


def _distance_sq_to_result_location(result: dict, lat: float, lng: float) -> float:
    """Squared distance (degrees²) from (lat, lng) to the result's geometry.location. For ACT tie-break."""
    geom = result.get("geometry", {})
    loc = geom.get("location") or {}
    try:
        r_lat = float(loc.get("lat"))
        r_lng = float(loc.get("lng"))
    except (TypeError, ValueError):
        return float("inf")
    return (lat - r_lat) ** 2 + (lng - r_lng) ** 2


# Location type preference: more specific first (ROOFTOP best, APPROXIMATE worst).
_LOCATION_TYPE_ORDER = {
    "ROOFTOP": 4,
    "RANGE_INTERPOLATED": 3,
    "GEOMETRIC_CENTER": 2,
    "APPROXIMATE": 1,
}


def _result_has_name_component(result: dict) -> bool:
    """True if result has at least one locality or neighborhood in address_components."""
    for comp in result.get("address_components", []):
        types = comp.get("types", [])
        if "locality" in types or "neighborhood" in types:
            if _is_valid_display_name((comp.get("long_name") or "").strip()):
                return True
    return False


def _result_has_locality(result: dict) -> bool:
    """True if result has a locality component (ACT suburb)."""
    return _result_has_component_type(result, "locality")


def _result_has_neighborhood_only(result: dict) -> bool:
    """True if result has neighborhood but no locality (ACT district without suburb)."""
    has_loc = _result_has_locality(result)
    has_neigh = _result_has_component_type(result, "neighborhood")
    return has_neigh and not has_loc


def _result_locality_name(result: dict) -> Optional[str]:
    """Return the locality long_name from address_components, or None."""
    for comp in result.get("address_components", []):
        if "locality" in comp.get("types", []):
            name = (comp.get("long_name") or "").strip()
            if _is_valid_display_name(name):
                return name
    return None


def _result_neighborhood_name(result: dict) -> Optional[str]:
    """Return the neighborhood long_name from address_components, or None."""
    for comp in result.get("address_components", []):
        if "neighborhood" in comp.get("types", []):
            name = (comp.get("long_name") or "").strip()
            if _is_valid_display_name(name):
                return name
    return None


def _result_has_component_type(result: dict, component_type: str) -> bool:
    """True if result has an address_component with the given type (e.g. administrative_area_level_4)."""
    for comp in result.get("address_components", []):
        if component_type in comp.get("types", []):
            if _is_valid_display_name((comp.get("long_name") or "").strip()):
                return True
    return False


def _result_is_plus_code_only(result: dict) -> bool:
    """True if this result's types are only plus_code (grid cell, often wrong locality near borders)."""
    types = result.get("types", [])
    return types == ["plus_code"] or (len(types) == 1 and "plus_code" in types)


def _result_sort_key(
    result: dict,
    lat: float,
    lng: float,
    in_act: bool = False,
    country_code: Optional[str] = None,
    act_has_containing_neighborhood: bool = False,
    act_containing_neighborhood_names: Optional[List[str]] = None,
    act_has_containing_real_suburb: bool = False,
) -> tuple:
    """
    Sort key for results: prefer (1) has locality/neighborhood, (2) bounds contain point,
    (3) in ACT or India: deprioritize plus_code-only results (wrong locality near borders
    or when overlapping names like Seraulim/Mungul),
    (4) smaller area, (5) better location_type.
    """
    has_name = _result_has_name_component(result)
    geom = result.get("geometry", {})
    bounds = geom.get("bounds") or geom.get("viewport")
    contains = _bounds_contain_point(bounds or {}, lat, lng)
    area = _bounds_area(bounds) if bounds else float("inf")
    loc_type = geom.get("location_type", "")
    type_rank = _LOCATION_TYPE_ORDER.get(loc_type, 0)

    # In ACT: deprioritize plus_code when its locality is not the district's suburb (e.g. Hume vs
    # Tuggeranong); don't deprioritize when locality matches district (Molonglo in Molonglo Valley).
    # Prefer district over locality when the locality name is not in the containing district name
    # (common "district location outside suburb" case: 34, 42, 43).
    if in_act:
        plus_only = _result_is_plus_code_only(result)
        dist_sq = _distance_sq_to_result_location(result, lat, lng)
        result_types = result.get("types", [])
        is_specific_address = "street_address" in result_types or "premise" in result_types
        has_locality = _result_has_locality(result)
        has_neighborhood_only = _result_has_neighborhood_only(result)
        locality_name = _result_locality_name(result)
        neighborhood_names = act_containing_neighborhood_names or []
        # Locality is "wrong" when from plus_code or from a specific place (establishment/POI) that's
        # across the border; don't deprioritize pure locality or street_address results (Chifley, etc.).
        is_establishment_or_poi = "establishment" in result_types or "point_of_interest" in result_types
        locality_wrong_for_district = (
            has_locality and act_has_containing_neighborhood and locality_name is not None
            and not any(locality_name in nn for nn in neighborhood_names)
            and (plus_only or is_establishment_or_poi)
        )
        # Deprioritize plus_code when a containing district exists and its locality isn't that district's suburb,
        # or when the district is the preferred level (e.g. "Weston Creek" over suburb "Weston" - test 40).
        plus_penalty = 0
        if plus_only:
            if dist_sq >= 1e-10:
                plus_penalty = 1
            elif act_has_containing_neighborhood and locality_name is not None:
                locality_in_district = any(locality_name in nn for nn in neighborhood_names)
                district_is_creek = any(nn == locality_name + " Creek" for nn in neighborhood_names)
                if not locality_in_district or district_is_creek:
                    plus_penalty = 1
        ACT_SUBURB_AREA_THRESHOLD = 0.01
        suburb_sized_locality = (
            has_locality and area < ACT_SUBURB_AREA_THRESHOLD and "postal_code" not in result_types
        )
        is_specific_effective = is_specific_address or (plus_only and dist_sq < 1e-10 and act_has_containing_real_suburb)
        return (
            0 if has_name else 1,
            0 if contains else 1,
            1 if locality_wrong_for_district else 0,  # prefer district over wrong locality (34, 42, 43)
            plus_penalty,
            0 if is_specific_effective else 1,
            0 if suburb_sized_locality else 1,  # suburb first
            0 if has_neighborhood_only else 1,   # then district (neighborhood-only)
            dist_sq,
            area,
            -type_rank,
        )

    # Indonesia (Bali): prefer results that have administrative_area_level_4 so we get
    # Pemogan/Benoa (desired level) rather than Denpasar/Kuta Selatan (city/regency).
    if country_code and country_code.upper() == "ID":
        has_admin4 = _result_has_component_type(result, "administrative_area_level_4")
        has_any_name = has_name or has_admin4
        return (0 if has_any_name else 1, 0 if has_admin4 else 1, 0 if contains else 1, area, -type_rank)

    # Spain: prefer results that have admin3, admin4, or neighborhood (municipality/barrio) so we
    # get Ribera d'Urgellet or Goya rather than plus_code locality (Saulet) or city (Madrid).
    # (Preferring admin3 over admin4 in the sort would get Baix Llobregat but break Boltaña/Ribera
    # d'Urgellet/Goya by picking larger comarca results like Sobrarbe/Alt Urgell.)
    if country_code and country_code.upper() == "ES":
        has_es_preferred = (
            _result_has_component_type(result, "administrative_area_level_3")
            or _result_has_component_type(result, "administrative_area_level_4")
            or _result_has_component_type(result, "neighborhood")
        )
        has_any_name = has_name or has_es_preferred
        return (0 if has_any_name else 1, 0 if has_es_preferred else 1, 0 if contains else 1, area, -type_rank)

    return (0 if has_name else 1, 0 if contains else 1, area, -type_rank)


def _is_act_result(result: dict) -> bool:
    """True if this result is in Australian Capital Territory (ACT)."""
    for comp in result.get("address_components", []):
        types = comp.get("types", [])
        if "administrative_area_level_1" in types:
            short_name = (comp.get("short_name") or "").strip()
            long_name = (comp.get("long_name") or "").strip()
            if short_name == "ACT" or "Australian Capital Territory" in long_name:
                return True
    return False


def _is_valid_display_name(name: str) -> bool:
    """Reject plus codes and long address-like strings."""
    if not name or not name.strip():
        return False
    if "+" in name and any(c.isdigit() for c in name):
        return False
    if "," in name and len(name.split()) > 4:
        return False
    return True


# ------------------------------------------------------------
# Naming logic
# ------------------------------------------------------------

def _get_name_from_result_act(result: dict) -> Optional[str]:
    """
    In ACT, suburbs are 'locality' and districts are 'neighborhood'.
    Prefer suburb (locality); if not present use district (neighborhood).
    """
    locality = None
    neighborhood = None
    for comp in result.get("address_components", []):
        types = comp.get("types", [])
        name = (comp.get("long_name") or "").strip()
        if not _is_valid_display_name(name):
            continue
        if "locality" in types:
            locality = name
        if "neighborhood" in types:
            neighborhood = name
    return locality or neighborhood


# Default type priority (locality first, then sublocality, then admin levels).
# India: use default (locality); no IN override. Overrides by country code capture
# "taste" per jurisdiction (e.g. municipality in Spain, admin4 in Indonesia).
# Structure is config-ready: could be moved to a JSON file later.
DEFAULT_TYPE_PRIORITY = [
    "locality",
    "sublocality",
    "sublocality_level_1",
    "administrative_area_level_2",
    "administrative_area_level_3",
    "neighborhood",
    "postal_town",
]

# Jurisdiction overrides: preferred component type order for a given country.
# Spain: municipality (admin3, sometimes admin4 in Catalonia), or neighborhood in cities (e.g. Goya in Madrid).
# Indonesia (Bali): admin4 works best (not tiny village, not regency/province).
TYPE_PRIORITY_BY_COUNTRY: dict = {
    "ES": [
        "administrative_area_level_3",  # municipality (rural)
        "administrative_area_level_4",  # e.g. Ribera d'Urgellet in Catalonia
        "neighborhood",  # e.g. Goya in Madrid (city barrio)
        "locality",
        "sublocality",
        "administrative_area_level_2",
        "postal_town",
    ],
    "ID": [
        "administrative_area_level_4",  # Bali etc.: not tiny village, not regency
        "locality",
        "sublocality",
        "administrative_area_level_3",
        "administrative_area_level_2",
        "neighborhood",
        "postal_town",
    ],
}


def _detect_country_code(data: dict) -> Optional[str]:
    """Return ISO country code (e.g. IN, ES, ID) from the first result that has one."""
    for result in data.get("results", []):
        for comp in result.get("address_components", []):
            if "country" in comp.get("types", []):
                code = (comp.get("short_name") or "").strip()
                if code:
                    return code
    return None


def _get_name_from_result_general(result: dict, country_code: Optional[str] = None) -> Optional[str]:
    """
    Extract best name by type priority. Uses jurisdiction override when provided
    (e.g. Spain → admin3 first, Indonesia → admin4 first), else default order.
    """
    type_priority = TYPE_PRIORITY_BY_COUNTRY.get(
        country_code.upper() if country_code else None,
        DEFAULT_TYPE_PRIORITY,
    )
    for ptype in type_priority:
        for comp in result.get("address_components", []):
            types = comp.get("types", [])
            if ptype in types:
                name = (comp.get("long_name") or "").strip()
                if _is_valid_display_name(name):
                    return name
    return None


def extract_best_name(data: dict, lat: float, lng: float, debug: bool = False) -> str:
    """
    Resolve the best location name from geocode data.
    - Ranks results by containment of (lat,lng) and specificity (smaller area, better location_type).
    - In ACT: only consider results that are in ACT; use locality (suburb) if present, else neighborhood (district).
    - Elsewhere: use locality, then sublocality, then admin levels, etc.
    - Output goes to console and clipboard; UI.Vision reads from clipboard.
    """
    lat = float(lat)
    lng = float(lng)
    results = data.get("results", [])
    if not results:
        return "Unknown"

    # If any result is in ACT, use only ACT results and ACT semantics (suburb = locality, district = neighborhood).
    in_act = any(_is_act_result(r) for r in results)
    country_code = _detect_country_code(data) if not in_act else None

    # When a containing district (neighborhood) exists: deprioritize plus_code when its locality is not
    # the district's suburb (e.g. Yarralumla vs Canberra Central); don't deprioritize when locality
    # matches the district (Molonglo in Molonglo Valley). Also prefer district over "wrong" locality
    # (e.g. Tuggeranong over Hume when point is in district outside suburb).
    act_has_containing_neighborhood = False
    act_containing_neighborhood_names: List[str] = []
    act_has_containing_real_suburb = False
    if in_act:
        for r in results:
            if not _is_act_result(r):
                continue
            geom = r.get("geometry", {})
            b = geom.get("bounds") or geom.get("viewport")
            contains_pt = b and _bounds_contain_point(b, lat, lng)
            if _result_has_neighborhood_only(r) and contains_pt:
                act_has_containing_neighborhood = True
                name = _result_neighborhood_name(r)
                if name and name not in act_containing_neighborhood_names:
                    act_containing_neighborhood_names.append(name)
            if contains_pt and _result_has_locality(r):
                t = r.get("types", [])
                if _result_is_plus_code_only(r) or "postal_code" in t:
                    continue
                act_has_containing_real_suburb = True

    # Sort so the best-matching result is first. ACT and India: deprioritize plus_code-only results.
    sorted_results = sorted(
        results,
        key=lambda r: _result_sort_key(
            r, lat, lng,
            in_act=in_act,
            country_code=country_code,
            act_has_containing_neighborhood=act_has_containing_neighborhood,
            act_containing_neighborhood_names=act_containing_neighborhood_names,
            act_has_containing_real_suburb=act_has_containing_real_suburb,
        ),
    )
    if in_act:
        candidates = [r for r in sorted_results if _is_act_result(r)]
        for result in candidates:
            name = _get_name_from_result_act(result)
            if name:
                return name.strip()
        return "Unknown"

    for result in sorted_results:
        name = _get_name_from_result_general(result, country_code=country_code)
        if name:
            return name.strip()

    # No usable component in any result (e.g. only plus_code with no locality).
    return "Unknown"


def resolve_location(lat: float, lng: float, api_key: str, debug=False) -> str:
    data = fetch_geocode(lat, lng, api_key, debug)
    return extract_best_name(data, lat, lng, debug)


def resolve_location_from_data(data: dict, lat: float, lng: float, debug: bool = False) -> str:
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

        # Skip cases with empty or non-numeric lat/lng (e.g. placeholder test data).
        try:
            if lat is None or lng is None or str(lat).strip() == "" or str(lng).strip() == "":
                raise ValueError("empty lat/lng")
            float(lat)
            float(lng)
        except (ValueError, TypeError):
            print(f"Test {i:02} SKIP (invalid or empty lat/lng; add coordinates and geocode_json)")
            skipped += 1
            continue

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

        # Normalise: strip and case-insensitive so "Mopa" / "MOPA" and "Ellis Beach " match
        if (name or "").strip().lower() == (expected or "").strip().lower():
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