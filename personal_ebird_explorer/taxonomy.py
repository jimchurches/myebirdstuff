"""
eBird taxonomy lookup for species links (refs #56).

Fetches the eBird taxonomy once and provides COMMON_NAME -> SPECIES_CODE
for CATEGORY == "species" only. Used to build eBird species and lifelist URLs.
No API key required. Offline or API failure: lookup returns None; notebook continues.

Locale: pass locale to load_taxonomy() so common names match your eBird export
(e.g. "en_AU" for Australian English: Grey Teal, Willie Wagtail, Common Starling).
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


def load_taxonomy(locale: str | None = None) -> bool:
    """Fetch eBird taxonomy and build common name -> species_code lookup (species only).

    Call once at startup (e.g. notebook data prep). On success returns True and
    get_species_url / get_species_lifelist_url will return URLs for species.
    On failure returns False; lookups return None and the notebook does not break.

    Args:
        locale: Optional locale code so common names match your eBird export.
            Examples: "en_AU" (Australian), "en_GB" (British), "" or None for API default (en_US).
            See eBird API 2.0 reference for supported codes.

    Returns:
        True if taxonomy loaded and cache is populated, False otherwise.
    """
    global _common_to_code
    _common_to_code = None
    url = _TAXONOMY_BASE
    if locale and str(locale).strip():
        url = f"{_TAXONOMY_BASE}?{urlencode({'locale': locale.strip()})}"
    try:
        req = Request(url, headers={"Accept": "text/csv"})
        with urlopen(req, timeout=30) as resp:
            raw = resp.read().decode("utf-8", errors="replace")
    except (URLError, OSError, TimeoutError):
        return False
    reader = csv.DictReader(io.StringIO(raw))
    if not reader.fieldnames:
        return False
    # Normalize column names (API may use COMMON_NAME or common_name, etc.)
    field_lower = {f.strip().lower(): f for f in reader.fieldnames}
    common_key = field_lower.get("common_name") or field_lower.get("common name")
    code_key = field_lower.get("species_code") or field_lower.get("species code")
    category_key = field_lower.get("category")
    if not common_key or not code_key or not category_key:
        return False
    lookup = {}
    for row in reader:
        cat = (row.get(category_key) or "").strip().lower()
        if cat != "species":
            continue
        common = (row.get(common_key) or "").strip()
        code = (row.get(code_key) or "").strip()
        if common and code:
            lookup[common] = code
    _common_to_code = lookup
    return True


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
    base = _base_common_name(common_name)
    if base:
        return _common_to_code.get(base)
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
