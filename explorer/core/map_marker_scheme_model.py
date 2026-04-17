"""
Nested dataclasses for :class:`MapMarkerColourScheme`.

**Naming**

- **Per collection:** ``fill_hex`` / ``stroke_hex`` for pin fill and outline colour; role-specific pairs use
  short prefixes (``lifer_*``, ``last_seen_*``, ``subspecies_*``) where needed. On non-global collections,
  ``None`` for a hex means inherit :class:`MapMarkerGlobalDefaults` for that channel (same resolution chain as
  ``fill_opacity``).
- **Sparse tweaks:** optional ``radius_px`` / ``fill_opacity`` / ``fill_opacity_override`` when a collection
  differs from :class:`MapMarkerGlobalDefaults`. On ``MapMarkerSpeciesLocationsStyle`` and
  ``MapMarkerLiferLocationsStyle``, ``fill_opacity`` / ``lifer_*_fill_opacity`` may be omitted (``None``) to
  inherit ``global_defaults.fill_opacity`` in resolution.
- **Family map:** ``radius_px`` / ``stroke_weight`` / band and highlight fields are required; ``fill_opacity``
  may be omitted (``None``) to inherit ``global_defaults.fill_opacity``. Optional ``*_override_*`` fields
  follow the same pattern as other collections.
- **Flat overrides:** :class:`SchemeColourOverrides` uses short keys layered on the scheme.

``explorer.app.streamlit.defaults`` builds the three bundled presets from these types.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class MapMarkerGlobalDefaults:
    """Fallback stroke/fill and default circle geometry shared across resolution (a)→(b)→(c)→(d)."""

    fill_hex: str
    stroke_hex: str
    radius_px: int
    fill_opacity: float
    stroke_weight: int


@dataclass(frozen=True)
class MapMarkerClusterStyle:
    """Leaflet.markercluster tier icon overrides (all-locations map only).

    Nine entries: small / medium / large tier, each (fill, border, halo) — see ``map_overlay_visit_map``.
    """

    tier_icon_hex: tuple[str, str, str, str, str, str, str, str, str] | None = None
    inner_fill_opacity: float | None = None
    halo_opacity: float | None = None
    border_opacity: float | None = None
    halo_spread_px: int | None = None
    border_width_px: int | None = None


@dataclass(frozen=True)
class MapMarkerAllLocationsStyle:
    """Default location pins on the all-locations map + optional cluster icon styling.

    Radius uses :data:`MapMarkerColourScheme.global_defaults.radius_px` unless ``radius_px`` is set here.
    ``fill_hex`` / ``stroke_hex`` / ``stroke_weight`` / ``fill_opacity`` default to ``None`` so they inherit
    globals where applicable (sparse presets).
    """

    fill_hex: str | None = None
    stroke_hex: str | None = None
    stroke_weight: int | None = None
    fill_opacity: float | None = None
    radius_px: int | None = None
    fill_opacity_override: float | None = None
    cluster: MapMarkerClusterStyle = field(default_factory=MapMarkerClusterStyle)


@dataclass(frozen=True)
class MapMarkerSpeciesLocationsStyle:
    """Species-filtered visit overlay: species / lifer / last-seen pins."""

    fill_hex: str | None = None
    stroke_hex: str | None = None
    lifer_fill_hex: str | None = None
    lifer_stroke_hex: str | None = None
    last_seen_fill_hex: str | None = None
    last_seen_stroke_hex: str | None = None
    fill_opacity: float | None = None
    stroke_weight_override: int | None = None
    radius_px: int | None = None
    fill_opacity_override: float | None = None


@dataclass(frozen=True)
class MapMarkerSpeciesMapBackgroundStyle:
    """Background (non-emphasis) pins on the species-filtered map only.

    Independent of :class:`MapMarkerAllLocationsStyle` (refs #147). Same sparse pattern as
    :class:`MapMarkerAllLocationsStyle` (no cluster).
    """

    fill_hex: str | None = None
    stroke_hex: str | None = None
    stroke_weight: int | None = None
    fill_opacity: float | None = None
    radius_px: int | None = None
    fill_opacity_override: float | None = None


@dataclass(frozen=True)
class MapMarkerLiferLocationsStyle:
    """Lifer-locations map: base lifer vs taxon-only (subspecies) lifer pins."""

    lifer_fill_hex: str | None = None
    lifer_stroke_hex: str | None = None
    subspecies_fill_hex: str | None = None
    subspecies_stroke_hex: str | None = None
    lifer_fill_opacity: float | None = None
    subspecies_fill_opacity: float | None = None
    stroke_weight_override: int | None = None
    lifer_radius_px: int | None = None
    subspecies_radius_px: int | None = None
    lifer_fill_opacity_override: float | None = None
    subspecies_fill_opacity_override: float | None = None


@dataclass(frozen=True)
class MapMarkerFamilyLocationsStyle:
    """Family density map: bands, highlight stroke, optional per-collection overrides."""

    radius_px: int
    stroke_weight: int
    highlight_stroke_hex: str
    highlight_stroke_weight: int
    density_fill_hex: tuple[str, ...]
    density_stroke_hex: tuple[str, ...]
    legend_highlight_band_index: int
    fill_opacity: float | None = None
    radius_px_override: int | None = None
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
    default_stroke_hex: str | None = None
    location_fill_hex: str | None = None
    location_stroke_hex: str | None = None
    species_fill_hex: str | None = None
    species_stroke_hex: str | None = None
    species_lifer_fill_hex: str | None = None
    species_lifer_stroke_hex: str | None = None
    lifer_fill_hex: str | None = None
    lifer_stroke_hex: str | None = None
    subspecies_fill_hex: str | None = None
    subspecies_stroke_hex: str | None = None
    last_seen_fill_hex: str | None = None
    last_seen_stroke_hex: str | None = None
    species_background_fill_hex: str | None = None
    species_background_stroke_hex: str | None = None


@dataclass(frozen=True)
class MapMarkerColourScheme:
    """Complete marker style bundle for the explorer (one active preset at a time)."""

    display_name: str
    global_defaults: MapMarkerGlobalDefaults
    all_locations: MapMarkerAllLocationsStyle
    species_locations: MapMarkerSpeciesLocationsStyle
    species_map_background: MapMarkerSpeciesMapBackgroundStyle
    lifer_locations: MapMarkerLiferLocationsStyle
    family_locations: MapMarkerFamilyLocationsStyle
    viewport: MapMarkerViewportStyle
    colour_overrides: SchemeColourOverrides | None = None
