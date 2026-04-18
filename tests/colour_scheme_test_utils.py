"""Helpers for tests against bundled map marker colour schemes (indices from YAML/schema).

Bundled presets in ``defaults.py`` are edited over time; tests should prefer
:data:`BUNDLED_COLOUR_SCHEME_INDICES` and resolver-driven expectations over
hard-coded hex names or assumptions about a single scheme index.
"""

from __future__ import annotations

from explorer.core.settings_schema_defaults import (
    MAP_MARKER_COLOUR_SCHEME_MAX,
    MAP_MARKER_COLOUR_SCHEME_MIN,
)

BUNDLED_COLOUR_SCHEME_INDICES: tuple[int, ...] = tuple(
    range(MAP_MARKER_COLOUR_SCHEME_MIN, MAP_MARKER_COLOUR_SCHEME_MAX + 1)
)


def leaflet_rgb_csv_from_hex_rrggbb(normalized_hex: str) -> str:
    """``#RRGGBB`` from resolvers → ``r,g,b`` substring used in Folium/Leaflet ``rgb()`` output."""
    h = normalized_hex.strip().removeprefix("#")
    if len(h) != 6:
        msg = f"expected #RRGGBB, got {normalized_hex!r}"
        raise ValueError(msg)
    return f"{int(h[0:2], 16)},{int(h[2:4], 16)},{int(h[4:6], 16)}"


def first_bundled_scheme_index_with_nine_cluster_tiers() -> int | None:
    """Return the first bundled index whose ``tier_icon_hex`` has length nine, or ``None``."""
    from explorer.app.streamlit.defaults import active_map_marker_colour_scheme

    for idx in BUNDLED_COLOUR_SCHEME_INDICES:
        sch = active_map_marker_colour_scheme(idx)
        v = sch.all_locations.cluster.tier_icon_hex
        if v is not None and len(v) == 9:
            return idx
    return None
