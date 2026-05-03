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
Folium **build**, serialized HTML cached for export plus **streamlit-folium** embed in the Map tab,
then clears the bird-emoji strip (refs #124) so the explorer spinner tracks the built-in Streamlit spinner.
Iframe min-height CSS reduces
letterboxing. Partial
``@st.fragment`` reruns do not use this spinner. Implementation: :mod:`explorer.app.streamlit.app_prep_map_ui`
(refs #130).

**Country:** Per-country yearly table uses the same ``CHECKLIST_STATS_*`` HTML/CSS as Checklist Statistics
(``country_stats_streamlit_html``). The tab runs inside ``@st.fragment`` so changing the country selectbox
triggers a **partial rerun** (not the whole map/checklist pipeline) (refs #75).

**Maintenance:** Same fragment pattern; incomplete checklists use ``cached_full_export_checklist_stats_payload``
(aligned with Rankings Top N + high-count settings). **Nearby location detection distance (m)** is set under **Settings → Tables & lists**
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

**Orchestration:** Phase boundaries for ``main()`` live in :mod:`explorer.app.streamlit.app_orchestration` (GitHub #200).
"""

from __future__ import annotations

import os
import sys

# ``streamlit run explorer/app/streamlit/app.py`` puts the script directory on ``sys.path``, not the
# repo root. Prepend repo root so ``import explorer.*`` resolves (refs #70).
_REPO_ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", ".."))
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)

from explorer.app.streamlit.app_landing_ui import (  # noqa: E402
    load_dataframe_after_landing,
)
from explorer.app.streamlit.app_map_working_ui import render_map_sidebar_and_working_set  # noqa: E402
from explorer.app.streamlit.app_orchestration import (  # noqa: E402
    bootstrap_session_after_csv_load,
    bootstrap_streamlit_page,
    build_taxonomy_popup_assets,
    coerce_session_upload_cache,
    init_session_defaults_before_data_load,
    render_dashboard_shell,
)
def main() -> None:
    """Thin orchestration entrypoint; see :mod:`explorer.app.streamlit.app_orchestration` for phase docs."""
    bootstrap_streamlit_page()
    init_session_defaults_before_data_load()

    upload_cache = coerce_session_upload_cache()
    loaded = load_dataframe_after_landing(upload_cache)
    if loaded is None:
        return
    df_full, provenance, source_label, data_abs_path, data_basename = loaded

    bootstrap_session_after_csv_load(df_full, source_label=source_label)

    mw = render_map_sidebar_and_working_set(df_full)
    tax = build_taxonomy_popup_assets()

    render_dashboard_shell(
        df_full=df_full,
        provenance=provenance,
        source_label=source_label,
        data_abs_path=data_abs_path,
        data_basename=data_basename,
        mw=mw,
        tax=tax,
    )


if __name__ == "__main__":
    main()
