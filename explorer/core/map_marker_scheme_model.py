"""
Nested dataclasses for :class:`MapMarkerColourScheme`.

Grouping follows map **collections** (globals → all-locations → species visit → lifer map → family)
so the shape is discoverable in the IDE and stable regardless of dict key order in presets.

``explorer.app.streamlit.defaults`` builds the three bundled presets from these types.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class MapMarkerGlobalDefaults:
    """Fallback stroke/fill and default circle geometry shared across resolution (a)→(b)→(c)→(d)."""

    fill_hex: str
    edge_hex: str
    circle_radius_px: int
    circle_fill_opacity: float
    base_stroke_weight: int


@dataclass(frozen=True)
class MapMarkerClusterStyle:
    """Leaflet.markercluster tier icon overrides (All locations map only)."""

    colours_hex: tuple[str, str, str, str, str, str, str, str, str] | None = None
    inner_fill_opacity: float | None = None
    halo_opacity: float | None = None
    border_opacity: float | None = None
    halo_spread_px: int | None = None
    border_width_px: int | None = None


@dataclass(frozen=True)
class MapMarkerAllLocationsStyle:
    """Default location pins on the all-locations map + optional cluster icon styling."""

    location_visit_fill_hex: str
    location_visit_edge_hex: str
    visit_circle_marker_radius_px: int
    visit_stroke_weight: int
    visit_fill_opacity_all_locations: float
    marker_circle_radius_px_locations: int | None = None
    marker_circle_fill_opacity_locations: float | None = None
    cluster: MapMarkerClusterStyle = field(default_factory=MapMarkerClusterStyle)


@dataclass(frozen=True)
class MapMarkerSpeciesLocationsStyle:
    """Species-filtered visit overlay: species / lifer / last-seen emphasis pins."""

    species_fill_hex: str
    species_edge_hex: str
    species_map_lifer_fill_hex: str
    species_map_lifer_edge_hex: str
    last_seen_fill_hex: str
    last_seen_edge_hex: str
    visit_fill_opacity_emphasis: float
    visit_fill_opacity_species_map_lifer: float
    marker_circle_radius_px_species: int | None = None
    marker_circle_radius_px_species_map_lifer: int | None = None
    marker_circle_fill_opacity_species: float | None = None
    marker_circle_fill_opacity_species_map_lifer: float | None = None


@dataclass(frozen=True)
class MapMarkerLiferLocationsStyle:
    """Lifer-locations map: base lifer vs taxon-only (subspecies) lifer pins."""

    lifer_map_lifer_fill_hex: str
    lifer_map_lifer_edge_hex: str
    lifer_map_subspecies_fill_hex: str
    lifer_map_subspecies_edge_hex: str
    visit_fill_opacity_lifer_map_lifer: float
    visit_fill_opacity_lifer_map_subspecies: float
    marker_circle_radius_px_lifer_map_lifer: int | None = None
    marker_circle_radius_px_lifer_map_subspecies: int | None = None
    marker_circle_fill_opacity_lifer_map_lifer: float | None = None
    marker_circle_fill_opacity_lifer_map_subspecies: float | None = None


@dataclass(frozen=True)
class MapMarkerFamilyLocationsStyle:
    """Family density map: bands, highlight stroke, optional per-collection overrides."""

    circle_marker_radius_px: int
    circle_marker_fill_opacity: float
    base_stroke_weight: int
    highlight_stroke_hex: str
    highlight_stroke_weight: int
    density_fill_hex: tuple[str, ...]
    density_stroke_hex: tuple[str, ...]
    legend_highlight_swatch_fill_index: int
    marker_circle_radius_px_families: int | None = None
    marker_circle_fill_opacity_families: float | None = None


@dataclass(frozen=True)
class MapMarkerViewportStyle:
    """Popup width and fit-bounds tuning (shared Folium behaviour)."""

    popup_max_width_px: int
    fit_bounds_padding_px: int
    fit_bounds_max_zoom: int
    fit_bounds_max_zoom_highlight: int


@dataclass(frozen=True)
class MapMarkerColourOverrides:
    """Optional hex overrides (flat keys) layered on :class:`MapMarkerColourScheme`.

    Resolution order: (a) override → (b) scheme role/global → (c) scheme defaults → (d) catch-all.
    """

    marker_default_fill_hex: str | None = None
    marker_default_edge_hex: str | None = None
    location_visit_fill_hex: str | None = None
    location_visit_edge_hex: str | None = None
    species_fill_hex: str | None = None
    species_edge_hex: str | None = None
    species_map_lifer_fill_hex: str | None = None
    species_map_lifer_edge_hex: str | None = None
    lifer_map_lifer_fill_hex: str | None = None
    lifer_map_lifer_edge_hex: str | None = None
    lifer_map_subspecies_fill_hex: str | None = None
    lifer_map_subspecies_edge_hex: str | None = None
    last_seen_fill_hex: str | None = None
    last_seen_edge_hex: str | None = None


@dataclass(frozen=True)
class MapMarkerColourScheme:
    """Complete marker style bundle for the explorer (one active preset at a time)."""

    display_name: str
    global_defaults: MapMarkerGlobalDefaults
    all_locations: MapMarkerAllLocationsStyle
    species_locations: MapMarkerSpeciesLocationsStyle
    lifer_locations: MapMarkerLiferLocationsStyle
    family_locations: MapMarkerFamilyLocationsStyle
    viewport: MapMarkerViewportStyle
    marker_overrides: MapMarkerColourOverrides | None = None
