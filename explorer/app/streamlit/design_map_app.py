"""
Map marker **design** utility — dummy Folium markers for tuning colours and geometry (refs #147).

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

import os
import re
import sys

# ``streamlit run explorer/app/streamlit/design_map_app.py`` puts the script directory on ``sys.path``,
# not the repo root — same as :mod:`explorer.app.streamlit.app` (refs #70).
_REPO_ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", ".."))
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)

import streamlit as st

from explorer.app.streamlit.defaults import (
    MAP_BASEMAP_LABELS,
    MAP_BASEMAP_OPTIONS,
    MAP_HEIGHT_PX_DEFAULT,
    MAP_HEIGHT_PX_MAX,
    MAP_HEIGHT_PX_MIN,
    MAP_HEIGHT_PX_STEP,
    MAP_MARKER_CIRCLE_RADIUS_PX_FALLBACK,
    MAP_MARKER_CIRCLE_RADIUS_PX_MAX,
    MAP_MARKER_CATCHALL_EDGE_HEX,
    MAP_MARKER_CATCHALL_FILL_HEX,
    active_map_marker_colour_scheme,
    clamp_map_marker_circle_fill_opacity,
    clamp_map_marker_circle_radius_px,
)
from explorer.app.streamlit.app_map_ui import inject_map_folium_iframe_min_height_css
from explorer.app.streamlit.design_map_constants import (
    FAMILY_DENSITY_BAND_UI_LABELS,
    H_BASEMAP,
    H_FO_DEFAULT,
    H_CLUSTER_TIER_LARGE,
    H_CLUSTER_TIER_MEDIUM,
    H_CLUSTER_TIER_SMALL,
    H_FO_FAMILY,
    H_FO_LIFERS,
    H_FO_LOCATIONS,
    H_FO_SPECIES,
    H_HEIGHT,
    H_HEX_DE,
    H_HEX_DF,
    H_HEX_FAM_HL,
    H_HEX_FF,
    H_HEX_FS,
    H_HEX_LE,
    H_HEX_LF,
    H_HEX_LSE,
    H_HEX_LSF,
    H_HEX_SE,
    H_HEX_SF,
    H_PRESET,
    H_RADIUS_DEFAULT,
    H_RADIUS_FAMILIES,
    H_RADIUS_LIFERS,
    H_RADIUS_LOCATIONS,
    H_RADIUS_SPECIES,
    H_SW_FAM,
    H_SW_FAM_HL,
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
    MARKER_SCHEME_FALLBACK_DEFAULT_BASE_STROKE_WEIGHT,
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
    """Prefix ``#`` when the widget value is hex digits only (e.g. pasted ``95A5B2``)."""
    v = st.session_state.get(key)
    if v is None:
        return
    s = str(v).strip()
    if not s or s.startswith("#"):
        return
    if _HEX_BODY_NO_HASH.match(s):
        st.session_state[key] = f"#{s}"


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


def _cluster_tier_fill_hex_from_session() -> tuple[str, str, str] | None:
    """Return three tier hexes only if all fields are non-empty; otherwise ``None`` (Folium defaults)."""
    parts: list[str] = []
    for i in range(3):
        raw = st.session_state.get(f"design_cluster_hex_{i}")
        s = "" if raw is None else str(raw).strip()
        parts.append(s)
    if all(x == "" for x in parts):
        return None
    if any(x == "" for x in parts):
        return None
    return (
        normalize_hex_colour(parts[0]),
        normalize_hex_colour(parts[1]),
        normalize_hex_colour(parts[2]),
    )


def _fill_opacity_from_session(key: str, *, legacy_key: str | None, default: float) -> float:
    """Read slider session value; optional *legacy_key* for renamed widgets (refs #147)."""
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
    # instantiated above the button — Streamlit forbids mutating that key afterward (refs #147).
    st.session_state["design_map_style"] = cfg.map_style
    st.session_state["design_height_px"] = int(cfg.height_px)
    st.session_state["design_radius_default"] = int(cfg.marker_default_circle_radius_px)
    st.session_state["design_radius_locations"] = int(cfg.marker_circle_radius_locations)
    st.session_state["design_radius_species"] = int(cfg.marker_circle_radius_species)
    st.session_state["design_radius_lifers"] = int(cfg.marker_circle_radius_lifers)
    st.session_state["design_radius_families"] = int(cfg.marker_circle_radius_families)
    st.session_state["design_sw_visit"] = int(cfg.stroke_weight_visit)
    st.session_state["design_sw_family"] = int(cfg.stroke_weight_family)
    st.session_state["design_sw_family_hl"] = int(cfg.stroke_weight_family_highlight)
    st.session_state["design_fo_locations"] = float(cfg.marker_circle_fill_opacity_locations)
    st.session_state["design_fo_species"] = float(cfg.marker_circle_fill_opacity_species)
    st.session_state["design_fo_lifers"] = float(cfg.marker_circle_fill_opacity_lifers)
    st.session_state["design_fo_family"] = float(cfg.marker_circle_fill_opacity_families)
    st.session_state["design_marker_default_fill_hex"] = cfg.marker_default_fill_hex
    st.session_state["design_marker_default_edge_hex"] = cfg.marker_default_edge_hex
    st.session_state["design_marker_default_circle_fill_opacity"] = float(cfg.marker_default_circle_fill_opacity)
    st.session_state["design_marker_default_base_stroke_weight"] = int(cfg.marker_default_base_stroke_weight)
    st.session_state["design_hex_de"] = cfg.default_edge
    st.session_state["design_hex_df"] = cfg.default_fill
    st.session_state["design_hex_se"] = cfg.species_edge
    st.session_state["design_hex_sf"] = cfg.species_fill
    st.session_state["design_hex_le"] = cfg.lifer_edge
    st.session_state["design_hex_lf"] = cfg.lifer_fill
    st.session_state["design_hex_lse"] = cfg.last_seen_edge
    st.session_state["design_hex_lsf"] = cfg.last_seen_fill
    for i in range(4):
        st.session_state[f"design_hex_ff{i}"] = cfg.family_fill_hex[i]
        st.session_state[f"design_hex_fs{i}"] = cfg.family_stroke_hex[i]
    st.session_state["design_hex_fam_hl"] = cfg.family_highlight_stroke_hex
    st.session_state["design_legend_hl_swatch_ix"] = int(cfg.legend_highlight_swatch_fill_index)
    ct = cfg.marker_cluster_tier_fill_hex
    if ct is not None and len(ct) == 3:
        for i in range(3):
            st.session_state[f"design_cluster_hex_{i}"] = ct[i]
    else:
        for i in range(3):
            st.session_state[f"design_cluster_hex_{i}"] = ""
    st.session_state[_K_EXPORT_NAME] = active_map_marker_colour_scheme(scheme_index).display_name


def _config_from_session() -> DesignMapPreviewConfig:
    _ps = str(st.session_state.get("design_preview_scope", MAP_SCOPE_ALL))
    _scope = _ps if _ps in MAP_SCOPES else MAP_SCOPE_ALL
    _fb = MAP_MARKER_CIRCLE_RADIUS_PX_FALLBACK
    _raw_default = st.session_state.get("design_radius_default")
    _md = clamp_map_marker_circle_radius_px(_raw_default if _raw_default is not None else _fb)
    _mdf = clamp_map_marker_circle_fill_opacity(
        st.session_state.get("design_marker_default_circle_fill_opacity"),
        fallback=MARKER_SCHEME_FALLBACK_DEFAULT_FILL_OPACITY,
    )
    return DesignMapPreviewConfig(
        preview_scope=_scope,
        map_style=str(st.session_state.get("design_map_style", "default")),
        height_px=max(
            MAP_HEIGHT_PX_MIN,
            min(MAP_HEIGHT_PX_MAX, int(st.session_state.get("design_height_px", MAP_HEIGHT_PX_DEFAULT))),
        ),
        marker_default_circle_radius_px=_md,
        marker_circle_radius_locations=_radius_from_session("design_radius_locations", default_px=_md),
        marker_circle_radius_species=_radius_from_session("design_radius_species", default_px=_md),
        marker_circle_radius_lifers=_radius_from_session("design_radius_lifers", default_px=_md),
        marker_circle_radius_families=_radius_from_session("design_radius_families", default_px=_md),
        stroke_weight_visit=max(1, int(st.session_state.get("design_sw_visit", 1))),
        stroke_weight_family=max(1, int(st.session_state.get("design_sw_family", 1))),
        stroke_weight_family_highlight=max(1, int(st.session_state.get("design_sw_family_hl", 1))),
        marker_circle_fill_opacity_locations=_fill_opacity_from_session(
            "design_fo_locations", legacy_key="design_fo_all", default=_mdf
        ),
        marker_circle_fill_opacity_species=_fill_opacity_from_session(
            "design_fo_species", legacy_key="design_fo_emph", default=_mdf
        ),
        marker_circle_fill_opacity_lifers=_fill_opacity_from_session(
            "design_fo_lifers", legacy_key=None, default=_mdf
        ),
        marker_circle_fill_opacity_families=_fill_opacity_from_session(
            "design_fo_family", legacy_key=None, default=_mdf
        ),
        marker_default_fill_hex=str(
            st.session_state.get("design_marker_default_fill_hex", MAP_MARKER_CATCHALL_FILL_HEX)
        ),
        marker_default_edge_hex=str(
            st.session_state.get("design_marker_default_edge_hex", MAP_MARKER_CATCHALL_EDGE_HEX)
        ),
        marker_default_circle_fill_opacity=_mdf,
        marker_default_base_stroke_weight=max(
            1,
            int(
                st.session_state.get(
                    "design_marker_default_base_stroke_weight",
                    MARKER_SCHEME_FALLBACK_DEFAULT_BASE_STROKE_WEIGHT,
                )
            ),
        ),
        default_edge=str(st.session_state.get("design_hex_de", MAP_MARKER_CATCHALL_EDGE_HEX)),
        default_fill=str(st.session_state.get("design_hex_df", MAP_MARKER_CATCHALL_FILL_HEX)),
        species_edge=str(st.session_state.get("design_hex_se", MAP_MARKER_CATCHALL_EDGE_HEX)),
        species_fill=str(st.session_state.get("design_hex_sf", MAP_MARKER_CATCHALL_FILL_HEX)),
        lifer_edge=str(st.session_state.get("design_hex_le", MAP_MARKER_CATCHALL_EDGE_HEX)),
        lifer_fill=str(st.session_state.get("design_hex_lf", MAP_MARKER_CATCHALL_FILL_HEX)),
        last_seen_edge=str(st.session_state.get("design_hex_lse", MAP_MARKER_CATCHALL_EDGE_HEX)),
        last_seen_fill=str(st.session_state.get("design_hex_lsf", MAP_MARKER_CATCHALL_FILL_HEX)),
        family_fill_hex=tuple(
            str(st.session_state.get(f"design_hex_ff{i}", MAP_MARKER_CATCHALL_FILL_HEX)) for i in range(4)
        ),
        family_stroke_hex=tuple(
            str(st.session_state.get(f"design_hex_fs{i}", MAP_MARKER_CATCHALL_EDGE_HEX)) for i in range(4)
        ),
        family_highlight_stroke_hex=str(
            st.session_state.get("design_hex_fam_hl", MAP_MARKER_CATCHALL_EDGE_HEX)
        ),
        legend_highlight_swatch_fill_index=max(
            0, min(3, int(st.session_state.get("design_legend_hl_swatch_ix", 0)))
        ),
        marker_cluster_tier_fill_hex=_cluster_tier_fill_hex_from_session(),
    )


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
        st.selectbox(
            "Map view",
            options=list(_scope_options),
            format_func=lambda k: PREVIEW_SCOPE_LABELS.get(k, k),
            key="design_preview_scope",
        )

        st.divider()
        st.subheader("Colour scheme (defaults)")
        scheme_ix = st.selectbox(
            "Preset from defaults.py",
            options=[1, 2, 3],
            key="design_scheme_pick",
            format_func=lambda i: active_map_marker_colour_scheme(int(i)).display_name,
            help=H_PRESET,
        )
        if st.button("Load preset into controls", use_container_width=True):
            _seed_controls_from_scheme(int(scheme_ix))
            st.rerun()
        if st.button("Shuffle positions", use_container_width=True):
            st.session_state[_K_POS_SEED] = int(st.session_state.get(_K_POS_SEED, 42)) + 1
        update = st.button("Update map", type="primary", use_container_width=True)

        st.divider()
        st.caption(
            "**Globals** holds defaults for all maps; each collection expander holds that map type’s "
            "circle radius, fill opacity, and colours (like **Map view**)."
        )

        with st.expander("Globals", expanded=False):
            st.slider(
                "Default circle radius (px) — all maps",
                min_value=1,
                max_value=MAP_MARKER_CIRCLE_RADIUS_PX_MAX,
                key="design_radius_default",
                help=H_RADIUS_DEFAULT,
            )
            st.slider(
                "Default circle fill opacity — all maps",
                min_value=0.0,
                max_value=1.0,
                step=0.05,
                key="design_marker_default_circle_fill_opacity",
                help=H_FO_DEFAULT,
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
                step=0.05,
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
                    "Optional fills for **All locations** map MarkerCluster icons (small → medium → large "
                    "marker counts). Leave all blank to keep Folium / Leaflet.markercluster defaults."
                )
                _hex_text_input_cluster_tier(
                    "Small tier",
                    key="design_cluster_hex_0",
                    help=H_CLUSTER_TIER_SMALL,
                )
                _hex_text_input_cluster_tier(
                    "Medium tier",
                    key="design_cluster_hex_1",
                    help=H_CLUSTER_TIER_MEDIUM,
                )
                _hex_text_input_cluster_tier(
                    "Large tier",
                    key="design_cluster_hex_2",
                    help=H_CLUSTER_TIER_LARGE,
                )

        with st.expander(PREVIEW_SCOPE_LABELS[MAP_SCOPE_SPECIES_LOCATIONS], expanded=False):
            st.slider(
                "Circle radius (px)",
                min_value=1,
                max_value=MAP_MARKER_CIRCLE_RADIUS_PX_MAX,
                key="design_radius_species",
                help=H_RADIUS_SPECIES,
            )
            st.caption(
                "Lifer marker colours and lifer fill opacity are configured in the Lifer locations expander."
            )
            st.slider(
                "Circle fill opacity (species / last seen)",
                min_value=0.0,
                max_value=1.0,
                step=0.05,
                key="design_fo_species",
                help=H_FO_SPECIES,
            )
            _hex_text_input("Fill (Species)", key="design_hex_sf", help=H_HEX_SF)
            _hex_text_input("Edge (Species)", key="design_hex_se", help=H_HEX_SE)
            _hex_text_input("Fill (Last seen)", key="design_hex_lsf", help=H_HEX_LSF)
            _hex_text_input("Edge (Last seen)", key="design_hex_lse", help=H_HEX_LSE)

        with st.expander(PREVIEW_SCOPE_LABELS[MAP_SCOPE_LIFER_LOCATIONS], expanded=False):
            st.slider(
                "Circle radius (px)",
                min_value=1,
                max_value=MAP_MARKER_CIRCLE_RADIUS_PX_MAX,
                key="design_radius_lifers",
                help=H_RADIUS_LIFERS,
            )
            st.slider(
                "Circle fill opacity",
                min_value=0.0,
                max_value=1.0,
                step=0.05,
                key="design_fo_lifers",
                help=H_FO_LIFERS,
            )
            _hex_text_input("Fill", key="design_hex_lf", help=H_HEX_LF)
            _hex_text_input("Edge", key="design_hex_le", help=H_HEX_LE)

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
                step=0.05,
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
            st.slider(
                "Edge weight (Species highlight)",
                min_value=1,
                max_value=8,
                key="design_sw_family_hl",
                help=H_SW_FAM_HL,
            )
            for i, band_label in enumerate(FAMILY_DENSITY_BAND_UI_LABELS):
                st.markdown(f"**{band_label}**")
                _hex_text_input("Fill", key=f"design_hex_ff{i}", help=H_HEX_FF)
                _hex_text_input("Edge", key=f"design_hex_fs{i}", help=H_HEX_FS)
            _hex_text_input(
                "Edge (Species highlight)",
                key="design_hex_fam_hl",
                help=H_HEX_FAM_HL,
            )

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
    cfg_live = _config_from_session()
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
                "Lifer **both**: outer ring is stroke-only; inner uses lifer fill. "
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
            cfg_live,
            display_name=str(st.session_state.get(_K_EXPORT_NAME, "Scheme")),
            template=template_sch,
        )
        st.code(export_body, language="python")
        st.caption(
            "Single ``MapMarkerColourScheme`` dict: resolved ``visit_*`` / ``circle_marker_*`` opacities "
            "and radii, plus optional sparse ``marker_circle_radius_px_*`` / ``marker_circle_fill_opacity_*`` "
            "and ``marker_cluster_tier_fill_hex`` when set. Rename ``EXPORT`` symbols as needed; #147 wires consumers."
        )


if __name__ == "__main__":
    main()
