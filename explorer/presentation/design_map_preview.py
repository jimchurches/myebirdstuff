"""
Folium preview map for the **Map marker design** Streamlit utility.

Builds a fixed Canberra-centred map at the same initial zoom as :func:`create_map` (zoom 5) with
dummy ``CircleMarker`` markers for each visit-map and family-map role. No UI dependencies.
"""

from __future__ import annotations

import html as html_module
import random
import re
from dataclasses import dataclass

import folium
from branca.element import Element

from explorer.app.streamlit.defaults import (
    MAP_MARKER_CIRCLE_RADIUS_PX_FALLBACK,
    MAP_POPUP_MAX_WIDTH_PX,
    clamp_map_marker_circle_fill_opacity,
    clamp_map_marker_circle_radius_px,
)
from explorer.core.family_map_compute import DENSITY_BAND_LABELS
from explorer.core.map_marker_colour_resolve import (
    MAP_MARKER_CATCHALL_EDGE_HEX,
    normalize_marker_hex,
    resolve_family_band_colours,
    resolve_last_seen_colours,
    resolve_lifer_colours,
    resolve_location_visit_colours,
    resolve_marker_global_colours,
    resolve_species_colours,
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

_HEX_RE = re.compile(r"^#([0-9A-Fa-f]{3}|[0-9A-Fa-f]{6}|[0-9A-Fa-f]{8})$")

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


def normalize_hex_colour(raw: str, *, fallback: str = MAP_MARKER_CATCHALL_EDGE_HEX) -> str:
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
    # Same scopes as production visit map default markers — not lifer-only or family-only maps.
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
    # Resolved circle radii (px): map collection uses global default unless overridden in the scheme.
    marker_default_circle_radius_px: int
    marker_circle_radius_locations: int
    marker_circle_radius_species: int
    marker_circle_radius_lifers: int
    marker_circle_radius_families: int
    stroke_weight_visit: int
    stroke_weight_family: int
    stroke_weight_family_highlight: int
    # Resolved circle fill opacities (``marker_default_circle_fill_opacity`` unless overridden in scheme).
    marker_circle_fill_opacity_locations: float
    marker_circle_fill_opacity_species: float
    marker_circle_fill_opacity_lifers: float
    marker_circle_fill_opacity_families: float
    # Align with ``MapMarkerColourScheme.marker_default_*`` (design export / future wiring).
    marker_default_fill_hex: str
    marker_default_edge_hex: str
    marker_default_circle_fill_opacity: float
    marker_default_base_stroke_weight: int
    # Visit-map style markers — map to ``marker_location_visit_*`` / ``marker_species_*`` / … on export.
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
    # Optional All-locations MarkerCluster tier fills (small → medium → large); ``None`` = Folium defaults.
    marker_cluster_tier_fill_hex: tuple[str, str, str] | None


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


def _circle_radius_px_for_marker_kind(cfg: DesignMapPreviewConfig, kind: str) -> int:
    """Resolved CircleMarker radius for this marker row (per-map collection overrides)."""
    if kind == "visit_default":
        return cfg.marker_circle_radius_locations
    if kind in ("visit_species", "visit_last_seen"):
        return cfg.marker_circle_radius_species
    if kind in ("visit_lifer", "lifer_subspecies", "lifer_both_outer", "lifer_both_inner"):
        return cfg.marker_circle_radius_lifers
    if kind.startswith("family"):
        return cfg.marker_circle_radius_families
    return cfg.marker_default_circle_radius_px


def _legend_entry_for_kind(kind: str, cfg: DesignMapPreviewConfig) -> tuple[str, str, str] | None:
    """One ``build_legend_html`` row: ``(stroke_hex, fill_hex, label)``."""
    if kind == "visit_default":
        lab = (
            "All locations"
            if cfg.preview_scope == MAP_SCOPE_ALL_LOCATIONS
            else "Default location marker"
        )
        return (cfg.default_edge, cfg.default_fill, lab)
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
            normalize_hex_colour(cfg.marker_default_fill_hex),
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


def _family_highlight_copy(copy_index: int) -> bool:
    """Highlight stroke on copies 0 (Canberra cluster) and 2 (wide scatter) so both are visible."""
    return copy_index == 0 or copy_index == 2


def _popup_text(kind: str, cfg: DesignMapPreviewConfig, *, copy_index: int) -> str:
    """Popup line (plain text; matches legend labels where applicable)."""
    if kind == "visit_default":
        return (
            "All locations"
            if cfg.preview_scope == MAP_SCOPE_ALL_LOCATIONS
            else "Default location marker"
        )
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
            return f"{base} — highlight stroke (cluster)"
        if copy_index == 2:
            return f"{base} — highlight stroke (spread)"
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
        for copy_index in range(DESIGN_PREVIEW_MARKER_COPY_COUNT):
            # Each block of four: copies 0–1 local cluster; 2–3 broad scatter (refs #147 design utility).
            local = (copy_index % 4) < 2
            loc = _memo_loc(kind, copy_index, type_slot, local)

            fill = True
            radius_px = max(1, int(_circle_radius_px_for_marker_kind(cfg, kind)))
            if kind == "visit_default":
                stroke, fill_c = cfg.default_edge, cfg.default_fill
                fo = max(0.0, min(1.0, cfg.marker_circle_fill_opacity_locations))
                sw = max(1, int(cfg.stroke_weight_visit))
            elif kind == "visit_species":
                _slug, (e, f) = next(x for x in visit_emphasis_specs if x[0] == kind)
                stroke = normalize_hex_colour(e)
                fill_c = normalize_hex_colour(f)
                fo = max(0.0, min(1.0, cfg.marker_circle_fill_opacity_species))
                sw = max(1, int(cfg.stroke_weight_visit))
            elif kind == "visit_lifer":
                _slug, (e, f) = next(x for x in visit_emphasis_specs if x[0] == kind)
                stroke = normalize_hex_colour(e)
                fill_c = normalize_hex_colour(f)
                fo = max(0.0, min(1.0, cfg.marker_circle_fill_opacity_lifers))
                sw = max(1, int(cfg.stroke_weight_visit))
            elif kind == "visit_last_seen":
                _slug, (e, f) = next(x for x in visit_emphasis_specs if x[0] == kind)
                stroke = normalize_hex_colour(e)
                fill_c = normalize_hex_colour(f)
                fo = max(0.0, min(1.0, cfg.marker_circle_fill_opacity_species))
                sw = max(1, int(cfg.stroke_weight_visit))
            elif kind == "lifer_subspecies":
                stroke = normalize_hex_colour(cfg.species_edge)
                fill_c = normalize_hex_colour(cfg.species_fill)
                fo = max(0.0, min(1.0, cfg.marker_circle_fill_opacity_species))
                sw = max(1, int(cfg.stroke_weight_visit))
            elif kind == "lifer_both_outer":
                stroke = normalize_hex_colour(cfg.species_edge)
                fill_c = normalize_hex_colour(cfg.species_fill)
                fo = 0.0
                fill = False
                radius_px = max(1, int(_circle_radius_px_for_marker_kind(cfg, kind)) + 2)
                sw = max(1, int(cfg.stroke_weight_visit))
            elif kind == "lifer_both_inner":
                stroke = normalize_hex_colour(cfg.lifer_edge)
                fill_c = normalize_hex_colour(cfg.lifer_fill)
                fo = max(0.0, min(1.0, cfg.marker_circle_fill_opacity_lifers))
                sw = max(1, int(cfg.stroke_weight_visit))
            else:
                bi = int(kind[-1])
                stroke = normalize_hex_colour(cfg.family_stroke_hex[bi])
                fill_c = normalize_hex_colour(cfg.family_fill_hex[bi])
                if _family_highlight_copy(copy_index):
                    stroke = normalize_hex_colour(cfg.family_highlight_stroke_hex)
                    sw = max(1, int(cfg.stroke_weight_family_highlight))
                else:
                    sw = max(1, int(cfg.stroke_weight_family))
                fo = max(0.0, min(1.0, cfg.marker_circle_fill_opacity_families))

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
    fb_fo = MARKER_SCHEME_FALLBACK_DEFAULT_FILL_OPACITY
    fb_sw = MARKER_SCHEME_FALLBACK_DEFAULT_BASE_STROKE_WEIGHT

    g_fill, g_edge = resolve_marker_global_colours(sch)
    d_fill, d_edge = resolve_location_visit_colours(sch)
    sp_fill, sp_edge = resolve_species_colours(sch)
    lf_fill, lf_edge = resolve_lifer_colours(sch)
    ls_fill, ls_edge = resolve_last_seen_colours(sch)
    fills = tuple(resolve_family_band_colours(sch, i)[0] for i in range(4))
    strokes = tuple(resolve_family_band_colours(sch, i)[1] for i in range(4))
    hl_stroke = normalize_marker_hex(str(getattr(sch, "highlight_stroke_hex", "")), channel="edge")

    def _int_attr(attr: str, fallback: int) -> int:
        v = getattr(sch, attr, None)
        try:
            return max(1, int(v)) if v is not None else fallback
        except (TypeError, ValueError):
            return fallback

    def _marker_default_radius() -> int:
        v = getattr(sch, "marker_default_circle_radius_px", None)
        if v is None:
            return clamp_map_marker_circle_radius_px(MAP_MARKER_CIRCLE_RADIUS_PX_FALLBACK)
        try:
            return clamp_map_marker_circle_radius_px(int(v))
        except (TypeError, ValueError):
            return clamp_map_marker_circle_radius_px(MAP_MARKER_CIRCLE_RADIUS_PX_FALLBACK)

    def _collection_radius(attr: str, md: int) -> int:
        v = getattr(sch, attr, None)
        if v is None:
            return md
        try:
            return clamp_map_marker_circle_radius_px(int(v))
        except (TypeError, ValueError):
            return md

    md = _marker_default_radius()
    md_fo = clamp_map_marker_circle_fill_opacity(
        getattr(sch, "marker_default_circle_fill_opacity", None),
        fallback=fb_fo,
    )
    md_sw = _int_attr("marker_default_base_stroke_weight", fb_sw)
    rl = _collection_radius("marker_circle_radius_px_locations", md)
    rs = _collection_radius("marker_circle_radius_px_species", md)
    rli = _collection_radius("marker_circle_radius_px_lifers", md)
    rf = _collection_radius("marker_circle_radius_px_families", md)

    def _collection_fill_opacity(attr: str, legacy: float) -> float:
        v = getattr(sch, attr, None)
        if v is not None:
            return clamp_map_marker_circle_fill_opacity(v, fallback=md_fo)
        return clamp_map_marker_circle_fill_opacity(legacy, fallback=md_fo)

    fo_loc = _collection_fill_opacity("marker_circle_fill_opacity_locations", float(sch.visit_fill_opacity_all_locations))
    fo_spec = _collection_fill_opacity("marker_circle_fill_opacity_species", float(sch.visit_fill_opacity_emphasis))
    fo_lif = _collection_fill_opacity("marker_circle_fill_opacity_lifers", float(sch.visit_fill_opacity_lifers))
    fo_fam = _collection_fill_opacity("marker_circle_fill_opacity_families", float(sch.circle_marker_fill_opacity))

    def _optional_cluster_tiers() -> tuple[str, str, str] | None:
        v = getattr(sch, "marker_cluster_tier_fill_hex", None)
        if v is None:
            return None
        if not isinstance(v, tuple) or len(v) != 3:
            return None
        return (
            normalize_marker_hex(str(v[0]), channel="fill"),
            normalize_marker_hex(str(v[1]), channel="fill"),
            normalize_marker_hex(str(v[2]), channel="fill"),
        )

    return DesignMapPreviewConfig(
        preview_scope=preview_scope,
        map_style=map_style,
        height_px=height_px,
        marker_default_circle_radius_px=md,
        marker_circle_radius_locations=rl,
        marker_circle_radius_species=rs,
        marker_circle_radius_lifers=rli,
        marker_circle_radius_families=rf,
        stroke_weight_visit=max(1, int(sch.visit_stroke_weight)),
        stroke_weight_family=max(1, int(sch.base_stroke_weight)),
        stroke_weight_family_highlight=max(1, int(sch.highlight_stroke_weight)),
        marker_circle_fill_opacity_locations=fo_loc,
        marker_circle_fill_opacity_species=fo_spec,
        marker_circle_fill_opacity_lifers=fo_lif,
        marker_circle_fill_opacity_families=fo_fam,
        marker_default_fill_hex=g_fill,
        marker_default_edge_hex=g_edge,
        marker_default_circle_fill_opacity=md_fo,
        marker_default_base_stroke_weight=max(1, md_sw),
        default_edge=d_edge,
        default_fill=d_fill,
        species_edge=sp_edge,
        species_fill=sp_fill,
        lifer_edge=lf_edge,
        lifer_fill=lf_fill,
        last_seen_edge=ls_edge,
        last_seen_fill=ls_fill,
        family_fill_hex=fills,
        family_stroke_hex=strokes,
        family_highlight_stroke_hex=hl_stroke,
        legend_highlight_swatch_fill_index=max(0, min(int(sch.legend_highlight_swatch_fill_index), 3)),
        marker_cluster_tier_fill_hex=_optional_cluster_tiers(),
    )
