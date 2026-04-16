"""
Folium preview map for the **Map marker design** Streamlit utility.

Builds a fixed Canberra-centred map at the same initial zoom as :func:`create_map` (zoom 5) with
dummy ``CircleMarker`` markers for each visit-map and family-map role, plus a separate
**SEQ (Brisbane / Gold Coast) MarkerCluster** demo (synthetic points) when the preview scope
includes all-locations roles. No UI dependencies.
"""

from __future__ import annotations

import html as html_module
import random
import re
from dataclasses import dataclass

import folium
from branca.element import Element
from folium.plugins import MarkerCluster

from explorer.app.streamlit.defaults import (
    MAP_DEFAULT_LOCATION_CLUSTER_DISABLE_AT_ZOOM,
    MAP_DEFAULT_LOCATION_CLUSTER_MAX_RADIUS_PX,
    MAP_DEFAULT_LOCATION_CLUSTER_SPIDERFY_ON_MAX_ZOOM,
    MAP_MARKER_CIRCLE_RADIUS_PX_FALLBACK,
    MAP_POPUP_MAX_WIDTH_PX,
    clamp_map_marker_circle_fill_opacity,
    clamp_map_marker_circle_radius_px,
)
from explorer.core.map_overlay_visit_map import (
    _marker_cluster_icon_create_function_from_scheme,
    _marker_cluster_root_background_reset_css,
)
from explorer.core.family_map_compute import DENSITY_BAND_LABELS
from explorer.core.map_marker_colour_resolve import (
    MAP_MARKER_CATCHALL_STROKE_HEX,
    normalize_marker_hex,
    resolve_family_band_colours,
    resolve_last_seen_colours,
    resolve_lifer_map_lifer_colours,
    resolve_lifer_map_subspecies_colours,
    resolve_location_visit_colours,
    resolve_marker_global_colours,
    resolve_species_colours,
    resolve_species_map_background_colours,
    resolve_species_map_lifer_colours,
)
from explorer.presentation.map_renderer import (
    build_legend_html,
    create_map,
    map_overlay_theme_stylesheet,
    map_popup_width_fix_script,
)

# Match :func:`create_map` default (eastern Australia context; refs design utility).
DESIGN_PREVIEW_MAP_CENTER: tuple[float, float] = (-35.28, 149.13)
# Zoom ~5 viewport: scatter markers across roughly what is visible; tune if needed.
DESIGN_PREVIEW_WIDE_SPAN_DEG = (9.0, 11.0)  # lat, lon — broad distribution over the framed map
# Tight cluster around Canberra / ACT for proximity examples.
DESIGN_PREVIEW_LOCAL_SPAN_DEG = (0.38, 0.48)
# Samples per marker kind (each block of four: two cluster + two spread).
DESIGN_PREVIEW_MARKER_COPY_COUNT = 8

# MarkerCluster demo: Brisbane / Gold Coast anchors, separate from Canberra role markers.
# Counts target Leaflet.markercluster tiers: ``<10`` small, ``<100`` medium, ``>=100`` large.
# Two SEQ city-area anchors are spaced W vs NE so they stay distinct clusters at default zoom.
DESIGN_PREVIEW_CLUSTER_DEMO_ANCHORS: tuple[tuple[float, float, int, str], ...] = (
    (-28.02, 153.42, 7, "Gold Coast (small tier)"),
    (-27.62, 152.78, 45, "Brisbane W (medium tier)"),
    (-27.05, 153.42, 120, "Brisbane NE (large tier)"),
)
DESIGN_PREVIEW_CLUSTER_JITTER_DEG = 0.008

_HEX_RE = re.compile(r"^#([0-9A-Fa-f]{3}|[0-9A-Fa-f]{6}|[0-9A-Fa-f]{8})$")

# Hard fallbacks when :class:`~explorer.app.streamlit.defaults.MapMarkerColourScheme` omits marker defaults.
MARKER_SCHEME_FALLBACK_DEFAULT_RADIUS_PX = 5
MARKER_SCHEME_FALLBACK_DEFAULT_FILL_OPACITY = 0.88
MARKER_SCHEME_FALLBACK_DEFAULT_STROKE_WEIGHT = 2

# Map view keys — align with sidebar "Preview scope" (four explorer map modes + all).
MAP_SCOPE_ALL = "all"
MAP_SCOPE_ALL_LOCATIONS = "all_locations"
MAP_SCOPE_SPECIES_LOCATIONS = "species_locations"
MAP_SCOPE_LIFER_LOCATIONS = "lifer_locations"
MAP_SCOPE_FAMILY_LOCATIONS = "family_locations"
MAP_SCOPES: tuple[str, ...] = (
    MAP_SCOPE_ALL,
    MAP_SCOPE_ALL_LOCATIONS,
    MAP_SCOPE_SPECIES_LOCATIONS,
    MAP_SCOPE_LIFER_LOCATIONS,
    MAP_SCOPE_FAMILY_LOCATIONS,
)


def normalize_hex_colour(raw: str, *, fallback: str = MAP_MARKER_CATCHALL_STROKE_HEX) -> str:
    """Return a ``#RRGGBB`` string, or *fallback* if input is empty/invalid."""
    s = (raw or "").strip()
    if not s:
        return fallback
    if not s.startswith("#"):
        s = f"#{s}"
    if _HEX_RE.match(s):
        return s[:7] if len(s) >= 7 else s  # ignore alpha if 8-char for Folium simplicity
    return fallback


@dataclass(frozen=True)
class PreviewMarkerRow:
    """One dummy marker role; popups match production legend wording where applicable."""

    kind: str
    # Which "Preview scope" options include this row (``all`` is handled separately = union).
    map_scopes: frozenset[str]


# Order: All-locations map pins → Species map roles (species, locations, lifer, last seen) → Lifer-map-only → Family.
# ``visit_species_map_locations`` is the species-map background pin (refs #147); ``visit_all_locations`` is the
# all-locations map only. ``species_visit_lifer`` / ``visit_last_seen`` match production overlays.
PREVIEW_MARKER_ROWS: tuple[PreviewMarkerRow, ...] = (
    PreviewMarkerRow("visit_all_locations", frozenset({MAP_SCOPE_ALL_LOCATIONS})),
    PreviewMarkerRow("visit_species", frozenset({MAP_SCOPE_SPECIES_LOCATIONS})),
    PreviewMarkerRow("visit_species_map_locations", frozenset({MAP_SCOPE_SPECIES_LOCATIONS})),
    PreviewMarkerRow("species_visit_lifer", frozenset({MAP_SCOPE_SPECIES_LOCATIONS})),
    PreviewMarkerRow("visit_last_seen", frozenset({MAP_SCOPE_SPECIES_LOCATIONS})),
    PreviewMarkerRow("lifer_map_lifer", frozenset({MAP_SCOPE_LIFER_LOCATIONS})),
    PreviewMarkerRow("lifer_subspecies", frozenset({MAP_SCOPE_LIFER_LOCATIONS})),
    PreviewMarkerRow("family_0", frozenset({MAP_SCOPE_FAMILY_LOCATIONS})),
    PreviewMarkerRow("family_1", frozenset({MAP_SCOPE_FAMILY_LOCATIONS})),
    PreviewMarkerRow("family_2", frozenset({MAP_SCOPE_FAMILY_LOCATIONS})),
    PreviewMarkerRow("family_3", frozenset({MAP_SCOPE_FAMILY_LOCATIONS})),
)


def _rows_for_scope(scope: str) -> tuple[PreviewMarkerRow, ...]:
    if scope == MAP_SCOPE_ALL:
        return PREVIEW_MARKER_ROWS
    out: list[PreviewMarkerRow] = []
    for row in PREVIEW_MARKER_ROWS:
        if scope in row.map_scopes:
            out.append(row)
    return tuple(out)


def _location_for_marker(
    kind: str,
    copy_index: int,
    type_slot: int,
    position_seed: int,
    *,
    local: bool,
) -> tuple[float, float]:
    """Pseudo-random point: *local* uses a tight Canberra box; otherwise wide viewport scatter."""
    seed_int = (
        int(position_seed) * 10009 + hash((kind, copy_index)) % 100003 + type_slot * 17
    ) & 0xFFFFFFFF
    rng = random.Random(seed_int)
    if local:
        dlat, dlon = DESIGN_PREVIEW_LOCAL_SPAN_DEG
    else:
        dlat, dlon = DESIGN_PREVIEW_WIDE_SPAN_DEG
    lat = DESIGN_PREVIEW_MAP_CENTER[0] + rng.uniform(-0.5 * dlat, 0.5 * dlat)
    lon = DESIGN_PREVIEW_MAP_CENTER[1] + rng.uniform(-0.5 * dlon, 0.5 * dlon)
    return lat, lon


@dataclass(frozen=True)
class DesignMapPreviewConfig:
    """Snapshot of sidebar controls used to build the preview map."""

    preview_scope: str
    map_style: str
    height_px: int
    # Resolved circle radii (px): map collection uses global default unless overridden in the scheme.
    marker_default_radius_px: int
    marker_radius_locations: int
    marker_radius_species: int
    marker_radius_species_map_background: int
    marker_radius_lifer_map_lifer: int
    marker_radius_lifer_map_subspecies: int
    marker_radius_families: int
    stroke_weight_visit: int
    stroke_weight_species: int
    stroke_weight_species_map_background: int
    stroke_weight_lifer: int
    stroke_weight_family: int
    stroke_weight_family_highlight: int
    # Resolved fill opacities (``marker_default_fill_opacity`` unless overridden in scheme).
    marker_fill_opacity_locations: float
    marker_fill_opacity_species: float
    marker_fill_opacity_species_map_background: float
    marker_fill_opacity_lifer_map_lifer: float
    marker_fill_opacity_lifer_map_subspecies: float
    marker_fill_opacity_families: float
    # Align with ``MapMarkerColourScheme.global_defaults.*`` (design export / future wiring).
    marker_default_fill_hex: str
    marker_default_stroke_hex: str
    marker_default_fill_opacity: float
    marker_default_stroke_weight: int
    # Visit-map style markers — map to ``all_locations`` / ``species_locations`` / … on export.
    default_stroke_hex: str
    default_fill_hex: str
    species_map_background_stroke_hex: str
    species_map_background_fill_hex: str
    species_stroke_hex: str
    species_fill_hex: str
    species_lifer_stroke_hex: str
    species_lifer_fill_hex: str
    lifer_map_lifer_stroke_hex: str
    lifer_map_lifer_fill_hex: str
    lifer_map_subspecies_stroke_hex: str
    lifer_map_subspecies_fill_hex: str
    last_seen_stroke_hex: str
    last_seen_fill_hex: str
    # Family density bands 0..3
    family_fill_hex: tuple[str, str, str, str]
    family_stroke_hex: tuple[str, str, str, str]
    family_highlight_stroke_hex: str
    # Swatch fill for the family-map highlight legend row (mirrors ``family_locations.legend_highlight_band_index``).
    legend_highlight_band_index: int
    # Optional MarkerCluster icon colours as:
    # ``(small_fill, small_border, small_halo, medium_fill, medium_border, medium_halo, large_fill, large_border, large_halo)``.
    marker_cluster_tier_icon_hex: tuple[str, str, str, str, str, str, str, str, str] | None
    # Rgba / geometry for custom cluster icons (see ``MAP_MARKER_CLUSTER_*_DEFAULT`` in defaults).
    marker_cluster_inner_fill_opacity: float
    marker_cluster_halo_opacity: float
    marker_cluster_border_opacity: float
    marker_cluster_halo_spread_px: int
    marker_cluster_border_width_px: int


# Bottom-left legend: species map order matches ``map_overlay_visit_map`` (refs #147): Species → Locations → Lifer → Last seen;
# all-locations-only row when that scope is selected; then lifer-map extras; then family bands.
_LEGEND_KIND_ORDER: tuple[str, ...] = (
    "visit_species",
    "visit_species_map_locations",
    "species_visit_lifer",
    "visit_last_seen",
    "visit_all_locations",
    "lifer_map_lifer",
    "lifer_subspecies",
    "family_0",
    "family_1",
    "family_2",
    "family_3",
)


def _circle_radius_px_for_marker_kind(cfg: DesignMapPreviewConfig, kind: str) -> int:
    """Resolved CircleMarker radius for this marker row (per-map collection overrides)."""
    if kind == "visit_all_locations":
        return cfg.marker_radius_locations
    if kind == "visit_species_map_locations":
        return cfg.marker_radius_species_map_background
    if kind in ("visit_species", "visit_last_seen"):
        return cfg.marker_radius_species
    if kind == "species_visit_lifer":
        return cfg.marker_radius_species
    if kind == "lifer_map_lifer":
        return cfg.marker_radius_lifer_map_lifer
    if kind == "lifer_subspecies":
        return cfg.marker_radius_lifer_map_subspecies
    if kind.startswith("family"):
        return cfg.marker_radius_families
    return cfg.marker_default_radius_px


def _legend_entry_for_kind(kind: str, cfg: DesignMapPreviewConfig) -> tuple[str, str, str] | None:
    """One ``build_legend_html`` row: ``(stroke_hex, fill_hex, label)``."""
    if kind == "visit_all_locations":
        return (cfg.default_stroke_hex, cfg.default_fill_hex, "All locations")
    if kind == "visit_species_map_locations":
        return (
            normalize_hex_colour(cfg.species_map_background_stroke_hex),
            normalize_hex_colour(cfg.species_map_background_fill_hex),
            "Locations",
        )
    if kind == "visit_species":
        return (
            normalize_hex_colour(cfg.species_stroke_hex),
            normalize_hex_colour(cfg.species_fill_hex),
            "Species",
        )
    if kind == "species_visit_lifer":
        return (
            normalize_hex_colour(cfg.species_lifer_stroke_hex),
            normalize_hex_colour(cfg.species_lifer_fill_hex),
            "Lifer",
        )
    if kind == "visit_last_seen":
        return (
            normalize_hex_colour(cfg.last_seen_stroke_hex),
            normalize_hex_colour(cfg.last_seen_fill_hex),
            "Last seen",
        )
    if kind == "lifer_map_lifer":
        return (
            normalize_hex_colour(cfg.lifer_map_lifer_stroke_hex),
            normalize_hex_colour(cfg.lifer_map_lifer_fill_hex),
            "Lifer",
        )
    if kind == "lifer_subspecies":
        return (
            normalize_hex_colour(cfg.lifer_map_subspecies_stroke_hex),
            normalize_hex_colour(cfg.lifer_map_subspecies_fill_hex),
            "Subspecies",
        )
    if kind.startswith("family_"):
        bi = int(kind.rsplit("_", 1)[-1])
        if 0 <= bi < len(DENSITY_BAND_LABELS):
            lab = f"{DENSITY_BAND_LABELS[bi]} species at location"
            return (
                normalize_hex_colour(cfg.family_stroke_hex[bi]),
                normalize_hex_colour(cfg.family_fill_hex[bi]),
                lab,
            )
    return None


def _design_legend_items(cfg: DesignMapPreviewConfig, rows: tuple[PreviewMarkerRow, ...]) -> list[tuple[str, str, str]]:
    """Legend tuples for the marker kinds currently shown (same HTML helper as production maps)."""
    kinds_present = {r.kind for r in rows}
    items: list[tuple[str, str, str]] = []
    for kind in _LEGEND_KIND_ORDER:
        if kind not in kinds_present:
            continue
        entry = _legend_entry_for_kind(kind, cfg)
        if entry is not None:
            items.append(entry)
    if kinds_present & {"family_0", "family_1", "family_2", "family_3"}:
        sw_i = max(0, min(int(cfg.legend_highlight_band_index), len(cfg.family_fill_hex) - 1))
        items.append(
            (
                normalize_hex_colour(cfg.family_highlight_stroke_hex),
                normalize_hex_colour(cfg.family_fill_hex[sw_i]),
                "Highlight: preview",
            )
        )
    return items


def _family_highlight_copy(copy_index: int) -> bool:
    """Highlight stroke on copies 0 (Canberra cluster) and 2 (wide scatter) so both are visible."""
    return copy_index == 0 or copy_index == 2


def _popup_text(kind: str, cfg: DesignMapPreviewConfig, *, copy_index: int) -> str:
    """Popup line (plain text; matches legend labels where applicable)."""
    if kind == "visit_all_locations":
        return "All locations"
    if kind == "visit_species_map_locations":
        return "Locations (species map)"
    if kind == "visit_species":
        return "Species"
    if kind == "species_visit_lifer":
        return "Lifer (species map)"
    if kind == "lifer_map_lifer":
        return "Lifer (lifer map)"
    if kind == "visit_last_seen":
        return "Last seen"
    if kind == "lifer_subspecies":
        return "Subspecies"
    if kind.startswith("family"):
        bi = int(kind[-1])
        base = f"{DENSITY_BAND_LABELS[bi]} species at location"
        if copy_index == 0:
            return f"{base} — highlight stroke (cluster)"
        if copy_index == 2:
            return f"{base} — highlight stroke (spread)"
        return base
    return kind


def _cluster_demo_jittered_locations(
    anchor_lat: float,
    anchor_lon: float,
    n: int,
    rng: random.Random,
) -> list[tuple[float, float]]:
    j = DESIGN_PREVIEW_CLUSTER_JITTER_DEG
    return [
        (
            anchor_lat + rng.uniform(-j, j),
            anchor_lon + rng.uniform(-j, j),
        )
        for _ in range(n)
    ]


def _add_seq_cluster_marker_demo(
    m: folium.Map,
    cfg: DesignMapPreviewConfig,
    *,
    position_seed: int,
) -> None:
    """Synthetic ``visit_all_locations`` circles in a ``MarkerCluster`` near SEQ (not Canberra)."""
    icon_fn = _marker_cluster_icon_create_function_from_scheme(cfg)
    if icon_fn is not None:
        m.get_root().html.add_child(Element(_marker_cluster_root_background_reset_css()))

    marker_cluster = MarkerCluster(
        name="SEQ cluster demo",
        icon_create_function=icon_fn,
        options={
            "maxClusterRadius": MAP_DEFAULT_LOCATION_CLUSTER_MAX_RADIUS_PX,
            "disableClusteringAtZoom": MAP_DEFAULT_LOCATION_CLUSTER_DISABLE_AT_ZOOM,
            "spiderfyOnMaxZoom": MAP_DEFAULT_LOCATION_CLUSTER_SPIDERFY_ON_MAX_ZOOM,
            "zoomToBoundsOnClick": True,
        },
    )

    rng = random.Random(int(position_seed) + 9001)
    radius_px = max(1, int(_circle_radius_px_for_marker_kind(cfg, "visit_all_locations")))
    stroke, fill_c = cfg.default_stroke_hex, cfg.default_fill_hex
    fo = max(0.0, min(1.0, cfg.marker_fill_opacity_locations))
    sw = max(1, int(cfg.stroke_weight_visit))

    for anchor_lat, anchor_lon, n, tier_label in DESIGN_PREVIEW_CLUSTER_DEMO_ANCHORS:
        for loc in _cluster_demo_jittered_locations(anchor_lat, anchor_lon, n, rng):
            label_esc = html_module.escape(
                f"SEQ cluster demo — {tier_label} (synthetic)",
                quote=False,
            )
            popup_html = f'<div class="pebird-map-popup"><p style="margin:0;">{label_esc}</p></div>'
            folium.CircleMarker(
                location=loc,
                radius=radius_px,
                color=stroke,
                weight=sw,
                fill=True,
                fill_color=fill_c,
                fill_opacity=fo,
                popup=folium.Popup(popup_html, max_width=MAP_POPUP_MAX_WIDTH_PX),
            ).add_to(marker_cluster)

    marker_cluster.add_to(m)


def build_design_preview_map(
    cfg: DesignMapPreviewConfig,
    *,
    position_seed: int = 42,
) -> folium.Map:
    """Return a Folium map with dummy markers; initial zoom matches :func:`create_map` (5)."""
    m = create_map(DESIGN_PREVIEW_MAP_CENTER, cfg.map_style, height_px=cfg.height_px)
    m.get_root().html.add_child(Element(map_overlay_theme_stylesheet()))
    m.get_root().html.add_child(Element(map_popup_width_fix_script()))

    rows = _rows_for_scope(cfg.preview_scope)
    legend_items = _design_legend_items(cfg, rows)
    if legend_items:
        m.get_root().html.add_child(Element(build_legend_html(legend_items)))

    visit_emphasis_specs: list[tuple[str, tuple[str, str]]] = [
        ("visit_species", (cfg.species_stroke_hex, cfg.species_fill_hex)),
        ("species_visit_lifer", (cfg.species_lifer_stroke_hex, cfg.species_lifer_fill_hex)),
        ("visit_last_seen", (cfg.last_seen_stroke_hex, cfg.last_seen_fill_hex)),
    ]

    _loc_memo: dict[tuple[tuple[str, int], bool], tuple[float, float]] = {}

    def _memo_loc(kind: str, copy_index: int, type_slot: int, local: bool) -> tuple[float, float]:
        key = (kind, copy_index, local)
        if key not in _loc_memo:
            _loc_memo[key] = _location_for_marker(kind, copy_index, type_slot, position_seed, local=local)
        return _loc_memo[key]

    for type_slot, row in enumerate(rows):
        kind = row.kind
        for copy_index in range(DESIGN_PREVIEW_MARKER_COPY_COUNT):
            # Eight copies per marker kind: (copy_index % 4) < 2 → tight local span, else wide span (two cluster pairs, two spread pairs).
            local = (copy_index % 4) < 2
            loc = _memo_loc(kind, copy_index, type_slot, local)

            fill = True
            radius_px = max(1, int(_circle_radius_px_for_marker_kind(cfg, kind)))
            if kind == "visit_all_locations":
                stroke, fill_c = cfg.default_stroke_hex, cfg.default_fill_hex
                fo = max(0.0, min(1.0, cfg.marker_fill_opacity_locations))
                sw = max(1, int(cfg.stroke_weight_visit))
            elif kind == "visit_species_map_locations":
                stroke = normalize_hex_colour(cfg.species_map_background_stroke_hex)
                fill_c = normalize_hex_colour(cfg.species_map_background_fill_hex)
                fo = max(0.0, min(1.0, cfg.marker_fill_opacity_species_map_background))
                sw = max(1, int(cfg.stroke_weight_species_map_background))
            elif kind == "visit_species":
                _slug, (e, f) = next(x for x in visit_emphasis_specs if x[0] == kind)
                stroke = normalize_hex_colour(e)
                fill_c = normalize_hex_colour(f)
                fo = max(0.0, min(1.0, cfg.marker_fill_opacity_species))
                sw = max(1, int(cfg.stroke_weight_species))
            elif kind == "species_visit_lifer":
                _slug, (e, f) = next(x for x in visit_emphasis_specs if x[0] == kind)
                stroke = normalize_hex_colour(e)
                fill_c = normalize_hex_colour(f)
                fo = max(0.0, min(1.0, cfg.marker_fill_opacity_species))
                sw = max(1, int(cfg.stroke_weight_species))
            elif kind == "lifer_map_lifer":
                stroke = normalize_hex_colour(cfg.lifer_map_lifer_stroke_hex)
                fill_c = normalize_hex_colour(cfg.lifer_map_lifer_fill_hex)
                fo = max(0.0, min(1.0, cfg.marker_fill_opacity_lifer_map_lifer))
                sw = max(1, int(cfg.stroke_weight_lifer))
            elif kind == "visit_last_seen":
                _slug, (e, f) = next(x for x in visit_emphasis_specs if x[0] == kind)
                stroke = normalize_hex_colour(e)
                fill_c = normalize_hex_colour(f)
                fo = max(0.0, min(1.0, cfg.marker_fill_opacity_species))
                sw = max(1, int(cfg.stroke_weight_species))
            elif kind == "lifer_subspecies":
                stroke = normalize_hex_colour(cfg.lifer_map_subspecies_stroke_hex)
                fill_c = normalize_hex_colour(cfg.lifer_map_subspecies_fill_hex)
                fo = max(0.0, min(1.0, cfg.marker_fill_opacity_lifer_map_subspecies))
                sw = max(1, int(cfg.stroke_weight_lifer))
            else:
                bi = int(kind[-1])
                stroke = normalize_hex_colour(cfg.family_stroke_hex[bi])
                fill_c = normalize_hex_colour(cfg.family_fill_hex[bi])
                if _family_highlight_copy(copy_index):
                    stroke = normalize_hex_colour(cfg.family_highlight_stroke_hex)
                    sw = max(1, int(cfg.stroke_weight_family_highlight))
                else:
                    sw = max(1, int(cfg.stroke_weight_family))
                fo = max(0.0, min(1.0, cfg.marker_fill_opacity_families))

            label_esc = html_module.escape(_popup_text(kind, cfg, copy_index=copy_index), quote=False)
            popup_html = f'<div class="pebird-map-popup"><p style="margin:0;">{label_esc}</p></div>'
            kw: dict = dict(
                location=loc,
                radius=radius_px,
                color=stroke,
                weight=sw,
                fill=fill,
                popup=folium.Popup(popup_html, max_width=MAP_POPUP_MAX_WIDTH_PX),
            )
            if fill:
                kw["fill_color"] = fill_c
                kw["fill_opacity"] = fo
            folium.CircleMarker(**kw).add_to(m)

    if cfg.preview_scope in (MAP_SCOPE_ALL, MAP_SCOPE_ALL_LOCATIONS):
        _add_seq_cluster_marker_demo(m, cfg, position_seed=position_seed)

    return m


def scheme_seed_config(
    scheme_index: int,
    *,
    map_style: str = "default",
    height_px: int = 720,
    preview_scope: str = MAP_SCOPE_ALL,
) -> DesignMapPreviewConfig:
    """Build a config from :func:`explorer.app.streamlit.defaults.active_map_marker_colour_scheme`."""
    from explorer.app.streamlit.defaults import (
        MAP_MARKER_CLUSTER_BORDER_OPACITY_DEFAULT,
        MAP_MARKER_CLUSTER_BORDER_WIDTH_PX_DEFAULT,
        MAP_MARKER_CLUSTER_HALO_OPACITY_DEFAULT,
        MAP_MARKER_CLUSTER_HALO_SPREAD_PX_DEFAULT,
        MAP_MARKER_CLUSTER_INNER_FILL_OPACITY_DEFAULT,
        active_map_marker_colour_scheme,
    )

    sch = active_map_marker_colour_scheme(scheme_index)
    fb_fo = MARKER_SCHEME_FALLBACK_DEFAULT_FILL_OPACITY
    fb_sw = MARKER_SCHEME_FALLBACK_DEFAULT_STROKE_WEIGHT

    g_fill, g_stroke = resolve_marker_global_colours(sch)
    d_fill, d_stroke = resolve_location_visit_colours(sch)
    sp_fill, sp_stroke = resolve_species_colours(sch)
    smap_fill, smap_stroke = resolve_species_map_background_colours(sch)
    sml_fill, sml_stroke = resolve_species_map_lifer_colours(sch)
    lml_fill, lml_stroke = resolve_lifer_map_lifer_colours(sch)
    lms_fill, lms_stroke = resolve_lifer_map_subspecies_colours(sch)
    ls_fill, ls_stroke = resolve_last_seen_colours(sch)
    fills = tuple(resolve_family_band_colours(sch, i)[0] for i in range(4))
    strokes = tuple(resolve_family_band_colours(sch, i)[1] for i in range(4))
    g = sch.global_defaults
    al = sch.all_locations
    sp = sch.species_locations
    smb = sch.species_map_background
    ll = sch.lifer_locations
    fam = sch.family_locations
    cl = al.cluster
    hl_stroke = normalize_marker_hex(str(fam.highlight_stroke_hex), channel="edge")

    def _int_or_fb(v: object, fallback: int) -> int:
        try:
            return max(1, int(v)) if v is not None else fallback
        except (TypeError, ValueError):
            return fallback

    def _marker_default_radius() -> int:
        v = getattr(g, "radius_px", None)
        if v is None:
            return clamp_map_marker_circle_radius_px(MAP_MARKER_CIRCLE_RADIUS_PX_FALLBACK)
        try:
            return clamp_map_marker_circle_radius_px(int(v))
        except (TypeError, ValueError):
            return clamp_map_marker_circle_radius_px(MAP_MARKER_CIRCLE_RADIUS_PX_FALLBACK)

    def _collection_radius(override: int | None, md: int) -> int:
        if override is None:
            return md
        try:
            return clamp_map_marker_circle_radius_px(int(override))
        except (TypeError, ValueError):
            return md

    md = _marker_default_radius()
    md_fo = clamp_map_marker_circle_fill_opacity(
        getattr(g, "fill_opacity", None),
        fallback=fb_fo,
    )
    md_sw = _int_or_fb(getattr(g, "stroke_weight", None), fb_sw)
    rl = _collection_radius(al.radius_px, md)
    rs = _collection_radius(sp.radius_px, md)
    r_smb = _collection_radius(smb.radius_px, md)
    r_lml = _collection_radius(ll.lifer_radius_px, md)
    r_lms = _collection_radius(ll.subspecies_radius_px, md)
    rf = _collection_radius(fam.radius_px_override, md)

    def _collection_fill_opacity(override: float | None, legacy: float) -> float:
        if override is not None:
            return clamp_map_marker_circle_fill_opacity(override, fallback=md_fo)
        return clamp_map_marker_circle_fill_opacity(legacy, fallback=md_fo)

    legacy_loc = float(al.fill_opacity) if al.fill_opacity is not None else md_fo
    fo_loc = _collection_fill_opacity(al.fill_opacity_override, legacy_loc)
    legacy_spec = float(sp.fill_opacity) if sp.fill_opacity is not None else md_fo
    fo_spec = _collection_fill_opacity(sp.fill_opacity_override, legacy_spec)
    legacy_smb = float(smb.fill_opacity) if smb.fill_opacity is not None else md_fo
    fo_smb = _collection_fill_opacity(smb.fill_opacity_override, legacy_smb)
    legacy_lml = float(ll.lifer_fill_opacity) if ll.lifer_fill_opacity is not None else md_fo
    fo_lml = _collection_fill_opacity(ll.lifer_fill_opacity_override, legacy_lml)
    legacy_lms = float(ll.subspecies_fill_opacity) if ll.subspecies_fill_opacity is not None else md_fo
    fo_lms = _collection_fill_opacity(ll.subspecies_fill_opacity_override, legacy_lms)
    fo_fam = _collection_fill_opacity(
        fam.fill_opacity_override, float(fam.fill_opacity)
    )

    def _optional_cluster_tier_icon_hex() -> tuple[str, str, str, str, str, str, str, str, str] | None:
        v = getattr(cl, "tier_icon_hex", None)
        if v is None:
            return None
        if not isinstance(v, tuple) or len(v) != 9:
            return None
        return (
            normalize_marker_hex(str(v[0]), channel="fill"),
            normalize_marker_hex(str(v[1]), channel="edge"),
            normalize_marker_hex(str(v[2]), channel="fill"),
            normalize_marker_hex(str(v[3]), channel="fill"),
            normalize_marker_hex(str(v[4]), channel="edge"),
            normalize_marker_hex(str(v[5]), channel="fill"),
            normalize_marker_hex(str(v[6]), channel="fill"),
            normalize_marker_hex(str(v[7]), channel="edge"),
            normalize_marker_hex(str(v[8]), channel="fill"),
        )

    def _cluster_style_float(attr: str, default: float) -> float:
        v = getattr(cl, attr, None)
        if v is None:
            return default
        try:
            return max(0.0, min(1.0, float(v)))
        except (TypeError, ValueError):
            return default

    def _cluster_style_int(attr: str, default: int, *, lo: int, hi: int) -> int:
        v = getattr(cl, attr, None)
        if v is None:
            return default
        try:
            return max(lo, min(hi, int(v)))
        except (TypeError, ValueError):
            return default

    _inner_fo = _cluster_style_float("inner_fill_opacity", MAP_MARKER_CLUSTER_INNER_FILL_OPACITY_DEFAULT)
    _halo_o = _cluster_style_float("halo_opacity", MAP_MARKER_CLUSTER_HALO_OPACITY_DEFAULT)
    _border_o = _cluster_style_float("border_opacity", MAP_MARKER_CLUSTER_BORDER_OPACITY_DEFAULT)
    _halo_sp = _cluster_style_int("halo_spread_px", MAP_MARKER_CLUSTER_HALO_SPREAD_PX_DEFAULT, lo=0, hi=24)
    _bw = _cluster_style_int("border_width_px", MAP_MARKER_CLUSTER_BORDER_WIDTH_PX_DEFAULT, lo=0, hi=8)

    return DesignMapPreviewConfig(
        preview_scope=preview_scope,
        map_style=map_style,
        height_px=height_px,
        marker_default_radius_px=md,
        marker_radius_locations=rl,
        marker_radius_species=rs,
        marker_radius_species_map_background=r_smb,
        marker_radius_lifer_map_lifer=r_lml,
        marker_radius_lifer_map_subspecies=r_lms,
        marker_radius_families=rf,
        stroke_weight_visit=_int_or_fb(al.stroke_weight, md_sw),
        stroke_weight_species=_int_or_fb(
            getattr(sp, "stroke_weight_override", None), _int_or_fb(al.stroke_weight, md_sw)
        ),
        stroke_weight_species_map_background=_int_or_fb(smb.stroke_weight, md_sw),
        stroke_weight_lifer=_int_or_fb(
            getattr(ll, "stroke_weight_override", None), _int_or_fb(al.stroke_weight, md_sw)
        ),
        stroke_weight_family=max(1, int(fam.stroke_weight)),
        stroke_weight_family_highlight=max(1, int(fam.highlight_stroke_weight)),
        marker_fill_opacity_locations=fo_loc,
        marker_fill_opacity_species=fo_spec,
        marker_fill_opacity_species_map_background=fo_smb,
        marker_fill_opacity_lifer_map_lifer=fo_lml,
        marker_fill_opacity_lifer_map_subspecies=fo_lms,
        marker_fill_opacity_families=fo_fam,
        marker_default_fill_hex=g_fill,
        marker_default_stroke_hex=g_stroke,
        marker_default_fill_opacity=md_fo,
        marker_default_stroke_weight=max(1, md_sw),
        default_stroke_hex=d_stroke,
        default_fill_hex=d_fill,
        species_map_background_stroke_hex=smap_stroke,
        species_map_background_fill_hex=smap_fill,
        species_stroke_hex=sp_stroke,
        species_fill_hex=sp_fill,
        species_lifer_stroke_hex=sml_stroke,
        species_lifer_fill_hex=sml_fill,
        lifer_map_lifer_stroke_hex=lml_stroke,
        lifer_map_lifer_fill_hex=lml_fill,
        lifer_map_subspecies_stroke_hex=lms_stroke,
        lifer_map_subspecies_fill_hex=lms_fill,
        last_seen_stroke_hex=ls_stroke,
        last_seen_fill_hex=ls_fill,
        family_fill_hex=fills,
        family_stroke_hex=strokes,
        family_highlight_stroke_hex=hl_stroke,
        legend_highlight_band_index=max(0, min(int(fam.legend_highlight_band_index), 3)),
        marker_cluster_tier_icon_hex=_optional_cluster_tier_icon_hex(),
        marker_cluster_inner_fill_opacity=_inner_fo,
        marker_cluster_halo_opacity=_halo_o,
        marker_cluster_border_opacity=_border_o,
        marker_cluster_halo_spread_px=_halo_sp,
        marker_cluster_border_width_px=_bw,
    )
