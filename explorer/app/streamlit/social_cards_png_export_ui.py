"""Social Cards PNG export controls — cache, lazy export, download button."""

from __future__ import annotations

import streamlit as st

from explorer.app.streamlit.app_map_ui import inject_auto_click_streamlit_download_js
from explorer.app.streamlit.perf_instrumentation import perf_span
from explorer.app.streamlit.social_cards_stat_picker_ui import (
    _rerun_social_cards_fragment,
)
from explorer.app.streamlit.social_cards_streamlit_helpers import png_export_fingerprint
from explorer.core.share_summary_compute import (
    ShareSummaryAllTimeStats,
    ShareSummaryGeoScope,
    ShareSummaryStats,
)
from explorer.core.share_summary_insight_facts import ShareSummaryInsightFact
from explorer.presentation.share_summary_png_export import (
    share_summary_to_png_bytes,
)
from explorer.presentation.share_summary_preview import (
    FormatId,
    LayoutId,
    SpotlightPresentationId,
    TilesPresentationId,
)

SOCIAL_CARDS_PNG_EXPORT_BYTES_KEY = "_social_cards_png_export_bytes"
SOCIAL_CARDS_PNG_EXPORT_FINGERPRINT_KEY = "_social_cards_png_export_fingerprint"
SOCIAL_CARDS_PNG_EXPORT_ERROR_KEY = "_social_cards_png_export_error"
SOCIAL_CARDS_PNG_AUTO_DOWNLOAD_KEY = "_social_cards_png_auto_download"
SOCIAL_CARDS_PNG_EXPORT_BTN_KEY = "social_cards_export_png_btn"
SOCIAL_CARDS_PNG_DOWNLOAD_BTN_KEY = "social_cards_export_png_download_btn"


@st.cache_data(show_spinner="Generating PNG…")
def cached_share_summary_png(
    stats: ShareSummaryStats,
    layout: LayoutId,
    fmt: FormatId,
    card_stat_labels: tuple[str, ...],
    spotlight_label: str,
    all_time: ShareSummaryAllTimeStats | None,
    color_scheme_index: int,
    color_scheme_fingerprint: tuple[tuple[str, str], ...],
    scope_label: str | None,
    geo_scope: ShareSummaryGeoScope,
    tiles_presentation: TilesPresentationId = "grid",
    spotlight_presentation: SpotlightPresentationId = "classic",
    insight_fact: ShareSummaryInsightFact | None = None,
) -> bytes:
    """Cache PNG bytes for share-summary card export."""
    del color_scheme_fingerprint  # cache key only — render reads live scheme by index
    return share_summary_to_png_bytes(
        stats,
        layout=layout,
        fmt=fmt,
        spotlight_label=spotlight_label,
        insight_fact=insight_fact,
        card_stat_labels=card_stat_labels,
        all_time=all_time,
        color_scheme_index=color_scheme_index,
        scope_label=scope_label,
        geo_scope=geo_scope,
        tiles_presentation=tiles_presentation,
        spotlight_presentation=spotlight_presentation,
    )


def centered_card_download_button(
    *,
    label: str,
    data: bytes,
    file_name: str,
    mime: str,
    help_text: str,
    button_key: str | None = None,
) -> None:
    """Download control centred under the scaled card preview."""
    _, btn_col, _ = st.columns([1, 1, 1])
    with btn_col:
        st.download_button(
            label,
            data=data,
            file_name=file_name,
            mime=mime,
            use_container_width=True,
            help=help_text,
            key=button_key,
        )


def _clear_stale_png_export(fingerprint: tuple[object, ...]) -> None:
    cached_fp = st.session_state.get(SOCIAL_CARDS_PNG_EXPORT_FINGERPRINT_KEY)
    if cached_fp == fingerprint:
        return
    st.session_state.pop(SOCIAL_CARDS_PNG_EXPORT_BYTES_KEY, None)
    st.session_state.pop(SOCIAL_CARDS_PNG_EXPORT_FINGERPRINT_KEY, None)
    st.session_state.pop(SOCIAL_CARDS_PNG_AUTO_DOWNLOAD_KEY, None)


def _lazy_png_export_ready(fingerprint: tuple[object, ...]) -> bytes | None:
    if st.session_state.get(SOCIAL_CARDS_PNG_EXPORT_FINGERPRINT_KEY) != fingerprint:
        return None
    raw = st.session_state.get(SOCIAL_CARDS_PNG_EXPORT_BYTES_KEY)
    if isinstance(raw, (bytes, bytearray)):
        return bytes(raw)
    return None


def _generate_share_summary_png_bytes(
    *,
    stats: ShareSummaryStats,
    layout: LayoutId,
    fmt: FormatId,
    card_stat_labels: tuple[str, ...],
    spotlight_label: str,
    all_time: ShareSummaryAllTimeStats | None,
    color_scheme_index: int,
    scope_label: str,
    geo_scope: ShareSummaryGeoScope,
    tiles_presentation: TilesPresentationId,
    spotlight_presentation: SpotlightPresentationId,
    resolved_fact: ShareSummaryInsightFact | None,
) -> bytes:
    """Build PNG on demand — bypasses ``cached_share_summary_png`` spinner/cache."""
    with perf_span("social_cards.png_export"):
        return share_summary_to_png_bytes(
            stats,
            layout=layout,
            fmt=fmt,
            spotlight_label=spotlight_label,
            insight_fact=resolved_fact,
            card_stat_labels=card_stat_labels,
            all_time=all_time,
            color_scheme_index=color_scheme_index,
            scope_label=scope_label,
            geo_scope=geo_scope,
            tiles_presentation=tiles_presentation,
            spotlight_presentation=spotlight_presentation,
        )


def render_lazy_png_export_controls(
    *,
    stats: ShareSummaryStats,
    layout: LayoutId,
    fmt: FormatId,
    card_stat_labels: tuple[str, ...],
    spotlight_label: str,
    all_time: ShareSummaryAllTimeStats | None,
    color_scheme_index: int,
    scope_label: str,
    geo_scope: ShareSummaryGeoScope,
    tiles_presentation: TilesPresentationId,
    spotlight_presentation: SpotlightPresentationId,
    resolved_fact: ShareSummaryInsightFact | None,
    export_button_label: str,
    png_filename: str,
) -> None:
    """One user click: build PNG (spinner), rerun, auto-fire Streamlit download."""
    fingerprint = png_export_fingerprint(
        stats=stats,
        layout=layout,
        fmt=fmt,
        card_stat_labels=card_stat_labels,
        spotlight_label=spotlight_label,
        all_time=all_time,
        color_scheme_index=color_scheme_index,
        scope_label=scope_label,
        geo_scope=geo_scope,
        tiles_presentation=tiles_presentation,
        spotlight_presentation=spotlight_presentation,
        insight_fact=resolved_fact,
    )
    _clear_stale_png_export(fingerprint)

    err = st.session_state.get(SOCIAL_CARDS_PNG_EXPORT_ERROR_KEY)
    if err:
        st.warning(str(err))

    if st.session_state.pop(SOCIAL_CARDS_PNG_AUTO_DOWNLOAD_KEY, False):
        ready_png = _lazy_png_export_ready(fingerprint)
        if ready_png is None:
            st.warning(
                "PNG export was prepared but bytes are missing. Try Export again."
            )
            return
        st.caption("Starting download…")
        centered_card_download_button(
            label=export_button_label,
            data=ready_png,
            file_name=png_filename,
            mime="image/png",
            help_text="PNG of the current card above.",
            button_key=SOCIAL_CARDS_PNG_DOWNLOAD_BTN_KEY,
        )
        inject_auto_click_streamlit_download_js(button_label=export_button_label)
        return

    _, btn_col, _ = st.columns([1, 1, 1])
    with btn_col:
        if st.button(
            export_button_label,
            key=SOCIAL_CARDS_PNG_EXPORT_BTN_KEY,
            use_container_width=True,
            help="Generate a PNG of the current card.",
        ):
            st.session_state.pop(SOCIAL_CARDS_PNG_EXPORT_ERROR_KEY, None)
            try:
                png_bytes = _lazy_png_export_ready(fingerprint)
                if png_bytes is None:
                    with st.spinner("Generating PNG…"):
                        png_bytes = _generate_share_summary_png_bytes(
                            stats=stats,
                            layout=layout,
                            fmt=fmt,
                            card_stat_labels=card_stat_labels,
                            spotlight_label=spotlight_label,
                            all_time=all_time,
                            color_scheme_index=color_scheme_index,
                            scope_label=scope_label,
                            geo_scope=geo_scope,
                            tiles_presentation=tiles_presentation,
                            spotlight_presentation=spotlight_presentation,
                            resolved_fact=resolved_fact,
                        )
            except RuntimeError as exc:
                st.session_state[SOCIAL_CARDS_PNG_EXPORT_ERROR_KEY] = str(exc)
                st.session_state.pop(SOCIAL_CARDS_PNG_EXPORT_BYTES_KEY, None)
                st.session_state.pop(SOCIAL_CARDS_PNG_EXPORT_FINGERPRINT_KEY, None)
                # Fragment must rerun so the warning at the top is painted; without
                # this, a failed first click looks like a no-op (#345).
                _rerun_social_cards_fragment()
                return
            st.session_state[SOCIAL_CARDS_PNG_EXPORT_BYTES_KEY] = png_bytes
            st.session_state[SOCIAL_CARDS_PNG_EXPORT_FINGERPRINT_KEY] = fingerprint
            st.session_state[SOCIAL_CARDS_PNG_AUTO_DOWNLOAD_KEY] = True
            _rerun_social_cards_fragment()
