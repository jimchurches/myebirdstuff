"""
Developer tweakables for the Streamlit explorer: **sizes, colours, layout bounds, and map behaviour**
you may edit in one place without hunting through core modules.

**What belongs here**

- Marker cluster options, pin **radius / stroke / opacities**, legend dot sizes, popup width
- Map UI: basemap list/labels, height slider bounds, view labels, date-filter default; **debug-only map toggles** registered in :func:`debug_defaults_enabled` for CI
- Theme hex values aligned with ``.streamlit/config.toml``, settings panel width cap
- Rankings HTML layout width / scroll hint default; spinner CSS cache key suffix when theme CSS changes

**What does *not* belong here** (see other modules)

- **Fixed copy, URLs, emoji lists, tab names** → :mod:`explorer.app.streamlit.streamlit_ui_constants`
- **Persisted YAML settings schema defaults** (tables, taxonomy locale ranges) →
  :mod:`explorer.core.settings_schema_defaults`

Map code under ``explorer/`` imports cluster/pin/theme values from this module where noted in code.
"""

from __future__ import annotations

from dataclasses import dataclass, field

# ---------------------------------------------------------------------------
# Marker cluster — default “all locations” map (Leaflet.markercluster via Folium)
# ---------------------------------------------------------------------------
MAP_DEFAULT_LOCATION_CLUSTER_MAX_RADIUS_PX = 40
MAP_DEFAULT_LOCATION_CLUSTER_DISABLE_AT_ZOOM = 9
MAP_DEFAULT_LOCATION_CLUSTER_SPIDERFY_ON_MAX_ZOOM = False

# Debug-only map overlay (live zoom readout). Listed in :func:`debug_defaults_enabled` for CI warnings.
MAP_DEBUG_SHOW_ZOOM_LEVEL = False

# ---------------------------------------------------------------------------
# Pin geometry — Folium ``CircleMarker`` + legend sample dots; popup width
# ---------------------------------------------------------------------------
MAP_CIRCLE_MARKER_RADIUS_PX = 4
MAP_CIRCLE_MARKER_STROKE_WEIGHT = 3
MAP_PIN_FILL_OPACITY_ALL_LOCATIONS = 1.0
MAP_PIN_FILL_OPACITY_EMPHASIS = 0.9
MAP_LEGEND_PIN_DOT_PX = 8
MAP_LEGEND_PIN_BORDER_PX = 2
MAP_POPUP_MAX_WIDTH_PX = 420  # Folium L.popup maxWidth; card-like popups (refs #145).
# Character shown for Macaulay Library media links in map popups (refs #145).
# Possible alternatives for user testing: ⧉ (two joined squares, U+29C9); ⊕ (circled plus, U+2295).
MAP_POPUP_MACAULAY_LINK_SYMBOL = "↗"

# ---------------------------------------------------------------------------
# Map UI (session-only; not persisted in embedded YAML)
# ---------------------------------------------------------------------------

MAP_BASEMAP_OPTIONS: tuple[str, ...] = ("default", "google", "carto")
MAP_BASEMAP_LABELS: dict[str, str] = {
    "default": "Default",
    "google": "Google (hybrid)",
    "carto": "CartoDB Positron",
}
MAP_BASEMAP_DEFAULT = "default"

MAP_HEIGHT_PX_DEFAULT = 720
MAP_HEIGHT_PX_MIN = 440
MAP_HEIGHT_PX_MAX = 1200
MAP_HEIGHT_PX_STEP = 20

MAP_DATE_FILTER_DEFAULT = False

# Species locations: when True, the map shows only pins for the selected species (session-only sidebar toggle).
MAP_SPECIES_HIDE_ONLY_DEFAULT = True

MAP_VIEW_LABELS: tuple[str, ...] = ("All locations", "Species locations", "Lifer locations", "Family locations")

# ---------------------------------------------------------------------------
# Map marker colour schemes (Folium circle markers; refs #138)
#
# Fallback when a scheme has no ``marker_default_circle_radius_px`` (design utility / migration).
MAP_MARKER_CIRCLE_RADIUS_PX_FALLBACK = 2
# Design-utility sliders and pasted preset values clamp to this max; you can set higher radii by
# editing ``defaults.py`` directly.
MAP_MARKER_CIRCLE_RADIUS_PX_MAX = 10


def clamp_map_marker_circle_radius_px(value: int | float | None) -> int:
    """Clamp circle-marker radius to ``[1, MAP_MARKER_CIRCLE_RADIUS_PX_MAX]`` for the design utility."""
    if value is None:
        n = MAP_MARKER_CIRCLE_RADIUS_PX_FALLBACK
    else:
        try:
            n = int(value)
        except (TypeError, ValueError):
            n = MAP_MARKER_CIRCLE_RADIUS_PX_FALLBACK
    return max(1, min(MAP_MARKER_CIRCLE_RADIUS_PX_MAX, n))


def clamp_map_marker_circle_fill_opacity(value: float | None, *, fallback: float) -> float:
    """Clamp circle fill opacity to ``[0, 1]`` for map marker schemes and the design utility."""
    if value is None:
        x = fallback
    else:
        try:
            x = float(value)
        except (TypeError, ValueError):
            x = fallback
    return max(0.0, min(1.0, x))


# Shared presets for marker styling on map views. Each scheme holds **family** density/highlight
# fields and **visit_*** tunables (geometry, opacities, hex pairs). All-locations and family maps read
# these via ``map_marker_colour_resolve`` when the sidebar scheme is active.
# Optional ``marker_circle_radius_px_*`` override the global ``marker_default_circle_radius_px`` per map collection.
# Optional ``marker_circle_fill_opacity_*`` override ``marker_default_circle_fill_opacity`` the same way (sparse dict).
# Optional ``marker_cluster_colours_hex`` provides all MarkerCluster icon tier colours in one tuple:
# ``(small_fill, small_border, small_halo, medium_fill, medium_border, medium_halo, large_fill, large_border, large_halo)``.
# Omit to keep Leaflet.markercluster defaults.
# Optional ``marker_cluster_*_opacity`` / spread / border width tune the custom ``iconCreateFunction``
# (plugin defaults use semi-transparent rgba layers — see ``MAP_MARKER_CLUSTER_*_DEFAULT``).
MAP_MARKER_CLUSTER_INNER_FILL_OPACITY_DEFAULT = 0.6
MAP_MARKER_CLUSTER_HALO_OPACITY_DEFAULT = 0.6
MAP_MARKER_CLUSTER_BORDER_OPACITY_DEFAULT = 1.0
MAP_MARKER_CLUSTER_HALO_SPREAD_PX_DEFAULT = 6
MAP_MARKER_CLUSTER_BORDER_WIDTH_PX_DEFAULT = 2
#
# Three presets (same structure). Family-map sidebar radio (session-only) selects the active scheme;
# ``MAP_MARKER_ACTIVE_COLOUR_SCHEME`` is the default when no UI index is passed (tests).
# Scheme 3 is a spare slot for palette experiments.
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class MapMarkerColourOverrides:
    """Optional hex overrides layered on :class:`MapMarkerColourScheme`.

    ``None`` on a field means “use the scheme’s normal field”; resolution order is
    (a) override → (b) scheme role/global → (c) scheme defaults → (d) catch-all
    (see :mod:`explorer.core.map_marker_colour_resolve`).
    """

    marker_default_fill_hex: str | None = None
    marker_default_edge_hex: str | None = None
    location_visit_fill_hex: str | None = None
    location_visit_edge_hex: str | None = None
    species_fill_hex: str | None = None
    species_edge_hex: str | None = None
    lifer_fill_hex: str | None = None
    lifer_edge_hex: str | None = None
    last_seen_fill_hex: str | None = None
    last_seen_edge_hex: str | None = None


@dataclass(frozen=True)
class MapMarkerColourScheme:
    """Folium map-marker tunables (colours, sizes, strokes, viewport, legend).

    **Family locations** Folium uses :func:`~explorer.core.map_marker_colour_resolve.family_map_resolved_circle_radius_px`
    and :func:`~explorer.core.map_marker_colour_resolve.family_map_resolved_fill_opacity` (same rules as the
    map-marker design utility), plus ``base_stroke_weight``, ``highlight_*``, and ``density_*``.
    ``circle_marker_radius_px`` / ``circle_marker_fill_opacity`` apply when the sparse
    ``marker_circle_*_families`` overrides are unset.

    **Colour resolution** for the active scheme: per channel, (a) role-specific hex and optional
    :class:`MapMarkerColourOverrides`, (b) ``marker_default_*``, (c) scheme defaults (white fill / cream
    edge), (d) catch-all — see :mod:`explorer.core.map_marker_colour_resolve`.
    """

    display_name: str
    marker_default_fill_hex: str
    marker_default_edge_hex: str
    marker_default_circle_radius_px: int
    marker_default_circle_fill_opacity: float
    marker_default_base_stroke_weight: int
    marker_location_visit_fill_hex: str
    marker_location_visit_edge_hex: str
    marker_species_fill_hex: str
    marker_species_edge_hex: str
    marker_lifer_fill_hex: str
    marker_lifer_edge_hex: str
    marker_last_seen_fill_hex: str
    marker_last_seen_edge_hex: str
    circle_marker_radius_px: int
    circle_marker_fill_opacity: float
    base_stroke_weight: int
    highlight_stroke_hex: str
    highlight_stroke_weight: int
    density_fill_hex: tuple[str, ...]
    density_stroke_hex: tuple[str, ...]
    visit_circle_marker_radius_px: int
    visit_stroke_weight: int
    visit_fill_opacity_all_locations: float
    visit_fill_opacity_emphasis: float
    visit_fill_opacity_lifers: float
    popup_max_width_px: int
    fit_bounds_padding_px: int
    fit_bounds_max_zoom: int
    fit_bounds_max_zoom_highlight: int
    legend_highlight_swatch_fill_index: int
    # Optional per-map collection circle radii (None = use ``marker_default_circle_radius_px``).
    marker_circle_radius_px_locations: int | None = field(default=None)
    marker_circle_radius_px_species: int | None = field(default=None)
    marker_circle_radius_px_lifers: int | None = field(default=None)
    marker_circle_radius_px_families: int | None = field(default=None)
    marker_circle_fill_opacity_locations: float | None = field(default=None)
    marker_circle_fill_opacity_species: float | None = field(default=None)
    marker_circle_fill_opacity_lifers: float | None = field(default=None)
    marker_circle_fill_opacity_families: float | None = field(default=None)
    # All-locations map only: Leaflet.markercluster **cluster icon** colours by tier and channel:
    # ``(small_fill, small_border, small_halo, medium_*, large_*)``. The halo is drawn as a ``box-shadow``
    # ring around the inner disc (do not nest extra divs — plugin CSS targets a single inner ``div``).
    # ``None`` keeps plugin default styling.
    marker_cluster_colours_hex: tuple[str, str, str, str, str, str, str, str, str] | None = field(default=None)
    # When ``marker_cluster_colours_hex`` is set, these tune rgba / geometry for the custom cluster icon
    # (``None`` = use ``MAP_MARKER_CLUSTER_*_DEFAULT`` in ``map_overlay_visit_map``).
    marker_cluster_inner_fill_opacity: float | None = field(default=None)
    marker_cluster_halo_opacity: float | None = field(default=None)
    marker_cluster_border_opacity: float | None = field(default=None)
    marker_cluster_halo_spread_px: int | None = field(default=None)
    marker_cluster_border_width_px: int | None = field(default=None)
    marker_overrides: MapMarkerColourOverrides | None = field(default=None)


# Scheme 1 — default: red density ramp
_MAP_MARKER_COLOUR_SCHEME_1_VALUES = dict(
    display_name="Reds",
    marker_default_fill_hex="#D3D3D3",
    marker_default_edge_hex="#008000",
    marker_default_circle_radius_px=5,
    marker_default_circle_fill_opacity=0.88,
    marker_default_base_stroke_weight=2,
    marker_location_visit_fill_hex="#D3D3D3",
    marker_location_visit_edge_hex="#008000",
    marker_species_fill_hex="#FF0000",
    marker_species_edge_hex="#800080",
    marker_lifer_fill_hex="#FFFF00",
    marker_lifer_edge_hex="#800080",
    marker_last_seen_fill_hex="#90EE90",
    marker_last_seen_edge_hex="#800080",
    circle_marker_radius_px=5,
    circle_marker_fill_opacity=0.88,
    base_stroke_weight=2,
    highlight_stroke_hex='#E00000',
    highlight_stroke_weight=2,
    density_fill_hex=(
        '#95A5B2',
        '#B78FAF',
        '#8D5383',
        '#221B1E',
    ),
    density_stroke_hex=(
        '#677C8E',
        '#704868',
        '#5A3554',
        '#0B090A',
    ),
    visit_circle_marker_radius_px=MAP_CIRCLE_MARKER_RADIUS_PX,
    visit_stroke_weight=MAP_CIRCLE_MARKER_STROKE_WEIGHT,
    visit_fill_opacity_all_locations=MAP_PIN_FILL_OPACITY_ALL_LOCATIONS,
    visit_fill_opacity_emphasis=MAP_PIN_FILL_OPACITY_EMPHASIS,
    visit_fill_opacity_lifers=MAP_PIN_FILL_OPACITY_EMPHASIS,
    popup_max_width_px=320,
    fit_bounds_padding_px=48,
    fit_bounds_max_zoom=6,
    fit_bounds_max_zoom_highlight=8,
    legend_highlight_swatch_fill_index=0,
)

# Scheme 2 — blue → purple density ramp
_MAP_MARKER_COLOUR_SCHEME_2_VALUES = dict(
    display_name="Blues & purples",
    marker_default_fill_hex="#D3D3D3",
    marker_default_edge_hex="#008000",
    marker_default_circle_radius_px=5,
    marker_default_circle_fill_opacity=0.88,
    marker_default_base_stroke_weight=2,
    marker_location_visit_fill_hex="#D3D3D3",
    marker_location_visit_edge_hex="#008000",
    marker_species_fill_hex="#FF0000",
    marker_species_edge_hex="#800080",
    marker_lifer_fill_hex="#FFFF00",
    marker_lifer_edge_hex="#800080",
    marker_last_seen_fill_hex="#90EE90",
    marker_last_seen_edge_hex="#800080",
    circle_marker_radius_px=5,
    circle_marker_fill_opacity=0.88,
    base_stroke_weight=2,
    highlight_stroke_hex="#FF7F11",
    highlight_stroke_weight=2,
    density_fill_hex=(
        "#3A86FF",
        "#5E60CE",
        "#9D4EDD",
        "#C9184A",
    ),
    density_stroke_hex=(
        "#2F6FD1",
        "#4A4DA6",
        "#7E3EAF",
        "#A1143A",
    ),
    visit_circle_marker_radius_px=MAP_CIRCLE_MARKER_RADIUS_PX,
    visit_stroke_weight=MAP_CIRCLE_MARKER_STROKE_WEIGHT,
    visit_fill_opacity_all_locations=MAP_PIN_FILL_OPACITY_ALL_LOCATIONS,
    visit_fill_opacity_emphasis=MAP_PIN_FILL_OPACITY_EMPHASIS,
    visit_fill_opacity_lifers=MAP_PIN_FILL_OPACITY_EMPHASIS,
    popup_max_width_px=320,
    fit_bounds_padding_px=48,
    fit_bounds_max_zoom=6,
    fit_bounds_max_zoom_highlight=8,
    legend_highlight_swatch_fill_index=0,
)

# Scheme 3 — experimental
_MAP_MARKER_COLOUR_SCHEME_3_VALUES = dict(
    display_name='Experimental',
    marker_default_fill_hex='#FFFFFF',
    marker_default_edge_hex='#FFF8E7',
    marker_default_circle_radius_px=5,
    marker_default_circle_fill_opacity=0.88,
    marker_default_base_stroke_weight=2,
    marker_location_visit_fill_hex='#C7A8C1',
    marker_location_visit_edge_hex='#4D2D48',
    marker_species_fill_hex='#B78FAF',
    marker_species_edge_hex='#704868',
    marker_lifer_fill_hex='#FCEC52',
    marker_lifer_edge_hex='#566776',
    marker_last_seen_fill_hex='#9EA93F',
    marker_last_seen_edge_hex='#704868',
    circle_marker_radius_px=5,
    circle_marker_fill_opacity=0.85,
    base_stroke_weight=2,
    highlight_stroke_hex='#E00000',
    highlight_stroke_weight=2,
    density_fill_hex=(
        '#95A5B2',
        '#B78FAF',
        '#8D5383',
        '#593653',
    ),
    density_stroke_hex=(
        '#677C8E',
        '#704868',
        '#5A3554',
        '#593654',
    ),
    visit_circle_marker_radius_px=5,
    visit_stroke_weight=2,
    visit_fill_opacity_all_locations=0.9,
    visit_fill_opacity_emphasis=0.9,
    visit_fill_opacity_lifers=0.9,
    popup_max_width_px=320,
    fit_bounds_padding_px=48,
    fit_bounds_max_zoom=6,
    fit_bounds_max_zoom_highlight=8,
    legend_highlight_swatch_fill_index=0,
    marker_circle_fill_opacity_locations=0.9,
    marker_circle_fill_opacity_species=0.9,
    marker_circle_fill_opacity_lifers=0.9,
    marker_circle_fill_opacity_families=0.85,
    marker_cluster_colours_hex=(
        '#DFCEDE',
        '#9E6B9B',
        '#DFCEDE',
        '#CFB4CD',
        '#9E6B9B',
        '#CFB4CD',
        '#B78FB4',
        '#9E6B9B',
        '#B78FB4',
    ),
    marker_cluster_inner_fill_opacity=0.8,
    marker_cluster_halo_opacity=0.4,
    marker_cluster_border_opacity=0.4,
    marker_cluster_halo_spread_px=5,
    marker_cluster_border_width_px=0,
)


MAP_MARKER_COLOUR_SCHEME_1 = MapMarkerColourScheme(**_MAP_MARKER_COLOUR_SCHEME_1_VALUES)
MAP_MARKER_COLOUR_SCHEME_2 = MapMarkerColourScheme(**_MAP_MARKER_COLOUR_SCHEME_2_VALUES)
MAP_MARKER_COLOUR_SCHEME_3 = MapMarkerColourScheme(**_MAP_MARKER_COLOUR_SCHEME_3_VALUES)

# Default scheme index when callers do not pass a UI selection (tests, non-Streamlit builders).
MAP_MARKER_ACTIVE_COLOUR_SCHEME: int = 1


def active_map_marker_colour_scheme(scheme_index: int | None = None) -> MapMarkerColourScheme:
    """Return the map-marker style bundle for *scheme_index* ``1``, ``2``, or ``3`` (refs #138).

    When *scheme_index* is ``None``, uses :data:`MAP_MARKER_ACTIVE_COLOUR_SCHEME` (Reds by default).
    Unknown indices fall back to scheme ``1``.
    """
    n = int(MAP_MARKER_ACTIVE_COLOUR_SCHEME if scheme_index is None else scheme_index)
    if n == 2:
        return MAP_MARKER_COLOUR_SCHEME_2
    if n == 3:
        return MAP_MARKER_COLOUR_SCHEME_3
    return MAP_MARKER_COLOUR_SCHEME_1


# ---------------------------------------------------------------------------
# Layout / theme (Streamlit-only)
# ---------------------------------------------------------------------------

SETTINGS_PANEL_MAX_WIDTH_REM = 40

THEME_TEXT_HEX = "#1A2E22"
THEME_PRIMARY_HEX = "#1F6F54"
THEME_SECONDARY_BG_HEX = "#EEF4F0"

SPINNER_THEME_CSS_CACHE_KEY_SUFFIX = "v18"

# ---------------------------------------------------------------------------
# Ranking & Lists HTML (``rankings_streamlit_html``)
# ---------------------------------------------------------------------------

RANKINGS_TABLE_LAYOUT_MAX_WIDTH_PX = 1400
RANKINGS_BUNDLE_SCROLL_HINT_DEFAULT = "shading"


def debug_defaults_enabled() -> list[str]:
    """Return names of debug toggles in this module that are currently ``True``.

    Used by CI (pytest + ``scripts/warn_streamlit_debug_defaults.py``) to emit non-failing warnings
    when a debug default is left on. Add new ``MAP_*``/``*_DEBUG_*`` style toggles here when introduced.
    """
    names: list[str] = []
    if MAP_DEBUG_SHOW_ZOOM_LEVEL:
        names.append("MAP_DEBUG_SHOW_ZOOM_LEVEL")
    return names
