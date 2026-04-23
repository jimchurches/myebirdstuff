"""
Hierarchical map marker hex resolution for Folium circle markers, plus family-map **geometry**
(radius / fill opacity) derived from :class:`~explorer.app.streamlit.defaults.MapMarkerColourScheme`
so the explorer matches the map-marker design utility.

Resolution order for each channel (fill / stroke) independently:

(a) Role-specific hex on the colour scheme (and optional :class:`~explorer.core.map_marker_scheme_model.SchemeColourOverrides`).
(b) Global hex on the scheme — ``global_defaults.{fill,stroke}_hex``.
(c) Scheme defaults — :data:`MAP_MARKER_SCHEME_DEFAULT_FILL_HEX` /
    :data:`MAP_MARKER_SCHEME_DEFAULT_STROKE_HEX` (white fill, cream stroke).
(d) Catch-all outside any scheme — :data:`MAP_MARKER_CATCHALL_FILL_HEX` /
    :data:`MAP_MARKER_CATCHALL_STROKE_HEX` (same as (c); used when values are missing or invalid).

Invalid hex at any step is treated as missing and the chain continues.
"""

from __future__ import annotations

import re
from typing import Any, Literal

from explorer.app.streamlit.defaults import (
    MAP_CIRCLE_MARKER_STROKE_WEIGHT,
    MAP_MARKER_CIRCLE_RADIUS_PX_FALLBACK,
    clamp_map_marker_circle_fill_opacity,
    clamp_map_marker_circle_radius_px,
)

_HEX_RE = re.compile(r"^#([0-9A-Fa-f]{3}|[0-9A-Fa-f]{6}|[0-9A-Fa-f]{8})$")

# (c) Defaults inside a colour scheme when (a)/(b) are unset or invalid.
MAP_MARKER_SCHEME_DEFAULT_FILL_HEX = "#FFFFFF"
MAP_MARKER_SCHEME_DEFAULT_STROKE_HEX = "#FFF8E7"

# (d) Catch-all when the scheme cannot supply a valid colour (same as (c) by design).
MAP_MARKER_CATCHALL_FILL_HEX = MAP_MARKER_SCHEME_DEFAULT_FILL_HEX
MAP_MARKER_CATCHALL_STROKE_HEX = MAP_MARKER_SCHEME_DEFAULT_STROKE_HEX


def is_valid_hex_colour(raw: str | None) -> bool:
    """True if *raw* is a non-empty string that matches a ``#`` RGB hex form."""
    if raw is None:
        return False
    s = str(raw).strip()
    if not s:
        return False
    if not s.startswith("#"):
        s = f"#{s}"
    return bool(_HEX_RE.match(s[:9]))


def normalize_marker_hex(raw: str | None, *, channel: str) -> str:
    """Normalize to ``#RRGGBB``; invalid or empty uses catch-all for *channel* (``\"fill\"`` or ``\"edge\"``)."""
    fb = MAP_MARKER_CATCHALL_FILL_HEX if channel == "fill" else MAP_MARKER_CATCHALL_STROKE_HEX
    if raw is None:
        return fb
    s = str(raw).strip()
    if not s:
        return fb
    if not s.startswith("#"):
        s = f"#{s}"
    if _HEX_RE.match(s):
        return s[:7] if len(s) >= 7 else s
    return fb


def _resolve_channel(
    *,
    override: str | None,
    specific: str | None,
    global_: str | None,
    scheme_default: str,
    catchall: str,
) -> str:
    for raw in (override, specific, global_, scheme_default, catchall):
        if raw is None:
            continue
        if not is_valid_hex_colour(str(raw)):
            continue
        s = str(raw).strip()
        if not s.startswith("#"):
            s = f"#{s}"
        return s[:7] if len(s) >= 7 else s
    return catchall


def _overrides(sch: Any) -> Any:
    return getattr(sch, "colour_overrides", None)


def _global_defaults(sch: Any) -> Any:
    return getattr(sch, "global_defaults", sch)


def resolve_marker_global_colours(sch: Any) -> tuple[str, str]:
    """(b)→(c)→(d) for global default fill/stroke only."""
    g = _global_defaults(sch)
    o = _overrides(sch)
    fill_o = getattr(o, "default_fill_hex", None) if o else None
    stroke_o = getattr(o, "default_stroke_hex", None) if o else None
    fill = _resolve_channel(
        override=fill_o,
        specific=getattr(g, "fill_hex", None),
        global_=None,
        scheme_default=MAP_MARKER_SCHEME_DEFAULT_FILL_HEX,
        catchall=MAP_MARKER_CATCHALL_FILL_HEX,
    )
    stroke = _resolve_channel(
        override=stroke_o,
        specific=getattr(g, "stroke_hex", None),
        global_=None,
        scheme_default=MAP_MARKER_SCHEME_DEFAULT_STROKE_HEX,
        catchall=MAP_MARKER_CATCHALL_STROKE_HEX,
    )
    return normalize_marker_hex(fill, channel="fill"), normalize_marker_hex(stroke, channel="edge")


def resolve_location_visit_colours(sch: Any) -> tuple[str, str]:
    """Default / all-locations visit markers: (a)→(b)→(c)→(d)."""
    g = _global_defaults(sch)
    al = getattr(sch, "all_locations", sch)
    o = _overrides(sch)
    fill = _resolve_channel(
        override=getattr(o, "location_fill_hex", None) if o else None,
        specific=getattr(al, "fill_hex", None),
        global_=getattr(g, "fill_hex", None),
        scheme_default=MAP_MARKER_SCHEME_DEFAULT_FILL_HEX,
        catchall=MAP_MARKER_CATCHALL_FILL_HEX,
    )
    stroke = _resolve_channel(
        override=getattr(o, "location_stroke_hex", None) if o else None,
        specific=getattr(al, "stroke_hex", None),
        global_=getattr(g, "stroke_hex", None),
        scheme_default=MAP_MARKER_SCHEME_DEFAULT_STROKE_HEX,
        catchall=MAP_MARKER_CATCHALL_STROKE_HEX,
    )
    return normalize_marker_hex(fill, channel="fill"), normalize_marker_hex(stroke, channel="edge")


def resolve_species_map_background_colours(sch: Any) -> tuple[str, str]:
    """Background visit pins on the species-filtered map — independent of :func:`resolve_location_visit_colours`."""
    g = _global_defaults(sch)
    smb = getattr(sch, "species_map_background", None)
    o = _overrides(sch)
    if smb is None:
        return resolve_location_visit_colours(sch)
    fill = _resolve_channel(
        override=getattr(o, "species_background_fill_hex", None) if o else None,
        specific=getattr(smb, "fill_hex", None),
        global_=getattr(g, "fill_hex", None),
        scheme_default=MAP_MARKER_SCHEME_DEFAULT_FILL_HEX,
        catchall=MAP_MARKER_CATCHALL_FILL_HEX,
    )
    stroke = _resolve_channel(
        override=getattr(o, "species_background_stroke_hex", None) if o else None,
        specific=getattr(smb, "stroke_hex", None),
        global_=getattr(g, "stroke_hex", None),
        scheme_default=MAP_MARKER_SCHEME_DEFAULT_STROKE_HEX,
        catchall=MAP_MARKER_CATCHALL_STROKE_HEX,
    )
    return normalize_marker_hex(fill, channel="fill"), normalize_marker_hex(stroke, channel="edge")


def _collection_radius_px(override: int | None, md: int) -> int:
    if override is None:
        return md
    try:
        return clamp_map_marker_circle_radius_px(int(override))
    except (TypeError, ValueError):
        return md


def _collection_fill_opacity_visit(
    override: float | None, legacy: float, *, md_fo: float
) -> float:
    if override is not None:
        return clamp_map_marker_circle_fill_opacity(override, fallback=md_fo)
    return clamp_map_marker_circle_fill_opacity(legacy, fallback=md_fo)


def resolve_species_visit_pin(
    sch: Any, role: Literal["lifer", "last_seen", "species", "default"]
) -> tuple[str, str, int, int, float]:
    """Species-filtered visit overlay: stroke hex, fill hex, radius, stroke weight, fill opacity."""
    g = _global_defaults(sch)
    al = getattr(sch, "all_locations", sch)
    sp = getattr(sch, "species_locations", sch)
    smb = getattr(sch, "species_map_background", None)
    md = _map_marker_scheme_default_radius_px(sch)
    md_fo = clamp_map_marker_circle_fill_opacity(
        getattr(g, "fill_opacity", None),
        fallback=0.88,
    )

    def _emphasis_stroke_weight() -> int:
        sw_raw = getattr(sp, "stroke_weight_override", None)
        if sw_raw is None:
            al_sw = getattr(al, "stroke_weight", None)
            if al_sw is not None:
                sw_raw = al_sw
            else:
                sw_raw = getattr(g, "stroke_weight", MAP_CIRCLE_MARKER_STROKE_WEIGHT)
        return max(1, int(sw_raw))

    def _species_background_stroke_weight() -> int:
        if smb is not None:
            sw_raw = getattr(smb, "stroke_weight", None)
            if sw_raw is not None:
                return max(1, int(sw_raw))
        return max(1, int(getattr(g, "stroke_weight", MAP_CIRCLE_MARKER_STROKE_WEIGHT)))

    def _species_emphasis_fill_opacity() -> float:
        raw = getattr(sp, "fill_opacity", None)
        return float(raw) if raw is not None else md_fo

    if role == "lifer":
        fill, stroke = resolve_species_map_lifer_colours(sch)
        r = _collection_radius_px(getattr(sp, "radius_px", None), md)
        fo = _collection_fill_opacity_visit(
            getattr(sp, "fill_opacity_override", None),
            _species_emphasis_fill_opacity(),
            md_fo=md_fo,
        )
        sw = _emphasis_stroke_weight()
    elif role == "last_seen":
        fill, stroke = resolve_last_seen_colours(sch)
        r = _collection_radius_px(getattr(sp, "radius_px", None), md)
        fo = _collection_fill_opacity_visit(
            getattr(sp, "fill_opacity_override", None),
            _species_emphasis_fill_opacity(),
            md_fo=md_fo,
        )
        sw = _emphasis_stroke_weight()
    elif role == "species":
        fill, stroke = resolve_species_colours(sch)
        r = _collection_radius_px(getattr(sp, "radius_px", None), md)
        fo = _collection_fill_opacity_visit(
            getattr(sp, "fill_opacity_override", None),
            _species_emphasis_fill_opacity(),
            md_fo=md_fo,
        )
        sw = _emphasis_stroke_weight()
    else:
        fill, stroke = resolve_species_map_background_colours(sch)
        if smb is not None:
            r = _collection_radius_px(getattr(smb, "radius_px", None), md)
            _raw_smb_fo = getattr(smb, "fill_opacity", None)
            legacy_fo = float(_raw_smb_fo) if _raw_smb_fo is not None else md_fo
            fo = _collection_fill_opacity_visit(
                getattr(smb, "fill_opacity_override", None),
                legacy_fo,
                md_fo=md_fo,
            )
        else:
            r = _collection_radius_px(getattr(al, "radius_px", None), md)
            _raw_al_fo = getattr(al, "fill_opacity", None)
            legacy_fo = float(_raw_al_fo) if _raw_al_fo is not None else md_fo
            fo = _collection_fill_opacity_visit(
                getattr(al, "fill_opacity_override", None),
                legacy_fo,
                md_fo=md_fo,
            )
        sw = _species_background_stroke_weight()
    return stroke, fill, r, sw, fo


def resolve_lifer_overlay_pin_params(
    sch: Any,
) -> tuple[str, str, str, str, int, int, int, float, float]:
    """Lifer-locations map: lifer + species pin styling (same resolver path as the design utility)."""
    g = _global_defaults(sch)
    al = getattr(sch, "all_locations", sch)
    ll = getattr(sch, "lifer_locations", sch)
    lf_fill, lf_stroke = resolve_lifer_map_lifer_colours(sch)
    sp_fill, sp_stroke = resolve_lifer_map_subspecies_colours(sch)
    md = _map_marker_scheme_default_radius_px(sch)
    r_lifer = _collection_radius_px(getattr(ll, "lifer_radius_px", None), md)
    r_sub = _collection_radius_px(getattr(ll, "subspecies_radius_px", None), md)
    sw_raw = getattr(ll, "stroke_weight_override", None)
    if sw_raw is None:
        al_sw = getattr(al, "stroke_weight", None)
        if al_sw is not None:
            sw_raw = al_sw
        else:
            sw_raw = getattr(g, "stroke_weight", MAP_CIRCLE_MARKER_STROKE_WEIGHT)
    sw = max(1, int(sw_raw))
    md_fo = clamp_map_marker_circle_fill_opacity(
        getattr(g, "fill_opacity", None),
        fallback=0.88,
    )
    _raw_lif = getattr(ll, "lifer_fill_opacity", None)
    legacy_lif = float(_raw_lif) if _raw_lif is not None else md_fo
    fo_lif = _collection_fill_opacity_visit(
        getattr(ll, "lifer_fill_opacity_override", None),
        legacy_lif,
        md_fo=md_fo,
    )
    _raw_sub = getattr(ll, "subspecies_fill_opacity", None)
    legacy_sub = float(_raw_sub) if _raw_sub is not None else md_fo
    fo_sub = _collection_fill_opacity_visit(
        getattr(ll, "subspecies_fill_opacity_override", None),
        legacy_sub,
        md_fo=md_fo,
    )
    return lf_stroke, lf_fill, sp_stroke, sp_fill, r_lifer, r_sub, sw, fo_lif, fo_sub


def resolve_species_colours(sch: Any) -> tuple[str, str]:
    """Species emphasis markers."""
    g = _global_defaults(sch)
    sp = getattr(sch, "species_locations", sch)
    o = _overrides(sch)
    fill = _resolve_channel(
        override=getattr(o, "species_fill_hex", None) if o else None,
        specific=getattr(sp, "fill_hex", None),
        global_=getattr(g, "fill_hex", None),
        scheme_default=MAP_MARKER_SCHEME_DEFAULT_FILL_HEX,
        catchall=MAP_MARKER_CATCHALL_FILL_HEX,
    )
    stroke = _resolve_channel(
        override=getattr(o, "species_stroke_hex", None) if o else None,
        specific=getattr(sp, "stroke_hex", None),
        global_=getattr(g, "stroke_hex", None),
        scheme_default=MAP_MARKER_SCHEME_DEFAULT_STROKE_HEX,
        catchall=MAP_MARKER_CATCHALL_STROKE_HEX,
    )
    return normalize_marker_hex(fill, channel="fill"), normalize_marker_hex(stroke, channel="edge")


def resolve_species_map_lifer_colours(sch: Any) -> tuple[str, str]:
    """Species-filtered map — **Lifer** pin (first-seen location for the selected taxon)."""
    g = _global_defaults(sch)
    sp = getattr(sch, "species_locations", sch)
    o = _overrides(sch)
    fill = _resolve_channel(
        override=getattr(o, "species_lifer_fill_hex", None) if o else None,
        specific=getattr(sp, "lifer_fill_hex", None),
        global_=getattr(g, "fill_hex", None),
        scheme_default=MAP_MARKER_SCHEME_DEFAULT_FILL_HEX,
        catchall=MAP_MARKER_CATCHALL_FILL_HEX,
    )
    stroke = _resolve_channel(
        override=getattr(o, "species_lifer_stroke_hex", None) if o else None,
        specific=getattr(sp, "lifer_stroke_hex", None),
        global_=getattr(g, "stroke_hex", None),
        scheme_default=MAP_MARKER_SCHEME_DEFAULT_STROKE_HEX,
        catchall=MAP_MARKER_CATCHALL_STROKE_HEX,
    )
    return normalize_marker_hex(fill, channel="fill"), normalize_marker_hex(stroke, channel="edge")


def resolve_lifer_map_lifer_colours(sch: Any) -> tuple[str, str]:
    """Lifer-locations map — base-species lifer pin."""
    g = _global_defaults(sch)
    ll = getattr(sch, "lifer_locations", sch)
    o = _overrides(sch)
    fill = _resolve_channel(
        override=getattr(o, "lifer_fill_hex", None) if o else None,
        specific=getattr(ll, "lifer_fill_hex", None),
        global_=getattr(g, "fill_hex", None),
        scheme_default=MAP_MARKER_SCHEME_DEFAULT_FILL_HEX,
        catchall=MAP_MARKER_CATCHALL_FILL_HEX,
    )
    stroke = _resolve_channel(
        override=getattr(o, "lifer_stroke_hex", None) if o else None,
        specific=getattr(ll, "lifer_stroke_hex", None),
        global_=getattr(g, "stroke_hex", None),
        scheme_default=MAP_MARKER_SCHEME_DEFAULT_STROKE_HEX,
        catchall=MAP_MARKER_CATCHALL_STROKE_HEX,
    )
    return normalize_marker_hex(fill, channel="fill"), normalize_marker_hex(stroke, channel="edge")


def resolve_lifer_map_subspecies_colours(sch: Any) -> tuple[str, str]:
    """Lifer-locations map — taxon-only (subspecies) lifer pin."""
    g = _global_defaults(sch)
    ll = getattr(sch, "lifer_locations", sch)
    o = _overrides(sch)
    fill = _resolve_channel(
        override=getattr(o, "subspecies_fill_hex", None) if o else None,
        specific=getattr(ll, "subspecies_fill_hex", None),
        global_=getattr(g, "fill_hex", None),
        scheme_default=MAP_MARKER_SCHEME_DEFAULT_FILL_HEX,
        catchall=MAP_MARKER_CATCHALL_FILL_HEX,
    )
    stroke = _resolve_channel(
        override=getattr(o, "subspecies_stroke_hex", None) if o else None,
        specific=getattr(ll, "subspecies_stroke_hex", None),
        global_=getattr(g, "stroke_hex", None),
        scheme_default=MAP_MARKER_SCHEME_DEFAULT_STROKE_HEX,
        catchall=MAP_MARKER_CATCHALL_STROKE_HEX,
    )
    return normalize_marker_hex(fill, channel="fill"), normalize_marker_hex(stroke, channel="edge")


def resolve_last_seen_colours(sch: Any) -> tuple[str, str]:
    """Last-seen emphasis markers."""
    g = _global_defaults(sch)
    sp = getattr(sch, "species_locations", sch)
    o = _overrides(sch)
    fill = _resolve_channel(
        override=getattr(o, "last_seen_fill_hex", None) if o else None,
        specific=getattr(sp, "last_seen_fill_hex", None),
        global_=getattr(g, "fill_hex", None),
        scheme_default=MAP_MARKER_SCHEME_DEFAULT_FILL_HEX,
        catchall=MAP_MARKER_CATCHALL_FILL_HEX,
    )
    stroke = _resolve_channel(
        override=getattr(o, "last_seen_stroke_hex", None) if o else None,
        specific=getattr(sp, "last_seen_stroke_hex", None),
        global_=getattr(g, "stroke_hex", None),
        scheme_default=MAP_MARKER_SCHEME_DEFAULT_STROKE_HEX,
        catchall=MAP_MARKER_CATCHALL_STROKE_HEX,
    )
    return normalize_marker_hex(fill, channel="fill"), normalize_marker_hex(stroke, channel="edge")


def family_map_resolved_highlight_pin_stroke_hex(sch: Any, density_band_index: int) -> str:
    """Family-map species-highlight pin edge: explicit ``highlight_stroke_hex`` else that band's density edge.

    When ``highlight_stroke_hex`` is omitted, the highlight marker keeps the same edge colour as a
    non-highlight pin at that richness band (``resolve_family_band_colours``), not ``global_defaults``.
    """
    fam = getattr(sch, "family_locations", sch)
    raw = getattr(fam, "highlight_stroke_hex", None)
    if raw is not None and str(raw).strip():
        return normalize_marker_hex(str(raw), channel="edge")
    fills = getattr(fam, "density_fill_hex", None) or ()
    n = len(fills)
    bi = max(0, min(int(density_band_index), n - 1)) if n else 0
    _, edge = resolve_family_band_colours(sch, bi)
    return edge


def resolve_family_highlight_stroke_hex(sch: Any) -> str:
    """Family-map highlight *legend* swatch edge: explicit ``highlight_stroke_hex`` else band edge at ``legend_highlight_band_index``."""
    fam = getattr(sch, "family_locations", sch)
    sw_i = max(0, min(int(fam.legend_highlight_band_index), len(fam.density_fill_hex) - 1))
    return family_map_resolved_highlight_pin_stroke_hex(sch, sw_i)


def resolve_family_highlight_halo_fill_hex(sch: Any) -> str:
    """Family-map highlight halo fill colour: explicit halo fill or ``global_defaults.fill_hex``."""
    g = _global_defaults(sch)
    fam = getattr(sch, "family_locations", sch)
    raw = getattr(fam, "highlight_halo_fill_hex", None)
    if raw is not None and str(raw).strip():
        return normalize_marker_hex(str(raw), channel="fill")
    return normalize_marker_hex(getattr(g, "fill_hex", None), channel="fill")


def family_map_has_highlight_halo(sch: Any) -> bool:
    """True when family highlight halo is explicitly configured on the scheme."""
    fam = getattr(sch, "family_locations", sch)

    def _hex_set(raw: object) -> bool:
        return raw is not None and bool(str(raw).strip())

    def _num_set(raw: object) -> bool:
        return raw is not None

    return any(
        (
            _hex_set(getattr(fam, "highlight_halo_fill_hex", None)),
            _hex_set(getattr(fam, "highlight_halo_stroke_hex", None)),
            _num_set(getattr(fam, "highlight_halo_radius_delta_px", None)),
            _num_set(getattr(fam, "highlight_halo_fill_opacity", None)),
            _num_set(getattr(fam, "highlight_halo_stroke_opacity", None)),
            _num_set(getattr(fam, "highlight_halo_stroke_weight", None)),
        )
    )


def resolve_family_highlight_halo_stroke_hex(sch: Any) -> str:
    """Family-map highlight halo edge colour: explicit halo stroke or ``global_defaults.stroke_hex``."""
    g = _global_defaults(sch)
    fam = getattr(sch, "family_locations", sch)
    raw = getattr(fam, "highlight_halo_stroke_hex", None)
    if raw is not None and str(raw).strip():
        return normalize_marker_hex(str(raw), channel="edge")
    return normalize_marker_hex(getattr(g, "stroke_hex", None), channel="edge")


def family_map_resolved_highlight_halo_radius_px(sch: Any) -> int:
    """Family highlight halo radius: base family radius plus optional delta (clamped)."""
    fam = getattr(sch, "family_locations", sch)
    base = family_map_resolved_circle_radius_px(sch)
    delta_raw = getattr(fam, "highlight_halo_radius_delta_px", None)
    if delta_raw is None:
        return clamp_map_marker_circle_radius_px(base + 2)
    try:
        delta = int(delta_raw)
    except (TypeError, ValueError):
        return clamp_map_marker_circle_radius_px(base + 2)
    return clamp_map_marker_circle_radius_px(base + max(0, delta))


def family_map_resolved_highlight_halo_fill_opacity(sch: Any) -> float:
    """Family highlight halo fill opacity, defaulting to 0.95 for high-contrast focus."""
    fam = getattr(sch, "family_locations", sch)
    raw = getattr(fam, "highlight_halo_fill_opacity", None)
    return clamp_map_marker_circle_fill_opacity(raw, fallback=0.95)


def family_map_resolved_highlight_halo_stroke_opacity(sch: Any) -> float:
    """Family highlight halo stroke opacity (Leaflet path ``opacity``); unset defaults to 1.0."""
    fam = getattr(sch, "family_locations", sch)
    raw = getattr(fam, "highlight_halo_stroke_opacity", None)
    return clamp_map_marker_circle_fill_opacity(raw, fallback=1.0)


def family_map_resolved_highlight_halo_stroke_weight(sch: Any) -> int:
    """Family highlight halo edge weight: explicit halo value, else global stroke weight."""
    g = _global_defaults(sch)
    fam = getattr(sch, "family_locations", sch)
    raw = getattr(fam, "highlight_halo_stroke_weight", None)
    if raw is None:
        raw = getattr(g, "stroke_weight", MAP_CIRCLE_MARKER_STROKE_WEIGHT)
    try:
        return max(1, int(raw))
    except (TypeError, ValueError):
        return max(1, int(MAP_CIRCLE_MARKER_STROKE_WEIGHT))


def resolve_family_band_colours(sch: Any, index: int) -> tuple[str, str]:
    """Family density band *index* (0..3): band colours then global then (c)→(d)."""
    g = _global_defaults(sch)
    fam = getattr(sch, "family_locations", sch)
    fills = getattr(fam, "density_fill_hex", None) or ()
    strokes = getattr(fam, "density_stroke_hex", None) or ()
    spec_f = fills[index] if 0 <= index < len(fills) else None
    spec_s = strokes[index] if 0 <= index < len(strokes) else None
    fill = _resolve_channel(
        override=None,
        specific=spec_f,
        global_=getattr(g, "fill_hex", None),
        scheme_default=MAP_MARKER_SCHEME_DEFAULT_FILL_HEX,
        catchall=MAP_MARKER_CATCHALL_FILL_HEX,
    )
    stroke = _resolve_channel(
        override=None,
        specific=spec_s,
        global_=getattr(g, "stroke_hex", None),
        scheme_default=MAP_MARKER_SCHEME_DEFAULT_STROKE_HEX,
        catchall=MAP_MARKER_CATCHALL_STROKE_HEX,
    )
    return normalize_marker_hex(fill, channel="fill"), normalize_marker_hex(stroke, channel="edge")


def _map_marker_scheme_default_radius_px(sch: Any) -> int:
    """Global default circle radius with clamp (same base as design ``scheme_seed_config``)."""
    g = _global_defaults(sch)
    v = getattr(g, "radius_px", None)
    if v is None:
        return clamp_map_marker_circle_radius_px(MAP_MARKER_CIRCLE_RADIUS_PX_FALLBACK)
    try:
        return clamp_map_marker_circle_radius_px(int(v))
    except (TypeError, ValueError):
        return clamp_map_marker_circle_radius_px(MAP_MARKER_CIRCLE_RADIUS_PX_FALLBACK)


def family_map_resolved_circle_radius_px(sch: Any) -> int:
    """Family map CircleMarker radius — matches :func:`~explorer.presentation.design_map_preview.scheme_seed_config`."""
    fam = getattr(sch, "family_locations", sch)
    md = _map_marker_scheme_default_radius_px(sch)
    ovr = getattr(fam, "radius_px_override", None)
    if ovr is not None:
        try:
            return clamp_map_marker_circle_radius_px(int(ovr))
        except (TypeError, ValueError):
            return md
    base = getattr(fam, "radius_px", None)
    if base is not None:
        try:
            return clamp_map_marker_circle_radius_px(int(base))
        except (TypeError, ValueError):
            return md
    return md


def family_map_resolved_fill_opacity(sch: Any) -> float:
    """Family map fill opacity — matches ``scheme_seed_config`` / design preview."""
    g = _global_defaults(sch)
    fam = getattr(sch, "family_locations", sch)
    md_fo = clamp_map_marker_circle_fill_opacity(
        getattr(g, "fill_opacity", None),
        fallback=0.88,
    )
    v = getattr(fam, "fill_opacity_override", None)
    if v is not None:
        return clamp_map_marker_circle_fill_opacity(v, fallback=md_fo)
    raw = getattr(fam, "fill_opacity", None)
    legacy = float(raw) if raw is not None else md_fo
    return clamp_map_marker_circle_fill_opacity(legacy, fallback=md_fo)
