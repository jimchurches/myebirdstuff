#!/usr/bin/env python3

"""
eBirdChecklistNameFromGPS.py

Resolves GPS coordinates into an eBird-friendly location name. Output is
printed to the console and copied to the clipboard (for UI.Vision macros).

Output format:
    Location Name ( lat, lng )

Requires a Google Geocoding API key in config_secret.py or config_template.py
(as GOOGLE_API_KEY).

Arguments / parameters
----------------------
  coords (positional, optional)
      One or more tokens: lat,lng or lat lng, or full formatted text containing
      two numbers. Examples: -35.327454,148.860410  or  -35.327454 148.860410
      or "Uriarra Village ( -35.327454, 148.860410 )".

  --clipboard
      Read coordinate text from the clipboard instead of command line.

  --debug
      Print ranking (order and sort key) to stderr so you can see why a result
      was chosen. Use when tuning logic or diagnosing a wrong name.

  --includejson
      Only has effect with --debug. Also print the raw Geocoding API JSON to
      stderr.

  --testfile PATH
      Run tests from a JSON file. Each case should have lat, lng, expected, and
      (unless --live) geocode_json. Summary and per-test pass/fail are printed.

  --live
      Only with --testfile. Ignore embedded geocode_json and call the API for
      each test. Use to verify behaviour against current API responses.

  --export-test
      Fetch the API for the given lat/lng, resolve the name, and print a
      JSON snippet suitable for pasting into the test file. Also copies to
      clipboard. Provide coordinates via coords or --clipboard.

Examples
--------
  # Single point from command line
  python eBirdChecklistNameFromGPS.py -35.327454,148.860410
  python eBirdChecklistNameFromGPS.py -35.327454 148.860410

  # Coordinates from clipboard
  python eBirdChecklistNameFromGPS.py --clipboard

  # Run test file (embedded geocode data)
  python eBirdChecklistNameFromGPS.py --testfile scripts/gps_checklistName_testing.json

  # Run test file against live API
  python eBirdChecklistNameFromGPS.py --testfile scripts/gps_checklistName_testing.json --live

  # Debug: see why a name was chosen
  python eBirdChecklistNameFromGPS.py -35.327454 148.860410 --debug

  # Export a new test case (paste into gps_checklistName_testing.json, set expected/notes)
  python eBirdChecklistNameFromGPS.py -35.362321 149.167076 --export-test

ACT (Australian Capital Territory)
----------------------------------
  In Google data, ACT suburbs are "locality" and districts are "neighborhood"
  (reversed from many other jurisdictions). The script prefers the geographically
  best-matching result, then uses locality (suburb) if present else neighborhood
  (district). Plus_code-only results are deprioritised so that open land (e.g. a
  reserve in Belconnen) yields the district (Belconnen) rather than a grid cell
  labelled with a neighbouring suburb.

Jurisdictions
-------------
  ACT has a dedicated branch in the sort key and naming logic because it is the
  primary use case and Google's reverse-geocode data for the ACT has specific
  quirks. Other areas use generic logic: country detection, type-priority by
  country (e.g. Spain, Indonesia), and sort by containment, area, and distance.
  A future refactor could move rules into a config file (e.g. JSON) for more
  jurisdictions; that is not implemented yet.

Development / credits
---------------------
  This script was developed largely with Cursor (https://cursor.com), an
  AI-assisted editor for writing, refactoring, and debugging code. Cursor is
  a legitimate and effective way to develop software; if you find this code
  useful and want similar help on your own projects, it is free to try.
"""

import argparse
import json
import re
import sys
from datetime import date
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


def fetch_geocode(lat: float, lng: float, api_key: str, debug: bool = False, include_json: bool = False) -> dict:
    url = "https://maps.googleapis.com/maps/api/geocode/json"
    params = {
        "latlng": f"{lat},{lng}",
        "key": api_key,
    }
    response = requests.get(url, params=params)
    data = response.json()

    if debug and include_json:
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
    act_min_neighborhood_area: Optional[float] = None,
    act_any_wrong_locality_result: bool = False,
    default_containing_pure_locality_names: Optional[set] = None,
    default_min_containing_pure_locality_area: Optional[float] = None,
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
        # Locality is "wrong" when from plus_code, route, or establishment/POI that's across the border;
        # also street_address with very small viewport (single building) when point is in another district.
        is_establishment_or_poi = "establishment" in result_types or "point_of_interest" in result_types
        route_result = "route" in result_types
        small_street = is_specific_address and area < 0.0001  # single-building viewport
        locality_wrong_for_district = (
            has_locality and act_has_containing_neighborhood and locality_name is not None
            and not any(locality_name in nn for nn in neighborhood_names)
            and (plus_only or is_establishment_or_poi or route_result or small_street)
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
        # Postal_code results can still supply a valid locality (e.g. Harman in 2600); prefer it over
        # neighborhood unless a containing district we want should win (list) or the neighborhood is
        # more specific (smaller area), e.g. Jerrabomberra over Harman when point is in Jerrabomberra.
        ACT_DISTRICTS_OVER_POSTCODE_LOCALITY = ("Canberra Central", "Weston Creek", "Cotter River", "Belconnen", "Stromlo")
        postcode_localities = result.get("postcode_localities") or []
        postcode_preferred_over_district = (
            act_has_containing_neighborhood and any(nn in ACT_DISTRICTS_OVER_POSTCODE_LOCALITY for nn in neighborhood_names)
        )
        neighborhood_more_specific_than_postcode = (
            act_min_neighborhood_area is not None and area > act_min_neighborhood_area
        )
        # Prefer neighborhood over postcode only when some result had wrong locality (route/establishment/etc.);
        # otherwise keep preferring postcode locality (e.g. Harman over Jerrabomberra when point is in Harman).
        prefer_neighborhood_over_postcode = (
            act_has_containing_neighborhood and neighborhood_more_specific_than_postcode and act_any_wrong_locality_result
        )
        valid_postcode_locality = (
            has_locality and "postal_code" in result_types and locality_name in postcode_localities
            and not postcode_preferred_over_district
            and not prefer_neighborhood_over_postcode
        )
        is_specific_effective = is_specific_address or (plus_only and dist_sq < 1e-10 and act_has_containing_real_suburb)
        return (
            0 if has_name else 1,
            0 if contains else 1,
            1 if locality_wrong_for_district else 0,  # prefer district over wrong locality (34, 42, 43)
            plus_penalty,
            0 if is_specific_effective else 1,
            0 if suburb_sized_locality else 1,  # suburb first
            0 if valid_postcode_locality else 1,  # then postcode locality (e.g. Harman) over district
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

    # India (IN): use simple key (no route/locality preference) so plus_code/locality wins over route at borders.
    if country_code and country_code.upper() == "IN":
        return (0 if has_name else 1, 0 if contains else 1, area, -type_rank)

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

    # When we have the set of containing pure locality names (default sort only): prefer pure locality
    # over route when they disagree (Norseman over Fraser Range), and prefer route over other
    # localities when the route matches a pure locality (Stirling Range from route over Cranbrook).
    if default_containing_pure_locality_names is None:
        return (0 if has_name else 1, 0 if contains else 1, area, -type_rank)

    result_types = result.get("types", [])
    route_locality = _result_locality_name(result) if "route" in result_types else None
    route_matches_pure = (
        route_locality is not None and route_locality in default_containing_pure_locality_names
    )
    # Route also "matches" when it contains the point, is more specific (smaller area) than any containing pure locality,
    # and its locality name looks like a park/reserve (so we prefer e.g. Stirling Range National Park over Cranbrook,
    # but do not prefer Fraser Range over Norseman).
    route_looks_like_park = (
        route_locality is not None
        and (
            "National Park" in route_locality
            or " Reserve" in route_locality
            or "State Forest" in route_locality
            or route_locality.endswith(" NP")
        )
    )
    route_more_specific_than_containing = (
        "route" in result_types
        and contains
        and default_min_containing_pure_locality_area is not None
        and area < default_min_containing_pure_locality_area
        and route_looks_like_park
    )
    # 0 = route with matching locality or more specific (best), 1 = pure locality or non-route, 2 = route with non-matching locality
    if "route" in result_types and (route_matches_pure or route_more_specific_than_containing):
        loc_rank = 0
    elif "route" in result_types:
        loc_rank = 2
    else:
        loc_rank = 1
    return (0 if has_name else 1, 0 if contains else 1, loc_rank, area, -type_rank)


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


def _result_debug_summary(result: dict, in_act: bool, country_code: Optional[str]) -> str:
    """One-line summary of result for debug: types and name we'd extract."""
    parts = []
    types = result.get("types", [])
    if types:
        parts.append(",".join(types[:3]))
    if in_act and _is_act_result(result):
        name = _get_name_from_result_act(result)
    else:
        name = _get_name_from_result_general(result, country_code=country_code)
    if name:
        parts.append(f"-> {name}")
    return "  ".join(parts) if parts else "(no name)"


def _print_debug_ranking(
    sorted_results: list,
    lat: float,
    lng: float,
    in_act: bool,
    country_code: Optional[str],
    act_has_containing_neighborhood: bool,
    act_containing_neighborhood_names: list,
    act_has_containing_real_suburb: bool,
    sort_key_fn,
    chosen_name: Optional[str],
) -> None:
    """Print ranking order and sort keys so user can see why a result was chosen."""
    print("\n=== Ranking (best first) ===", file=sys.stderr)
    for i, r in enumerate(sorted_results[:20], 1):
        key = sort_key_fn(r)
        summary = _result_debug_summary(r, in_act, country_code)
        name = _get_name_from_result_act(r) if (in_act and _is_act_result(r)) else _get_name_from_result_general(r, country_code=country_code)
        print(f"  {i:2}. {name or '(no name)'}  key={key}  [{summary}]", file=sys.stderr)
    print(f"Chosen: {chosen_name or 'Unknown'}", file=sys.stderr)
    if in_act:
        print("(ACT mode: first result with a name from ACT candidates, or fallback to any result)", file=sys.stderr)
    print("", file=sys.stderr)


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

    # Decide ACT vs non-ACT by the "best" result (containment + specificity), not by "any result is ACT".
    # So a point in Uriarra NSW near the ACT border gets Uriarra (NSW) not Coree (ACT) when the API returns both.
    neutral_key = lambda r: _result_sort_key(r, lat, lng, in_act=False, country_code=None)
    sorted_neutral = sorted(results, key=neutral_key)
    preliminary_best = None
    for r in sorted_neutral:
        if _get_name_from_result_general(r, country_code=None):
            preliminary_best = r
            break
    in_act = (
        _is_act_result(preliminary_best)
        if preliminary_best
        else any(_is_act_result(r) for r in results)
    )
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

    # Minimum area among containing neighborhood-only results (for preferring district over postcode when more specific).
    act_min_neighborhood_area: Optional[float] = None
    if in_act and act_has_containing_neighborhood:
        for r in results:
            if not _is_act_result(r) or not _result_has_neighborhood_only(r):
                continue
            geom = r.get("geometry", {})
            b = geom.get("bounds") or geom.get("viewport")
            if not b or not _bounds_contain_point(b, lat, lng):
                continue
            a = _bounds_area(b)
            if act_min_neighborhood_area is None or a < act_min_neighborhood_area:
                act_min_neighborhood_area = a

    # True if any ACT result has "wrong" locality (route/establishment/small street) for the containing district.
    act_any_wrong_locality_result = False
    if in_act and act_has_containing_neighborhood:
        neighborhood_names = act_containing_neighborhood_names or []
        for r in results:
            if not _is_act_result(r):
                continue
            has_loc = _result_has_locality(r)
            loc_name = _result_locality_name(r)
            if not has_loc or loc_name is None or any(loc_name in nn for nn in neighborhood_names):
                continue
            t = r.get("types", [])
            plus_only = _result_is_plus_code_only(r)
            is_poi = "establishment" in t or "point_of_interest" in t
            route_result = "route" in t
            geom = r.get("geometry", {})
            b = geom.get("bounds") or geom.get("viewport")
            area_r = _bounds_area(b) if b else float("inf")
            is_specific = "street_address" in t or "premise" in t
            small_street = is_specific and area_r < 0.0001
            # Only count route/establishment/small_street (not plus_code) so we don't prefer neighborhood
            # over postcode when the only "wrong" result is a plus_code (e.g. test 57 has plus_code Pialligo).
            if is_poi or route_result or small_street:
                act_any_wrong_locality_result = True
                break

    # For default (non-ACT) sort: names from pure locality results, plus names from the most specific
    # containing results (min area) so a route can "match" when it's the best containing result
    # (e.g. Stirling Range from route over Cranbrook). Norseman: plus_code has min area so set stays {Norseman}.
    default_containing_pure_locality_names: Optional[set] = None
    default_min_containing_pure_locality_area: Optional[float] = None
    if not in_act:
        default_containing_pure_locality_names = set()
        for r in results:
            t = r.get("types", [])
            if "locality" not in t or "route" in t:
                continue
            name = _get_name_from_result_general(r, country_code=country_code)
            if name:
                default_containing_pure_locality_names.add(name)
        # Add names from containing results that have the smallest area (so the best-containing result's name is in the set).
        # Prefer non-route min-area results; only add from a route when no non-route min-area had a name.
        # When we already have a containing pure locality, do not add from a route (keeps Norseman over Fraser Range).
        had_containing_pure_locality = len(default_containing_pure_locality_names) > 0
        min_containing_area = None
        for r in results:
            geom = r.get("geometry", {})
            b = geom.get("bounds") or geom.get("viewport")
            if not b or not _bounds_contain_point(b, lat, lng):
                continue
            a = _bounds_area(b)
            if min_containing_area is None or a < min_containing_area:
                min_containing_area = a
        if min_containing_area is not None:
            added_from_min = False
            for r in results:
                geom = r.get("geometry", {})
                b = geom.get("bounds") or geom.get("viewport")
                if not b or not _bounds_contain_point(b, lat, lng):
                    continue
                if _bounds_area(b) > min_containing_area * 1.001:
                    continue
                t = r.get("types", [])
                if "route" in t:
                    continue  # add from non-route min-area results first
                name = _get_name_from_result_general(r, country_code=country_code)
                if name:
                    default_containing_pure_locality_names.add(name)
                    added_from_min = True
            if not added_from_min and not had_containing_pure_locality:
                for r in results:
                    geom = r.get("geometry", {})
                    b = geom.get("bounds") or geom.get("viewport")
                    if not b or not _bounds_contain_point(b, lat, lng):
                        continue
                    if _bounds_area(b) > min_containing_area * 1.001:
                        continue
                    t = r.get("types", [])
                    if "route" not in t:
                        continue
                    name = _result_locality_name(r)
                    if name:
                        default_containing_pure_locality_names.add(name)
                        break
        for r in results:
            t = r.get("types", [])
            if "locality" not in t or "route" in t:
                continue
            geom = r.get("geometry", {})
            b = geom.get("bounds") or geom.get("viewport")
            if not b or not _bounds_contain_point(b, lat, lng):
                continue
            a = _bounds_area(b)
            if default_min_containing_pure_locality_area is None or a < default_min_containing_pure_locality_area:
                default_min_containing_pure_locality_area = a

    # Sort so the best-matching result is first. ACT and India: deprioritize plus_code-only results.
    sort_key_fn = lambda r: _result_sort_key(
        r, lat, lng,
        in_act=in_act,
        country_code=country_code,
        act_has_containing_neighborhood=act_has_containing_neighborhood,
        act_containing_neighborhood_names=act_containing_neighborhood_names,
        act_has_containing_real_suburb=act_has_containing_real_suburb,
        act_min_neighborhood_area=act_min_neighborhood_area,
        act_any_wrong_locality_result=act_any_wrong_locality_result,
        default_containing_pure_locality_names=default_containing_pure_locality_names,
        default_min_containing_pure_locality_area=default_min_containing_pure_locality_area,
    )
    sorted_results = sorted(results, key=sort_key_fn)

    chosen_name = None
    if in_act:
        candidates = [r for r in sorted_results if _is_act_result(r)]
        for result in candidates:
            name = _get_name_from_result_act(result)
            if name:
                chosen_name = name.strip()
                break
        if chosen_name is None:
            # No ACT result had a name (e.g. point is in NSW near ACT—Williamsdale); use best from any result.
            cc = _detect_country_code(data)
            for result in sorted_results:
                name = _get_name_from_result_general(result, country_code=cc)
                if name:
                    chosen_name = name.strip()
                    break
    if chosen_name is None:
        for result in sorted_results:
            name = _get_name_from_result_general(result, country_code=country_code)
            if name:
                chosen_name = name.strip()
                break

    if debug:
        _print_debug_ranking(
            sorted_results, lat, lng, in_act, country_code,
            act_has_containing_neighborhood, act_containing_neighborhood_names, act_has_containing_real_suburb,
            sort_key_fn, chosen_name,
        )

    if chosen_name is not None:
        return chosen_name
    return "Unknown"


def resolve_location(lat: float, lng: float, api_key: str, debug: bool = False, include_json: bool = False) -> str:
    data = fetch_geocode(lat, lng, api_key, debug=debug, include_json=include_json)
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
    # Up to 6 decimal places, no trailing zeros
    lat_str = f"{lat:.6f}".rstrip("0").rstrip(".")
    lng_str = f"{lng:.6f}".rstrip("0").rstrip(".")

    return f"{name} ( {lat_str}, {lng_str} )"


# ------------------------------------------------------------
# Clipboard output
# ------------------------------------------------------------


def copy_to_clipboard(text: str):
    pyperclip.copy(text)


# ------------------------------------------------------------
# Test file runner
# ------------------------------------------------------------


def run_test_file(
    testfile: str, api_key: str, debug: bool = False, live: bool = False, include_json: bool = False
) -> int:
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
        # Basic structural validation (don't crash on junk/blank entries)
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
                name = resolve_location(lat, lng, api_key, debug=debug, include_json=include_json)

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
    parser.add_argument(
        "--debug",
        action="store_true",
        help="Print ranking (order + sort key) so you can see why a result was chosen.",
    )
    parser.add_argument(
        "--includejson",
        action="store_true",
        help="With --debug, also print raw API JSON (default: ranking only).",
    )
    parser.add_argument("--testfile", help="Run a JSON test file.")
    parser.add_argument(
        "--live",
        action="store_true",
        help="For --testfile runs, ignore embedded geocode_json and fetch live from the API.",
    )
    parser.add_argument(
        "--export-test",
        action="store_true",
        help="Output a JSON snippet for the test file (fetches API for given lat/lng). Paste into gps_checklistName_testing.json and fill expected/notes.",
    )

    args, extras = parser.parse_known_args()

    api_key = load_api_key()

    if args.testfile:
        raise SystemExit(
            run_test_file(
                args.testfile,
                api_key=api_key,
                debug=args.debug,
                live=args.live,
                include_json=args.includejson,
            )
        )

    # 1) Get coordinate text from clipboard or argv tokens
    if args.clipboard:
        coord_text = pyperclip.paste()
    else:
        coord_text = " ".join(list(args.coords) + list(extras))
    # If no args were given, fall back to clipboard (so "run with nothing" uses clipboard)
    if (not coord_text or not coord_text.strip()) and not args.coords and not extras:
        coord_text = pyperclip.paste() or ""

    # 2) Parse coordinates (robust to commas/spaces/formatted strings)
    lat, lng, lat_dp, lng_dp = parse_coords_from_text(coord_text)

    if args.export_test:
        # --export-test: fetch API, resolve name, output test-case JSON snippet and copy to clipboard
        data = fetch_geocode(lat, lng, api_key, debug=False)
        name = extract_best_name(data, lat, lng, debug=False)
        country = _detect_country_code(data) or ""
        snippet = {
            "name": name,
            "country": country,
            "lat": str(lat),
            "lng": str(lng),
            "expected": "",
            "v2result": "",
            "notes": "",
            "json_extracted": date.today().strftime("%Y%m%d"),
            "geocode_json": data,
        }
        # Indent whole snippet by 2 spaces so pasted into test file: braces at 2, top-level keys at 4
        raw = json.dumps(snippet, indent=2, ensure_ascii=False)
        snippet_str = "\n".join("  " + line for line in raw.split("\n"))
        copy_to_clipboard(snippet_str)
        print(snippet_str)
        return

    # 3) Resolve + format output (always 6 decimal places for lat/lng in output)
    name = resolve_location(lat, lng, api_key=api_key, debug=args.debug, include_json=args.includejson)
    output = format_location_string(name, lat, lng, 6, 6)

    print(output)
    copy_to_clipboard(output)


# ------------------------------------------------------------

if __name__ == "__main__":
    main()
