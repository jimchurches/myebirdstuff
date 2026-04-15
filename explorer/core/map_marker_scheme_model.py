"""
Nested dataclasses for :class:`MapMarkerColourScheme`.

**Naming**

- **Per collection:** ``fill_hex`` / ``edge_hex`` for the primary pin colours; role-specific pairs
  use short prefixes (``map_lifer_*``, ``last_seen_*``, ``lifer_*``, ``subspecies_*``).
- **Sparse tweaks:** ``radius_override_px`` and ``fill_opacity_override`` only when a collection differs
  from :class:`MapMarkerGlobalDefaults`.
- **Family map:** ``pin_radius_px`` / ``pin_fill_opacity`` are the styled defaults; overrides use the same
  ``*_override_*`` pattern.
- **Flat overrides:** :class:`SchemeColourOverrides` uses short keys (``default_fill_hex``, ``location_fill_hex``, …).

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
    """Leaflet.markercluster tier icon overrides (all-locations map only)."""

    colours_hex: tuple[str, str, str, str, str, str, str, str, str] | None = None
    inner_fill_opacity: float | None = None
    halo_opacity: float | None = None
    border_opacity: float | None = None
    halo_spread_px: int | None = None
    border_width_px: int | None = None


@dataclass(frozen=True)
class MapMarkerAllLocationsStyle:
    """Default location pins on the all-locations map + optional cluster icon styling.

    Radius uses :data:`MapMarkerColourScheme.global_defaults.circle_radius_px` unless
    ``radius_override_px`` is set. ``stroke_weight`` / ``fill_opacity`` default to ``None`` so they inherit
    ``global_defaults.base_stroke_weight`` and ``global_defaults.circle_fill_opacity`` (sparse presets).
    """

    fill_hex: str
    edge_hex: str
    stroke_weight: int | None = None
    fill_opacity: float | None = None
    radius_override_px: int | None = None
    fill_opacity_override: float | None = None
    cluster: MapMarkerClusterStyle = field(default_factory=MapMarkerClusterStyle)


@dataclass(frozen=True)
class MapMarkerSpeciesLocationsStyle:
    """Species-filtered visit overlay: species / map-lifer / last-seen pins."""

    fill_hex: str
    edge_hex: str
    map_lifer_fill_hex: str
    map_lifer_edge_hex: str
    last_seen_fill_hex: str
    last_seen_edge_hex: str
    emphasis_fill_opacity: float
    stroke_weight_override: int | None = None
    radius_override_px: int | None = None
    fill_opacity_override: float | None = None


@dataclass(frozen=True)
class MapMarkerLiferLocationsStyle:
    """Lifer-locations map: base lifer vs taxon-only (subspecies) lifer pins."""

    lifer_fill_hex: str
    lifer_edge_hex: str
    subspecies_fill_hex: str
    subspecies_edge_hex: str
    lifer_fill_opacity: float
    subspecies_fill_opacity: float
    stroke_weight_override: int | None = None
    lifer_radius_override_px: int | None = None
    subspecies_radius_override_px: int | None = None
    lifer_fill_opacity_override: float | None = None
    subspecies_fill_opacity_override: float | None = None


@dataclass(frozen=True)
class MapMarkerFamilyLocationsStyle:
    """Family density map: bands, highlight stroke, optional per-collection overrides."""

    pin_radius_px: int
    pin_fill_opacity: float
    base_stroke_weight: int
    highlight_stroke_hex: str
    highlight_stroke_weight: int
    density_fill_hex: tuple[str, ...]
    density_stroke_hex: tuple[str, ...]
    legend_highlight_band_index: int
    radius_override_px: int | None = None
    fill_opacity_override: float | None = None


@dataclass(frozen=True)
class MapMarkerViewportStyle:
    """Popup width and fit-bounds tuning (shared Folium behaviour)."""

    popup_max_width_px: int
    fit_bounds_padding_px: int
    fit_bounds_max_zoom: int
    fit_bounds_max_zoom_highlight: int


@dataclass(frozen=True)
class SchemeColourOverrides:
    """Optional hex overrides (flat keys) layered on :class:`MapMarkerColourScheme`.

    Resolution order: (a) override → (b) scheme role/global → (c) scheme defaults → (d) catch-all.
    """

    default_fill_hex: str | None = None
    default_edge_hex: str | None = None
    location_fill_hex: str | None = None
    location_edge_hex: str | None = None
    species_fill_hex: str | None = None
    species_edge_hex: str | None = None
    map_lifer_fill_hex: str | None = None
    map_lifer_edge_hex: str | None = None
    lifer_fill_hex: str | None = None
    lifer_edge_hex: str | None = None
    subspecies_fill_hex: str | None = None
    subspecies_edge_hex: str | None = None
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
    colour_overrides: SchemeColourOverrides | None = None
