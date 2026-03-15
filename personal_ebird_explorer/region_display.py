"""
Display helpers: convert region codes to human-readable names at render time.

Uses pycountry for ISO country and subdivision (state/province) names.
Used by the notebook when building rankings table HTML. (refs #43)
"""

import pandas as pd

try:
    import pycountry
except ImportError:
    pycountry = None


def country_for_display(code):
    """Convert ISO alpha-2 country code to common name. Fallback to code if unknown or lib missing."""
    if code is None or pd.isna(code) or str(code).strip() == "":
        return ""
    if pycountry is None:
        return str(code).strip()
    c = pycountry.countries.get(alpha_2=str(code).strip().upper())
    return c.name if c else str(code).strip()


def state_for_display(country_code, state_code):
    """Convert country+state codes to subdivision name. Fallback to state code if unknown or lib missing."""
    if state_code is None or pd.isna(state_code) or str(state_code).strip() == "":
        return ""
    state_s = str(state_code).strip()
    country_s = (
        str(country_code).strip().upper()
        if country_code and not pd.isna(country_code)
        else ""
    ) or ""
    if not country_s or pycountry is None:
        return state_s
    code = f"{country_s}-{state_s}"
    sub = pycountry.subdivisions.get(code=code)
    return sub.name if sub else state_s
