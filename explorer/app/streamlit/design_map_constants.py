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

# Tooltips: nested ``MapMarkerColourScheme`` field paths or Streamlit session keys.
H_PRESET = "design_scheme_pick"
H_BASEMAP = "design_map_style"
H_HEIGHT = "design_height_px"
H_RADIUS_DEFAULT = "global_defaults.circle_radius_px"
H_GLOBAL_FILL = "global_defaults.fill_hex"
H_GLOBAL_EDGE = "global_defaults.edge_hex"
H_SW_GLOBAL = "global_defaults.base_stroke_weight"
H_RADIUS_LOCATIONS = "all_locations.radius_override_px"
H_RADIUS_SPECIES = "species_locations.radius_override_px"
H_RADIUS_LIFER_MAP_LIFER = "lifer_locations.lifer_radius_override_px"
H_RADIUS_LIFER_MAP_SUBSPECIES = "lifer_locations.subspecies_radius_override_px"
H_RADIUS_FAMILIES = "family_locations.radius_override_px"
H_SW_VISIT = "all_locations.stroke_weight"
H_SW_SPECIES = "species_locations.stroke_weight_override"
H_SW_LIFER = "lifer_locations.stroke_weight_override"
H_SW_FAM = "family_locations.base_stroke_weight"
H_SW_FAM_HL = "family_locations.highlight_stroke_weight"
H_FO_DEFAULT = "global_defaults.circle_fill_opacity"
H_FO_LOCATIONS = "all_locations.fill_opacity_override"
H_FO_SPECIES = "species_locations.fill_opacity_override"
H_FO_LIFER_MAP_LIFER = "lifer_locations.lifer_fill_opacity_override"
H_FO_LIFER_MAP_SUBSPECIES = "lifer_locations.subspecies_fill_opacity_override"
H_FO_FAMILY = "family_locations.fill_opacity_override"
H_CLUSTER_SMALL_FILL = "all_locations.cluster.colours_hex[0]"
H_CLUSTER_SMALL_BORDER = "all_locations.cluster.colours_hex[1]"
H_CLUSTER_SMALL_HALO = "all_locations.cluster.colours_hex[2]"
H_CLUSTER_MEDIUM_FILL = "all_locations.cluster.colours_hex[3]"
H_CLUSTER_MEDIUM_BORDER = "all_locations.cluster.colours_hex[4]"
H_CLUSTER_MEDIUM_HALO = "all_locations.cluster.colours_hex[5]"
H_CLUSTER_LARGE_FILL = "all_locations.cluster.colours_hex[6]"
H_CLUSTER_LARGE_BORDER = "all_locations.cluster.colours_hex[7]"
H_CLUSTER_LARGE_HALO = "all_locations.cluster.colours_hex[8]"
H_CLUSTER_INNER_FO = "all_locations.cluster.inner_fill_opacity"
H_CLUSTER_HALO_O = "all_locations.cluster.halo_opacity"
H_CLUSTER_BORDER_O = "all_locations.cluster.border_opacity"
H_CLUSTER_HALO_SPREAD = "all_locations.cluster.halo_spread_px"
H_CLUSTER_BORDER_W = "all_locations.cluster.border_width_px"
H_HEX_DE = "all_locations.edge_hex"
H_HEX_DF = "all_locations.fill_hex"
H_HEX_SE = "species_locations.edge_hex"
H_HEX_SF = "species_locations.fill_hex"
H_HEX_SML_E = "species_locations.map_lifer_edge_hex"
H_HEX_SML_F = "species_locations.map_lifer_fill_hex"
H_HEX_LML_E = "lifer_locations.lifer_edge_hex"
H_HEX_LML_F = "lifer_locations.lifer_fill_hex"
H_HEX_LMS_E = "lifer_locations.subspecies_edge_hex"
H_HEX_LMS_F = "lifer_locations.subspecies_fill_hex"
H_HEX_LSE = "species_locations.last_seen_edge_hex"
H_HEX_LSF = "species_locations.last_seen_fill_hex"
H_HEX_FF = "family_locations.density_fill_hex[i]"
H_HEX_FS = "family_locations.density_stroke_hex[i]"
H_HEX_FAM_HL = "family_locations.highlight_stroke_hex"
