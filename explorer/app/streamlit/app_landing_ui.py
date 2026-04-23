"""No-data landing: upload flow until a dataframe is available (refs #131)."""

from __future__ import annotations

import base64
import os
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
from explorer.app.streamlit.streamlit_ui_constants import explorer_readme_github_url
from explorer.app.streamlit.streamlit_theme import inject_app_header_css

_APP_LOGO_SVG = Path(REPO_ROOT) / "docs" / "explorer" / "assets" / "personal-ebird-explorer-logo.svg"
_HOSTED_NOTICE_ENV_KEY = "STREAMLIT_SHOW_HOSTED_PERFORMANCE_NOTICE"

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
            "<div class='pebird-app-header' style='display:flex;flex-direction:row;align-items:flex-start;"
            "justify-content:space-between;flex-wrap:wrap;column-gap:0.75rem;row-gap:0.35rem;"
            "margin:0;padding:0;'>"
            "<div style='flex:1;min-width:min(100%,12rem);margin:0;padding:0;'>"
            "<h1 style='margin:0;padding:0;font-size:clamp(1.35rem,3.5vw,2.25rem);"
            "line-height:1.15;font-weight:600;'>Personal eBird Explorer</h1>"
            "<p style='margin:0.25rem 0 0 0;padding:0;font-size:1rem;line-height:1.45;'>"
            f"{tagline_esc}</p></div>"
            f"<img src='data:image/svg+xml;base64,{b64}' alt='' width='64' "
            "style='width:64px;max-width:min(64px,16vw);height:auto;display:block;margin:0.15rem 0 0 0;"
            "flex-shrink:0;'/>"
            "</div>"
        )
    else:
        tagline_esc = (
            APP_TAGLINE.replace("&", "&amp;")
            .replace("<", "&lt;")
            .replace(">", "&gt;")
        )
        st.html(
            "<div class='pebird-app-header' style='display:flex;flex-direction:row;align-items:flex-start;"
            "justify-content:space-between;flex-wrap:wrap;column-gap:0.75rem;row-gap:0.35rem;"
            "margin:0;padding:0;'>"
            "<div style='flex:1;min-width:min(100%,12rem);margin:0;padding:0;'>"
            "<h1 style='margin:0;padding:0;font-size:clamp(1.35rem,3.5vw,2.25rem);"
            "line-height:1.15;font-weight:600;'>Personal eBird Explorer</h1>"
            f"<p style='margin:0.25rem 0 0 0;padding:0;font-size:1rem;line-height:1.45;'>{tagline_esc}</p>"
            "</div></div>"
        )
    inject_app_header_css()


def inject_landing_typography_css() -> None:
    """Keep landing-page typography aligned with the rest of the app."""
    st.html(
        """<style>
.st-key-ebird_landing_main [data-testid="stMarkdownContainer"],
.st-key-ebird_landing_main [data-testid="stMarkdownContainer"] * {
  font-family: "Source Sans Pro", -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
}
.st-key-ebird_landing_main h1,
.st-key-ebird_landing_main h2,
.st-key-ebird_landing_main h3 {
  line-height: 1.25;
}
.st-key-ebird_landing_main [data-testid="stMarkdownContainer"] code,
.st-key-ebird_landing_main [data-testid="stCaptionContainer"] code {
  font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, "Liberation Mono", "Courier New", monospace;
  font-size: 0.92em;
  font-weight: 500;
  color: #1f6f54;
  background: rgba(31, 111, 84, 0.10);
  padding: 0.08em 0.34em;
  border-radius: 0.22rem;
}
</style>"""
    )


def _env_flag_true(key: str) -> bool:
    """Boolean flag parser from environment or Streamlit secrets (true/1/yes/on)."""
    raw: str = ""
    try:
        # Streamlit Community Cloud commonly provides config via ``st.secrets``.
        if key in st.secrets:
            raw = str(st.secrets[key]).strip()
    except Exception:
        # Keep landing resilient if secrets backend is unavailable in local/dev runs.
        raw = ""
    if not raw:
        raw = str(os.environ.get(key, "")).strip()
    raw = raw.lower()
    return raw in {"1", "true", "yes", "on"}


def show_hosted_performance_notice() -> bool:
    """Show hosted landing note only when explicitly enabled by environment."""
    return _env_flag_true(_HOSTED_NOTICE_ENV_KEY)


def hosted_performance_notice_markdown() -> str:
    """Landing note for hosted environments: set expectations and point to local setup docs."""
    docs_url = explorer_readme_github_url()
    return (
        "**Running on free Streamlit hosting**\n\n"
        "Explorer works here, but performance can be slow at times.\n\n"
        "- Best experience: run locally  \n"
        f"- Setup guide: [Explorer docs]({docs_url})  \n"
        "- Future: may move to faster hosting with community support"
    )


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
            inject_landing_typography_css()
            if show_hosted_performance_notice():
                st.info(hosted_performance_notice_markdown(), icon="ℹ️")
            st.markdown("Upload your `My eBird Data CSV` to open the map and tabs.")
            uploaded = st.file_uploader(
                " ",
                type=["csv"],
                key=EBIRD_LANDING_CSV_UPLOADER_KEY,
                label_visibility="collapsed",
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
Upload your eBird data to get started.

### Get your eBird data

1. Go to eBird -> [`Download My Data`](https://ebird.org/downloadMyData)
2. Under `My eBird Observations`, select `Request My Observations`
3. Wait for the email (usually a few minutes)
4. Download and unzip the file
5. Upload the CSV here (file name usually `MyEBirdData.csv`)

Tip: If species names look wrong, check `Settings -> Taxonomy` after loading.
                    """
                )
                st.caption(
                    "Species names come from the configured taxonomy; you can configure the taxonomy options "
                    "on the `Settings` tab once the full application has loaded. The default is `en_AU`.\n\n"
                    "If you’re running Explorer locally, you can load data automatically from a configured file. "
                    f"See [Explorer docs]({explorer_readme_github_url()}) for details."
                )
        sidebar_footer_links()
        if df_full is None:
            return None

    return (df_full, provenance, source_label, data_abs_path, data_basename)
