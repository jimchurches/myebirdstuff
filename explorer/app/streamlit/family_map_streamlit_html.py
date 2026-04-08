"""Family Map tab — Streamlit UI (refs #138).

Runs in ``@st.fragment`` so family/highlight changes do not rerun the full script. Taxonomy + work
frame are cached in :func:`~explorer.app.streamlit.app_caches.cached_family_map_bundle`.
"""

from __future__ import annotations

from typing import Callable

import pandas as pd
import streamlit as st

from explorer.app.streamlit.app_caches import cached_family_map_bundle
from explorer.app.streamlit.app_constants import (
    STREAMLIT_FAMILY_MAP_COLOUR_SCHEME_KEY,
    STREAMLIT_FAMILY_MAP_FAMILY_KEY,
    STREAMLIT_FAMILY_MAP_HIGHLIGHT_KEY,
)
from explorer.app.streamlit.app_map_working_ui import invalidate_folium_map_embed_cache
from explorer.app.streamlit.defaults import (
    FAMILY_MAP_COLOUR_SCHEME_1,
    FAMILY_MAP_COLOUR_SCHEME_2,
    active_family_map_colour_scheme,
)
from explorer.app.streamlit.app_map_ui import inject_map_folium_iframe_min_height_css
from explorer.core.family_map_compute import (
    build_family_location_pins,
    compute_family_map_banner_metrics,
    filter_work_to_family,
    highlight_species_choices_alphabetical,
)
from explorer.core.family_map_folium import (
    build_family_composition_folium_map,
    build_family_map_banner_overlay_html,
    build_family_map_legend_overlay_html_for_pins,
)


def _ebird_location_url(location_id: str) -> str | None:
    lid = str(location_id).strip()
    if not lid:
        return None
    return f"https://ebird.org/lifelist/{lid}"


@st.fragment
def run_family_map_streamlit_fragment(
    *,
    df_full: pd.DataFrame,
    taxonomy_locale: str,
    map_height: int,
    map_style: str,
    species_url_fn: Callable[[str], str | None],
) -> None:
    """Render the **Families** tab: family + highlight controls and Folium composition map."""
    st.caption(
        "Map species-group (family) richness by location. Select a family to load pins; "
        "optionally highlight locations where a chosen species occurs (refs #138)."
    )

    if df_full is None or df_full.empty:
        st.info("Load your eBird export to explore families on the map.")
        return

    bundle = cached_family_map_bundle(df_full, taxonomy_locale)
    families = bundle["families"]
    work = bundle["work"]
    tax_merged = bundle["tax_merged"]
    base_to_common = bundle["base_to_common"]

    if not families:
        st.warning(
            "No taxonomy-backed families found in your data. "
            "Check your network connection so eBird taxonomy and species groups can load, "
            "then refresh the page."
        )
        m = build_family_composition_folium_map((), colour_scheme_index=1)
        _embed_family_map(m, map_height)
        return

    fam_options = [""] + list(families)
    family = st.selectbox(
        "Family",
        options=fam_options,
        format_func=lambda x: "— Select a family —" if x == "" else x,
        key=STREAMLIT_FAMILY_MAP_FAMILY_KEY,
    )

    if not family:
        st.selectbox(
            "Highlight species (optional)",
            options=["— None —"],
            disabled=True,
            key=f"{STREAMLIT_FAMILY_MAP_HIGHLIGHT_KEY}__none",
        )
    else:
        wf = filter_work_to_family(work, family)
        choices = highlight_species_choices_alphabetical(wf, base_to_common)
        label_to_base = {"— None —": None}
        for lab, bs in choices:
            label_to_base[lab] = bs
        hl_labels = list(label_to_base.keys())
        hl_key = f"{STREAMLIT_FAMILY_MAP_HIGHLIGHT_KEY}__{family}"
        hl_label = st.selectbox(
            "Highlight species (optional)",
            options=hl_labels,
            key=hl_key,
        )
        highlight_base = label_to_base.get(hl_label)

    colour_scheme = int(
        st.radio(
            "Colour scheme",
            options=[1, 2],
            format_func=lambda n: (
                FAMILY_MAP_COLOUR_SCHEME_1.display_name
                if n == 1
                else FAMILY_MAP_COLOUR_SCHEME_2.display_name
            ),
            horizontal=True,
            key=STREAMLIT_FAMILY_MAP_COLOUR_SCHEME_KEY,
            index=0,
            on_change=invalidate_folium_map_embed_cache,
        )
    )

    if not family:
        m = build_family_composition_folium_map((), colour_scheme_index=colour_scheme)
        _embed_family_map(m, map_height)
        st.info("Select a family above to show where you recorded those species.")
        return

    metrics = compute_family_map_banner_metrics(wf, family, tax_merged)
    pins = build_family_location_pins(wf, highlight_base_species=highlight_base)
    banner = build_family_map_banner_overlay_html(metrics) if metrics else ""
    _sch = active_family_map_colour_scheme(colour_scheme)
    hl_label_common = (base_to_common.get(highlight_base) or highlight_base) if highlight_base else ""
    hl_species_url = None
    if highlight_base and hl_label_common:
        _u = species_url_fn(hl_label_common)
        hl_species_url = _u if _u else None
    legend = build_family_map_legend_overlay_html_for_pins(
        pins,
        highlight_label=hl_label_common or None,
        highlight_species_url=hl_species_url,
        style=_sch,
    )

    m = build_family_composition_folium_map(
        pins,
        banner_html=banner,
        legend_html=legend,
        map_style=map_style,
        height_px=int(map_height),
        location_page_url_fn=_ebird_location_url,
        species_url_fn=species_url_fn,
        fit_bounds_highlight_only=bool(highlight_base),
        colour_scheme_index=colour_scheme,
    )
    _embed_family_map(m, map_height)


def _embed_family_map(m: object, map_height: int) -> None:
    inject_map_folium_iframe_min_height_css(map_height)
    try:
        from streamlit_folium import st_folium
    except ImportError:
        st.error(
            "Missing **streamlit-folium** (needed to embed the Folium map). "
            "Install with: `pip install -r requirements.txt`."
        )
        return
    st_folium(
        m,
        use_container_width=True,
        height=map_height,
        key="explorer_family_map_folium_v1",
        returned_objects=[],
        return_on_hover=False,
    )
