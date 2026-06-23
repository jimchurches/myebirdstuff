"""
Personal eBird Explorer — Streamlit app (Leaflet map component + rich location popups).

Run locally from repo root::

    pip install -r requirements.txt
    streamlit run explorer/app/streamlit/app.py

**Data loading:** Disk resolution uses ``config/config_secret.yaml``, ``config/config.yaml``
(``data_folder``), then the process working directory. With no file on disk, the landing page
offers a CSV upload; session state keeps upload bytes across reruns. See
``explorer/app/streamlit/README.md`` — *Data loading*. Implementation:
:mod:`explorer.app.streamlit.app_landing_ui`.

**Architecture:** ``main()`` loads CSV data, builds map working context and taxonomy popup assets,
then delegates to :mod:`explorer.app.streamlit.app_dashboard_shell` for the tab shell, map prep,
and tab fragments. Orchestration phases are documented in
:mod:`explorer.app.streamlit.app_orchestration`.

**Main tabs:** Map, Checklist Statistics, Ranking & Lists, Bird Families, Yearly Summary,
Country, Maintenance, Settings. Map prep runs first in a sidebar bottom ``st.spinner`` (see
:mod:`explorer.app.streamlit.app_prep_map_ui`). Data tabs use ``@st.fragment`` where possible so
control changes avoid rerunning the full map pipeline.

**Map:** Leaflet custom component; sidebar controls and working-set resolution in
:mod:`explorer.app.streamlit.app_map_working_ui`.

**Rankings & Bird Families:** Shared prep bundle from ``build_ranking_lists_families_bundle``;
Bird Families is its own main tab (:mod:`explorer.app.streamlit.bird_families_streamlit_html`).

**Settings:** Persisted YAML-backed options in :mod:`explorer.app.streamlit.app_settings_ui`
(batched **Apply** on the Tables & lists form).

**Taxonomy:** Fetched once per session after CSV load so species names can link to eBird. Default
locale is **en_AU**; override via env vars or **Settings → Taxonomy**.
"""

from __future__ import annotations

import os
import sys

# ``streamlit run explorer/app/streamlit/app.py`` puts the script directory on ``sys.path``, not the
# repo root — prepend repo root so ``import explorer.*`` resolves.
_REPO_ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", ".."))
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)

from explorer.app.streamlit.app_landing_ui import (  # noqa: E402
    load_dataframe_after_landing,
)
from explorer.app.streamlit.app_map_working_ui import (
    render_map_sidebar_and_working_set,  # noqa: E402
)
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

    map_working = render_map_sidebar_and_working_set(df_full)
    taxonomy_assets = build_taxonomy_popup_assets()

    render_dashboard_shell(
        df_full=df_full,
        provenance=provenance,
        source_label=source_label,
        data_abs_path=data_abs_path,
        data_basename=data_basename,
        map_working=map_working,
        taxonomy_assets=taxonomy_assets,
    )


if __name__ == "__main__":
    main()
