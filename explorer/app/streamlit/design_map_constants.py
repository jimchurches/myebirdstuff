"""
Labels and ``help=`` text for :mod:`explorer.app.streamlit.design_map_app`.

``help`` strings are attribute / session key names only (developer mapping).
"""

from __future__ import annotations

from explorer.presentation.design_map_preview import (
    MAP_SCOPE_ALL,
    MAP_SCOPE_ALL_LOCATIONS,
    MAP_SCOPE_FAMILY_LOCATIONS,
    MAP_SCOPE_LIFER_LOCATIONS,
    MAP_SCOPE_SPECIES_LOCATIONS,
)

PREVIEW_SCOPE_LABELS: dict[str, str] = {
    MAP_SCOPE_ALL: "All maps",
    MAP_SCOPE_ALL_LOCATIONS: "All locations",
    MAP_SCOPE_SPECIES_LOCATIONS: "Species locations",
    MAP_SCOPE_LIFER_LOCATIONS: "Lifer locations",
    MAP_SCOPE_FAMILY_LOCATIONS: "Family locations",
}

# Sidebar labels for family density rows (match production legend: 1 / 2–3 / 4–5 / 6+ species).
FAMILY_DENSITY_BAND_UI_LABELS: tuple[str, ...] = (
    "Band 1",
    "Band 2-3",
    "Band 4-5",
    "Band 6+",
)

# Tooltips: underlying ``MapMarkerColourScheme`` field or Streamlit session key.
H_PRESET = "design_scheme_pick"
H_BASEMAP = "design_map_style"
H_HEIGHT = "design_height_px"
H_RADIUS = "circle_marker_radius_px"
H_SW_VISIT = "visit_stroke_weight"
H_SW_FAM = "base_stroke_weight"
H_SW_FAM_HL = "highlight_stroke_weight"
H_FO_ALL = "visit_fill_opacity_all_locations"
H_FO_EMPH = "visit_fill_opacity_emphasis"
H_FO_FAMILY = "circle_marker_fill_opacity"
H_HEX_DE = "marker_location_visit_edge_hex"
H_HEX_DF = "marker_location_visit_fill_hex"
H_HEX_SE = "marker_species_edge_hex"
H_HEX_SF = "marker_species_fill_hex"
H_HEX_LE = "marker_lifer_edge_hex"
H_HEX_LF = "marker_lifer_fill_hex"
H_HEX_LSE = "marker_last_seen_edge_hex"
H_HEX_LSF = "marker_last_seen_fill_hex"
H_HEX_FF = "density_fill_hex[i]"
H_HEX_FS = "density_stroke_hex[i]"
H_HEX_FAM_HL = "highlight_stroke_hex"
