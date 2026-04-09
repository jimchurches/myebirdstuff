"""No-data landing: upload flow until a dataframe is available (refs #131)."""

from __future__ import annotations

import base64
from pathlib import Path
from typing import Any

import streamlit as st

from explorer.app.streamlit.app_constants import (
    EBIRD_LANDING_CSV_UPLOADER_KEY,
    EBIRD_LANDING_MAIN_CONTAINER_KEY,
    REPO_ROOT,
    SESSION_UPLOAD_CACHE_KEY,
)
from explorer.app.streamlit.app_data_loading import load_dataframe
from explorer.app.streamlit.app_map_ui import sidebar_footer_links

_APP_LOGO_SVG = Path(REPO_ROOT) / "docs" / "explorer" / "assets" / "personal-ebird-explorer-logo.svg"

APP_TAGLINE = "Your eBird data, made visible, navigable, and ready to explore"


def title_with_logo() -> None:
    """App heading: title + tagline stacked on the left, logo top-right—row height follows text, not the image."""
    if _APP_LOGO_SVG.is_file():
        b64 = base64.b64encode(_APP_LOGO_SVG.read_bytes()).decode("ascii")
        tagline_esc = (
            APP_TAGLINE.replace("&", "&amp;")
            .replace("<", "&lt;")
            .replace(">", "&gt;")
        )
        st.html(
            "<div style='display:flex;flex-direction:row;align-items:flex-start;justify-content:space-between;"
            "flex-wrap:wrap;column-gap:0.75rem;row-gap:0.35rem;margin:0;padding:0 0 0.5rem 0;'>"
            "<div style='flex:1;min-width:min(100%,12rem);margin:0;padding:0;'>"
            "<h1 style='margin:0;padding:0;font-size:clamp(1.35rem,3.5vw,2.25rem);"
            "line-height:1.15;font-weight:600;'>Personal eBird Explorer</h1>"
            "<p style='margin:0.25rem 0 0 0;padding:0;font-size:1rem;line-height:1.45;"
            "color:rgb(49,51,63);'>"
            f"{tagline_esc}</p></div>"
            f"<img src='data:image/svg+xml;base64,{b64}' alt='' width='64' "
            "style='width:64px;max-width:min(64px,16vw);height:auto;display:block;margin:0.15rem 0 0 0;"
            "flex-shrink:0;'/>"
            "</div>"
        )
    else:
        st.title("Personal eBird Explorer")
        st.markdown(APP_TAGLINE)


def load_dataframe_after_landing(
    upload_cache: Any,
) -> tuple[Any, Any, str, Any, str] | None:
    """Load CSV from disk/cache; if missing, run landing upload UI.

    Returns ``None`` when there is still no dataframe (caller should return). Otherwise returns the
    ``load_dataframe`` tuple ``(df_full, provenance, source_label, data_abs_path, data_basename)``.
    """
    df_full, provenance, source_label, data_abs_path, data_basename = load_dataframe(
        uploaded=None, upload_cache=upload_cache
    )

    if df_full is not None and provenance and "Disk:" in provenance:
        st.session_state.pop(SESSION_UPLOAD_CACHE_KEY, None)

    if df_full is None:
        with st.container(key=EBIRD_LANDING_MAIN_CONTAINER_KEY):
            title_with_logo()
            st.markdown("Upload your **My eBird Data** CSV to open the map and tabs.")
            uploaded = st.file_uploader(
                "eBird export (CSV)",
                type=["csv"],
                key=EBIRD_LANDING_CSV_UPLOADER_KEY,
                help="Official eBird full data export (CSV).",
            )
            if uploaded is not None:
                df_full, provenance, source_label, data_abs_path, data_basename = load_dataframe(
                    uploaded=uploaded, upload_cache=None
                )
                if df_full is not None:
                    st.session_state[SESSION_UPLOAD_CACHE_KEY] = (uploaded.getvalue(), uploaded.name)
                    st.rerun()

            if df_full is None:
                st.markdown(
                    """
**From eBird**

1. Sign in: [Download My Data](https://ebird.org/downloadMyData)
2. Under **My eBird Observations**, use **Request My Observations**.
3. A link to your data will be sent to your email address (often a few minutes; sometimes longer).
4. Open the email, download the **.zip** and unzip it.
5. Upload the CSV here (in English the file name should be **MyEBirdData.csv**).
                    """
                )
                st.caption(
                    "Species links default to **en_AU**; change locale under **Settings → Taxonomy** after load. "
                    "Data still loads if names don’t match.\n\n"
                    "This page is skipped when a CSV is already found on disk (local config path). "
                    "Support for local files works when Streamlit is running locally; see the code repo for more information. "
                    "Proper instructions will appear here in future releases."
                )
        sidebar_footer_links()
        if df_full is None:
            return None

    return (df_full, provenance, source_label, data_abs_path, data_basename)
