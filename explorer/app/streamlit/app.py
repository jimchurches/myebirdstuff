"""
Personal eBird Explorer — Streamlit app (Folium map + rich location popups).

Planning and phased migration notes: https://github.com/jimchurches/myebirdstuff/issues/70 (refs #70).

Run locally from repo root::

    pip install -r requirements.txt
    streamlit run explorer/app/streamlit/app.py

Disk resolution when no file is uploaded: ``config/config_secret.yaml`` and
``config/config.yaml`` (``data_folder``), then the **process working directory**
(where you ran ``streamlit run``). See ``explorer/app/streamlit/README.md`` — *Data loading*.

Streamlit Cloud: CSV upload on the **landing** main area when disk resolution finds no file; session
state keeps upload bytes for reruns (no data picker on the dashboard). After a successful pick we
``st.rerun()`` so the next run loads from cache and **does not** emit landing widgets (title/uploader)
in the same pass as the dashboard — otherwise Streamlit’s top-to-bottom execution leaves landing + tabs
on screen together. If Streamlit Cloud still shows a stray upload blurb under tabs, treat as a
separate delta/orphan issue (e.g. container boundaries, Streamlit version); same-run load traded that
for a worse duplicate layout locally.

**No-data landing:** No disk file and no cached upload → title, copy, uploader in the main column.
Disk path takes precedence over a stale session upload when both exist. Implementation:
:mod:`explorer.app.streamlit.app_landing_ui` (refs #131).

**Taxonomy:** After CSV load, the app fetches the eBird taxonomy once per session (cached) so species
names in popups can link to eBird species pages. Default locale is **en_AU**; override with
``STREAMLIT_EBIRD_TAXONOMY_LOCALE`` / ``EBIRD_TAXONOMY_LOCALE`` or **Settings → Taxonomy**.
Streamlit does not expose the browser language to Python.

**Checklist Statistics:** Shared HTML sections (nested ``st.tabs`` + formatted tables from
``checklist_stats_streamlit_tab_sections_html``). ``sync_checklist_stats_tab_session_inputs`` + ``@st.fragment``
match Country / Yearly (refs #70).

**Prep vs Map load:** One **sidebar** ``st.spinner`` in a **dedicated bottom slot** wraps checklist prep, tab syncs,
Folium **build**, ``st_folium`` in the Map tab, then clears the bird-emoji strip (refs #124) so the explorer spinner
tracks the built-in Streamlit spinner. Iframe min-height CSS reduces streamlit-folium letterboxing. Partial
``@st.fragment`` reruns do not use this spinner. Implementation: :mod:`explorer.app.streamlit.app_prep_map_ui`
(refs #130).

**Country:** Per-country yearly table uses the same ``CHECKLIST_STATS_*`` HTML/CSS as Checklist Statistics
(``country_stats_streamlit_html``). The tab runs inside ``@st.fragment`` so changing the country selectbox
triggers a **partial rerun** (not the whole map/checklist pipeline) (refs #75).

**Maintenance:** Same fragment pattern; incomplete checklists use ``cached_full_export_checklist_stats_payload``
(aligned with Rankings Top N + high-count settings). **Close location (m)** is set under **Settings → Tables & lists**
(refs #79).

**Ranking & Lists:** ``cached_full_export_checklist_stats_payload`` + ``format_checklist_stats_bundle``;
``build_rankings_tab_bundle`` runs in the **prep** spinner pass (above the tab row, with other full-export prep);
**Top N** / **visible rows** / table options are under **Settings → Tables & lists** (batch **Apply**; refs `#81`).

**Yearly Summary:** ``yearly_summary_streamlit_html`` — nested **All** / **Travelling** / **Stationary** tabs inside
``@st.fragment``; ``st.toggle`` switches recent vs full year columns when count exceeds **Settings → Yearly tables:
recent year columns** (default 10). ``sync_yearly_summary_session_inputs`` + ``run_yearly_summary_streamlit_fragment``
match the Country tab fragment pattern (refs #85).

**Main tabs + sidebar:** Primary ``st.tabs`` first (``Map``, ``Families``, …; empty panels until filled). Prep + Folium embed run in a sidebar
bottom ``st.spinner`` (Map tab content is nested in script order so loading indicators stay aligned). Data tabs use
``@st.fragment`` where possible. One sidebar
for map controls, export, and footer links (refs #70). Map sidebar + working set: :mod:`explorer.app.streamlit.app_map_working_ui`
(refs #131). **Settings** tab body lives in :mod:`explorer.app.streamlit.app_settings_ui`
(refs #118). Settings use a keyed container with
``max-width: min(100%, 40rem)`` on wide viewports. **Tables & lists** controls are batched in a form (one rerun on **Apply**).
"""

from __future__ import annotations

import os
import sys

# ``streamlit run explorer/app/streamlit/app.py`` puts the script directory on ``sys.path``, not the
# repo root. Prepend repo root so ``import explorer.*`` resolves (refs #70).
_REPO_ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", ".."))
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)

from collections import OrderedDict

import streamlit as st

from explorer.presentation.checklist_stats_display import (  # noqa: E402
    COUNTRY_TAB_SORT_ALPHABETICAL,
)
from explorer.core.explorer_paths import settings_yaml_path_for_source  # noqa: E402
from explorer.app.streamlit.app_caches import (  # noqa: E402
    cached_species_url_fn,
)
from explorer.app.streamlit.app_constants import (  # noqa: E402
    DEFAULT_TAXONOMY_LOCALE,
    FILTERED_BY_LOC_CACHE_KEY,
    POPUP_HTML_CACHE_KEY,
    REPO_ROOT,
    SETTINGS_BASELINE_KEY,
    SETTINGS_CONFIG_PATH_KEY,
    SETTINGS_CONFIG_SOURCE_KEY,
    SETTINGS_LOADED_FROM_KEY,
    SETTINGS_WARNED_KEY,
    SESSION_UPLOAD_CACHE_KEY,
    STREAMLIT_TAXONOMY_LOCALE_KEY,
)
from explorer.app.streamlit.app_landing_ui import (  # noqa: E402
    load_dataframe_after_landing,
    title_with_logo,
)
from explorer.app.streamlit.app_map_working_ui import render_map_sidebar_and_working_set  # noqa: E402
from explorer.app.streamlit.app_prep_map_ui import render_prep_spinner_and_map_tab  # noqa: E402
from explorer.app.streamlit.app_settings_ui import render_settings_tab  # noqa: E402
from explorer.app.streamlit.app_settings_state import (  # noqa: E402
    apply_settings_payload_to_state,
    env_taxonomy_locale,
    init_and_clamp_streamlit_table_settings,
    load_settings_yaml_via_module,
    settings_state_payload,
)
from explorer.app.streamlit.streamlit_theme import (  # noqa: E402
    inject_main_tab_panel_top_compact_css,
)
from explorer.app.streamlit.checklist_stats_streamlit_html import (  # noqa: E402
    run_checklist_stats_streamlit_fragment,
)
from explorer.app.streamlit.country_stats_streamlit_html import (  # noqa: E402
    run_country_tab_streamlit_fragment,
)
from explorer.app.streamlit.maintenance_streamlit_html import (  # noqa: E402
    run_maintenance_streamlit_tab_fragment,
)
from explorer.app.streamlit.rankings_streamlit_html import (  # noqa: E402
    run_rankings_streamlit_tab_fragment,
)
from explorer.app.streamlit.streamlit_ui_constants import (  # noqa: E402
    NOTEBOOK_MAIN_TAB_LABELS,
)
from explorer.app.streamlit.yearly_summary_streamlit_html import (  # noqa: E402
    run_yearly_summary_streamlit_fragment,
)


def _run_non_map_data_tab_fragments(
    tab_checklist,
    tab_rankings,
    tab_yearly,
    tab_country,
    tab_maint,
) -> None:
    """Checklist, Rankings, Yearly, Country, Maintenance tabs (refs #118)."""
    with tab_checklist:
        run_checklist_stats_streamlit_fragment()

    with tab_rankings:
        run_rankings_streamlit_tab_fragment()

    with tab_yearly:
        run_yearly_summary_streamlit_fragment()

    with tab_country:
        run_country_tab_streamlit_fragment()

    with tab_maint:
        run_maintenance_streamlit_tab_fragment()


def main() -> None:
    st.set_page_config(page_title="Personal eBird Explorer (Streamlit)", layout="wide")

    if STREAMLIT_TAXONOMY_LOCALE_KEY not in st.session_state:
        st.session_state[STREAMLIT_TAXONOMY_LOCALE_KEY] = (
            env_taxonomy_locale() or DEFAULT_TAXONOMY_LOCALE
        )
    if "streamlit_country_tab_sort" not in st.session_state:
        st.session_state.streamlit_country_tab_sort = COUNTRY_TAB_SORT_ALPHABETICAL

    upload_cache = st.session_state.get(SESSION_UPLOAD_CACHE_KEY)
    if upload_cache is not None and not (
        isinstance(upload_cache, tuple) and len(upload_cache) == 2 and isinstance(upload_cache[0], bytes)
    ):
        upload_cache = None

    loaded = load_dataframe_after_landing(upload_cache)
    if loaded is None:
        return
    df_full, provenance, source_label, data_abs_path, data_basename = loaded

    st.session_state[SETTINGS_CONFIG_SOURCE_KEY] = source_label or ""
    settings_yaml_path = settings_yaml_path_for_source(REPO_ROOT, source_label or "")
    st.session_state[SETTINGS_CONFIG_PATH_KEY] = settings_yaml_path or ""
    if settings_yaml_path and st.session_state.get(SETTINGS_LOADED_FROM_KEY) != settings_yaml_path:
        cfg_data, cfg_warn = load_settings_yaml_via_module(settings_yaml_path)
        if cfg_warn and not st.session_state.get(SETTINGS_WARNED_KEY):
            st.warning(cfg_warn)
            st.session_state[SETTINGS_WARNED_KEY] = True
        apply_settings_payload_to_state(cfg_data)
        st.session_state[SETTINGS_LOADED_FROM_KEY] = settings_yaml_path
        st.session_state[SETTINGS_BASELINE_KEY] = settings_state_payload()

    init_and_clamp_streamlit_table_settings()
    if SETTINGS_BASELINE_KEY not in st.session_state:
        st.session_state[SETTINGS_BASELINE_KEY] = settings_state_payload()

    if POPUP_HTML_CACHE_KEY not in st.session_state:
        st.session_state[POPUP_HTML_CACHE_KEY] = {}
    if FILTERED_BY_LOC_CACHE_KEY not in st.session_state:
        st.session_state[FILTERED_BY_LOC_CACHE_KEY] = OrderedDict()

    mw = render_map_sidebar_and_working_set(df_full)

    tax_locale_effective = (
        str(st.session_state.get(STREAMLIT_TAXONOMY_LOCALE_KEY, "")).strip()
        or DEFAULT_TAXONOMY_LOCALE
    )
    species_url_fn = cached_species_url_fn(tax_locale_effective)
    popup_sort_order = st.session_state.streamlit_popup_sort_order
    popup_scroll_hint = st.session_state.streamlit_popup_scroll_hint
    mark_lifer = bool(st.session_state.streamlit_mark_lifer)
    mark_last_seen = bool(st.session_state.streamlit_mark_last_seen)

    title_with_logo()
    st.markdown("Your eBird data, made visible, navigable, and ready to explore")

    # Main tabs: plain ``st.tabs`` (no ``key`` / ``on_change``). Keyed lazy tabs existed only for Family Lists
    # “main tab” session bookkeeping; the Families flow now relies on dataframe selection only (refs #73).
    (
        tab_map,
        tab_checklist,
        tab_rankings,
        tab_yearly,
        tab_country,
        tab_maint,
        tab_settings,
    ) = st.tabs(NOTEBOOK_MAIN_TAB_LABELS)

    inject_main_tab_panel_top_compact_css()

    render_prep_spinner_and_map_tab(
        tab_map=tab_map,
        work_df=mw.work_df,
        df_full=df_full,
        provenance=provenance,
        tax_locale_effective=tax_locale_effective,
        map_height=mw.map_height,
        map_style=mw.map_style,
        map_view_mode=mw.map_view_mode,
        is_lifer_view=mw.is_lifer_view,
        date_filter_banner=mw.date_filter_banner,
        species_pick_common=mw.species_pick_common,
        species_pick_sci=mw.species_pick_sci,
        family_name=mw.family_name,
        family_highlight_base=mw.family_highlight_base,
        family_colour_scheme=mw.family_colour_scheme,
        hide_non_matching_locations=mw.hide_non_matching_locations,
        popup_sort_order=popup_sort_order,
        popup_scroll_hint=popup_scroll_hint,
        mark_lifer=mark_lifer,
        mark_last_seen=mark_last_seen,
        species_url_fn=species_url_fn,
    )

    _run_non_map_data_tab_fragments(
        tab_checklist,
        tab_rankings,
        tab_yearly,
        tab_country,
        tab_maint,
    )

    with tab_settings:
        render_settings_tab(
            data_basename=data_basename,
            data_abs_path=data_abs_path,
            source_label=source_label,
        )


if __name__ == "__main__":
    main()
