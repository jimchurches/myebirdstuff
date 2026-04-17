"""
Map marker **design** utility — dummy Folium markers for tuning colours and geometry.

No eBird data required. Run from repo root::

    pip install -r requirements.txt
    streamlit run explorer/app/streamlit/design_map_app.py

Uses :mod:`explorer.presentation.design_map_preview` and :mod:`explorer.app.streamlit.defaults`
(:class:`~explorer.app.streamlit.defaults.MapMarkerColourScheme` presets).

The preview map matches the main explorer’s initial framing: Canberra centre, zoom **5** (see
:func:`explorer.presentation.map_renderer.create_map`). The map **renders only** when you click
**Update map**; slider and text edits do not trigger a rebuild.
"""

from __future__ import annotations

from dataclasses import replace
import os
import re
import sys

# ``streamlit run explorer/app/streamlit/design_map_app.py`` puts the script directory on ``sys.path``,
# not the repo root — same as :mod:`explorer.app.streamlit.app` (refs #70).
_REPO_ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", ".."))
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)

import streamlit as st

from explorer.core.map_marker_colour_resolve import (
    MAP_MARKER_CATCHALL_FILL_HEX,
    MAP_MARKER_CATCHALL_STROKE_HEX,
)
from explorer.app.streamlit.defaults import (
    MAP_BASEMAP_LABELS,
    MAP_BASEMAP_OPTIONS,
    MAP_HEIGHT_PX_DEFAULT,
    MAP_HEIGHT_PX_MAX,
    MAP_HEIGHT_PX_MIN,
    MAP_HEIGHT_PX_STEP,
    MAP_MARKER_CIRCLE_RADIUS_PX_FALLBACK,
    MAP_MARKER_CIRCLE_RADIUS_PX_MAX,
    MAP_MARKER_CLUSTER_BORDER_OPACITY_DEFAULT,
    MAP_MARKER_CLUSTER_BORDER_WIDTH_PX_DEFAULT,
    MAP_MARKER_CLUSTER_HALO_OPACITY_DEFAULT,
    MAP_MARKER_CLUSTER_HALO_SPREAD_PX_DEFAULT,
    MAP_MARKER_CLUSTER_INNER_FILL_OPACITY_DEFAULT,
    active_map_marker_colour_scheme,
    clamp_map_marker_circle_fill_opacity,
    clamp_map_marker_circle_radius_px,
)
from explorer.app.streamlit.app_map_ui import inject_map_folium_iframe_min_height_css
from explorer.app.streamlit.design_map_constants import (
    FAMILY_DENSITY_BAND_UI_LABELS,
    H_BASEMAP,
    H_FO_DEFAULT,
    H_CLUSTER_BORDER_O,
    H_CLUSTER_BORDER_W,
    H_CLUSTER_HALO_O,
    H_CLUSTER_HALO_SPREAD,
    H_CLUSTER_INNER_FO,
    H_CLUSTER_LARGE_BORDER,
    H_CLUSTER_LARGE_FILL,
    H_CLUSTER_LARGE_HALO,
    H_CLUSTER_MEDIUM_BORDER,
    H_CLUSTER_MEDIUM_FILL,
    H_CLUSTER_MEDIUM_HALO,
    H_CLUSTER_SMALL_BORDER,
    H_CLUSTER_SMALL_FILL,
    H_CLUSTER_SMALL_HALO,
    H_FO_FAMILY,
    H_FO_LIFER_MAP_LIFER,
    H_FO_LIFER_MAP_SUBSPECIES,
    H_FO_LOCATIONS,
    H_FO_SPECIES,
    H_FO_SPECIES_MAP_LOCATIONS,
    H_HEIGHT,
    H_GLOBAL_EDGE,
    H_GLOBAL_FILL,
    H_HEX_DE,
    H_HEX_DF,
    H_HEX_FAM_HL,
    H_HEX_FF,
    H_HEX_FS,
    H_HEX_LML_E,
    H_HEX_LML_F,
    H_HEX_LMS_E,
    H_HEX_LMS_F,
    H_HEX_LSE,
    H_HEX_LSF,
    H_HEX_SE,
    H_HEX_SF,
    H_HEX_SMPL_E,
    H_HEX_SMPL_F,
    H_HEX_SML_E,
    H_HEX_SML_F,
    H_PRESET,
    H_RADIUS_DEFAULT,
    H_RADIUS_FAMILIES,
    H_SW_GLOBAL,
    H_RADIUS_LIFER_MAP_LIFER,
    H_RADIUS_LIFER_MAP_SUBSPECIES,
    H_RADIUS_LOCATIONS,
    H_RADIUS_SPECIES,
    H_RADIUS_SPECIES_MAP_LOCATIONS,
    H_SW_FAM,
    H_SW_FAM_HL,
    H_SW_LIFER,
    H_SW_SPECIES,
    H_SW_SPECIES_MAP_LOCATIONS,
    H_SW_VISIT,
    PREVIEW_SCOPE_LABELS,
)
from explorer.presentation.design_map_export import format_full_defaults_export
from explorer.presentation.design_map_preview import (
    MAP_SCOPES,
    MAP_SCOPE_ALL,
    MAP_SCOPE_ALL_LOCATIONS,
    MAP_SCOPE_FAMILY_LOCATIONS,
    MAP_SCOPE_LIFER_LOCATIONS,
    MAP_SCOPE_SPECIES_LOCATIONS,
    MARKER_SCHEME_FALLBACK_DEFAULT_STROKE_WEIGHT,
    MARKER_SCHEME_FALLBACK_DEFAULT_FILL_OPACITY,
    DesignMapPreviewConfig,
    build_design_preview_map,
    normalize_hex_colour,
    scheme_seed_config,
)

# Session keys
_K_SEEDED = "design_ui_seeded"
_K_APPLIED = "design_applied_config"
_K_POS_SEED = "design_position_seed"
_K_RENDER = "design_render_nonce"
_K_EXPORT_NAME = "design_export_display_name"

# Valid hex body without leading ``#``: 3 (short), 6, or 8 (RGBA) digits.
_HEX_BODY_NO_HASH = re.compile(r"^(?:[0-9A-Fa-f]{3}|[0-9A-Fa-f]{6}|[0-9A-Fa-f]{8})$")


def _ensure_hex_leading_hash(key: str) -> None:
    """Prefix ``#`` and uppercase A–F when the value is a valid hex colour (e.g. ``95a5b2`` → ``#95A5B2``)."""
    v = st.session_state.get(key)
    if v is None:
        return
    s = str(v).strip()
    if not s:
        return
    body = s[1:] if s.startswith("#") else s
    if not body:
        return
    if not _HEX_BODY_NO_HASH.match(body):
        return
    normalized = f"#{body.upper()}"
    if normalized != s:
        st.session_state[key] = normalized


def _hex_hash_on_change(key: str):
    def _cb() -> None:
        _ensure_hex_leading_hash(key)

    return _cb


def _hex_text_input(label: str, *, key: str, help: str) -> None:
    st.text_input(label, key=key, help=help, on_change=_hex_hash_on_change(key))


def _hex_text_input_cluster_tier(label: str, *, key: str, help: str) -> None:
    """Optional hex fields for MarkerCluster tiers; empty means use Folium defaults."""
    st.text_input(
        label,
        key=key,
        help=help,
        placeholder="no value required",
        on_change=_hex_hash_on_change(key),
    )


def _radius_from_session(key: str, *, default_px: int) -> int:
    """Clamp session circle radius to ``[1, MAP_MARKER_CIRCLE_RADIUS_PX_MAX]``."""
    v = st.session_state.get(key)
    if v is None:
        return default_px
    try:
        return clamp_map_marker_circle_radius_px(int(v))
    except (TypeError, ValueError):
        return default_px


def _cluster_colours_from_session() -> tuple[str, str, str, str, str, str, str, str, str] | None:
    """Return all nine MarkerCluster colours when complete; otherwise ``None`` (plugin defaults)."""
    parts: list[str] = []
    for i in range(9):
        raw = st.session_state.get(f"design_cluster_colour_hex_{i}")
        s = "" if raw is None else str(raw).strip()
        parts.append(s)
    if all(x == "" for x in parts):
        return None
    if any(x == "" for x in parts):
        return None
    return tuple(normalize_hex_colour(parts[i]) for i in range(9))


def _cluster_style_float_from_session(key: str, default: float) -> float:
    v = st.session_state.get(key)
    if v is None:
        return default
    try:
        return max(0.0, min(1.0, float(v)))
    except (TypeError, ValueError):
        return default


def _cluster_style_int_from_session(key: str, default: int, *, lo: int, hi: int) -> int:
    v = st.session_state.get(key)
    if v is None:
        return default
    try:
        return max(lo, min(hi, int(v)))
    except (TypeError, ValueError):
        return default


def _fill_opacity_from_session(key: str, *, legacy_key: str | None, default: float) -> float:
    """Read slider session value; *legacy_key* supports session keys from older widget names."""
    v = st.session_state.get(key)
    if v is None and legacy_key is not None:
        v = st.session_state.get(legacy_key)
    if v is None:
        return clamp_map_marker_circle_fill_opacity(None, fallback=default)
    try:
        return clamp_map_marker_circle_fill_opacity(float(v), fallback=default)
    except (TypeError, ValueError):
        return default


def _seed_controls_from_scheme(scheme_index: int) -> None:
    scope = str(st.session_state.get("design_preview_scope", MAP_SCOPE_ALL))
    cfg = scheme_seed_config(scheme_index, preview_scope=scope)
    # Do not set ``design_scheme_pick`` here: when "Load preset" runs, the selectbox is already
    # instantiated above the button, and Streamlit forbids mutating that widget key after creation.
    st.session_state["design_map_style"] = cfg.map_style
    st.session_state["design_height_px"] = int(cfg.height_px)
    st.session_state["design_radius_default"] = int(cfg.marker_default_radius_px)
    st.session_state["design_radius_locations"] = int(cfg.marker_radius_locations)
    st.session_state["design_radius_species"] = int(cfg.marker_radius_species)
    st.session_state["design_radius_species_map_background"] = int(cfg.marker_radius_species_map_background)
    st.session_state["design_radius_lifer_map_lifer"] = int(cfg.marker_radius_lifer_map_lifer)
    st.session_state["design_radius_lifer_map_subspecies"] = int(cfg.marker_radius_lifer_map_subspecies)
    st.session_state["design_radius_families"] = int(cfg.marker_radius_families)
    st.session_state["design_sw_visit"] = int(cfg.stroke_weight_visit)
    st.session_state["design_sw_species"] = int(cfg.stroke_weight_species)
    st.session_state["design_sw_species_map_background"] = int(cfg.stroke_weight_species_map_background)
    st.session_state["design_sw_lifer"] = int(cfg.stroke_weight_lifer)
    st.session_state["design_sw_family"] = int(cfg.stroke_weight_family)
    st.session_state["design_sw_family_hl"] = int(cfg.stroke_weight_family_highlight)
    st.session_state["design_fo_locations"] = float(cfg.marker_fill_opacity_locations)
    st.session_state["design_fo_species"] = float(cfg.marker_fill_opacity_species)
    st.session_state["design_fo_species_map_background"] = float(cfg.marker_fill_opacity_species_map_background)
    st.session_state["design_fo_lifer_map_lifer"] = float(cfg.marker_fill_opacity_lifer_map_lifer)
    st.session_state["design_fo_lifer_map_subspecies"] = float(cfg.marker_fill_opacity_lifer_map_subspecies)
    st.session_state["design_fo_family"] = float(cfg.marker_fill_opacity_families)
    st.session_state["design_marker_default_fill_hex"] = cfg.marker_default_fill_hex
    st.session_state["design_marker_default_stroke_hex"] = cfg.marker_default_stroke_hex
    st.session_state["design_marker_default_fill_opacity"] = float(cfg.marker_default_fill_opacity)
    st.session_state["design_marker_default_stroke_weight"] = int(cfg.marker_default_stroke_weight)
    st.session_state["design_hex_de"] = cfg.default_stroke_hex
    st.session_state["design_hex_df"] = cfg.default_fill_hex
    st.session_state["design_hex_se"] = cfg.species_stroke_hex
    st.session_state["design_hex_sf"] = cfg.species_fill_hex
    st.session_state["design_hex_smpl_f"] = cfg.species_map_background_fill_hex
    st.session_state["design_hex_smpl_e"] = cfg.species_map_background_stroke_hex
    st.session_state["design_hex_sml_e"] = cfg.species_lifer_stroke_hex
    st.session_state["design_hex_sml_f"] = cfg.species_lifer_fill_hex
    st.session_state["design_hex_lml_e"] = cfg.lifer_map_lifer_stroke_hex
    st.session_state["design_hex_lml_f"] = cfg.lifer_map_lifer_fill_hex
    st.session_state["design_hex_lms_e"] = cfg.lifer_map_subspecies_stroke_hex
    st.session_state["design_hex_lms_f"] = cfg.lifer_map_subspecies_fill_hex
    st.session_state["design_hex_lse"] = cfg.last_seen_stroke_hex
    st.session_state["design_hex_lsf"] = cfg.last_seen_fill_hex
    for i in range(4):
        st.session_state[f"design_hex_ff{i}"] = cfg.family_fill_hex[i]
        st.session_state[f"design_hex_fs{i}"] = cfg.family_stroke_hex[i]
    st.session_state["design_hex_fam_hl"] = cfg.family_highlight_stroke_hex
    st.session_state["design_legend_hl_swatch_ix"] = int(cfg.legend_highlight_band_index)
    cc = cfg.marker_cluster_tier_icon_hex
    if cc is not None and len(cc) == 9:
        for i in range(9):
            st.session_state[f"design_cluster_colour_hex_{i}"] = cc[i]
    else:
        for i in range(9):
            st.session_state[f"design_cluster_colour_hex_{i}"] = ""
    st.session_state["design_cluster_inner_fo"] = float(cfg.marker_cluster_inner_fill_opacity)
    st.session_state["design_cluster_halo_o"] = float(cfg.marker_cluster_halo_opacity)
    st.session_state["design_cluster_border_o"] = float(cfg.marker_cluster_border_opacity)
    st.session_state["design_cluster_halo_spread"] = int(cfg.marker_cluster_halo_spread_px)
    st.session_state["design_cluster_border_w"] = int(cfg.marker_cluster_border_width_px)
    st.session_state[_K_EXPORT_NAME] = active_map_marker_colour_scheme(scheme_index).display_name


def _config_from_session() -> DesignMapPreviewConfig:
    _ps = str(st.session_state.get("design_preview_scope", MAP_SCOPE_ALL))
    _scope = _ps if _ps in MAP_SCOPES else MAP_SCOPE_ALL
    _fb = MAP_MARKER_CIRCLE_RADIUS_PX_FALLBACK
    _raw_default = st.session_state.get("design_radius_default")
    _md = clamp_map_marker_circle_radius_px(_raw_default if _raw_default is not None else _fb)
    _mdf = clamp_map_marker_circle_fill_opacity(
        st.session_state.get("design_marker_default_fill_opacity"),
        fallback=MARKER_SCHEME_FALLBACK_DEFAULT_FILL_OPACITY,
    )
    _global_fill_hex = str(
        st.session_state.get("design_marker_default_fill_hex", MAP_MARKER_CATCHALL_FILL_HEX)
    )
    _global_stroke_hex = str(
        st.session_state.get("design_marker_default_stroke_hex", MAP_MARKER_CATCHALL_STROKE_HEX)
    )

    def _hex_from_session(key: str, *, fallback: str) -> str:
        """Blank session hex means 'inherit' (fall back to the provided channel default)."""
        raw = str(st.session_state.get(key, fallback))
        return raw if raw.strip() else fallback

    return DesignMapPreviewConfig(
        preview_scope=_scope,
        map_style=str(st.session_state.get("design_map_style", "default")),
        height_px=max(
            MAP_HEIGHT_PX_MIN,
            min(MAP_HEIGHT_PX_MAX, int(st.session_state.get("design_height_px", MAP_HEIGHT_PX_DEFAULT))),
        ),
        marker_default_radius_px=_md,
        marker_radius_locations=_radius_from_session("design_radius_locations", default_px=_md),
        marker_radius_species=_radius_from_session("design_radius_species", default_px=_md),
        marker_radius_species_map_background=_radius_from_session(
            "design_radius_species_map_background", default_px=_md
        ),
        marker_radius_lifer_map_lifer=_radius_from_session(
            "design_radius_lifer_map_lifer", default_px=_md
        ),
        marker_radius_lifer_map_subspecies=_radius_from_session(
            "design_radius_lifer_map_subspecies", default_px=_md
        ),
        marker_radius_families=_radius_from_session("design_radius_families", default_px=_md),
        stroke_weight_visit=max(1, int(st.session_state.get("design_sw_visit", 1))),
        stroke_weight_species=max(1, int(st.session_state.get("design_sw_species", st.session_state.get("design_sw_visit", 1)))),
        stroke_weight_species_map_background=max(
            1,
            int(
                st.session_state.get(
                    "design_sw_species_map_background",
                    st.session_state.get("design_sw_species", st.session_state.get("design_sw_visit", 1)),
                )
            ),
        ),
        stroke_weight_lifer=max(1, int(st.session_state.get("design_sw_lifer", st.session_state.get("design_sw_visit", 1)))),
        stroke_weight_family=max(1, int(st.session_state.get("design_sw_family", 1))),
        stroke_weight_family_highlight=max(1, int(st.session_state.get("design_sw_family_hl", 1))),
        marker_fill_opacity_locations=_fill_opacity_from_session(
            "design_fo_locations", legacy_key="design_fo_all", default=_mdf
        ),
        marker_fill_opacity_species=_fill_opacity_from_session(
            "design_fo_species", legacy_key="design_fo_emph", default=_mdf
        ),
        marker_fill_opacity_species_map_background=_fill_opacity_from_session(
            "design_fo_species_map_background", legacy_key=None, default=_mdf
        ),
        marker_fill_opacity_lifer_map_lifer=_fill_opacity_from_session(
            "design_fo_lifer_map_lifer", legacy_key=None, default=_mdf
        ),
        marker_fill_opacity_lifer_map_subspecies=_fill_opacity_from_session(
            "design_fo_lifer_map_subspecies", legacy_key=None, default=_mdf
        ),
        marker_fill_opacity_families=_fill_opacity_from_session(
            "design_fo_family", legacy_key=None, default=_mdf
        ),
        marker_default_fill_hex=_global_fill_hex,
        marker_default_stroke_hex=_global_stroke_hex,
        marker_default_fill_opacity=_mdf,
        marker_default_stroke_weight=max(
            1,
            int(
                st.session_state.get(
                    "design_marker_default_stroke_weight",
                    MARKER_SCHEME_FALLBACK_DEFAULT_STROKE_WEIGHT,
                )
            ),
        ),
        default_stroke_hex=_hex_from_session("design_hex_de", fallback=_global_stroke_hex),
        default_fill_hex=_hex_from_session("design_hex_df", fallback=_global_fill_hex),
        species_map_background_fill_hex=_hex_from_session(
            "design_hex_smpl_f", fallback=_global_fill_hex
        ),
        species_map_background_stroke_hex=_hex_from_session(
            "design_hex_smpl_e", fallback=_global_stroke_hex
        ),
        species_stroke_hex=_hex_from_session("design_hex_se", fallback=_global_stroke_hex),
        species_fill_hex=_hex_from_session("design_hex_sf", fallback=_global_fill_hex),
        species_lifer_stroke_hex=_hex_from_session(
            "design_hex_sml_e", fallback=_global_stroke_hex
        ),
        species_lifer_fill_hex=_hex_from_session("design_hex_sml_f", fallback=_global_fill_hex),
        lifer_map_lifer_stroke_hex=_hex_from_session(
            "design_hex_lml_e", fallback=_global_stroke_hex
        ),
        lifer_map_lifer_fill_hex=_hex_from_session("design_hex_lml_f", fallback=_global_fill_hex),
        lifer_map_subspecies_stroke_hex=_hex_from_session(
            "design_hex_lms_e", fallback=_global_stroke_hex
        ),
        lifer_map_subspecies_fill_hex=_hex_from_session(
            "design_hex_lms_f", fallback=_global_fill_hex
        ),
        last_seen_stroke_hex=_hex_from_session("design_hex_lse", fallback=_global_stroke_hex),
        last_seen_fill_hex=_hex_from_session("design_hex_lsf", fallback=_global_fill_hex),
        family_fill_hex=tuple(
            _hex_from_session(f"design_hex_ff{i}", fallback=_global_fill_hex) for i in range(4)
        ),
        family_stroke_hex=tuple(
            _hex_from_session(f"design_hex_fs{i}", fallback=_global_stroke_hex) for i in range(4)
        ),
        family_highlight_stroke_hex=_hex_from_session(
            "design_hex_fam_hl", fallback=_global_stroke_hex
        ),
        legend_highlight_band_index=max(
            0, min(3, int(st.session_state.get("design_legend_hl_swatch_ix", 0)))
        ),
        marker_cluster_tier_icon_hex=_cluster_colours_from_session(),
        marker_cluster_inner_fill_opacity=_cluster_style_float_from_session(
            "design_cluster_inner_fo", MAP_MARKER_CLUSTER_INNER_FILL_OPACITY_DEFAULT
        ),
        marker_cluster_halo_opacity=_cluster_style_float_from_session(
            "design_cluster_halo_o", MAP_MARKER_CLUSTER_HALO_OPACITY_DEFAULT
        ),
        marker_cluster_border_opacity=_cluster_style_float_from_session(
            "design_cluster_border_o", MAP_MARKER_CLUSTER_BORDER_OPACITY_DEFAULT
        ),
        marker_cluster_halo_spread_px=_cluster_style_int_from_session(
            "design_cluster_halo_spread", MAP_MARKER_CLUSTER_HALO_SPREAD_PX_DEFAULT, lo=0, hi=24
        ),
        marker_cluster_border_width_px=_cluster_style_int_from_session(
            "design_cluster_border_w", MAP_MARKER_CLUSTER_BORDER_WIDTH_PX_DEFAULT, lo=0, hi=8
        ),
    )


def _config_for_export() -> DesignMapPreviewConfig:
    """Session config for **Export** tab.

    If the nine cluster hex fields are empty in session (e.g. preset was changed before we synced)
    but the selected **defaults.py** preset defines ``tier_icon_hex``, merge those
    resolved values so the export block matches the file without requiring a separate button click.
    """
    cfg = _config_from_session()
    if cfg.marker_cluster_tier_icon_hex is not None:
        return cfg
    pick = int(st.session_state.get("design_scheme_pick", 1))
    sch = active_map_marker_colour_scheme(pick)
    if sch.all_locations.cluster.tier_icon_hex is None:
        return cfg
    scope = str(st.session_state.get("design_preview_scope", MAP_SCOPE_ALL))
    if scope not in MAP_SCOPES:
        scope = MAP_SCOPE_ALL
    seeded = scheme_seed_config(pick, preview_scope=scope)
    return replace(
        cfg,
        marker_cluster_tier_icon_hex=seeded.marker_cluster_tier_icon_hex,
        marker_cluster_inner_fill_opacity=seeded.marker_cluster_inner_fill_opacity,
        marker_cluster_halo_opacity=seeded.marker_cluster_halo_opacity,
        marker_cluster_border_opacity=seeded.marker_cluster_border_opacity,
        marker_cluster_halo_spread_px=seeded.marker_cluster_halo_spread_px,
        marker_cluster_border_width_px=seeded.marker_cluster_border_width_px,
    )


def _on_preset_scheme_change() -> None:
    """Keep sidebar widgets aligned with the selected ``defaults.py`` preset (incl. cluster hex)."""
    _seed_controls_from_scheme(int(st.session_state["design_scheme_pick"]))


def main() -> None:
    st.set_page_config(page_title="Map marker design", layout="wide")
    st.title("Map marker design")
    st.caption(
        "Preview visit-map and family-map **CircleMarker** styles on a fixed Canberra view (zoom 5). "
        "Adjust the sidebar, then click **Update map** to render — edits do not redraw until then."
    )

    if _K_POS_SEED not in st.session_state:
        st.session_state[_K_POS_SEED] = 42
    if "design_preview_scope" not in st.session_state:
        st.session_state["design_preview_scope"] = MAP_SCOPE_ALL
    if not st.session_state.get(_K_SEEDED):
        st.session_state["design_scheme_pick"] = 1
        _seed_controls_from_scheme(1)
        st.session_state[_K_SEEDED] = True
    if _K_EXPORT_NAME not in st.session_state:
        st.session_state[_K_EXPORT_NAME] = active_map_marker_colour_scheme(
            int(st.session_state.get("design_scheme_pick", 1))
        ).display_name

    _scope_options = tuple(PREVIEW_SCOPE_LABELS.keys())

    with st.sidebar:
        st.subheader("Colour scheme (defaults)")
        st.selectbox(
            "Preset from defaults.py",
            options=[1, 2, 3],
            key="design_scheme_pick",
            format_func=lambda i: active_map_marker_colour_scheme(int(i)).display_name,
            help=H_PRESET,
            on_change=_on_preset_scheme_change,
        )
        st.caption(
            "Changing the preset reloads all controls from ``defaults.py``, including MarkerCluster hex fields."
        )
        if st.button("Load preset into controls", use_container_width=True):
            _seed_controls_from_scheme(int(st.session_state.get("design_scheme_pick", 1)))
            st.rerun()
        if st.button("Shuffle positions", use_container_width=True):
            st.session_state[_K_POS_SEED] = int(st.session_state.get(_K_POS_SEED, 42)) + 1
        update = st.button("Update map", type="primary", use_container_width=True)

        st.divider()
        st.selectbox(
            "Map view",
            options=list(_scope_options),
            format_func=lambda k: PREVIEW_SCOPE_LABELS.get(k, k),
            key="design_preview_scope",
        )

        st.divider()
        st.caption(
            "**Globals** contains the base marker settings used across all map types. Per-map sections "
            "override these values where required. The saved scheme is sparse, so values equal to the "
            "globals are omitted."
        )

        with st.expander("Globals", expanded=False):
            st.slider(
                "Circle radius (px)",
                min_value=1,
                max_value=MAP_MARKER_CIRCLE_RADIUS_PX_MAX,
                key="design_radius_default",
                help=H_RADIUS_DEFAULT,
            )
            st.slider(
                "Circle fill opacity",
                min_value=0.0,
                max_value=1.0,
                step=0.01,
                key="design_marker_default_fill_opacity",
                help=H_FO_DEFAULT,
            )
            st.slider(
                "Edge weight",
                min_value=1,
                max_value=8,
                key="design_marker_default_stroke_weight",
                help=H_SW_GLOBAL,
            )
            _hex_text_input(
                "Fill",
                key="design_marker_default_fill_hex",
                help=H_GLOBAL_FILL,
            )
            _hex_text_input(
                "Edge",
                key="design_marker_default_stroke_hex",
                help=H_GLOBAL_EDGE,
            )

        with st.expander(PREVIEW_SCOPE_LABELS[MAP_SCOPE_ALL_LOCATIONS], expanded=False):
            st.slider(
                "Circle radius (px)",
                min_value=1,
                max_value=MAP_MARKER_CIRCLE_RADIUS_PX_MAX,
                key="design_radius_locations",
                help=H_RADIUS_LOCATIONS,
            )
            st.slider(
                "Circle fill opacity",
                min_value=0.0,
                max_value=1.0,
                step=0.01,
                key="design_fo_locations",
                help=H_FO_LOCATIONS,
            )
            st.slider(
                "Edge weight",
                min_value=1,
                max_value=8,
                key="design_sw_visit",
                help=H_SW_VISIT,
            )
            _hex_text_input("Fill", key="design_hex_df", help=H_HEX_DF)
            _hex_text_input("Edge", key="design_hex_de", help=H_HEX_DE)
            with st.expander("Cluster colours", expanded=False):
                st.caption(
                    "Optional MarkerCluster icon colours for **All locations** (small → medium → large "
                    "marker counts). Enter all nine values (fill/border/halo per tier), or leave blank "
                    "for Leaflet.markercluster defaults."
                )
                _hex_text_input_cluster_tier(
                    "Small tier fill",
                    key="design_cluster_colour_hex_0",
                    help=H_CLUSTER_SMALL_FILL,
                )
                _hex_text_input_cluster_tier(
                    "Small tier border",
                    key="design_cluster_colour_hex_1",
                    help=H_CLUSTER_SMALL_BORDER,
                )
                _hex_text_input_cluster_tier(
                    "Small tier halo",
                    key="design_cluster_colour_hex_2",
                    help=H_CLUSTER_SMALL_HALO,
                )
                _hex_text_input_cluster_tier(
                    "Medium tier fill",
                    key="design_cluster_colour_hex_3",
                    help=H_CLUSTER_MEDIUM_FILL,
                )
                _hex_text_input_cluster_tier(
                    "Medium tier border",
                    key="design_cluster_colour_hex_4",
                    help=H_CLUSTER_MEDIUM_BORDER,
                )
                _hex_text_input_cluster_tier(
                    "Medium tier halo",
                    key="design_cluster_colour_hex_5",
                    help=H_CLUSTER_MEDIUM_HALO,
                )
                _hex_text_input_cluster_tier(
                    "Large tier fill",
                    key="design_cluster_colour_hex_6",
                    help=H_CLUSTER_LARGE_FILL,
                )
                _hex_text_input_cluster_tier(
                    "Large tier border",
                    key="design_cluster_colour_hex_7",
                    help=H_CLUSTER_LARGE_BORDER,
                )
                _hex_text_input_cluster_tier(
                    "Large tier halo",
                    key="design_cluster_colour_hex_8",
                    help=H_CLUSTER_LARGE_HALO,
                )
                st.caption(
                    "Opacity / spread mirror Leaflet.markercluster’s layered rgba look (inner fill, halo ring, border). "
                    "Defaults match ``MAP_MARKER_CLUSTER_*_DEFAULT`` in ``defaults.py``."
                )
                st.slider(
                    "Inner fill opacity",
                    min_value=0.0,
                    max_value=1.0,
                    step=0.01,
                    key="design_cluster_inner_fo",
                    help=H_CLUSTER_INNER_FO,
                )
                st.slider(
                    "Halo ring opacity",
                    min_value=0.0,
                    max_value=1.0,
                    step=0.01,
                    key="design_cluster_halo_o",
                    help=H_CLUSTER_HALO_O,
                )
                st.slider(
                    "Border opacity",
                    min_value=0.0,
                    max_value=1.0,
                    step=0.01,
                    key="design_cluster_border_o",
                    help=H_CLUSTER_BORDER_O,
                )
                st.slider(
                    "Halo spread (px)",
                    min_value=0,
                    max_value=24,
                    step=1,
                    key="design_cluster_halo_spread",
                    help=H_CLUSTER_HALO_SPREAD,
                )
                st.slider(
                    "Border width (px)",
                    min_value=0,
                    max_value=8,
                    step=1,
                    key="design_cluster_border_w",
                    help=H_CLUSTER_BORDER_W,
                )

        with st.expander(PREVIEW_SCOPE_LABELS[MAP_SCOPE_SPECIES_LOCATIONS], expanded=False):
            st.markdown("**Species** (species-match pins)")
            st.slider(
                "Circle radius (px)",
                min_value=1,
                max_value=MAP_MARKER_CIRCLE_RADIUS_PX_MAX,
                key="design_radius_species",
                help=H_RADIUS_SPECIES,
            )
            st.slider(
                "Circle fill opacity (species / last seen)",
                min_value=0.0,
                max_value=1.0,
                step=0.01,
                key="design_fo_species",
                help=H_FO_SPECIES,
            )
            st.slider(
                "Edge weight",
                min_value=1,
                max_value=8,
                key="design_sw_species",
                help=H_SW_SPECIES,
            )
            _hex_text_input("Fill (Species)", key="design_hex_sf", help=H_HEX_SF)
            _hex_text_input("Edge (Species)", key="design_hex_se", help=H_HEX_SE)
            st.divider()
            st.markdown("**Lifer** (map lifer)")
            _hex_text_input("Fill", key="design_hex_sml_f", help=H_HEX_SML_F)
            _hex_text_input("Edge", key="design_hex_sml_e", help=H_HEX_SML_E)
            st.divider()
            st.markdown("**Last seen**")
            _hex_text_input("Fill", key="design_hex_lsf", help=H_HEX_LSF)
            _hex_text_input("Edge", key="design_hex_lse", help=H_HEX_LSE)
            st.divider()
            with st.expander("Locations", expanded=False):
                st.slider(
                    "Circle radius (px)",
                    min_value=1,
                    max_value=MAP_MARKER_CIRCLE_RADIUS_PX_MAX,
                    key="design_radius_species_map_background",
                    help=H_RADIUS_SPECIES_MAP_LOCATIONS,
                )
                st.slider(
                    "Circle fill opacity",
                    min_value=0.0,
                    max_value=1.0,
                    step=0.01,
                    key="design_fo_species_map_background",
                    help=H_FO_SPECIES_MAP_LOCATIONS,
                )
                st.slider(
                    "Edge weight",
                    min_value=1,
                    max_value=8,
                    key="design_sw_species_map_background",
                    help=H_SW_SPECIES_MAP_LOCATIONS,
                )
                _hex_text_input("Fill", key="design_hex_smpl_f", help=H_HEX_SMPL_F)
                _hex_text_input("Edge", key="design_hex_smpl_e", help=H_HEX_SMPL_E)

        with st.expander(PREVIEW_SCOPE_LABELS[MAP_SCOPE_LIFER_LOCATIONS], expanded=False):
            st.markdown("**Base lifer** (species-level lifer at this location)")
            st.slider(
                "Circle radius (px)",
                min_value=1,
                max_value=MAP_MARKER_CIRCLE_RADIUS_PX_MAX,
                key="design_radius_lifer_map_lifer",
                help=H_RADIUS_LIFER_MAP_LIFER,
            )
            st.slider(
                "Circle fill opacity",
                min_value=0.0,
                max_value=1.0,
                step=0.01,
                key="design_fo_lifer_map_lifer",
                help=H_FO_LIFER_MAP_LIFER,
            )
            st.slider(
                "Edge weight",
                min_value=1,
                max_value=8,
                key="design_sw_lifer",
                help=H_SW_LIFER,
            )
            _hex_text_input("Fill", key="design_hex_lml_f", help=H_HEX_LML_F)
            _hex_text_input("Edge", key="design_hex_lml_e", help=H_HEX_LML_E)
            st.divider()
            st.markdown("**Subspecies** (taxon-only lifer when no species lifer at that location)")
            st.slider(
                "Circle radius (px)",
                min_value=1,
                max_value=MAP_MARKER_CIRCLE_RADIUS_PX_MAX,
                key="design_radius_lifer_map_subspecies",
                help=H_RADIUS_LIFER_MAP_SUBSPECIES,
            )
            st.slider(
                "Circle fill opacity",
                min_value=0.0,
                max_value=1.0,
                step=0.01,
                key="design_fo_lifer_map_subspecies",
                help=H_FO_LIFER_MAP_SUBSPECIES,
            )
            _hex_text_input("Fill", key="design_hex_lms_f", help=H_HEX_LMS_F)
            _hex_text_input("Edge", key="design_hex_lms_e", help=H_HEX_LMS_E)

        with st.expander(PREVIEW_SCOPE_LABELS[MAP_SCOPE_FAMILY_LOCATIONS], expanded=False):
            st.slider(
                "Circle radius (px)",
                min_value=1,
                max_value=MAP_MARKER_CIRCLE_RADIUS_PX_MAX,
                key="design_radius_families",
                help=H_RADIUS_FAMILIES,
            )
            st.slider(
                "Circle fill opacity",
                min_value=0.0,
                max_value=1.0,
                step=0.01,
                key="design_fo_family",
                help=H_FO_FAMILY,
            )
            st.slider(
                "Edge weight",
                min_value=1,
                max_value=8,
                key="design_sw_family",
                help=H_SW_FAM,
            )
            for i, band_label in enumerate(FAMILY_DENSITY_BAND_UI_LABELS):
                st.markdown(f"**{band_label}**")
                _hex_text_input("Fill", key=f"design_hex_ff{i}", help=H_HEX_FF)
                _hex_text_input("Edge", key=f"design_hex_fs{i}", help=H_HEX_FS)
            st.divider()
            st.markdown("**Species highlight**")
            st.slider(
                "Edge weight",
                min_value=1,
                max_value=8,
                key="design_sw_family_hl",
                help=H_SW_FAM_HL,
            )
            _hex_text_input("Edge", key="design_hex_fam_hl", help=H_HEX_FAM_HL)

        st.divider()
        st.subheader("Map frame")
        st.selectbox(
            "Basemap",
            options=list(MAP_BASEMAP_OPTIONS),
            format_func=lambda k: MAP_BASEMAP_LABELS.get(k, k),
            key="design_map_style",
            help=H_BASEMAP,
        )
        st.slider(
            "Map height (px)",
            min_value=MAP_HEIGHT_PX_MIN,
            max_value=MAP_HEIGHT_PX_MAX,
            step=MAP_HEIGHT_PX_STEP,
            key="design_height_px",
            help=H_HEIGHT,
        )

    if update:
        cfg = _config_from_session()
        st.session_state[_K_APPLIED] = cfg
        st.session_state[_K_RENDER] = int(st.session_state.get(_K_RENDER, 0)) + 1

    applied: DesignMapPreviewConfig | None = st.session_state.get(_K_APPLIED)
    cfg_export = _config_for_export()
    template_sch = active_map_marker_colour_scheme(int(st.session_state.get("design_scheme_pick", 1)))

    tab_preview, tab_export = st.tabs(["Map preview", "Export to defaults.py"])

    with tab_preview:
        if applied is None:
            st.info("Configure the sidebar and click **Update map** to render the preview.")
        else:
            h = int(applied.height_px)
            inject_map_folium_iframe_min_height_css(h)
            m = build_design_preview_map(
                applied,
                position_seed=int(st.session_state[_K_POS_SEED]),
            )
            try:
                from streamlit_folium import st_folium
            except ImportError:
                st.error("Install **streamlit-folium** (`pip install -r requirements.txt`).")
                st.stop()

            st_folium(
                m,
                use_container_width=True,
                height=h,
                key=f"design_folium_{st.session_state.get(_K_RENDER, 0)}",
                returned_objects=[],
                return_on_hover=False,
            )
            st.caption(
                "Bottom-left legend matches production maps (``build_legend_html``). "
                "Copies **0–1** cluster near Canberra; **2–3** scatter. Family bands: highlight stroke on "
                "copy **0** (cluster) and copy **2** (spread) so you can compare packed vs isolated. "
                "Invalid hex falls back to catch-all white/cream (see ``map_marker_colour_resolve``); "
                "resolved colours follow the scheme hierarchy in the sidebar preset."
            )

    with tab_export:
        st.markdown(
            "Generate **paste-ready** snippets for ``explorer/app/streamlit/defaults.py``. "
            "Edit the display name, then copy the code block — the app does **not** write files."
        )
        st.text_input(
            "Scheme display name",
            key=_K_EXPORT_NAME,
            help="display_name",
        )
        export_body = format_full_defaults_export(
            cfg_export,
            display_name=str(st.session_state.get(_K_EXPORT_NAME, "Scheme")),
            template=template_sch,
        )
        st.code(export_body, language="python")


if __name__ == "__main__":
    main()
