"""
Optional GitHub release vs embedded build notice for local runs (refs #189).

Uses ``@st.cache_data`` (24h TTL) for the GitHub API call so reruns do not hammer the network.
"""

from __future__ import annotations

import html as html_module
import json
import os
import urllib.error
import urllib.request
from typing import Any, Optional
from urllib.parse import urlparse

import streamlit as st

from explorer.app.streamlit.explorer_build_version import EXPLORER_BUILD_VERSION
from explorer.app.streamlit.streamlit_ui_constants import SIDEBAR_FOOTER_LINK_HEX
from explorer.core.explorer_paths import _safe_load_yaml_mapping
from explorer.core.explorer_release_version import remote_release_is_newer_than_embedded

GITHUB_RELEASES_LATEST_API = (
    "https://api.github.com/repos/jimchurches/myebirdstuff/releases/latest"
)
_UPDATE_CHECK_CACHE_TTL_SECONDS = 86400  # 24h
_HTTP_TIMEOUT_SEC = 5.0
_HTTP_USER_AGENT = "Personal-eBird-Explorer-update-check (+https://github.com/jimchurches/myebirdstuff)"


def _raw_explorer_update_check_override() -> str:
    """Env or Streamlit secrets value for ``EXPLORER_UPDATE_CHECK`` (empty if unset)."""
    raw = ""
    try:
        if "EXPLORER_UPDATE_CHECK" in st.secrets:
            raw = str(st.secrets["EXPLORER_UPDATE_CHECK"]).strip()
    except Exception:
        raw = ""
    if not raw:
        raw = str(os.environ.get("EXPLORER_UPDATE_CHECK", "")).strip()
    return raw


def _hostname_from_context_url(url: Any) -> str:
    if url is None:
        return ""
    try:
        if isinstance(url, str):
            return (urlparse(url).hostname or "").lower()
        h = getattr(url, "hostname", None) or getattr(url, "host", None)
        return (str(h) or "").lower()
    except Exception:
        return ""


def _config_files_opt_out_update_check(repo_root: str) -> bool:
    """True if ``check_for_updates: false`` appears in either YAML config."""
    config_dir = os.path.join(repo_root, "config")
    for name in ("config_secret.yaml", "config.yaml"):
        raw = _safe_load_yaml_mapping(os.path.join(config_dir, name))
        v = raw.get("check_for_updates")
        if v is False:
            return True
        if isinstance(v, str) and v.strip().lower() in {"false", "0", "no", "off"}:
            return True
    return False


def should_offer_explorer_update_check(repo_root: str) -> bool:
    """
    Whether to run the GitHub check and show UI.

    ``EXPLORER_UPDATE_CHECK=0`` / ``false`` forces off. ``EXPLORER_UPDATE_CHECK=1`` / ``true`` forces on
    (overrides Streamlit Community Cloud detection for tests). Otherwise hosted ``*.streamlit.app`` skips;
    YAML can opt out with ``check_for_updates: false``.
    """
    o = _raw_explorer_update_check_override().lower()
    if o in {"0", "false", "no", "off"}:
        return False
    if o in {"1", "true", "yes", "on"}:
        return True
    try:
        host = _hostname_from_context_url(st.context.url)
    except Exception:
        host = ""
    if host.endswith(".streamlit.app"):
        return False
    if _config_files_opt_out_update_check(repo_root):
        return False
    return True


def _fetch_github_latest_release_uncached() -> Optional[tuple[str, str]]:
    """Return ``(tag_name, html_url)`` or ``None`` on any failure."""
    req = urllib.request.Request(
        GITHUB_RELEASES_LATEST_API,
        headers={"Accept": "application/vnd.github+json", "User-Agent": _HTTP_USER_AGENT},
        method="GET",
    )
    try:
        with urllib.request.urlopen(req, timeout=_HTTP_TIMEOUT_SEC) as resp:  # noqa: S310
            if int(resp.status) != 200:
                return None
            body = resp.read().decode("utf-8", errors="replace")
    except (urllib.error.HTTPError, urllib.error.URLError, TimeoutError, OSError, ValueError):
        return None
    try:
        data = json.loads(body)
    except json.JSONDecodeError:
        return None
    tag = data.get("tag_name")
    if not isinstance(tag, str) or not tag.strip():
        return None
    html_url = data.get("html_url")
    url_out = html_url.strip() if isinstance(html_url, str) and html_url.strip() else ""
    return (tag.strip(), url_out)


@st.cache_data(ttl=_UPDATE_CHECK_CACHE_TTL_SECONDS, show_spinner=False)
def cached_github_latest_release() -> Optional[tuple[str, str]]:
    """
    Cached GitHub ``releases/latest`` result for this process.

    Failures are cached for the TTL as well so a flaky network does not retry every rerun.
    """
    try:
        return _fetch_github_latest_release_uncached()
    except Exception:
        return None


def _embedded_build_version() -> str:
    return EXPLORER_BUILD_VERSION


def explorer_update_notice_if_applicable(repo_root: str) -> Optional[tuple[str, str]]:
    """
    If an update should be advertised, return ``(remote_tag, release_url)``; else ``None``.

    Never raises; safe for sidebar/landing without try/except at call sites.
    """
    if not should_offer_explorer_update_check(repo_root):
        return None
    rel = cached_github_latest_release()
    if rel is None:
        return None
    tag, url = rel
    if not remote_release_is_newer_than_embedded(tag, _embedded_build_version()):
        return None
    return (tag, url)


def render_explorer_update_notice_sidebar(repo_root: str) -> None:
    """Subtle sidebar line + link when a newer GitHub release exists."""
    info = explorer_update_notice_if_applicable(repo_root)
    if info is None:
        return
    tag, url = info
    tag_esc = html_module.escape(tag, quote=True)
    hex_c = SIDEBAR_FOOTER_LINK_HEX
    if url:
        link = (
            f'<a href="{html_module.escape(url, quote=True)}" '
            'target="_blank" rel="noopener noreferrer" '
            f'style="color:{hex_c};text-decoration:underline;">See release notes</a>'
        )
    else:
        link = ""
    inner = f"New version available: <strong>{tag_esc}</strong>"
    if link:
        inner += f"<br/>{link}"
    st.sidebar.markdown(
        f'<div style="text-align:center;font-size:0.78rem;line-height:1.35;color:{hex_c};margin:0 0 0.5em 0;">'
        f"{inner}</div>",
        unsafe_allow_html=True,
    )


def render_explorer_update_notice_landing(repo_root: str) -> None:
    """Slightly more visible landing notice (``st.info``) when applicable."""
    info = explorer_update_notice_if_applicable(repo_root)
    if info is None:
        return
    tag, url = info
    if url:
        st.info(
            f"New version available: **{tag}**\n\n"
            f"[See release notes]({url})",
            icon="ℹ️",
        )
    else:
        st.info(f"New version available: **{tag}**", icon="ℹ️")
