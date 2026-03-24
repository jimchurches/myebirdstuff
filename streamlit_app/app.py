"""
Personal eBird Explorer — Streamlit prototype (Folium map + notebook-style popups).

Planning and phased migration notes: https://github.com/jimchurches/myebirdstuff/issues/70 (refs #70).

Run locally from repo root::

    pip install -r requirements-streamlit.txt
    streamlit run streamlit_app/app.py

Same path resolution as the notebook when no file is uploaded: optional
``STREAMLIT_EBIRD_DATA_FOLDER``, then ``scripts/config_*.py``, then CSV in
this ``streamlit_app/`` folder.

Streamlit Cloud: CSV upload on the **landing** main area when disk resolution finds no file; session
state keeps upload bytes for reruns (no data picker on the dashboard). After a successful pick we
``st.rerun()`` so the next run loads from cache and **does not** emit landing widgets (title/uploader)
in the same pass as the dashboard — otherwise Streamlit’s top-to-bottom execution leaves landing + tabs
on screen together. If Streamlit Cloud still shows a stray upload blurb under tabs, treat as a
separate delta/orphan issue (e.g. container boundaries, Streamlit version); same-run load traded that
for a worse duplicate layout locally.

**No-data landing:** No disk file and no cached upload → title, copy, uploader in the main column.
Disk path takes precedence over a stale session upload when both exist.

**Taxonomy:** After CSV load, the app fetches the eBird taxonomy once per session (cached) so species
names in popups can link to eBird species pages. Default locale is **en_AU**; override with
``STREAMLIT_EBIRD_TAXONOMY_LOCALE`` / ``EBIRD_TAXONOMY_LOCALE`` or **Settings → Species links**.
Streamlit does not expose the browser language to Python.

**Checklist Statistics:** Shared HTML sections (nested ``st.tabs`` + formatted tables from
``checklist_stats_streamlit_tab_sections_html``). ``_cached_checklist_stats_payload`` runs **once** immediately
under the main tab bar (inside ``st.spinner("Doing interesting things with your eBird data...")``) so the loading message shows
no matter which tab is selected (refs #70).

**Country:** Per-country yearly table uses the same ``CHECKLIST_STATS_*`` HTML/CSS as Checklist Statistics
(``country_stats_streamlit_html``). The tab runs inside ``@st.fragment`` so changing the country selectbox
triggers a **partial rerun** (not the whole map/checklist pipeline) (refs #75).

**Maintenance:** Location duplicates / close locations, incomplete checklists, and sex-notation scan use
``maintenance_streamlit_html`` (nested tabs + expanders + shared HTML builders). Incomplete lists and sex
notation use the **full** export (``df_full``), not the date-filtered working set. **Close location (m)** is
configurable under **Settings → Maintenance** (refs #79).

**Rankings & lists:** ``rankings_streamlit_html`` — nested **Top Lists** / **Interesting Lists** tabs,
expanders per list, HTML from ``format_checklist_stats_bundle`` on ``df_full``. **Top N** and **visible rows**
are configured under **Settings → Tables & lists** (refs `#81`).

**Yearly Summary:** ``yearly_summary_streamlit_html`` — nested **All** / **Travelling** / **Stationary** tabs,
HTML tables from ``build_yearly_summary_streamlit_tab_html_dict`` on the date-filtered working set. When there are
more than 10 years, default columns are the most recent 10 with a **Show full history** toggle (refs #85).
"""

from __future__ import annotations

import io
import os
import sys
from collections import OrderedDict
from typing import Any, Callable

import pandas as pd
import streamlit as st

# Repo root (parent of streamlit_app/)
_APP_DIR = os.path.dirname(os.path.abspath(__file__))
_REPO_ROOT = os.path.normpath(os.path.join(_APP_DIR, ".."))
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)
if _APP_DIR not in sys.path:
    sys.path.insert(0, _APP_DIR)

from personal_ebird_explorer.checklist_stats_compute import (  # noqa: E402
    ChecklistStatsPayload,
    compute_checklist_stats_payload,
)
from personal_ebird_explorer.data_loader import load_dataset  # noqa: E402
from personal_ebird_explorer.explorer_paths import (  # noqa: E402
    build_explorer_candidate_dirs,
    resolve_ebird_data_file,
)
from personal_ebird_explorer.map_controller import build_species_overlay_map  # noqa: E402
from personal_ebird_explorer.species_search import (  # noqa: E402
    build_ram_species_whoosh_index,
    whoosh_species_suggestions,
)
from personal_ebird_explorer.species_logic import base_species_for_lifer  # noqa: E402
from personal_ebird_explorer.streamlit_map_prep import (  # noqa: E402
    data_signature_for_caches,
    prepare_all_locations_map_context,
)
from checklist_stats_streamlit_html import render_checklist_stats_streamlit_html  # noqa: E402
from rankings_streamlit_html import render_rankings_streamlit_tab  # noqa: E402
from personal_ebird_explorer.checklist_stats_display import (  # noqa: E402
    COUNTRY_TAB_SORT_ALPHABETICAL,
    COUNTRY_TAB_SORT_LIFERS_WORLD,
    COUNTRY_TAB_SORT_TOTAL_SPECIES,
)
from country_stats_streamlit_html import (  # noqa: E402
    run_country_tab_streamlit_fragment,
    sync_country_tab_session_inputs,
)
from maintenance_streamlit_html import render_maintenance_streamlit_tab  # noqa: E402
from yearly_summary_streamlit_html import render_yearly_summary_streamlit_tab  # noqa: E402
from map_working import (  # noqa: E402
    date_inception_to_today_default,
    folium_map_to_html_bytes,
    streamlit_working_set_and_status,
)

DEFAULT_EBIRD_FILENAME = os.environ.get("STREAMLIT_EBIRD_DATA_FILE", "MyEBirdData.csv")

# Open-source repo + author links (sidebar footer — text-only links; refs #70).
GITHUB_REPO_URL = "https://github.com/jimchurches/myebirdstuff"
EBIRD_PROFILE_URL = "https://ebird.org/profile/MjkxNDYyNQ"
INSTAGRAM_PROFILE_URL = "https://www.instagram.com/jimchurches/"

# Aligns with ``main_tabs`` in ``notebooks/personal_ebird_explorer`` (refs #70).
NOTEBOOK_MAIN_TAB_LABELS = (
    "Map",
    "Checklist Statistics",
    "Rankings & lists",
    "Yearly Summary",
    "Country",
    "Maintenance",
    "Settings",
)

# Same cap as notebook ``TOP_N_TABLE_LIMIT`` (checklist stats payload; Rankings tab uses its own sliders).
CHECKLIST_STATS_TOP_N_TABLE_LIMIT = 200

# Default Maintenance → close-location threshold (metres); overridden by Settings (refs #79).
DEFAULT_CLOSE_LOCATION_METERS = 10

# Match notebook-friendly default; eBird API uses this for common-name spellings in taxonomy CSV.
DEFAULT_TAXONOMY_LOCALE = "en_AU"

# Session-only: bytes + filename so reruns work without rendering ``st.file_uploader`` on the dashboard.
_SESSION_UPLOAD_CACHE_KEY = "_ebird_streamlit_upload_csv_cache"
# Survive Map view switch All locations ↔ Lifer (widgets not rendered on Lifer runs).
_PERSIST_MAP_DATE_FILTER_KEY = "_preserve_map_date_filter"
_PERSIST_MAP_DATE_RANGE_KEY = "_preserve_map_date_range"
# Remember species pick when switching map view (e.g. species → Lifer → back).
_PERSIST_SPECIES_COMMON_KEY = "_preserve_streamlit_species_common"
_PERSIST_SPECIES_SCI_KEY = "_preserve_streamlit_species_sci"
_SESSION_PREV_MAP_VIEW_KEY = "_streamlit_prev_map_view_mode"
_SESSION_SPECIES_SEARCH_KEY = "streamlit_species_searchbox"
_SESSION_SPECIES_WS_KEY = "_ws_for_species_search_fragment"
_SESSION_SPECIES_IX_KEY = "_streamlit_species_whoosh_ix"
_SESSION_SPECIES_IX_SIG_KEY = "_streamlit_species_whoosh_ix_sig"
_SESSION_SPECIES_PICK_KEY = "_streamlit_species_pick_common"
_FOLIUM_STATIC_MAP_CACHE_KEY = "_folium_static_all_lifer_cache"

_COUNTRY_SORT_LABELS = {
    COUNTRY_TAB_SORT_ALPHABETICAL: "Alphabetical",
    COUNTRY_TAB_SORT_LIFERS_WORLD: "By lifers (world)",
    COUNTRY_TAB_SORT_TOTAL_SPECIES: "By total species",
}

# Match ``.streamlit/config.toml`` [theme] (forest / eBird-adjacent greens).
_THEME_TEXT = "#1A2E22"
_THEME_PRIMARY = "#1F6F54"
_THEME_SECONDARY_BG = "#EEF4F0"

# Session flag: avoid stacking duplicate ``<style>`` blocks on every rerun.
# Bump suffix when CSS changes so returning users pick up new rules without clearing session.
_SPINNER_THEME_CSS_INJECTED_KEY = "_ebird_spinner_theme_css_injected_v3"

_SPINNER_THEME_CSS = f"""
<style>
/* Hoisted ``st.spinner`` — align with [theme] in .streamlit/config.toml */
/* Modern Streamlit uses an icon spinner (``iconValue: spinner``), not a CSS border ring. */
div[data-testid="stSpinner"],
div[data-testid="stSpinner"].stSpinner {{
  color: {_THEME_TEXT};
  font-family: "Source Sans Pro", -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
}}
/* Graphic: ``currentColor`` on the SVG so the arc tracks primary (not default grey). */
div[data-testid="stSpinner"] svg {{
  color: {_THEME_PRIMARY} !important;
}}
div[data-testid="stSpinner"] svg path,
div[data-testid="stSpinner"] svg circle {{
  fill: currentColor !important;
  stroke: currentColor !important;
}}
/* Spinner message is rendered as Streamlit markdown — target container + descendants. */
div[data-testid="stSpinner"] [data-testid="stMarkdownContainer"],
div[data-testid="stSpinner"] [data-testid="stMarkdownContainer"] * {{
  color: {_THEME_TEXT} !important;
  font-family: "Source Sans Pro", -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif !important;
}}
div[data-testid="stSpinner"] p,
div[data-testid="stSpinner"] span,
div[data-testid="stSpinner"] label {{
  color: {_THEME_TEXT} !important;
}}
/* Older border-based spinner (harmless if unused) */
div[data-testid="stSpinner"] div[class*="Spinner"] {{
  border-color: {_THEME_SECONDARY_BG} !important;
  border-top-color: {_THEME_PRIMARY} !important;
}}
</style>
"""


def _inject_spinner_theme_css() -> None:
    """Tweak hoisted checklist-stats spinner to match our theme (refs #70).

    Use :func:`streamlit.html` for **style-only** blocks: ``st.markdown(..., unsafe_allow_html)``
    sanitizes or scopes HTML so global ``<style>`` may not affect the spinner; style-only
    ``st.html`` is applied via Streamlit’s event container (see Streamlit ``HtmlMixin.html``).
    """
    if st.session_state.get(_SPINNER_THEME_CSS_INJECTED_KEY):
        return
    # ``st.html`` exists from Streamlit 1.31+; requirements pin 1.40+.
    st.html(_SPINNER_THEME_CSS.strip())
    st.session_state[_SPINNER_THEME_CSS_INJECTED_KEY] = True


def _init_and_clamp_streamlit_table_settings() -> None:
    """Defaults and ranges for Settings → tables / maintenance (refs #81)."""
    if "streamlit_rankings_top_n" not in st.session_state:
        st.session_state.streamlit_rankings_top_n = 200
    else:
        st.session_state.streamlit_rankings_top_n = max(
            10, min(500, int(st.session_state.streamlit_rankings_top_n))
        )
    if "streamlit_rankings_visible_rows" not in st.session_state:
        st.session_state.streamlit_rankings_visible_rows = 16
    else:
        st.session_state.streamlit_rankings_visible_rows = max(
            10, min(50, int(st.session_state.streamlit_rankings_visible_rows))
        )
    if "streamlit_close_location_meters" not in st.session_state:
        st.session_state.streamlit_close_location_meters = DEFAULT_CLOSE_LOCATION_METERS
    else:
        st.session_state.streamlit_close_location_meters = max(
            0, min(250, int(st.session_state.streamlit_close_location_meters))
        )


def _static_map_cache_key(
    work_df: pd.DataFrame,
    map_view_mode: str,
    date_filter_banner: str,
    map_style: str,
) -> tuple:
    """Stable key for All / Lifer map reuse (same CSV + filter + basemap)."""
    n = len(work_df)
    sid0 = ""
    if n > 0 and "Submission ID" in work_df.columns:
        sid0 = str(work_df["Submission ID"].iloc[0])
    return (map_view_mode, date_filter_banner, map_style, n, sid0)


def _env_taxonomy_locale() -> str:
    """Non-empty locale from env if set (notebook parity)."""
    return (
        os.environ.get("STREAMLIT_EBIRD_TAXONOMY_LOCALE", "").strip()
        or os.environ.get("EBIRD_TAXONOMY_LOCALE", "").strip()
    )


def _sidebar_footer_links() -> None:
    """Small centred sidebar footer: GitHub, eBird, Instagram — text links only (icons dropped; narrow sidebar)."""
    st.sidebar.divider()
    link_style = 'color:#868e96;text-decoration:none;'
    sep = '<span style="opacity:0.45;margin:0 0.55em;" aria-hidden="true">·</span>'
    st.sidebar.markdown(
        f'<div style="text-align:center;font-size:0.8rem;">'
        f'<a href="{GITHUB_REPO_URL}" target="_blank" rel="noopener noreferrer" '
        f'style="{link_style}" title="View source on GitHub">GitHub</a>'
        f"{sep}"
        f'<a href="{EBIRD_PROFILE_URL}" target="_blank" rel="noopener noreferrer" '
        f'style="{link_style}" title="eBird profile">eBird</a>'
        f"{sep}"
        f'<a href="{INSTAGRAM_PROFILE_URL}" target="_blank" rel="noopener noreferrer" '
        f'style="{link_style}" title="Instagram">Instagram</a>'
        "</div>",
        unsafe_allow_html=True,
    )


@st.cache_data(show_spinner=False)
def _cached_checklist_stats_payload(df: pd.DataFrame) -> ChecklistStatsPayload | None:
    """Structured checklist stats for the Checklist Statistics tab (refs #68)."""
    return compute_checklist_stats_payload(df, CHECKLIST_STATS_TOP_N_TABLE_LIMIT)


@st.cache_data(show_spinner=False)
def _cached_sex_notation_by_year(df: pd.DataFrame) -> dict:
    """Sex-notation maintenance scan on full export (refs #79)."""
    from personal_ebird_explorer.stats import get_sex_notation_by_year

    return get_sex_notation_by_year(df)


def _full_location_data_for_maintenance(df: pd.DataFrame) -> pd.DataFrame:
    """Unique locations for map maintenance (same columns as notebook ``full_location_data``)."""
    cols = ["Location ID", "Location", "Latitude", "Longitude"]
    if not all(c in df.columns for c in cols):
        return pd.DataFrame(columns=cols)
    return df[cols].drop_duplicates()


@st.cache_resource(show_spinner="Loading eBird taxonomy…")
def _cached_species_url_fn(locale_key: str) -> Callable[[str], str | None]:
    """One taxonomy fetch per session per locale; used for species links in map UI."""
    from personal_ebird_explorer.taxonomy import get_species_url, load_taxonomy

    loc = locale_key.strip() if locale_key and locale_key.strip() else None
    if load_taxonomy(locale=loc):
        return get_species_url
    return lambda _: None


@st.fragment
def _species_searchbox_fragment() -> None:
    """Whoosh-backed search; fragment-scoped reruns avoid greying the whole app (refs #70)."""
    try:
        from streamlit_searchbox import st_searchbox
    except ImportError:
        st.error(
            "Missing **streamlit-searchbox**. Install with: "
            "`pip install -r requirements-streamlit.txt` (refs #70)."
        )
        return
    ix = st.session_state.get(_SESSION_SPECIES_IX_KEY)
    if ix is None:
        return
    persisted = st.session_state.get(_PERSIST_SPECIES_COMMON_KEY)

    def _search(term: str) -> list:
        return whoosh_species_suggestions(
            ix,
            term,
            max_options=12,
            min_query_len=3,
        )

    def _on_species_submit(selected: Any) -> None:
        """Library does not rerun the full app on submit; the map lives outside this fragment."""
        st.session_state[_SESSION_SPECIES_PICK_KEY] = selected
        st.rerun()

    def _on_species_reset() -> None:
        st.session_state.pop(_SESSION_SPECIES_PICK_KEY, None)
        st.rerun()

    pick = st_searchbox(
        _search,
        key=_SESSION_SPECIES_SEARCH_KEY,
        placeholder="Type species name…",
        label="Species",
        default=persisted,
        default_searchterm=persisted or "",
        debounce=400,
        edit_after_submit="option",
        rerun_scope="fragment",
        submit_function=_on_species_submit,
        reset_function=_on_species_reset,
    )
    st.session_state[_SESSION_SPECIES_PICK_KEY] = pick


def _secrets_data_folder() -> str | None:
    try:
        s = st.secrets
        if "EBIRD_DATA_FOLDER" in s and str(s["EBIRD_DATA_FOLDER"]).strip():
            return str(s["EBIRD_DATA_FOLDER"]).strip()
    except Exception:
        pass
    return None


def _load_dataframe(
    *,
    uploaded: Any | None = None,
    upload_cache: tuple[bytes, str] | None = None,
) -> tuple[pd.DataFrame | None, str | None]:
    """
    Return ``(df, provenance_html)`` or ``(None, None)`` if nothing loaded yet.

    Precedence: *uploaded* (landing widget, new pick) → **disk** (config / path resolution) →
    *upload_cache* (session bytes from a prior upload this session). ``load_dataset`` / path logic stay
    here for later enhancements (refs #70).
    """
    if uploaded is not None:
        try:
            raw = uploaded.getvalue()
            df = load_dataset(io.BytesIO(raw))
            return df, f"Upload: **{uploaded.name}**"
        except Exception as e:
            st.error(f"Could not load CSV: {e}")
            return None, None

    env_folder = os.environ.get("STREAMLIT_EBIRD_DATA_FOLDER", "").strip() or None
    secrets_folder = _secrets_data_folder()
    hardcoded = env_folder or secrets_folder

    try:
        folders, sources = build_explorer_candidate_dirs(
            repo_root=_REPO_ROOT,
            anchor_dir=_APP_DIR,
            data_folder_hardcoded=hardcoded,
            anchor_label="streamlit app folder",
        )
        path, _folder, src = resolve_ebird_data_file(DEFAULT_EBIRD_FILENAME, folders, sources)
        df = load_dataset(path)
        label = src.replace("_", " ").title()
        return df, f"Disk: `{path}` (_{label}_)"
    except FileNotFoundError:
        pass

    if upload_cache is not None:
        raw, name = upload_cache
        try:
            df = load_dataset(io.BytesIO(raw))
            return df, f"Upload: **{name}**"
        except Exception as e:
            st.error(f"Could not load CSV: {e}")
            return None, None

    return None, None


def main() -> None:
    st.set_page_config(page_title="Personal eBird Explorer (Streamlit)", layout="wide")

    if "streamlit_taxonomy_locale" not in st.session_state:
        st.session_state.streamlit_taxonomy_locale = _env_taxonomy_locale() or DEFAULT_TAXONOMY_LOCALE
    if "streamlit_country_tab_sort" not in st.session_state:
        st.session_state.streamlit_country_tab_sort = COUNTRY_TAB_SORT_ALPHABETICAL
    _init_and_clamp_streamlit_table_settings()

    upload_cache = st.session_state.get(_SESSION_UPLOAD_CACHE_KEY)
    if upload_cache is not None and not (
        isinstance(upload_cache, tuple) and len(upload_cache) == 2 and isinstance(upload_cache[0], bytes)
    ):
        upload_cache = None

    df_full, provenance = _load_dataframe(uploaded=None, upload_cache=upload_cache)

    if df_full is not None and provenance and "Disk:" in provenance:
        # Drop stale session upload when disk resolution wins (local path after a prior Cloud upload).
        st.session_state.pop(_SESSION_UPLOAD_CACHE_KEY, None)

    if df_full is None:
        # Keyed container: on the post-upload rerun this block is skipped entirely, so Cloud/Streamlit
        # can drop the whole landing subtree instead of leaving orphan markdown under tabs.
        with st.container(key="ebird_landing_main"):
            st.title("Personal eBird Explorer")
            st.subheader("Streamlit prototype")
            st.markdown("Upload your **My eBird Data** CSV to open the map and tabs.")
            uploaded = st.file_uploader(
                "eBird export (CSV)",
                type=["csv"],
                key="ebird_landing_csv_uploader",
                help="Official eBird full data export (CSV).",
            )
            if uploaded is not None:
                df_full, provenance = _load_dataframe(uploaded=uploaded, upload_cache=None)
                if df_full is not None:
                    st.session_state[_SESSION_UPLOAD_CACHE_KEY] = (uploaded.getvalue(), uploaded.name)
                    # Landing widgets already ran above in this run; rerun loads from cache and skips this block.
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
                    "Species links default to **en_AU**; change locale under **Settings → Species links** after load. "
                    "Data still loads if names don’t match.\n\n"
                    "This page is skipped when a CSV is already found on disk (local config path). "
                    "Support for local files works when Streamlit is running locally; see the code repo for more information. "
                    "Proper instructions will appear here in future releases."
                )
        _sidebar_footer_links()
        if df_full is None:
            return

    if "popup_html_cache" not in st.session_state:
        st.session_state.popup_html_cache = {}
    if "filtered_by_loc_cache" not in st.session_state:
        st.session_state.filtered_by_loc_cache = OrderedDict()

    _MAP_VIEW_LABEL_TO_MODE = {
        "All locations": "all",
        "Selected species": "species",
        "Lifer locations": "lifers",
    }

    with st.sidebar:
        st.header("Map")

        map_view_label = st.selectbox(
            "Map view",
            ["All locations", "Selected species", "Lifer locations"],
            key="streamlit_map_view_label",
        )
        map_view_mode = _MAP_VIEW_LABEL_TO_MODE[map_view_label]
        is_lifer_view = map_view_mode == "lifers"

        st.markdown("**Date**")
        if is_lifer_view:
            st.caption("Lifer locations is not date-filtered.")
            if st.session_state.get(_PERSIST_MAP_DATE_FILTER_KEY, False):
                st.caption(
                    "Your date filter is preserved for other map views."
                )
            date_filter_on_effective = False
            date_range_sel: tuple | None = None
        else:
            # Restore widget keys after Lifer view (those widgets were not rendered, keys may be missing).
            if "streamlit_map_date_filter" not in st.session_state:
                st.session_state.streamlit_map_date_filter = bool(
                    st.session_state.get(_PERSIST_MAP_DATE_FILTER_KEY, False)
                )
            if st.session_state.get("streamlit_map_date_filter", False):
                if "streamlit_map_date_range" not in st.session_state:
                    pr = st.session_state.get(_PERSIST_MAP_DATE_RANGE_KEY)
                    if isinstance(pr, tuple) and len(pr) == 2:
                        st.session_state.streamlit_map_date_range = pr
                    else:
                        a, b = date_inception_to_today_default(df_full)
                        st.session_state.streamlit_map_date_range = (a, b)

            date_filter_on_effective = st.toggle(
                "Date filter",
                key="streamlit_map_date_filter",
                help="Turn on to limit the map and checklist stats to a date range.",
            )
            if not date_filter_on_effective:
                date_range_sel = None
            else:
                d_inception, today = date_inception_to_today_default(df_full)
                # Clamp range into [d_inception, today] via session state only — do not pass
                # `value=` here or Streamlit warns when the key is also set via session_state.
                if "streamlit_map_date_range" not in st.session_state:
                    st.session_state.streamlit_map_date_range = (d_inception, today)
                rng = st.session_state["streamlit_map_date_range"]
                if not isinstance(rng, tuple) or len(rng) != 2:
                    st.session_state.streamlit_map_date_range = (d_inception, today)
                else:
                    r0 = max(min(rng[0], today), d_inception)
                    r1 = max(min(rng[1], today), d_inception)
                    rng_val = (r0, r1) if r0 <= r1 else (r1, r0)
                    if rng_val != rng:
                        st.session_state.streamlit_map_date_range = rng_val
                dr = st.date_input(
                    "Date range",
                    min_value=d_inception,
                    max_value=today,
                    key="streamlit_map_date_range",
                )
                if isinstance(dr, tuple) and len(dr) == 2:
                    date_range_sel = (dr[0], dr[1])
                else:
                    date_range_sel = (d_inception, today)

            # Persist for return from Lifer map (and page reruns).
            st.session_state[_PERSIST_MAP_DATE_FILTER_KEY] = date_filter_on_effective
            if date_filter_on_effective and date_range_sel is not None:
                st.session_state[_PERSIST_MAP_DATE_RANGE_KEY] = date_range_sel

    ws, date_filter_banner = streamlit_working_set_and_status(
        df_full,
        map_view_mode=map_view_mode,
        date_filter_on=date_filter_on_effective,
        date_range=date_range_sel,
        map_caches=(st.session_state.popup_html_cache, st.session_state.filtered_by_loc_cache),
    )
    if ws is None:
        st.error("Invalid date range. Using all-time data for this run.")
        ws, date_filter_banner = streamlit_working_set_and_status(
            df_full,
            map_view_mode=map_view_mode,
            date_filter_on=False,
            date_range=None,
            map_caches=(st.session_state.popup_html_cache, st.session_state.filtered_by_loc_cache),
        )
    work_df = ws.df

    hide_non_matching_locations = False
    species_pick_common: str | None = None
    species_pick_sci = ""

    # Re-entering Selected species from another view: drop widget state so default + searchterm apply.
    _prev_mv = st.session_state.get(_SESSION_PREV_MAP_VIEW_KEY)
    if map_view_mode == "species" and _prev_mv is not None and _prev_mv != "species":
        st.session_state.pop(_SESSION_SPECIES_SEARCH_KEY, None)

    if map_view_mode == "species":
        _ix_sig = (len(ws.species_list), st.session_state.get("ebird_data_sig"))
        if st.session_state.get(_SESSION_SPECIES_IX_SIG_KEY) != _ix_sig:
            st.session_state[_SESSION_SPECIES_IX_KEY] = build_ram_species_whoosh_index(
                ws.species_list, ws.name_map
            )
            st.session_state[_SESSION_SPECIES_IX_SIG_KEY] = _ix_sig
        st.session_state[_SESSION_SPECIES_WS_KEY] = ws

        with st.sidebar:
            st.markdown("**Species**")
            st.caption("Type at least three letters. Searches common and scientific names.")
            _species_searchbox_fragment()
            hide_non_matching_locations = st.toggle(
                "Show only selected species",
                key="streamlit_species_hide_only",
                help=(
                    "When off, all locations are shown with your species highlighted. "
                    "When on, only locations where you recorded the species."
                ),
            )

        species_pick_common = st.session_state.get(_SESSION_SPECIES_PICK_KEY)
        if species_pick_common:
            species_pick_sci = str(ws.name_map.get(species_pick_common, "") or "")
            st.session_state[_PERSIST_SPECIES_COMMON_KEY] = species_pick_common
            st.session_state[_PERSIST_SPECIES_SCI_KEY] = species_pick_sci
        else:
            st.session_state.pop(_PERSIST_SPECIES_COMMON_KEY, None)
            st.session_state.pop(_PERSIST_SPECIES_SCI_KEY, None)
    else:
        st.session_state.pop(_SESSION_SPECIES_PICK_KEY, None)

    with st.sidebar:
        st.divider()
        map_style = st.selectbox(
            "Basemap",
            options=["default", "satellite", "google", "carto"],
            index=0,
        )
        st.markdown(
            '<div style="height:0.65rem" aria-hidden="true"></div>',
            unsafe_allow_html=True,
        )
        map_height = st.slider(
            "Map height (px)",
            min_value=440,
            max_value=1200,
            value=720,
            step=20,
        )

    st.session_state[_SESSION_PREV_MAP_VIEW_KEY] = map_view_mode

    tax_locale_effective = (st.session_state.streamlit_taxonomy_locale.strip() or DEFAULT_TAXONOMY_LOCALE)
    species_url_fn = _cached_species_url_fn(tax_locale_effective)

    _inject_spinner_theme_css()

    st.title("Personal eBird Explorer — Streamlit prototype")

    (
        tab_map,
        tab_checklist,
        tab_rankings,
        tab_yearly,
        tab_country,
        tab_maint,
        tab_settings,
    ) = st.tabs(NOTEBOOK_MAIN_TAB_LABELS)

    # Hoisted: spinner lives in the main column (not inside a tab panel) so it’s visible on Map, etc.
    with st.spinner("Doing interesting things with your eBird data  🐣  🐥  🐧  🦆  🦉  🦢  🦅  …"):
        checklist_payload = _cached_checklist_stats_payload(work_df)
        maint_full_payload = _cached_checklist_stats_payload(df_full)
        sex_notation_by_year = _cached_sex_notation_by_year(df_full)

    with tab_map:
        prov_plain = provenance or ""
        sig = data_signature_for_caches(df_full, prov_plain)
        if st.session_state.get("ebird_data_sig") != sig:
            st.session_state.ebird_data_sig = sig
            st.session_state.popup_html_cache = {}
            st.session_state.filtered_by_loc_cache = OrderedDict()
            st.session_state.pop(_FOLIUM_STATIC_MAP_CACHE_KEY, None)

        try:
            ctx = prepare_all_locations_map_context(work_df, full_df=df_full)
        except ValueError as e:
            st.warning(str(e))
            st.session_state.pop("_explorer_map_html_bytes", None)
        else:
            overlay_common = (
                (species_pick_common or "").strip() if map_view_mode == "species" else ""
            )
            overlay_sci = (
                (species_pick_sci or "").strip() if map_view_mode == "species" else ""
            )
            hide_nm = (
                map_view_mode == "species"
                and bool(overlay_sci)
                and hide_non_matching_locations
            )
            _map_kw = {
                **ctx,
                "selected_species": overlay_sci,
                "selected_common_name": overlay_common,
                "map_style": map_style,
                "popup_sort_order": "ascending",
                "popup_scroll_hint": "shading",
                "date_filter_status": date_filter_banner,
                "species_url_fn": species_url_fn,
                "base_species_fn": base_species_for_lifer,
                "popup_html_cache": st.session_state.popup_html_cache,
                "filtered_by_loc_cache": st.session_state.filtered_by_loc_cache,
                "map_view_mode": map_view_mode,
                "hide_non_matching_locations": hide_nm,
            }
            _ck = _static_map_cache_key(work_df, map_view_mode, date_filter_banner, map_style)
            _use_static_cache = map_view_mode in ("all", "lifers")
            _cached = (
                st.session_state.get(_FOLIUM_STATIC_MAP_CACHE_KEY) if _use_static_cache else None
            )
            if (
                _use_static_cache
                and isinstance(_cached, dict)
                and _cached.get("key") == _ck
                and _cached.get("map") is not None
            ):
                result_map = _cached["map"]
                result_warning = _cached.get("warning")
            else:
                result = build_species_overlay_map(**_map_kw)
                result_map = result.map
                result_warning = result.warning
                if _use_static_cache and result_map is not None:
                    st.session_state[_FOLIUM_STATIC_MAP_CACHE_KEY] = {
                        "key": _ck,
                        "map": result_map,
                        "warning": result_warning,
                    }

            if result_warning:
                st.warning(result_warning)
                st.session_state.pop("_explorer_map_html_bytes", None)
            elif result_map is None:
                st.warning("Map could not be built.")
                st.session_state.pop("_explorer_map_html_bytes", None)
            else:
                st.session_state["_explorer_map_html_bytes"] = folium_map_to_html_bytes(result_map)
                try:
                    from streamlit_folium import st_folium
                except ImportError:
                    st.error(
                        "Missing **streamlit-folium** (needed to embed the Folium map). "
                        "Locally: `pip install -r requirements-streamlit.txt`. "
                        "**Streamlit Community Cloud:** set app **Python requirements** to "
                        "`requirements-streamlit.txt` or `streamlit_app/requirements.txt` "
                        "(not the repo root `requirements.txt`)."
                    )
                    st.stop()
                # returned_objects=[] avoids pan/zoom reruns; key includes height for resize.
                st_folium(
                    result_map,
                    use_container_width=True,
                    height=map_height,
                    key=f"explorer_folium_map_h{map_height}",
                    returned_objects=[],
                    return_on_hover=False,
                )

    with tab_checklist:
        if checklist_payload is not None:
            render_checklist_stats_streamlit_html(
                checklist_payload,
                species_url_fn=species_url_fn,
            )
        else:
            st.warning("No checklist data to show.")

    with tab_rankings:
        if df_full is None or df_full.empty:
            st.info("Load checklist data to use Rankings & lists.")
        else:
            render_rankings_streamlit_tab(
                df_full,
                country_sort=st.session_state.streamlit_country_tab_sort,
                taxonomy_locale=tax_locale_effective,
            )

    with tab_yearly:
        render_yearly_summary_streamlit_tab(checklist_payload)

    with tab_country:
        if checklist_payload is not None:
            sync_country_tab_session_inputs(checklist_payload)
            run_country_tab_streamlit_fragment()
        else:
            st.warning("No checklist data to show.")

    with tab_maint:
        loc_maint = _full_location_data_for_maintenance(df_full)
        incomplete_maint: dict = {}
        if maint_full_payload is not None:
            incomplete_maint = maint_full_payload.incomplete_by_year or {}
        render_maintenance_streamlit_tab(
            loc_maint,
            close_location_meters=int(st.session_state.streamlit_close_location_meters),
            incomplete_by_year=incomplete_maint,
            sex_notation_by_year=sex_notation_by_year,
            species_url_fn=species_url_fn,
        )

    with tab_settings:
        st.subheader("Species links")
        st.text_input(
            "Taxonomy locale (species page URLs)",
            key="streamlit_taxonomy_locale",
            help="eBird API locale for species names in taxonomy CSV (e.g. en_AU, en_GB). "
            "Empty is treated as en_AU.",
        )
        st.caption(
            "Used for species links in map popups and elsewhere. First-visit default: "
            "``STREAMLIT_EBIRD_TAXONOMY_LOCALE`` / ``EBIRD_TAXONOMY_LOCALE``, else en_AU."
        )
        st.divider()
        st.subheader("Tables & lists")
        st.slider(
            "Top N table limit",
            min_value=10,
            max_value=500,
            value=200,
            step=1,
            key="streamlit_rankings_top_n",
            help="Caps how many rows feed each “Top …” ranking on **Rankings & lists**.",
        )
        st.slider(
            "Rankings visible rows",
            min_value=10,
            max_value=50,
            value=16,
            step=1,
            key="streamlit_rankings_visible_rows",
            help="Scroll area height for rankings tables (row shading) on **Rankings & lists**.",
        )
        st.radio(
            "Country ordering",
            options=[
                COUNTRY_TAB_SORT_ALPHABETICAL,
                COUNTRY_TAB_SORT_LIFERS_WORLD,
                COUNTRY_TAB_SORT_TOTAL_SPECIES,
            ],
            format_func=lambda k: _COUNTRY_SORT_LABELS[k],
            key="streamlit_country_tab_sort",
            help="Order of countries on the **Country** tab.",
        )
        st.divider()
        st.subheader("Maintenance")
        st.slider(
            "Close location (m)",
            min_value=0,
            max_value=250,
            value=DEFAULT_CLOSE_LOCATION_METERS,
            step=1,
            key="streamlit_close_location_meters",
            help=(
                "Locations within this distance (metres), excluding exact duplicate coordinates, "
                "are listed under **Maintenance → Location Maintenance → Close locations**."
            ),
        )

    if st.session_state.get("_explorer_map_html_bytes"):
        with st.sidebar:
            st.divider()
            st.download_button(
                "Export map HTML",
                data=st.session_state["_explorer_map_html_bytes"],
                file_name="ebird_map.html",
                mime="text/html",
                key="export_map_html_btn",
                help="Standalone HTML for the current map (notebook-style export).",
            )

    _sidebar_footer_links()


if __name__ == "__main__":
    main()
