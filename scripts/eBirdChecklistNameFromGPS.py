#!/usr/bin/env python3

import sys
import json
from collections import Counter
from typing import Dict, List, Tuple, Optional

import requests
import pyperclip

# ----------------- Config / constants -----------------

CANBERRA_FOCUS = True

CANBERRA_REGIONS = [
    # -- Urban districts
    "Belconnen",
    "Canberra Central",
    "Gungahlin",
    "Molonglo Valley",
    "Tuggeranong",
    "Weston Creek",
    "Woden Valley",
    # -- Rural districts
    "Booth",
    "Coree",
    "Cotter River",
    "Majura",
    "Molonglo Valley",
    "Naas",
    "Paddys River",
    "Rendezvous Creek",
    "Stromlo",
    "Uriarra",
]

CANBERRA_SUBURBS = [
    "Acton", "Ainslie", "Amaroo","Aranda",
    "Banks", "Barton", "Beard", "Belconnen", "Bonner", "Braddon", "Bruce",
    "Calwell", "Campbell", "Canberra Airport", "Chapman", "Charnwood", "Chifley", "Conder", "Cook", "Curtin",
    "Deakin", "Dickson", "Downer", "Duffy", "Dunlop",
    "Evatt",
    "Fadden", "Farrer", "Fisher", "Florey", "Flynn", "Forde", "Forrest", "Franklin", "Fraser", "Fyshwick",
    "Garran", "Gilmore", "Giralang", "Gordon", "Gowrie", "Greenway", "Griffith",
    "Hackett", "Harman", "Harrison", "Hawker", "Higgins", "Holder", "Holt", "Hughes", "Hume",
    "Isaacs", "Isabella Plains",
    "Kaleen", "Kambah", "Kingston", "Latham", "Lawson", "Lyneham", "Lyons",
    "Macarthur", "Macgregor", "Macquarie", "Majura", "Manuka", "Mawson", "McKellar", "Melba", "Monash",
    "Narrabundah", "Ngunnawal", "Nicholls",
    "O'Connor", "O'Malley", "Oxley", "Page",
    "Palmerston", "Parkes", "Pearce", "Phillip", "Pialligo",
    "Red Hill", "Reid", "Rivett",
    "Scullin", "Spence", "Stirling", "Symonston",
    "Taylor", "Tharwa", "Theodore", "Torrens", "Turner",
    "Watson", "Weetangera", "Weston", "Whitlam", "Wright", "Wanniassa", "Yarralumla",
]

PREFERRED_TYPES = [
    "neighborhood",
    "sublocality",
    "locality",
    "postal_town",
    "administrative_area_level_4",
    "administrative_area_level_3",
    "administrative_area_level_2",
    "administrative_area_level_1",
    "country",
]


# ----------------- Core helpers -----------------

def load_api_key() -> str:
    try:
        from config_secret import GOOGLE_API_KEY
    except ImportError:
        from config_template import GOOGLE_API_KEY
    return GOOGLE_API_KEY


def parse_gps_arg_or_clipboard(argv: List[str]) -> Tuple[str, str, bool]:
    """
    GPS source priority:
      1. Positional arguments (ignoring flags starting with '--'):
         - "lat,lon" or "lat, lon" as a single arg
         - or lat lon as two separate args
      2. Clipboard if no positional args.

    Returns:
        lat_str, lon_str, use_clipboard
    """
    args = argv[1:]

    # Treat only '--something' as flags; allow negative numbers like '-35.2' as positional
    positional = [a for a in args if not a.startswith("--")]

    if positional:
        # We are using arguments -> do NOT touch clipboard on output
        use_clipboard = False

        if len(positional) == 1:
            # Single arg like "lat,lon" or "lat, lon"
            gps_raw = positional[0]
            try:
                lat_str, lon_str = [s.strip() for s in gps_raw.split(",")]
            except ValueError:
                print("❌ Invalid format. Expected: 'lat, lon' in single argument.")
                sys.exit(1)
        else:
            # Two or more positionals: treat first two as lat and lon
            lat_str = positional[0].rstrip(",")
            lon_str = positional[1].lstrip(",")
    else:
        # No positional args – fall back to clipboard, and update it later
        use_clipboard = True
        gps_raw = pyperclip.paste()
        try:
            lat_str, lon_str = [s.strip() for s in gps_raw.split(",")]
        except ValueError:
            print("❌ Invalid format in clipboard. Expected: lat, lon")
            sys.exit(1)

    # Validate numeric
    try:
        float(lat_str)
        float(lon_str)
    except ValueError:
        print("❌ GPS values are not valid numbers.")
        sys.exit(1)

    return lat_str, lon_str, use_clipboard


def fetch_geocode(lat: str, lon: str, api_key: str) -> Dict:
    url = (
        "https://maps.googleapis.com/maps/api/geocode/json"
        f"?latlng={lat},{lon}&key={api_key}"
    )
    try:
        resp = requests.get(url, timeout=10)
    except requests.RequestException as e:
        print(f"❌ Network error contacting Google Maps API: {e}")
        sys.exit(1)

    try:
        data = resp.json()
    except ValueError:
        print("❌ Failed to parse JSON from Google Maps API.")
        sys.exit(1)

    status = data.get("status", "UNKNOWN")
    if status != "OK":
        print(f"❌ Geocode API returned status: {status}")
        # You could special-case ZERO_RESULTS here if you want
        sys.exit(1)

    return data

# See comment about India related locations further below
def detect_is_india(geocode_data: Dict) -> bool:
    for result in geocode_data.get("results", []):
        for comp in result.get("address_components", []):
            types = comp.get("types", [])
            if "country" in types:
                if comp.get("short_name") == "IN" or comp.get("long_name") == "India":
                    return True
    return False


def build_candidates(
    geocode_data: Dict,
    q_lat: float,
    q_lon: float,
    is_india: bool,
) -> Tuple[
    List[Tuple[int, str, str]],
    Counter,
    Dict[str, float],
    Optional[str],
    Optional[str],
]:
    """
    Returns:
      - candidates: list of (rank, name, type)
      - locality_counts: name -> count
      - locality_distances: name -> min squared distance
      - chosen_suburb (for Canberra override)
      - chosen_region (for Canberra override)
    """
    candidates: List[Tuple[int, str, str]] = []
    locality_counts: Counter = Counter()
    locality_distances: Dict[str, float] = {}
    chosen_suburb: Optional[str] = None
    chosen_region: Optional[str] = None
    chosen_suburb_d2: Optional[float] = None
    chosen_region_d2: Optional[float] = None

    for result in geocode_data.get("results", []):
        loc = result.get("geometry", {}).get("location", {})
        r_lat = loc.get("lat")
        r_lon = loc.get("lng")
        result_types = set(result.get("types", []))
        is_plus_code_result = "plus_code" in result_types

        d2 = None
        if isinstance(r_lat, (int, float)) and isinstance(r_lon, (int, float)):
            d2 = (q_lat - r_lat) ** 2 + (q_lon - r_lon) ** 2

        for comp in result.get("address_components", []):
            types = comp.get("types", [])
            name = comp.get("long_name")

            # Only trust locality from "real" results (not plus_code; optionally not postal_code)
            if "locality" in types and not is_plus_code_result:
                # existing locality_counts / locality_distances logic
                locality_counts[name] += 1
                prev = locality_distances.get(name)
                if prev is None or d2 < prev:
                    locality_distances[name] = d2                        

            # Canberra-specific tracking (choose closest suburb/region, not last seen)
            # Track suburb
            if "locality" in types and name in CANBERRA_SUBURBS and not is_plus_code_result:
                if d2 is None:
                    if chosen_suburb is None:
                        chosen_suburb = name
                        chosen_suburb_d2 = None
                else:
                    if chosen_suburb_d2 is None or d2 < chosen_suburb_d2:
                        chosen_suburb = name
                        chosen_suburb_d2 = d2

            # Track region
            if "neighborhood" in types and name in CANBERRA_REGIONS:
                if d2 is None:
                    if chosen_region is None:
                        chosen_region = name
                        chosen_region_d2 = None
                else:
                    if chosen_region_d2 is None or d2 < chosen_region_d2:
                        chosen_region = name
                        chosen_region_d2 = d2

            # General candidate list
            for p_type in PREFERRED_TYPES:
                if p_type in types:
                    if is_india and p_type in ("neighborhood", "sublocality"):
                        # Ignore hyper-local levels in India
                        continue
                    candidates.append((PREFERRED_TYPES.index(p_type), name, p_type))
                    break

    return candidates, locality_counts, locality_distances, chosen_suburb, chosen_region


def compute_best_locality(
    locality_counts: Counter,
    locality_distances: Dict[str, float],
) -> Optional[str]:
    """
    Best locality by:
      1. Highest frequency
      2. If tie, smallest distance to query
    """
    if not locality_counts:
        return None

    most_common = locality_counts.most_common()
    top_count = most_common[0][1]
    tied = [name for name, c in most_common if c == top_count]

    if len(tied) == 1:
        return tied[0]

    best_name = None
    best_d2 = float("inf")
    for name in tied:
        d2 = locality_distances.get(name)
        if d2 is not None and d2 < best_d2:
            best_d2 = d2
            best_name = name

    return best_name if best_name is not None else tied[0]


def choose_best_name(
    candidates: List[Tuple[int, str, str]],
    locality_counts: Counter,
    locality_distances: Dict[str, float],
    chosen_suburb: Optional[str],
    chosen_region: Optional[str],
) -> Tuple[str, str]:
    """
    Decide final chosen_name and optional override_note.
    """
    override_note = ""

    # Canberra override hierarchy:
    # suburb → district/region → fallback
    if CANBERRA_FOCUS:

        if chosen_suburb:
            override_note = f"🎯 Canberra suburb override: {chosen_suburb}"
            return chosen_suburb, override_note

        if chosen_region:
            override_note = f"🎯 ACT district override: {chosen_region}"
            return chosen_region, override_note

    # Global best locality (frequency then distance)
    best_locality = compute_best_locality(locality_counts, locality_distances)

    # Fallback: first ranked candidate
    candidates.sort(key=lambda x: x[0])
    candidate_name = candidates[0][1] if candidates else "Unknown"
    chosen_name = candidate_name
    return chosen_name, override_note


# ----------------- Main -----------------

def main() -> None:
    # Flags:
    show_json = "--json" in sys.argv or "--debug" in sys.argv
    show_rich = "--rich" in sys.argv or "--debug" in sys.argv
    show_candidates = "--candidates" in sys.argv or "--debug" in sys.argv

    lat_str, lon_str, use_clipboard = parse_gps_arg_or_clipboard(sys.argv)
    q_lat = float(lat_str)
    q_lon = float(lon_str)

    api_key = load_api_key()
    data = fetch_geocode(lat_str, lon_str, api_key)

    # 1) JSON layer
    if show_json:
        print("==== Geocode JSON ====")
        print(json.dumps(data, indent=2))
        print("======================\n")

    # Indian results had to much detail and I wanted to make the results zoom out just a bit
    # Basically it would name the location after the smallest village/hamlet when just the
    # slightly bigger regional area would work nicely.  This flag is part of that logic.  All 
    # the India logic should be removed at a re-factor I'm about to do and this an other Indian 
    # logic can then probably be removed.
    is_india = detect_is_india(data)

    (
        candidates,
        locality_counts,
        locality_distances,
        chosen_suburb,
        chosen_region,
    ) = build_candidates(data, q_lat, q_lon, is_india)

    # 2) Rich candidate table (ordered view)
    #    This is your usual semi-processed "localities" view.
    candidates.sort(key=lambda x: x[0])
    if show_rich:
        print("📦 Candidate address components:")
        for i, (rank, name, tag) in enumerate(candidates, start=1):
            print(f" {i:>2}. {name:<25} ({tag})")
        print("")

    # 3) Candidate / locality decision debug
    if show_candidates:
        print("==== Candidate / locality debug ====")
        if locality_counts:
            print("Locality counts:")
            for name, count in locality_counts.most_common():
                print(f"  {name}: {count}")
        else:
            print("  (no localities found)")

        if locality_distances:
            print("\nLocality distances (squared degrees):")
            for name, d2 in sorted(locality_distances.items(), key=lambda x: x[1]):
                print(f"  {name}: {d2:.10f}")
        best_loc = compute_best_locality(locality_counts, locality_distances)
        print(f"\nBest locality (freq + distance): {best_loc}")
        if CANBERRA_FOCUS:
            print(f"Canberra suburb candidate: {chosen_suburb}")
            print(f"Canberra region candidate: {chosen_region}")
        print("===============================\n")

    chosen_name, override_note = choose_best_name(
        candidates,
        locality_counts,
        locality_distances,
        chosen_suburb,
        chosen_region,
    )

    # If rich and/or candidates printed, and a Canberra override applied,
    # it's still useful to see the note once more:
    if override_note and not show_rich and not show_candidates:
        # Only print it here if it hasn't already appeared above
        print(override_note)

    output = f"{chosen_name} ( {lat_str}, {lon_str} )"

    # Only write to clipboard if GPS came from clipboard
    if use_clipboard:
        pyperclip.copy(output)

    print(output)


if __name__ == "__main__":
    main()