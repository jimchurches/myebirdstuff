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
H_RADIUS_DEFAULT = "marker_default_circle_radius_px"
H_RADIUS_LOCATIONS = "marker_circle_radius_px_locations"
H_RADIUS_SPECIES = "marker_circle_radius_px_species"
H_RADIUS_SPECIES_MAP_LIFER = "marker_circle_radius_px_species_map_lifer"
H_RADIUS_LIFER_MAP_LIFER = "marker_circle_radius_px_lifer_map_lifer"
H_RADIUS_LIFER_MAP_SUBSPECIES = "marker_circle_radius_px_lifer_map_subspecies"
H_RADIUS_FAMILIES = "marker_circle_radius_px_families"
H_SW_VISIT = "visit_stroke_weight"
H_SW_FAM = "base_stroke_weight"
H_SW_FAM_HL = "highlight_stroke_weight"
H_FO_DEFAULT = "marker_default_circle_fill_opacity"
H_FO_LOCATIONS = "marker_circle_fill_opacity_locations"
H_FO_SPECIES = "marker_circle_fill_opacity_species"
H_FO_SPECIES_MAP_LIFER = "marker_circle_fill_opacity_species_map_lifer"
H_FO_LIFER_MAP_LIFER = "marker_circle_fill_opacity_lifer_map_lifer"
H_FO_LIFER_MAP_SUBSPECIES = "marker_circle_fill_opacity_lifer_map_subspecies"
H_FO_FAMILY = "marker_circle_fill_opacity_families"
H_CLUSTER_SMALL_FILL = "marker_cluster_colours_hex[0]"
H_CLUSTER_SMALL_BORDER = "marker_cluster_colours_hex[1]"
H_CLUSTER_SMALL_HALO = "marker_cluster_colours_hex[2]"
H_CLUSTER_MEDIUM_FILL = "marker_cluster_colours_hex[3]"
H_CLUSTER_MEDIUM_BORDER = "marker_cluster_colours_hex[4]"
H_CLUSTER_MEDIUM_HALO = "marker_cluster_colours_hex[5]"
H_CLUSTER_LARGE_FILL = "marker_cluster_colours_hex[6]"
H_CLUSTER_LARGE_BORDER = "marker_cluster_colours_hex[7]"
H_CLUSTER_LARGE_HALO = "marker_cluster_colours_hex[8]"
H_CLUSTER_INNER_FO = "marker_cluster_inner_fill_opacity"
H_CLUSTER_HALO_O = "marker_cluster_halo_opacity"
H_CLUSTER_BORDER_O = "marker_cluster_border_opacity"
H_CLUSTER_HALO_SPREAD = "marker_cluster_halo_spread_px"
H_CLUSTER_BORDER_W = "marker_cluster_border_width_px"
H_HEX_DE = "marker_location_visit_edge_hex"
H_HEX_DF = "marker_location_visit_fill_hex"
H_HEX_SE = "marker_species_edge_hex"
H_HEX_SF = "marker_species_fill_hex"
H_HEX_SML_E = "marker_species_map_lifer_edge_hex"
H_HEX_SML_F = "marker_species_map_lifer_fill_hex"
H_HEX_LML_E = "marker_lifer_map_lifer_edge_hex"
H_HEX_LML_F = "marker_lifer_map_lifer_fill_hex"
H_HEX_LMS_E = "marker_lifer_map_subspecies_edge_hex"
H_HEX_LMS_F = "marker_lifer_map_subspecies_fill_hex"
H_HEX_LSE = "marker_last_seen_edge_hex"
H_HEX_LSF = "marker_last_seen_fill_hex"
H_HEX_FF = "density_fill_hex[i]"
H_HEX_FS = "density_stroke_hex[i]"
H_HEX_FAM_HL = "highlight_stroke_hex"
