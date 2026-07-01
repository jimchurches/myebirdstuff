"""Social Cards sidebar controls — shared by design studio and main app."""

from __future__ import annotations

from dataclasses import dataclass

import pandas as pd
import streamlit as st

from explorer.app.streamlit.social_cards_session_keys import SocialCardsSessionKeys
from explorer.core.region_display import map_focus_key_for_display
from explorer.core.share_summary_compute import (
    ShareSummaryGeoScope,
    geo_country_keys_from_df,
    geo_region_options_for_country,
)
from explorer.core.share_summary_defaults import (
    SHARE_SUMMARY_COLOR_SCHEME_IDS,
    share_summary_color_scheme_index,
    share_summary_color_scheme_label,
    share_summary_layout_label,
    share_summary_spotlight_presentation_label,
    share_summary_tiles_presentation_label,
)
from explorer.presentation.share_summary_preview import (
    FORMAT_LABELS,
    FORMAT_PIXELS,
    FormatId,
    LayoutId,
    SpotlightPresentationId,
    TilesPresentationId,
)

_GEO_WORLD_OPTION = ""
_PREVIEW_SCALE_DEFAULT = 0.42
_PREVIEW_SCALE_FULL = 1.0
SOCIAL_CARDS_CURRENT_CARD_SIDEBAR_HEADER = "Current card"


@dataclass(frozen=True)
class SocialCardsSidebarSelection:
    """Card layout and presentation choices from the Social Cards sidebar block."""

    layout: LayoutId
    fmt: FormatId
    color_scheme_index: int
    tiles_presentation: TilesPresentationId
    spotlight_presentation: SpotlightPresentationId
    scale: float


def _geo_country_select_label(country_key: str) -> str:
    if not country_key:
        return "World"
    return map_focus_key_for_display(country_key)


def render_sidebar_geo_scope_controls(
    df: pd.DataFrame,
    keys: SocialCardsSessionKeys,
) -> ShareSummaryGeoScope:
    """Country and region pickers; World is the default (no filter)."""
    country_keys = geo_country_keys_from_df(df)
    country_options = [_GEO_WORLD_OPTION, *country_keys]
    country_key = st.selectbox(
        "Country",
        options=country_options,
        format_func=_geo_country_select_label,
        key=keys.geo_country,
    )
    if not country_key:
        st.session_state.pop(keys.geo_region, None)
        return ShareSummaryGeoScope()

    region_pairs = geo_region_options_for_country(df, country_key)
    region_options = [_GEO_WORLD_OPTION, *[code for code, _ in region_pairs]]
    region_labels = {_GEO_WORLD_OPTION: "All regions"}
    region_labels.update({code: label for code, label in region_pairs})
    current_region = st.session_state.get(keys.geo_region, _GEO_WORLD_OPTION)
    if current_region not in region_options:
        st.session_state[keys.geo_region] = _GEO_WORLD_OPTION
    region_code = st.selectbox(
        "Region",
        options=region_options,
        format_func=lambda code: region_labels[code],
        key=keys.geo_region,
    )
    return ShareSummaryGeoScope(
        country_key=country_key,
        region_code=region_code or None,
    )


def preview_scale_caption(fmt: FormatId, scale: float) -> str | None:
    """Hint when preview is at or near export pixel size."""
    if scale < _PREVIEW_SCALE_FULL - 0.005:
        return None
    width, height = FORMAT_PIXELS[fmt]
    return (
        f"Export size ({width}×{height}px). "
        "Scroll the page to see the full card — story format is tall."
        if height > width
        else f"Export size ({width}×{height}px) — matches the PNG export."
    )


def render_sidebar_preview_scale_controls(
    fmt: FormatId,
    keys: SocialCardsSessionKeys,
) -> float:
    """Preview scale slider from compact default up to export pixel size."""
    scale = st.slider(
        "Preview scale",
        min_value=_PREVIEW_SCALE_DEFAULT,
        max_value=_PREVIEW_SCALE_FULL,
        value=_PREVIEW_SCALE_DEFAULT,
        step=0.01,
        help="Drag right for full export size (100%). Default 0.42 is a compact preview.",
        key=keys.preview_scale,
    )
    caption = preview_scale_caption(fmt, scale)
    if caption:
        st.caption(caption)
    return scale


def render_sidebar_card_controls(
    keys: SocialCardsSessionKeys,
    *,
    section_header: str = SOCIAL_CARDS_CURRENT_CARD_SIDEBAR_HEADER,
) -> SocialCardsSidebarSelection:
    """Layout, format, theme, and preview-scale controls for the current card."""
    st.header(section_header)
    selected_layout: LayoutId = st.selectbox(
        "Layout",
        options=["tiles", "minimal", "spotlight", "insight"],
        format_func=share_summary_layout_label,
    )
    tiles_presentation: TilesPresentationId = "grid"
    if selected_layout == "tiles":
        tiles_presentation = st.radio(
            "Tiles presentation",
            options=["grid", "circles"],
            format_func=share_summary_tiles_presentation_label,
            key=keys.tiles_presentation,
            horizontal=True,
        )
    spotlight_presentation: SpotlightPresentationId = "classic"
    if selected_layout == "spotlight":
        spotlight_presentation = st.radio(
            "Spotlight presentation",
            options=["classic", "circle"],
            format_func=share_summary_spotlight_presentation_label,
            key=keys.spotlight_presentation,
            horizontal=True,
        )
    fmt: FormatId = st.selectbox(
        "Aspect ratio",
        options=["square", "portrait_post", "story"],
        format_func=lambda x: FORMAT_LABELS[x],
    )
    color_theme_id = st.selectbox(
        "Theme",
        options=list(SHARE_SUMMARY_COLOR_SCHEME_IDS),
        format_func=share_summary_color_scheme_label,
        key=keys.color_theme,
    )
    color_scheme_index = share_summary_color_scheme_index(color_theme_id)
    scale = render_sidebar_preview_scale_controls(fmt, keys)
    return SocialCardsSidebarSelection(
        layout=selected_layout,
        fmt=fmt,
        color_scheme_index=color_scheme_index,
        tiles_presentation=tiles_presentation,
        spotlight_presentation=spotlight_presentation,
        scale=scale,
    )
