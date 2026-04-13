"""
Folium preview map for the **Map marker design** Streamlit utility.

Builds a fixed Canberra-centred map at the same initial zoom as :func:`create_map` (zoom 5) with
dummy ``CircleMarker`` pins for each visit-map and family-map role. No UI dependencies.
"""

from __future__ import annotations

import html as html_module
import random
import re
from dataclasses import dataclass

import folium
from branca.element import Element

from explorer.app.streamlit.defaults import MAP_POPUP_MAX_WIDTH_PX
from explorer.core.family_map_compute import DENSITY_BAND_LABELS
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

_HEX_RE = re.compile(r"^#([0-9A-Fa-f]{3}|[0-9A-Fa-f]{6}|[0-9A-Fa-f]{8})$")

# Undefined / invalid hex in the design utility (avoids clashing with red ramps; refs #147).
DESIGN_HEX_FALLBACK = "#FFFFFF"
# Hard fallbacks when :class:`~explorer.app.streamlit.defaults.MapMarkerColourScheme` omits marker defaults (refs #147).
MARKER_SCHEME_FALLBACK_DEFAULT_RADIUS_PX = 5
MARKER_SCHEME_FALLBACK_DEFAULT_FILL_OPACITY = 0.88
MARKER_SCHEME_FALLBACK_DEFAULT_BASE_STROKE_WEIGHT = 2

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


def normalize_hex_colour(raw: str, *, fallback: str = DESIGN_HEX_FALLBACK) -> str:
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


# Order: All locations → Species → Lifer (incl. subspecies / both rings) → Family bands.
# ``lifer_subspecies`` / ``lifer_both_*`` mirror :mod:`explorer.core.map_overlay_lifer_map` when
# subspecies lifers are enabled.
PREVIEW_MARKER_ROWS: tuple[PreviewMarkerRow, ...] = (
    PreviewMarkerRow("visit_default", frozenset({MAP_SCOPE_ALL_LOCATIONS, MAP_SCOPE_SPECIES_LOCATIONS})),
    PreviewMarkerRow("visit_species", frozenset({MAP_SCOPE_SPECIES_LOCATIONS})),
    PreviewMarkerRow("visit_lifer", frozenset({MAP_SCOPE_SPECIES_LOCATIONS, MAP_SCOPE_LIFER_LOCATIONS})),
    PreviewMarkerRow("visit_last_seen", frozenset({MAP_SCOPE_SPECIES_LOCATIONS})),
    PreviewMarkerRow("lifer_subspecies", frozenset({MAP_SCOPE_LIFER_LOCATIONS})),
    PreviewMarkerRow("lifer_both_outer", frozenset({MAP_SCOPE_LIFER_LOCATIONS})),
    PreviewMarkerRow("lifer_both_inner", frozenset({MAP_SCOPE_LIFER_LOCATIONS})),
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


def _location_key(kind: str, copy_index: int) -> tuple[str, int]:
    """Outer/inner ``both`` rings share the same coordinates per copy."""
    if kind in ("lifer_both_outer", "lifer_both_inner"):
        return ("lifer_both_pair", copy_index)
    return (kind, copy_index)


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
        int(position_seed) * 10009 + hash(_location_key(kind, copy_index)) % 100003 + type_slot * 17
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
    circle_radius_px: int
    stroke_weight_visit: int
    stroke_weight_family: int
    stroke_weight_family_highlight: int
    fill_opacity_all_locations: float
    fill_opacity_emphasis: float
    family_fill_opacity: float
    # Align with ``MapMarkerColourScheme.marker_default_*`` (design export / future wiring).
    marker_default_fill_hex: str
    marker_default_edge_hex: str
    marker_default_circle_radius_px: int
    marker_default_circle_fill_opacity: float
    marker_default_base_stroke_weight: int
    # Visit-map style pins — map to ``marker_location_visit_*`` / ``marker_species_*`` / … on export.
    default_edge: str
    default_fill: str
    species_edge: str
    species_fill: str
    lifer_edge: str
    lifer_fill: str
    last_seen_edge: str
    last_seen_fill: str
    # Family density bands 0..3
    family_fill_hex: tuple[str, str, str, str]
    family_stroke_hex: tuple[str, str, str, str]
    family_highlight_stroke_hex: str
    # Swatch fill for the family-map highlight legend row (:class:`~explorer.app.streamlit.defaults.MapMarkerColourScheme`).
    legend_highlight_swatch_fill_index: int


# Bottom-left legend row order: visit map matches ``map_overlay_visit_map`` (Lifer → Last seen → Species → Other);
# then lifer-map extras; then density bands (``DENSITY_BAND_LABELS`` + ``species at location``, same as family_map_folium).
_LEGEND_KIND_ORDER: tuple[str, ...] = (
    "visit_lifer",
    "visit_last_seen",
    "visit_species",
    "visit_default",
    "lifer_subspecies",
    "lifer_both_outer",
    "lifer_both_inner",
    "family_0",
    "family_1",
    "family_2",
    "family_3",
)


def _legend_entry_for_kind(kind: str, cfg: DesignMapPreviewConfig) -> tuple[str, str, str] | None:
    """One ``build_legend_html`` row: ``(stroke_hex, fill_hex, label)``."""
    if kind == "visit_default":
        lab = "All locations" if cfg.preview_scope == MAP_SCOPE_ALL_LOCATIONS else "Other"
        return (normalize_hex_colour(cfg.default_edge), normalize_hex_colour(cfg.default_fill), lab)
    if kind == "visit_species":
        return (normalize_hex_colour(cfg.species_edge), normalize_hex_colour(cfg.species_fill), "Species")
    if kind == "visit_lifer":
        return (normalize_hex_colour(cfg.lifer_edge), normalize_hex_colour(cfg.lifer_fill), "Lifer")
    if kind == "visit_last_seen":
        return (normalize_hex_colour(cfg.last_seen_edge), normalize_hex_colour(cfg.last_seen_fill), "Last seen")
    if kind == "lifer_subspecies":
        return (normalize_hex_colour(cfg.species_edge), normalize_hex_colour(cfg.species_fill), "Subspecies")
    if kind == "lifer_both_outer":
        return (
            normalize_hex_colour(cfg.species_edge),
            DESIGN_HEX_FALLBACK,
            "Both — outer ring",
        )
    if kind == "lifer_both_inner":
        return (normalize_hex_colour(cfg.lifer_edge), normalize_hex_colour(cfg.lifer_fill), "Both — inner fill")
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
        sw_i = max(0, min(int(cfg.legend_highlight_swatch_fill_index), len(cfg.family_fill_hex) - 1))
        items.append(
            (
                normalize_hex_colour(cfg.family_highlight_stroke_hex),
                normalize_hex_colour(cfg.family_fill_hex[sw_i]),
                "Highlight: preview",
            )
        )
    return items


def _popup_text(kind: str, cfg: DesignMapPreviewConfig, *, copy_index: int) -> str:
    """Popup line (plain text; matches legend labels where applicable)."""
    if kind == "visit_default":
        return "All locations" if cfg.preview_scope == MAP_SCOPE_ALL_LOCATIONS else "Other"
    if kind == "visit_species":
        return "Species"
    if kind == "visit_lifer":
        return "Lifer"
    if kind == "visit_last_seen":
        return "Last seen"
    if kind == "lifer_subspecies":
        return "Subspecies"
    if kind == "lifer_both_outer":
        return "Both — outer ring"
    if kind == "lifer_both_inner":
        return "Both — inner fill"
    if kind.startswith("family"):
        bi = int(kind[-1])
        base = f"{DENSITY_BAND_LABELS[bi]} species at location"
        if copy_index == 0:
            return f"{base} — highlight stroke"
        return base
    return kind


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
        ("visit_species", (cfg.species_edge, cfg.species_fill)),
        ("visit_lifer", (cfg.lifer_edge, cfg.lifer_fill)),
        ("visit_last_seen", (cfg.last_seen_edge, cfg.last_seen_fill)),
    ]

    _loc_memo: dict[tuple[tuple[str, int], bool], tuple[float, float]] = {}

    def _memo_loc(kind: str, copy_index: int, type_slot: int, local: bool) -> tuple[float, float]:
        lk = _location_key(kind, copy_index)
        key = (lk, local)
        if key not in _loc_memo:
            # Paired lifer “both” rings share one draw so inner/outer align (``map_overlay_lifer_map``).
            slot = 0 if lk[0] == "lifer_both_pair" else type_slot
            _loc_memo[key] = _location_for_marker(kind, copy_index, slot, position_seed, local=local)
        return _loc_memo[key]

    for type_slot, row in enumerate(rows):
        kind = row.kind
        for copy_index in range(4):
            # Copies 0–1: local cluster; 2–3: broad scatter (refs #147 design utility).
            local = copy_index < 2
            loc = _memo_loc(kind, copy_index, type_slot, local)

            fill = True
            radius_px = max(1, int(cfg.circle_radius_px))
            if kind == "visit_default":
                stroke = normalize_hex_colour(cfg.default_edge)
                fill_c = normalize_hex_colour(cfg.default_fill)
                fo = max(0.0, min(1.0, cfg.fill_opacity_all_locations))
                sw = max(1, int(cfg.stroke_weight_visit))
            elif kind in ("visit_species", "visit_lifer", "visit_last_seen"):
                _slug, (e, f) = next(x for x in visit_emphasis_specs if x[0] == kind)
                stroke = normalize_hex_colour(e)
                fill_c = normalize_hex_colour(f)
                fo = max(0.0, min(1.0, cfg.fill_opacity_emphasis))
                sw = max(1, int(cfg.stroke_weight_visit))
            elif kind == "lifer_subspecies":
                stroke = normalize_hex_colour(cfg.species_edge)
                fill_c = normalize_hex_colour(cfg.species_fill)
                fo = max(0.0, min(1.0, cfg.fill_opacity_emphasis))
                sw = max(1, int(cfg.stroke_weight_visit))
            elif kind == "lifer_both_outer":
                stroke = normalize_hex_colour(cfg.species_edge)
                fill_c = normalize_hex_colour(cfg.species_fill)
                fo = 0.0
                fill = False
                radius_px = max(1, int(cfg.circle_radius_px) + 2)
                sw = max(1, int(cfg.stroke_weight_visit))
            elif kind == "lifer_both_inner":
                stroke = normalize_hex_colour(cfg.lifer_edge)
                fill_c = normalize_hex_colour(cfg.lifer_fill)
                fo = max(0.0, min(1.0, cfg.fill_opacity_emphasis))
                sw = max(1, int(cfg.stroke_weight_visit))
            else:
                bi = int(kind[-1])
                stroke = normalize_hex_colour(cfg.family_stroke_hex[bi])
                fill_c = normalize_hex_colour(cfg.family_fill_hex[bi])
                if copy_index == 0:
                    stroke = normalize_hex_colour(cfg.family_highlight_stroke_hex)
                    sw = max(1, int(cfg.stroke_weight_family_highlight))
                else:
                    sw = max(1, int(cfg.stroke_weight_family))
                fo = max(0.0, min(1.0, cfg.family_fill_opacity))

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

    return m


def scheme_seed_config(
    scheme_index: int,
    *,
    map_style: str = "default",
    height_px: int = 720,
    preview_scope: str = MAP_SCOPE_ALL,
) -> DesignMapPreviewConfig:
    """Build a config from :func:`explorer.app.streamlit.defaults.active_map_marker_colour_scheme`."""
    from explorer.app.streamlit.defaults import active_map_marker_colour_scheme

    sch = active_map_marker_colour_scheme(scheme_index)
    fb_hex = DESIGN_HEX_FALLBACK
    fb_r = MARKER_SCHEME_FALLBACK_DEFAULT_RADIUS_PX
    fb_fo = MARKER_SCHEME_FALLBACK_DEFAULT_FILL_OPACITY
    fb_sw = MARKER_SCHEME_FALLBACK_DEFAULT_BASE_STROKE_WEIGHT

    def _hex(attr: str) -> str:
        v = getattr(sch, attr, None)
        return str(v) if isinstance(v, str) and v.strip() else fb_hex

    def _int_attr(attr: str, fallback: int) -> int:
        v = getattr(sch, attr, None)
        try:
            return max(1, int(v)) if v is not None else fallback
        except (TypeError, ValueError):
            return fallback

    def _float_attr(attr: str, fallback: float) -> float:
        v = getattr(sch, attr, None)
        try:
            return float(v) if v is not None else fallback
        except (TypeError, ValueError):
            return fallback

    fills = tuple(sch.density_fill_hex[i] for i in range(4))
    strokes = tuple(sch.density_stroke_hex[i] for i in range(4))
    cr = max(1, int(sch.circle_marker_radius_px))
    md_radius = _int_attr("marker_default_circle_radius_px", fb_r)
    md_fo = _float_attr("marker_default_circle_fill_opacity", fb_fo)
    md_sw = _int_attr("marker_default_base_stroke_weight", fb_sw)

    return DesignMapPreviewConfig(
        preview_scope=preview_scope,
        map_style=map_style,
        height_px=height_px,
        circle_radius_px=cr,
        stroke_weight_visit=max(1, int(sch.visit_stroke_weight)),
        stroke_weight_family=max(1, int(sch.base_stroke_weight)),
        stroke_weight_family_highlight=max(1, int(sch.highlight_stroke_weight)),
        fill_opacity_all_locations=float(sch.visit_fill_opacity_all_locations),
        fill_opacity_emphasis=float(sch.visit_fill_opacity_emphasis),
        family_fill_opacity=float(sch.circle_marker_fill_opacity),
        marker_default_fill_hex=_hex("marker_default_fill_hex"),
        marker_default_edge_hex=_hex("marker_default_edge_hex"),
        marker_default_circle_radius_px=md_radius,
        marker_default_circle_fill_opacity=md_fo,
        marker_default_base_stroke_weight=max(1, md_sw),
        default_edge=_hex("marker_location_visit_edge_hex"),
        default_fill=_hex("marker_location_visit_fill_hex"),
        species_edge=_hex("marker_species_edge_hex"),
        species_fill=_hex("marker_species_fill_hex"),
        lifer_edge=_hex("marker_lifer_edge_hex"),
        lifer_fill=_hex("marker_lifer_fill_hex"),
        last_seen_edge=_hex("marker_last_seen_edge_hex"),
        last_seen_fill=_hex("marker_last_seen_fill_hex"),
        family_fill_hex=fills,
        family_stroke_hex=strokes,
        family_highlight_stroke_hex=str(sch.highlight_stroke_hex),
        legend_highlight_swatch_fill_index=max(0, min(int(sch.legend_highlight_swatch_fill_index), 3)),
    )
