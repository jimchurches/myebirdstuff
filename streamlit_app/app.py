"""
Personal eBird Explorer — Streamlit prototype (Folium map + notebook-style popups).

Planning and phased migration notes: https://github.com/jimchurches/myebirdstuff/issues/70 (refs #70).

Run locally from repo root::

    pip install -r requirements-streamlit.txt
    streamlit run streamlit_app/app.py

Same path resolution as the notebook when no file is uploaded: optional
``STREAMLIT_EBIRD_DATA_FOLDER``, then ``scripts/config_*.py``, then CSV in
this ``streamlit_app/`` folder.

Streamlit Cloud: use the **sidebar** file uploader (drag-and-drop or browse; no repo CSV required).

**No-data landing:** If no CSV is found on disk and nothing is uploaded, the app shows a simple
landing page (title + short copy) and a sidebar focused on upload. The map, taxonomy prefetch, and
main tabs appear after data loads.

**Taxonomy:** After CSV load, the app fetches the eBird taxonomy once per session (cached) so species
names in popups can link to eBird species pages. Default locale is **en_AU**; override with
``STREAMLIT_EBIRD_TAXONOMY_LOCALE`` / ``EBIRD_TAXONOMY_LOCALE`` or the sidebar field. Streamlit does
not expose the browser language to Python; optional future approaches are query params, a tiny
custom component, or heuristics from export columns (e.g. dominant ``Country``) — none wired yet.

**Checklist Statistics:** Native Streamlit layout (``st.expander`` + tables) from
``compute_checklist_stats_payload`` — same metrics as the notebook tab, without injected HTML.
"""

from __future__ import annotations

import io
import os
import sys
from collections import OrderedDict
from typing import Callable

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
from personal_ebird_explorer.species_logic import base_species_for_lifer  # noqa: E402
from personal_ebird_explorer.streamlit_map_prep import (  # noqa: E402
    data_signature_for_caches,
    prepare_all_locations_map_context,
)
from checklist_stats_streamlit_native import render_checklist_stats_streamlit_native  # noqa: E402

DEFAULT_EBIRD_FILENAME = os.environ.get("STREAMLIT_EBIRD_DATA_FILE", "MyEBirdData.csv")

# Same order and labels as ``main_tabs`` in ``notebooks/personal_ebird_explorer`` (refs #70).
NOTEBOOK_MAIN_TAB_LABELS = (
    "Map",
    "Checklist Statistics",
    "Rankings & lists",
    "Yearly Summary",
    "Country",
    "Maintenance",
    "Settings",
)

# Same cap as notebook ``TOP_N_TABLE_LIMIT`` (rankings prep inside payload; Rankings tab not wired yet).
CHECKLIST_STATS_TOP_N_TABLE_LIMIT = 200

# Match notebook-friendly default; eBird API uses this for common-name spellings in taxonomy CSV.
DEFAULT_TAXONOMY_LOCALE = "en_AU"


def _env_taxonomy_locale() -> str:
    """Non-empty locale from env if set (notebook parity)."""
    return (
        os.environ.get("STREAMLIT_EBIRD_TAXONOMY_LOCALE", "").strip()
        or os.environ.get("EBIRD_TAXONOMY_LOCALE", "").strip()
    )


@st.cache_data(show_spinner="Computing checklist statistics…")
def _cached_checklist_stats_payload(df: pd.DataFrame) -> ChecklistStatsPayload | None:
    """Structured checklist stats for the Checklist Statistics tab (refs #68)."""
    return compute_checklist_stats_payload(df, CHECKLIST_STATS_TOP_N_TABLE_LIMIT)


@st.cache_resource(show_spinner="Loading eBird taxonomy…")
def _cached_species_url_fn(locale_key: str) -> Callable[[str], str | None]:
    """One taxonomy fetch per session per locale; used for species links in map UI."""
    from personal_ebird_explorer.taxonomy import get_species_url, load_taxonomy

    loc = locale_key.strip() if locale_key and locale_key.strip() else None
    if load_taxonomy(locale=loc):
        return get_species_url
    return lambda _: None


def _secrets_data_folder() -> str | None:
    try:
        s = st.secrets
        if "EBIRD_DATA_FOLDER" in s and str(s["EBIRD_DATA_FOLDER"]).strip():
            return str(s["EBIRD_DATA_FOLDER"]).strip()
    except Exception:
        pass
    return None


def _load_dataframe(*, uploaded) -> tuple[pd.DataFrame | None, str | None]:
    """
    Return ``(df, provenance_html)`` or ``(None, None)`` if nothing loaded yet.

    Precedence: *uploaded* file (from sidebar) → disk resolution (env/secrets/config/anchor).
    """
    if uploaded is not None:
        try:
            raw = uploaded.read()
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
        return None, None


def _render_landing_no_data() -> None:
    """Minimal first-run view when no CSV is on disk and nothing uploaded (e.g. Streamlit Cloud)."""
    with st.sidebar:
        st.divider()
        with st.expander("Local file or advanced setup"):
            st.markdown(
                f"""
                **Local:** Put **{DEFAULT_EBIRD_FILENAME}** in `streamlit_app/`, or set
                `STREAMLIT_EBIRD_DATA_FOLDER`, or use `scripts/config_secret.py` like the Jupyter notebook.

                **Streamlit Cloud:** Upload your export via **Data** above. Optional secret
                `EBIRD_DATA_FOLDER` only helps if your host provides a mounted path.

                Replacing a file on disk does not auto-reload; rerun the app if needed.
                """
            )

    st.title("Personal eBird Explorer")
    st.subheader("Streamlit prototype")
    st.write(
        "Explore your personal eBird checklists on a map and in summary tabs. "
        "Load an official **My eBird Data** CSV export to begin."
    )
    st.info(
        f"**Upload a CSV** using **Data** in the sidebar (drag-and-drop or **Browse files**). "
        f"Expected name by default: `{DEFAULT_EBIRD_FILENAME}`."
    )


def main() -> None:
    st.set_page_config(page_title="Personal eBird Explorer (Streamlit)", layout="wide")

    if "streamlit_taxonomy_locale" not in st.session_state:
        st.session_state.streamlit_taxonomy_locale = _env_taxonomy_locale() or DEFAULT_TAXONOMY_LOCALE

    with st.sidebar:
        st.header("Data")
        uploaded = st.file_uploader(
            "eBird export (CSV)",
            type=["csv"],
            help="Drag-and-drop or browse. For a fixed local file without uploading, "
            "set STREAMLIT_EBIRD_DATA_FOLDER or place the CSV in streamlit_app/.",
        )

    df, provenance = _load_dataframe(uploaded=uploaded)

    if df is None:
        _render_landing_no_data()
        return

    with st.sidebar:
        st.divider()
        st.header("Map")
        map_style = st.selectbox(
            "Basemap",
            options=["default", "satellite", "google", "carto"],
            index=0,
            help="Same tile sets as the notebook User Variables.",
        )
        st.text_input(
            "Taxonomy locale (species links)",
            key="streamlit_taxonomy_locale",
            help="eBird API locale (e.g. en_AU, en_GB). Empty input is treated as en_AU. "
            "First visit default: STREAMLIT_EBIRD_TAXONOMY_LOCALE / EBIRD_TAXONOMY_LOCALE, else en_AU.",
        )
        map_height = st.slider(
            "Map height (px)",
            min_value=440,
            max_value=1200,
            value=720,
            step=20,
            help="Folium is embedded at a fixed pixel height — adjust for your display. "
            "True “full viewport” height isn’t available without custom components.",
        )

    tax_locale_effective = (st.session_state.streamlit_taxonomy_locale.strip() or DEFAULT_TAXONOMY_LOCALE)
    species_url_fn = _cached_species_url_fn(tax_locale_effective)

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

    def _tab_test_placeholder(notebook_name: str, blurb: str) -> None:
        st.markdown(f"**TEST** — `{notebook_name}` tab (placeholder only).")
        st.write(blurb)

    with tab_map:
        prov_plain = provenance or ""
        sig = data_signature_for_caches(df, prov_plain)
        if st.session_state.get("ebird_data_sig") != sig:
            st.session_state.ebird_data_sig = sig
            st.session_state.popup_html_cache = {}
            st.session_state.filtered_by_loc_cache = OrderedDict()

        try:
            ctx = prepare_all_locations_map_context(df)
        except ValueError as e:
            st.warning(str(e))
        else:
            result = build_species_overlay_map(
                **ctx,
                selected_species="",
                selected_common_name="",
                map_style=map_style,
                popup_sort_order="ascending",
                popup_scroll_hint="shading",
                date_filter_status="",
                species_url_fn=species_url_fn,
                base_species_fn=base_species_for_lifer,
                popup_html_cache=st.session_state.popup_html_cache,
                filtered_by_loc_cache=st.session_state.filtered_by_loc_cache,
                map_view_mode="all",
                hide_non_matching_locations=False,
            )

            if result.warning:
                st.warning(result.warning)
            elif result.map is None:
                st.warning("Map could not be built.")
            else:
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
                    result.map,
                    use_container_width=True,
                    height=map_height,
                    key=f"explorer_folium_map_h{map_height}",
                    returned_objects=[],
                    return_on_hover=False,
                )

    with tab_checklist:
        checklist_payload = _cached_checklist_stats_payload(df)
        if checklist_payload is not None:
            render_checklist_stats_streamlit_native(checklist_payload)
        else:
            st.warning("No checklist data to show.")

    with tab_rankings:
        _tab_test_placeholder(
            "Rankings & lists",
            "Pretend: top species, locations, months, seen-once table.",
        )
        st.json({"rankings": "TEST", "species": ["Alpha", "Beta", "Gamma"]})

    with tab_yearly:
        _tab_test_placeholder(
            "Yearly Summary",
            "Pretend: one row per year with species counts and km traveled.",
        )
        st.bar_chart(pd.DataFrame({"TEST_year": [2022, 2023, 2024], "TEST_n": [3, 7, 2]}).set_index("TEST_year"))

    with tab_country:
        _tab_test_placeholder(
            "Country",
            "Pretend: accordions per country with sparse year columns.",
        )
        st.code("TEST country block\n  AU: 12 lifers\n  NZ: 4 lifers", language="text")

    with tab_maint:
        _tab_test_placeholder(
            "Maintenance",
            "Pretend: duplicate locations, incomplete checklists, sex-notation scan.",
        )
        st.warning("TEST warning style — not a real problem.")

    with tab_settings:
        _tab_test_placeholder(
            "Settings",
            "Pretend: table row limits, country tab sort order, close-location metres.",
        )
        st.button("TEST button (does nothing)", disabled=True)


if __name__ == "__main__":
    main()
