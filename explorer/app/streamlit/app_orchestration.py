"""Orchestration phases for the Streamlit dashboard entrypoint.

Implementation lives in :mod:`explorer.app.streamlit.app_bootstrap` and
:mod:`explorer.app.streamlit.app_dashboard_shell`. This module re-exports the public
API used by :mod:`explorer.app.streamlit.app.main`.

Ordered flow:

1. :func:`bootstrap_streamlit_page` — ``set_page_config`` + Streamlit chrome theme CSS.
2. :func:`init_session_defaults_before_data_load` — taxonomy locale + country tab sort defaults.
3. :func:`coerce_session_upload_cache` — normalize cached upload tuple for the loader.
4. :func:`explorer.app.streamlit.app_landing_ui.load_dataframe_after_landing` — disk / upload /
   landing; may return ``None`` (caller exits).
5. :func:`bootstrap_session_after_csv_load` — run id, perf dataset context, settings YAML,
   table clamps.
6. :func:`explorer.app.streamlit.app_map_working_ui.render_map_sidebar_and_working_set` —
   sidebar + working dataframe.
7. :func:`build_taxonomy_popup_assets` — cached taxonomy URL fn + popup preferences.
8. :func:`render_dashboard_shell` — title row, primary ``st.tabs``, prep spinner
   + Map tab, then non-map tab fragments, then Settings.

Prep + Leaflet map embed run **after** ``st.tabs`` are created so loading indicators stay aligned with the
tab row.
"""

from __future__ import annotations

from explorer.app.streamlit.app_bootstrap import (
    TaxonomyPopupAssets,
    bootstrap_session_after_csv_load,
    bootstrap_streamlit_page,
    build_taxonomy_popup_assets,
    coerce_session_upload_cache,
    init_session_defaults_before_data_load,
)
from explorer.app.streamlit.app_dashboard_shell import (
    render_dashboard_shell,
    run_non_map_data_tab_fragments,
)

__all__ = [
    "TaxonomyPopupAssets",
    "bootstrap_session_after_csv_load",
    "bootstrap_streamlit_page",
    "build_taxonomy_popup_assets",
    "coerce_session_upload_cache",
    "init_session_defaults_before_data_load",
    "render_dashboard_shell",
    "run_non_map_data_tab_fragments",
]
