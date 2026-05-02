"""
eBird taxonomy lookup for building species and lifelist URLs from common names.

Fetches the taxonomy CSV once and provides COMMON_NAME -> SPECIES_CODE for CATEGORY == "species"
only, so map and rankings links stay consistent with eBird’s site. No API key required.
Offline or API failure: lookup returns None; callers continue without links.

Locale: pass locale to load_taxonomy() so common names match your eBird export
(e.g. "en_AU" for Australian English: Grey Teal, Willie Wagtail, Common Starling).

For any locale **other than** ``en_US``, we also merge in the ``en_US`` common names for the
same species codes. eBird uses different English names in different regions (e.g. *en_AU*
``Grey Ternlet`` vs *en_US* ``Gray Noddy``, or *en_AU* ``Black Petrel`` vs *en_US*
``Parkinson's Petrel``). Checklist rows may use either wording; merging avoids missing links.

API reference: https://documenter.getpostman.com/view/664302/S1ENwy59
"""

import csv
import io
from urllib.error import URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

_TAXONOMY_BASE = "https://api.ebird.org/v2/ref/taxonomy/ebird"
# In-memory cache: common_name (strip) -> species_code. None if not loaded or load failed.
_common_to_code: dict[str, str] | None = None


def _taxonomy_csv_to_lookup(raw: str) -> dict[str, str] | None:
    """Parse taxonomy CSV body into common_name -> species_code for category ``species`` only."""
    reader = csv.DictReader(io.StringIO(raw))
    if not reader.fieldnames:
        return None
    field_lower = {f.strip().lower(): f for f in reader.fieldnames}
    common_key = field_lower.get("common_name") or field_lower.get("common name")
    code_key = field_lower.get("species_code") or field_lower.get("species code")
    category_key = field_lower.get("category")
    if not common_key or not code_key or not category_key:
        return None
    lookup: dict[str, str] = {}
    for row in reader:
        cat = (row.get(category_key) or "").strip().lower()
        if cat != "species":
            continue
        common = (row.get(common_key) or "").strip()
        code = (row.get(code_key) or "").strip()
        if common and code:
            lookup[common] = code
    return lookup


def _fetch_taxonomy_csv(url: str) -> str | None:
    try:
        req = Request(url, headers={"Accept": "text/csv"})
        with urlopen(req, timeout=30) as resp:
            return resp.read().decode("utf-8", errors="replace")
    except (URLError, OSError, TimeoutError):
        return None


def load_taxonomy(locale: str | None = None) -> bool:
    """Fetch eBird taxonomy and build common name -> species_code lookup (species only).

    Call once at startup. On success returns True and
    get_species_url / get_species_lifelist_url will return URLs for species.
    On failure returns False; lookups return None and the UI does not break.

    Args:
        locale: Optional locale code so common names match your eBird export.
            Examples: "en_AU" (Australian), "en_GB" (British), "" or None for API default (en_US).
            See eBird API 2.0 reference for supported codes.
            Non-``en_US`` locales load that CSV and merge **en_US** names so alternate regional
            labels for the same species code still resolve (see module docstring).

    Returns:
        True if taxonomy loaded and cache is populated, False otherwise.
    """
    global _common_to_code
    _common_to_code = None
    loc_clean = str(locale).strip() if locale else ""
    primary_url = _TAXONOMY_BASE
    if loc_clean:
        primary_url = f"{_TAXONOMY_BASE}?{urlencode({'locale': loc_clean})}"
    raw_primary = _fetch_taxonomy_csv(primary_url)
    if raw_primary is None:
        return False
    primary_lookup = _taxonomy_csv_to_lookup(raw_primary)
    if primary_lookup is None:
        return False
    if loc_clean and loc_clean.lower() != "en_us":
        us_url = f"{_TAXONOMY_BASE}?{urlencode({'locale': 'en_US'})}"
        raw_us = _fetch_taxonomy_csv(us_url)
        if raw_us:
            us_lookup = _taxonomy_csv_to_lookup(raw_us)
            if us_lookup:
                _common_to_code = {**us_lookup, **primary_lookup}
                return True
    _common_to_code = primary_lookup
    return True


def _hyphen_space_lookup_variants(name: str) -> tuple[str, ...]:
    """Alternate spellings swapping spaces and hyphens between word parts.

    eBird uses different conventions by locale (e.g. *en_US* ``Jacky-winter`` vs *en_AU*
    ``Jacky Winter``). Checklist exports follow the observer's regional names, which may not
    match :func:`load_taxonomy`'s locale, so we try both separator forms before giving up.

    Note: swapping ``' '`` → ``'-'`` preserves per-word casing, so ``Jacky Winter`` becomes
    ``Jacky-Winter`` while the CSV may use ``Jacky-winter``; :func:`_code_for_common_name`
    falls back to normalized matching when direct key lookups miss.
    """
    key = str(name).strip()
    alts: list[str] = []
    if " " in key:
        alts.append(key.replace(" ", "-"))
    if "-" in key:
        alts.append(key.replace("-", " "))
    return tuple(alts)


def _normalize_common_name_for_lookup(name: str) -> str:
    """Collapse hyphen vs space and case so two spellings of the same name compare equal.

    Needed when naive space-to-hyphen substitution yields the wrong letter case after a
    hyphen (e.g. ``Jacky-Winter``) while the taxonomy row uses eBird's casing (e.g.
    ``Jacky-winter``), or when locale and export strings disagree on spaces vs hyphens.
    """
    s = str(name).strip().replace("-", " ")
    while "  " in s:
        s = s.replace("  ", " ")
    return s.casefold()


def _code_by_normalized_common_name(common_name: str) -> str | None:
    """Linear scan: same species may differ only by hyphen/spaces/casing in the CSV vs query."""
    if _common_to_code is None:
        return None
    target = _normalize_common_name_for_lookup(common_name)
    if not target:
        return None
    for k, code in _common_to_code.items():
        if _normalize_common_name_for_lookup(k) == target:
            return code
    return None


def _base_common_name(common_name: str) -> str | None:
    """Strip trailing ' (Subspecies)' from common name so subspecies link to main species page.

    e.g. 'Eastern Barn Owl (Eastern)' -> 'Eastern Barn Owl'. Returns None if no parenthetical suffix.
    """
    s = str(common_name).strip()
    if " (" in s and s.endswith(")"):
        base = s[: s.rindex(" (")].strip()
        if base:
            return base
    return None


def _code_for_common_name(common_name: str) -> str | None:
    """Return species_code for this common name, or None.

    Tries exact match first. If not found and name looks like a subspecies (trailing ' (X)'),
    tries the base common name so e.g. 'Eastern Barn Owl (Eastern)' links to Eastern Barn Owl.
    """
    if _common_to_code is None or not common_name:
        return None
    key = str(common_name).strip()
    code = _common_to_code.get(key)
    if code:
        return code
    for alt in _hyphen_space_lookup_variants(key):
        code = _common_to_code.get(alt)
        if code:
            return code
    code = _code_by_normalized_common_name(key)
    if code:
        return code
    base = _base_common_name(common_name)
    if base:
        code = _common_to_code.get(base)
        if code:
            return code
        for alt in _hyphen_space_lookup_variants(base):
            code = _common_to_code.get(alt)
            if code:
                return code
        code = _code_by_normalized_common_name(base)
        if code:
            return code
    return None


def get_species_url(common_name: str) -> str | None:
    """Return eBird species page URL for this common name, or None if not a linked species."""
    code = _code_for_common_name(common_name)
    if not code:
        return None
    return f"https://ebird.org/species/{code}"


def get_species_lifelist_url(common_name: str) -> str | None:
    """Return eBird lifelist page URL for this species (lifelist?spp=CODE), or None."""
    code = _code_for_common_name(common_name)
    if not code:
        return None
    return f"https://ebird.org/lifelist?spp={code}"


def get_species_and_lifelist_urls(common_name: str) -> tuple[str | None, str | None]:
    """Return (species_url, lifelist_url) in one lookup. Use for tables that need both (e.g. Most checklists)."""
    code = _code_for_common_name(common_name)
    if not code:
        return (None, None)
    return (f"https://ebird.org/species/{code}", f"https://ebird.org/lifelist?spp={code}")
