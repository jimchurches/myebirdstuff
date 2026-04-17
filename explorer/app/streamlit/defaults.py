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

from explorer.core.map_marker_scheme_model import (
    MapMarkerAllLocationsStyle,
    MapMarkerClusterStyle,
    MapMarkerColourScheme,
    MapMarkerFamilyLocationsStyle,
    MapMarkerGlobalDefaults,
    MapMarkerLiferLocationsStyle,
    MapMarkerSpeciesLocationsStyle,
    MapMarkerSpeciesMapBackgroundStyle,
)

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
# Family-locations map only (popup width + initial ``fit_bounds``); not tied to marker colour presets.
MAP_FAMILY_MAP_POPUP_MAX_WIDTH_PX = 320
MAP_FAMILY_MAP_FIT_BOUNDS_PADDING_PX = 48
MAP_FAMILY_MAP_FIT_BOUNDS_MAX_ZOOM = 6
MAP_FAMILY_MAP_FIT_BOUNDS_MAX_ZOOM_HIGHLIGHT = 8
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
# Fallback when a scheme has no ``global_defaults.radius_px`` (design utility / migration).
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


# Nested :class:`~explorer.core.map_marker_scheme_model.MapMarkerColourScheme` — globals, then per-map
# collections (all-locations → species visit → lifer map → family). See that module for structure.
# MarkerCluster defaults for rgba math in ``map_overlay_visit_map``:
MAP_MARKER_CLUSTER_INNER_FILL_OPACITY_DEFAULT = 0.6
MAP_MARKER_CLUSTER_HALO_OPACITY_DEFAULT = 0.6
MAP_MARKER_CLUSTER_BORDER_OPACITY_DEFAULT = 1.0
MAP_MARKER_CLUSTER_HALO_SPREAD_PX_DEFAULT = 6
MAP_MARKER_CLUSTER_BORDER_WIDTH_PX_DEFAULT = 2
#
# Three presets. Family-map sidebar radio selects the active scheme;
# ``MAP_MARKER_ACTIVE_COLOUR_SCHEME`` is the default when no UI index is passed (tests).
# ---------------------------------------------------------------------------

# Scheme 1 — default: red density ramp
MAP_MARKER_COLOUR_SCHEME_1 = MapMarkerColourScheme(
    display_name='Experimental',
    global_defaults=MapMarkerGlobalDefaults(
        fill_hex='#D3D3D3',
        stroke_hex='#008000',
        radius_px=5,
        fill_opacity=0.88,
        stroke_weight=2,
    ),
    all_locations=MapMarkerAllLocationsStyle(
        cluster=MapMarkerClusterStyle(),
    ),
    species_locations=MapMarkerSpeciesLocationsStyle(
        lifer_fill_hex='#FFC600',
        last_seen_fill_hex='#70E000',
    ),
    species_map_background=MapMarkerSpeciesMapBackgroundStyle(
        fill_hex='#F6F5F4',
        stroke_hex='#E6E1DB',
        radius_px=4,
    ),
    lifer_locations=MapMarkerLiferLocationsStyle(
        lifer_fill_hex='#FF8700',
    ),
    family_locations=MapMarkerFamilyLocationsStyle(
        density_fill_hex=(
            '#FFF2C2',
            '#D3D3D3',
            '#30B06A',
            '#05612B',
        ),
        legend_highlight_band_index=0,
        density_stroke_hex=(
            '#23804D',
            '#033A1A',
            '#033A1A',
            '#033A1A',
        ),
        highlight_stroke_hex='#E00000',
    ),
)

# Scheme 2 — blue → purple density ramp
MAP_MARKER_COLOUR_SCHEME_2 = MapMarkerColourScheme(
    display_name="Blues & purples",
    global_defaults=MapMarkerGlobalDefaults(
        fill_hex="#D3D3D3",
        stroke_hex="#008000",
        radius_px=5,
        fill_opacity=0.88,
        stroke_weight=2,
    ),
    all_locations=MapMarkerAllLocationsStyle(
        fill_hex="#D3D3D3",
        stroke_hex="#008000",
        stroke_weight=MAP_CIRCLE_MARKER_STROKE_WEIGHT,
        fill_opacity=MAP_PIN_FILL_OPACITY_ALL_LOCATIONS,
    ),
    species_locations=MapMarkerSpeciesLocationsStyle(
        fill_hex="#FF0000",
        stroke_hex="#800080",
        lifer_fill_hex="#FFFF00",
        lifer_stroke_hex="#800080",
        last_seen_fill_hex="#90EE90",
        last_seen_stroke_hex="#800080",
        fill_opacity=MAP_PIN_FILL_OPACITY_EMPHASIS,
    ),
    species_map_background=MapMarkerSpeciesMapBackgroundStyle(
        fill_hex="#D3D3D3",
        stroke_hex="#008000",
        stroke_weight=MAP_CIRCLE_MARKER_STROKE_WEIGHT,
        fill_opacity=MAP_PIN_FILL_OPACITY_ALL_LOCATIONS,
    ),
    lifer_locations=MapMarkerLiferLocationsStyle(
        lifer_fill_hex="#FFFF00",
        lifer_stroke_hex="#800080",
        subspecies_fill_hex="#FF0000",
        subspecies_stroke_hex="#800080",
        lifer_fill_opacity=MAP_PIN_FILL_OPACITY_EMPHASIS,
        subspecies_fill_opacity=MAP_PIN_FILL_OPACITY_EMPHASIS,
    ),
    family_locations=MapMarkerFamilyLocationsStyle(
        density_fill_hex=("#3A86FF", "#5E60CE", "#9D4EDD", "#C9184A"),
        legend_highlight_band_index=0,
        density_stroke_hex=("#2F6FD1", "#4A4DA6", "#7E3EAF", "#A1143A"),
        highlight_stroke_hex="#FF7F11",
    ),
)

# Scheme 3 — Ash Violet
MAP_MARKER_COLOUR_SCHEME_3 = MapMarkerColourScheme(
    display_name="Ash Violet",
    global_defaults=MapMarkerGlobalDefaults(
        fill_hex='#FFFFFF',
        stroke_hex='#FFF8E7',
        radius_px=5,
        fill_opacity=0.88,
        stroke_weight=2,
    ),
    all_locations=MapMarkerAllLocationsStyle(
        fill_hex='#D3D3D3',
        stroke_hex='#857891',
        cluster=MapMarkerClusterStyle(
            tier_icon_hex=(
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
            inner_fill_opacity=0.8,
            halo_opacity=0.4,
            border_opacity=0.4,
            halo_spread_px=5,
            border_width_px=0,
        ),
    ),
    species_locations=MapMarkerSpeciesLocationsStyle(
        fill_hex='#B78FAF',
        stroke_hex='#704868',
        lifer_fill_hex='#EEE82C',
        lifer_stroke_hex='#660700',
        last_seen_fill_hex='#03DD70',
        last_seen_stroke_hex='#660700',
    ),
    species_map_background=MapMarkerSpeciesMapBackgroundStyle(
        fill_hex='#EBE9ED',
        stroke_hex='#CCC7D1',
        radius_px=4,
        fill_opacity=0.75,
    ),
    lifer_locations=MapMarkerLiferLocationsStyle(
        lifer_fill_hex='#B78FAF',
        lifer_stroke_hex='#704868',
        subspecies_fill_hex='#CCC7D1',
        subspecies_stroke_hex='#704868',
    ),
    family_locations=MapMarkerFamilyLocationsStyle(
        density_fill_hex=("#95A5B2", "#B78FAF", "#8D5383", "#593653"),
        legend_highlight_band_index=0,
        density_stroke_hex=("#677C8E", "#704868", "#5A3554", "#593654"),
        highlight_stroke_hex="#E00000",
        fill_opacity=0.85,
    ),
)

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
