"""Sidebar “Go to GPS” expander for All locations / Species locations maps (refs #199)."""

from __future__ import annotations

import math

import streamlit as st

from explorer.app.streamlit.app_constants import (
    SESSION_GO_TO_GPS_PIN_KEY,
    STREAMLIT_GO_TO_GPS_DRAFT_LAT_TEXT_KEY,
    STREAMLIT_GO_TO_GPS_DRAFT_LON_TEXT_KEY,
)

# Pending draft updates must run before ``text_input`` widgets mount (Streamlit session_state rule).
_GO_TO_GPS_PENDING_DRAFT_UPDATE_KEY = "_go_to_gps_pending_draft_update"


def format_coord_for_display(v: float) -> str:
    """Stable decimal-degrees text without noisy trailing zeros."""
    s = f"{v:.10f}".rstrip("0").rstrip(".")
    return s if s else "0"


def parse_lat_lon_pair(text: str) -> tuple[float, float] | None:
    """Parse ``lat, lon`` paste (Google-style comma-separated decimal degrees)."""
    raw = (text or "").strip()
    if "," not in raw:
        return None
    parts = [p.strip() for p in raw.split(",", 1)]
    if len(parts) != 2:
        return None
    try:
        a = float(parts[0])
        b = float(parts[1])
    except ValueError:
        return None
    if not math.isfinite(a) or not math.isfinite(b):
        return None
    # Standard order from Google / eBird: latitude first, then longitude.
    la, lo = a, b
    if -90.0 <= la <= 90.0 and -180.0 <= lo <= 180.0:
        return (la, lo)
    return None


def parse_single_coord(text: str) -> float | None:
    """Parse one decimal number (strip stray commas from pasted fragments)."""
    raw = (text or "").strip()
    if not raw:
        return None
    raw = raw.replace(",", "")
    try:
        x = float(raw)
    except ValueError:
        return None
    return x if math.isfinite(x) else None


def go_to_gps_pin_from_session() -> tuple[float, float] | None:
    """Validated ``(lat, lon)`` for map build, or ``None``."""
    v = st.session_state.get(SESSION_GO_TO_GPS_PIN_KEY)
    if v is None:
        return None
    if not isinstance(v, (tuple, list)) or len(v) != 2:
        return None
    try:
        la, lo = float(v[0]), float(v[1])
    except (TypeError, ValueError):
        return None
    if not math.isfinite(la) or not math.isfinite(lo):
        return None
    if not (-90.0 <= la <= 90.0 and -180.0 <= lo <= 180.0):
        return None
    return (la, lo)


def _try_split_pasted_lat_lon() -> None:
    """If either field contains a ``lat, lon`` paste, split into both fields (refs #199)."""
    lat_s = str(st.session_state.get(STREAMLIT_GO_TO_GPS_DRAFT_LAT_TEXT_KEY, "")).strip()
    lon_s = str(st.session_state.get(STREAMLIT_GO_TO_GPS_DRAFT_LON_TEXT_KEY, "")).strip()
    for raw in (lat_s, lon_s):
        pair = parse_lat_lon_pair(raw)
        if pair:
            la, lo = pair
            st.session_state[STREAMLIT_GO_TO_GPS_DRAFT_LAT_TEXT_KEY] = format_coord_for_display(la)
            st.session_state[STREAMLIT_GO_TO_GPS_DRAFT_LON_TEXT_KEY] = format_coord_for_display(lo)
            break


def _sync_draft_text_from_pin() -> None:
    """Seed coordinate text fields from the active pin when draft keys are uninitialized."""
    _pin = st.session_state.get(SESSION_GO_TO_GPS_PIN_KEY)
    _missing = (
        STREAMLIT_GO_TO_GPS_DRAFT_LAT_TEXT_KEY not in st.session_state
        or STREAMLIT_GO_TO_GPS_DRAFT_LON_TEXT_KEY not in st.session_state
    )
    if not _missing:
        return
    if _pin and len(_pin) == 2:
        try:
            la, lo = float(_pin[0]), float(_pin[1])
            st.session_state[STREAMLIT_GO_TO_GPS_DRAFT_LAT_TEXT_KEY] = format_coord_for_display(la)
            st.session_state[STREAMLIT_GO_TO_GPS_DRAFT_LON_TEXT_KEY] = format_coord_for_display(lo)
        except (TypeError, ValueError):
            st.session_state[STREAMLIT_GO_TO_GPS_DRAFT_LAT_TEXT_KEY] = ""
            st.session_state[STREAMLIT_GO_TO_GPS_DRAFT_LON_TEXT_KEY] = ""
    else:
        st.session_state[STREAMLIT_GO_TO_GPS_DRAFT_LAT_TEXT_KEY] = ""
        st.session_state[STREAMLIT_GO_TO_GPS_DRAFT_LON_TEXT_KEY] = ""


def render_go_to_gps_sidebar_expander() -> None:
    """Collapsible lat/long fields + form actions; bumps Folium cache when pin is set or cleared."""
    from explorer.app.streamlit.app_map_working_ui import invalidate_folium_map_embed_cache

    _pending = st.session_state.pop(_GO_TO_GPS_PENDING_DRAFT_UPDATE_KEY, None)
    if _pending == "clear":
        st.session_state[STREAMLIT_GO_TO_GPS_DRAFT_LAT_TEXT_KEY] = ""
        st.session_state[STREAMLIT_GO_TO_GPS_DRAFT_LON_TEXT_KEY] = ""
    elif isinstance(_pending, tuple) and len(_pending) == 2:
        try:
            la = float(_pending[0])
            lo = float(_pending[1])
        except (TypeError, ValueError):
            pass
        else:
            if math.isfinite(la) and math.isfinite(lo):
                st.session_state[STREAMLIT_GO_TO_GPS_DRAFT_LAT_TEXT_KEY] = format_coord_for_display(la)
                st.session_state[STREAMLIT_GO_TO_GPS_DRAFT_LON_TEXT_KEY] = format_coord_for_display(lo)

    _sync_draft_text_from_pin()

    with st.expander("Go to GPS", expanded=False):
        st.text_input(
            "Latitude",
            key=STREAMLIT_GO_TO_GPS_DRAFT_LAT_TEXT_KEY,
            on_change=_try_split_pasted_lat_lon,
            placeholder="Decimal degrees, or paste lat, lon",
        )
        st.text_input(
            "Longitude",
            key=STREAMLIT_GO_TO_GPS_DRAFT_LON_TEXT_KEY,
            on_change=_try_split_pasted_lat_lon,
            placeholder="Decimal degrees, or paste lat, lon",
        )
        with st.form("go_to_gps_sidebar_form"):
            go = st.form_submit_button("Go to location")
            clear = st.form_submit_button("Clear marker")

        if go:
            lat_raw = str(st.session_state.get(STREAMLIT_GO_TO_GPS_DRAFT_LAT_TEXT_KEY, "")).strip()
            lon_raw = str(st.session_state.get(STREAMLIT_GO_TO_GPS_DRAFT_LON_TEXT_KEY, "")).strip()
            pair = parse_lat_lon_pair(lat_raw) or parse_lat_lon_pair(lon_raw)
            if pair:
                la, lo = pair
            else:
                la = parse_single_coord(lat_raw)
                lo = parse_single_coord(lon_raw)
            if (
                la is not None
                and lo is not None
                and -90.0 <= la <= 90.0
                and -180.0 <= lo <= 180.0
            ):
                st.session_state[SESSION_GO_TO_GPS_PIN_KEY] = (la, lo)
                invalidate_folium_map_embed_cache()
            else:
                st.error(
                    "Could not use those coordinates. Enter decimal degrees for latitude and "
                    'longitude, or paste a pair such as "-35.26897, 149.08054".'
                )

        if clear:
            st.session_state.pop(SESSION_GO_TO_GPS_PIN_KEY, None)
            st.session_state[_GO_TO_GPS_PENDING_DRAFT_UPDATE_KEY] = "clear"
            invalidate_folium_map_embed_cache()
            st.rerun()
