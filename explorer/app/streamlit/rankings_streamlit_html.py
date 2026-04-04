"""
**Ranking & Lists** (Streamlit): nested tabs **Top Lists** / **Interesting Lists** / **Family Lists**
(eBird species groups under the hood; refs `#73`), expanders per list on the first two tabs.

Uses HTML from :func:`explorer.presentation.checklist_stats_display.format_checklist_stats_bundle`
(``rankings_sections_top_n`` / ``rankings_sections_other``) — same tables as the explorer’s richly-linked HTML tables,
rendered with ``st.markdown(..., unsafe_allow_html=True)``. Table styling matches **Checklist Statistics**:
:func:`~explorer.app.streamlit.streamlit_theme.inject_streamlit_checklist_css` plus Rankings width scoped under
``streamlit-checklist-html-ab`` (plus ``streamlit-rankings-html`` for width). The **Family Lists** tab uses
``st.dataframe`` with **single-row selection** and a **bounded height** so the summary scrolls inside the grid
(compact layout). With **no family selected**, the lower panel shows **family-level coverage** metrics and an
eBird taxonomy link; selecting a row shows species detail (HTML ``stats-tbl`` / ``rankings-tbl``). Session-only
**last family** restores detail when you leave **Ranking & Lists** for another main tab and return (or use
**Resume last family** after **Back to family summary** on the same tab).

**Top N** and **visible rows** are controlled from **Settings → Tables & lists** (session keys
``streamlit_rankings_top_n``, ``streamlit_rankings_visible_rows``; refs `#81`). **Top Lists** tables
include a narrow leading **Rank** column with soft accent styling (refs `#83`). **Species: Not seen in
the past year** is the last expander under Interesting Lists; it lists countable species with no
observation in the trailing twelve months and is not Top-N–capped (refs `#106`; geographic filters are `#108`).
"""

from __future__ import annotations

import csv
import io
import json
from typing import Any
from urllib.parse import urlencode
from urllib.request import Request, urlopen

import pandas as pd
import streamlit as st

from explorer.presentation.checklist_stats_display import format_checklist_stats_bundle
from explorer.core.species_logic import countable_species_vectorized
from explorer.core.stats import safe_count
from explorer.core.taxonomy import get_species_and_lifelist_urls, load_taxonomy

from explorer.app.streamlit.app_caches import cached_full_export_checklist_stats_payload
from explorer.app.streamlit.app_constants import (
    EXPLORER_MAIN_TABS_STATE_KEY,
    RANKINGS_TAB_BUNDLE_KEY,
    SESSION_PREV_MAIN_TAB_FOR_FAMILY_KEY,
)
from explorer.app.streamlit.defaults import RANKINGS_BUNDLE_SCROLL_HINT_DEFAULT, RANKINGS_TABLE_LAYOUT_MAX_WIDTH_PX
from explorer.app.streamlit.streamlit_ui_constants import NOTEBOOK_MAIN_TAB_LABELS
from explorer.app.streamlit.streamlit_theme import inject_streamlit_checklist_css

# Must include ``streamlit-checklist-html-ab`` — ``CHECKLIST_STATS_*`` rules are scoped to it (same as Checklist Statistics).
_STREAMLIT_TABLE_SCOPE = "streamlit-checklist-html-ab"
_RANKINGS_SCOPE_EXTRA = "streamlit-rankings-html"
_TAXONOMY_BASE_URL = "https://api.ebird.org/v2/ref/taxonomy/ebird"
_GROUPS_BASE_URL = "https://api.ebird.org/v2/ref/sppgroup/ebird"

# Bundle keys and widget/session keys: eBird "group" in code; nested tab label Family Lists (refs #73).
_GROUP_COVERAGE_SUMMARY_KEY = "group_coverage_summary"
_GROUP_COVERAGE_DETAIL_KEY = "group_coverage_detail"
_GROUP_COVERAGE_ERROR_KEY = "group_coverage_error"
_STREAMLIT_GROUP_COVERAGE_SELECTED_KEY = "streamlit_group_coverage_selected_group"
_STREAMLIT_GROUP_COVERAGE_TABLE_KEY = "streamlit_group_coverage_summary_table"
_STREAMLIT_GROUP_COVERAGE_FALLBACK_KEY = "streamlit_group_coverage_selected_group_fallback"
_STREAMLIT_FAMILY_SUMMARY_BACK_BTN_KEY = "streamlit_family_summary_back_btn"
# Session-only “last family” (not persisted across browser sessions):
# last_* = last opened family; pin_* = user chose overview via Back (blocks auto-restore until tab change or Resume).
_STREAMLIT_FAMILY_COVERAGE_RESUME_BTN_KEY = "streamlit_family_coverage_resume_last_btn"
_STREAMLIT_LAST_FAMILY_COVERAGE_KEY = "streamlit_last_family_coverage"
_STREAMLIT_FAMILY_COVERAGE_PIN_OVERVIEW_KEY = "streamlit_family_coverage_pin_overview"
# One-shot: set when main tab becomes Ranking & Lists from elsewhere; consumed when Family Lists runs (fallback path).
_STREAMLIT_FAMILY_COVERAGE_ENTERED_FROM_OTHER_MAIN_TAB_KEY = (
    "_family_coverage_entered_rankings_from_other_main_tab"
)
_FAMILY_COVERAGE_RESET_NONCE_KEY = "_family_coverage_summary_reset_nonce"

_EBIRD_TAXONOMY_URL = "https://science.ebird.org/en/use-ebird-data/the-ebird-taxonomy"

# Summary grid height (px): scroll inside the dataframe so long family lists do not push the detail table down.
_FAMILY_COVERAGE_SUMMARY_DATAFRAME_HEIGHT_PX = 280


def _family_coverage_summary_metrics_df(summary: pd.DataFrame) -> pd.DataFrame:
    """Two-column overview when no family row is selected (counts + percentages)."""
    if summary.empty:
        return pd.DataFrame({"Metric": [], "Value": []})
    n_total = len(summary)
    seen = summary["seen_species"].astype(int)
    total_sp = summary["total_species"].astype(int)
    n_with_any = int((seen > 0).sum())
    complete = (seen >= total_sp) & (total_sp > 0)
    n_complete = int(complete.sum())
    pct_any = (n_with_any / n_total * 100.0) if n_total else 0.0
    pct_complete = (n_complete / n_total * 100.0) if n_total else 0.0
    return pd.DataFrame(
        {
            "Metric": [
                "Total families",
                "Families with ≥1 species recorded",
                "Families fully recorded (all species in family)",
                "% of families with ≥1 species recorded",
                "% of families fully recorded",
            ],
            "Value": [
                f"{n_total:,}",
                f"{n_with_any:,}",
                f"{n_complete:,}",
                f"{pct_any:.1f}%",
                f"{pct_complete:.1f}%",
            ],
        }
    )


def _rankings_family_coverage_inject_css() -> str:
    """Rankings max-width only (refs #73, #81)."""
    return (
        f".{_STREAMLIT_TABLE_SCOPE}.{_RANKINGS_SCOPE_EXTRA} {{ max-width:{RANKINGS_TABLE_LAYOUT_MAX_WIDTH_PX}px;width:100%; }}"
    )


@st.cache_data(show_spinner=False)
def _cached_rankings_stats_bundle(
    df: pd.DataFrame,
    top_n: int,
    visible_rows: int,
    country_sort: str,
    taxonomy_locale: str,
    high_count_sort: str,
    high_count_tie_break: str,
) -> dict[str, Any]:
    """Notebook-parity rankings bundle (full export + Top N + scroll + taxonomy links). refs #81."""
    loc = taxonomy_locale.strip() if taxonomy_locale else None
    link_urls_fn = get_species_and_lifelist_urls if load_taxonomy(locale=loc) else (lambda _: (None, None))
    payload = cached_full_export_checklist_stats_payload(
        df,
        top_n,
        high_count_sort,
        high_count_tie_break,
    )
    return format_checklist_stats_bundle(
        payload,
        link_urls_fn=link_urls_fn,
        scroll_hint=RANKINGS_BUNDLE_SCROLL_HINT_DEFAULT,
        visible_rows=visible_rows,
        country_sort=country_sort,
        high_count_sort=high_count_sort,
        high_count_tie_break=high_count_tie_break,
    )


def sync_rankings_tab_session_inputs(bundle: dict[str, Any]) -> None:
    """Store formatted Rankings bundle for :func:`run_rankings_streamlit_tab_fragment` (full script runs)."""
    st.session_state[RANKINGS_TAB_BUNDLE_KEY] = bundle


@st.cache_data(show_spinner=False)
def _load_taxonomy_species_rows(locale: str) -> pd.DataFrame:
    """Load eBird taxonomy rows (species only) with taxon order and link code."""
    loc = (locale or "").strip()
    url = _TAXONOMY_BASE_URL
    if loc:
        url = f"{url}?{urlencode({'locale': loc})}"
    req = Request(url, headers={"Accept": "text/csv"})
    with urlopen(req, timeout=30) as resp:
        raw = resp.read().decode("utf-8", errors="replace")
    reader = csv.DictReader(io.StringIO(raw))
    rows: list[dict[str, Any]] = []
    for row in reader:
        cat = str(row.get("CATEGORY", row.get("category", ""))).strip().lower()
        if cat != "species":
            continue
        sci = str(
            row.get("SCIENTIFIC_NAME")
            or row.get("SCI_NAME")
            or row.get("scientific_name")
            or row.get("sci_name")
            or ""
        ).strip()
        common = str(
            row.get("COMMON_NAME")
            or row.get("PRIMARY_COM_NAME")
            or row.get("common_name")
            or ""
        ).strip()
        code = str(row.get("SPECIES_CODE") or row.get("species_code") or "").strip()
        tax_raw = row.get("TAXON_ORDER") or row.get("taxon_order") or ""
        try:
            taxon_order = float(str(tax_raw).strip())
        except Exception:
            continue
        if not sci or not common:
            continue
        rows.append(
            {
                "scientific_name": sci,
                "common_name": common,
                "species_code": code,
                "taxon_order": taxon_order,
                "base_species": " ".join(sci.lower().split()[:2]).strip(),
            }
        )
    return pd.DataFrame(rows)


@st.cache_data(show_spinner=False)
def _load_taxonomy_groups(locale: str) -> list[dict[str, Any]]:
    """Load eBird species-group ranges."""
    loc = (locale or "").strip()
    url = _GROUPS_BASE_URL
    if loc:
        url = f"{url}?{urlencode({'locale': loc})}"
    req = Request(url, headers={"Accept": "application/json"})
    with urlopen(req, timeout=30) as resp:
        raw = resp.read().decode("utf-8", errors="replace")
    data = json.loads(raw)
    out: list[dict[str, Any]] = []
    for item in data:
        bounds_in = item.get("taxonOrderBounds", []) or []
        bounds: list[tuple[float, float]] = []
        for pair in bounds_in:
            if not isinstance(pair, list) or len(pair) != 2:
                continue
            try:
                lo = float(pair[0])
                hi = float(pair[1])
            except Exception:
                continue
            bounds.append((lo, hi))
        out.append(
            {
                "group_name": str(item.get("groupName", "")).strip(),
                "group_order": int(item.get("groupOrder", 0) or 0),
                "bounds": bounds,
            }
        )
    return out


def _assign_group_for_taxon_order(taxon_order: float, groups: list[dict[str, Any]]) -> tuple[str, int]:
    """Map one taxon order to (group_name, group_order) by bounds."""
    for g in groups:
        for lo, hi in g["bounds"]:
            if lo <= taxon_order <= hi:
                return g["group_name"], g["group_order"]
    return "Unmapped", 999999


@st.cache_data(show_spinner=False)
def _build_group_coverage_tables(df_full: pd.DataFrame, taxonomy_locale: str) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Build summary/detail DataFrames for species-group coverage (eBird taxonomy + sppgroup)."""
    tax = _load_taxonomy_species_rows(taxonomy_locale)
    groups = _load_taxonomy_groups(taxonomy_locale)
    if tax.empty or not groups:
        return pd.DataFrame(), pd.DataFrame()

    tax = tax.copy()
    tax[["group_name", "group_order"]] = tax["taxon_order"].apply(
        lambda x: pd.Series(_assign_group_for_taxon_order(float(x), groups))
    )

    work = df_full.copy()
    work["_base"] = countable_species_vectorized(work)
    work = work.dropna(subset=["_base"]).copy()
    work["_base"] = work["_base"].astype(str).str.strip()
    work["_count"] = work["Count"].apply(safe_count)
    # Checklist-level facts per base species (dedupe within checklist, but keep dates + IDs
    # so first/last seen can link to the relevant checklist).
    cl_facts = (
        work[["_base", "Submission ID", "Date"]]
        .dropna(subset=["Submission ID", "Date"])
        .drop_duplicates(subset=["_base", "Submission ID"])
        .copy()
    )
    if cl_facts.empty:
        obs = (
            work.groupby("_base", as_index=False)
            .agg(
                checklists=("Submission ID", "nunique"),
                individuals=("_count", "sum"),
            )
            .rename(columns={"_base": "base_species"})
        )
        obs["first_seen"] = pd.NA
        obs["last_seen"] = pd.NA
        obs["first_sid"] = ""
        obs["last_sid"] = ""
    else:
        cl_facts["_dt"] = pd.to_datetime(cl_facts["Date"], errors="coerce")
        cl_facts = cl_facts.dropna(subset=["_dt"])
        idx_first = cl_facts.groupby("_base")["_dt"].idxmin()
        idx_last = cl_facts.groupby("_base")["_dt"].idxmax()
        first = cl_facts.loc[idx_first, ["_base", "_dt", "Submission ID"]].rename(
            columns={"_dt": "first_seen", "Submission ID": "first_sid"}
        )
        last = cl_facts.loc[idx_last, ["_base", "_dt", "Submission ID"]].rename(
            columns={"_dt": "last_seen", "Submission ID": "last_sid"}
        )
        checklist_counts = cl_facts.groupby("_base", as_index=False).agg(checklists=("Submission ID", "nunique"))
        individuals = work.groupby("_base", as_index=False).agg(individuals=("_count", "sum"))
        obs = (
            checklist_counts.merge(individuals, on="_base", how="outer")
            .merge(first, on="_base", how="left")
            .merge(last, on="_base", how="left")
            .rename(columns={"_base": "base_species"})
        )
        obs["checklists"] = obs["checklists"].fillna(0).astype(int)
        obs["individuals"] = obs["individuals"].fillna(0).astype(int)
        obs["first_sid"] = obs["first_sid"].fillna("").astype(str)
        obs["last_sid"] = obs["last_sid"].fillna("").astype(str)
    merged = tax.merge(obs, how="left", on="base_species")
    merged["seen"] = merged["checklists"].notna()
    merged["checklists"] = merged["checklists"].fillna(0).astype(int)
    merged["individuals"] = merged["individuals"].fillna(0).astype(int)
    merged["first_seen"] = pd.to_datetime(merged["first_seen"], errors="coerce").dt.strftime("%Y-%m-%d").fillna("")
    merged["last_seen"] = pd.to_datetime(merged["last_seen"], errors="coerce").dt.strftime("%Y-%m-%d").fillna("")
    merged["first_sid"] = merged.get("first_sid", "").fillna("").astype(str)
    merged["last_sid"] = merged.get("last_sid", "").fillna("").astype(str)
    merged["species_url"] = merged["species_code"].map(
        lambda c: f"https://ebird.org/species/{c}" if str(c).strip() else ""
    )

    summary = (
        merged.groupby(["group_name", "group_order"], as_index=False)
        .agg(
            total_species=("base_species", "nunique"),
            seen_species=("seen", "sum"),
        )
        .sort_values(["seen_species", "total_species"], ascending=[False, False])
    )
    summary["seen_species"] = summary["seen_species"].astype(int)
    summary["percent_seen"] = (
        (summary["seen_species"] / summary["total_species"].replace(0, pd.NA)) * 100.0
    ).fillna(0.0)
    summary = summary.sort_values(
        by=["percent_seen", "group_name"],
        ascending=[False, True],
        kind="mergesort",
    ).reset_index(drop=True)
    return summary, merged


def render_rankings_streamlit_tab_from_bundle(bundle: dict[str, Any]) -> None:
    """Render Rankings HTML from a precomputed bundle (fragment-safe)."""
    inject_streamlit_checklist_css(_rankings_family_coverage_inject_css())

    # Family Lists “last family”: compare current main tab to end-of-previous-run snapshot (app.py).
    # Entering Ranking & Lists from another main tab clears the overview pin so auto-restore may run;
    # staying on this tab after Back keeps the pin until Resume or a new selection.
    _rankings_main_tab_label = NOTEBOOK_MAIN_TAB_LABELS[2]
    _default_main_tab = NOTEBOOK_MAIN_TAB_LABELS[0]
    _now_main = str(st.session_state.get(EXPLORER_MAIN_TABS_STATE_KEY) or _default_main_tab).strip()
    _prev_main = str(st.session_state.get(SESSION_PREV_MAIN_TAB_FOR_FAMILY_KEY) or "").strip()
    if _now_main == _rankings_main_tab_label and _prev_main and _prev_main != _rankings_main_tab_label:
        st.session_state[_STREAMLIT_FAMILY_COVERAGE_PIN_OVERVIEW_KEY] = False
        st.session_state[_STREAMLIT_FAMILY_COVERAGE_ENTERED_FROM_OTHER_MAIN_TAB_KEY] = True

    # Third tab: species-group coverage (Family Lists label; refs #73).
    tab_top, tab_int, tab_group = st.tabs(["Top Lists", "Interesting Lists", "Family Lists"])

    with tab_top:
        for title, inner_html in bundle.get("rankings_sections_top_n") or []:
            with st.expander(title, expanded=False):
                st.markdown(
                    f'<div class="{_STREAMLIT_TABLE_SCOPE} {_RANKINGS_SCOPE_EXTRA}">{inner_html}</div>',
                    unsafe_allow_html=True,
                )

    with tab_int:
        for title, inner_html in bundle.get("rankings_sections_other") or []:
            with st.expander(title, expanded=False):
                st.markdown(
                    f'<div class="{_STREAMLIT_TABLE_SCOPE} {_RANKINGS_SCOPE_EXTRA}">{inner_html}</div>',
                    unsafe_allow_html=True,
                )

    with tab_group:
        summary = bundle.get(_GROUP_COVERAGE_SUMMARY_KEY)
        detail = bundle.get(_GROUP_COVERAGE_DETAIL_KEY)
        coverage_error = str(bundle.get(_GROUP_COVERAGE_ERROR_KEY) or "").strip()
        if coverage_error:
            st.error(f"Family coverage error: {coverage_error}")
        if not isinstance(summary, pd.DataFrame) or summary.empty:
            st.info("Family coverage unavailable (taxonomy data not loaded).")
            return

        display_summary = summary.copy()
        display_summary["% seen"] = display_summary["percent_seen"].map(lambda x: f"{float(x):.1f}%")
        display_summary = display_summary.rename(
            columns={
                "group_name": "Family",
                "total_species": "Total species",
                "seen_species": "Seen species",
            }
        )[["Family", "Seen species", "Total species", "% seen"]]

        fam_values = set(display_summary["Family"].astype(str))

        # Without this, the fallback “overview” option would re-set pin on the same run we cleared it for tab return.
        _skip_pin_for_summary_on_fallback = st.session_state.pop(
            _STREAMLIT_FAMILY_COVERAGE_ENTERED_FROM_OTHER_MAIN_TAB_KEY, False
        )

        _reset_nonce = int(st.session_state.get(_FAMILY_COVERAGE_RESET_NONCE_KEY, 0))
        _table_key = f"{_STREAMLIT_GROUP_COVERAGE_TABLE_KEY}_{_reset_nonce}"

        st.caption(
            "Scroll the family list above **if needed**, then **select one row** to see species for that family. "
            "With no row selected, the panel below shows family-level coverage. "
            "A **fully recorded** family is one where you have recorded every species in that family "
            "for your data under the eBird taxonomy."
        )
        selection_supported = True
        try:
            event = st.dataframe(
                display_summary,
                width="stretch",
                hide_index=True,
                height=_FAMILY_COVERAGE_SUMMARY_DATAFRAME_HEIGHT_PX,
                column_config={
                    "Family": st.column_config.TextColumn("Family", width="large"),
                    "Seen species": st.column_config.NumberColumn("Seen", width="small"),
                    "Total species": st.column_config.NumberColumn("Total", width="small"),
                    "% seen": st.column_config.TextColumn("% seen", width="small"),
                },
                on_select="rerun",
                selection_mode="single-row",
                key=_table_key,
            )
            selected_rows: list = []
            if isinstance(event, dict):
                selected_rows = event.get("selection", {}).get("rows", []) or []
            if selected_rows:
                idx = int(selected_rows[0])
                if 0 <= idx < len(display_summary):
                    selected_group = str(display_summary.iloc[idx]["Family"])
                    st.session_state[_STREAMLIT_GROUP_COVERAGE_SELECTED_KEY] = selected_group
                    st.session_state[_STREAMLIT_LAST_FAMILY_COVERAGE_KEY] = selected_group
                    st.session_state[_STREAMLIT_FAMILY_COVERAGE_PIN_OVERVIEW_KEY] = False
        except TypeError:
            selection_supported = False
            st.dataframe(
                display_summary,
                width="stretch",
                hide_index=True,
                height=_FAMILY_COVERAGE_SUMMARY_DATAFRAME_HEIGHT_PX,
            )

        selected_group = str(st.session_state.get(_STREAMLIT_GROUP_COVERAGE_SELECTED_KEY) or "").strip()
        if selected_group not in fam_values:
            selected_group = ""
            st.session_state[_STREAMLIT_GROUP_COVERAGE_SELECTED_KEY] = ""

        if not selection_supported:
            _summary_label = "— Family summary (overview) —"
            group_options = sorted(summary["group_name"].tolist(), key=lambda s: str(s).lower())
            opts = [_summary_label] + group_options
            if selected_group and selected_group in group_options:
                _pick = selected_group
            else:
                _pick = _summary_label
            pick = st.selectbox(
                "Select family",
                options=opts,
                index=opts.index(_pick) if _pick in opts else 0,
                key=_STREAMLIT_GROUP_COVERAGE_FALLBACK_KEY,
            )
            if pick == _summary_label:
                selected_group = ""
                st.session_state[_STREAMLIT_GROUP_COVERAGE_SELECTED_KEY] = ""
                # Pin overview when user explicitly picks summary (mirrors Back); skipped once after returning from another main tab.
                if not _skip_pin_for_summary_on_fallback:
                    st.session_state[_STREAMLIT_FAMILY_COVERAGE_PIN_OVERVIEW_KEY] = True
            else:
                selected_group = pick
                st.session_state[_STREAMLIT_GROUP_COVERAGE_SELECTED_KEY] = selected_group
                st.session_state[_STREAMLIT_LAST_FAMILY_COVERAGE_KEY] = selected_group
                st.session_state[_STREAMLIT_FAMILY_COVERAGE_PIN_OVERVIEW_KEY] = False

        # Auto-restore last family when selection is empty, pin is off, and name still valid (e.g. after leaving Ranking & Lists).
        if not selected_group:
            _last_fam = str(st.session_state.get(_STREAMLIT_LAST_FAMILY_COVERAGE_KEY) or "").strip()
            _pin = bool(st.session_state.get(_STREAMLIT_FAMILY_COVERAGE_PIN_OVERVIEW_KEY, False))
            if _last_fam and not _pin and _last_fam in fam_values:
                selected_group = _last_fam
                st.session_state[_STREAMLIT_GROUP_COVERAGE_SELECTED_KEY] = selected_group

        if selected_group:
            if st.button("Back to family summary", key=_STREAMLIT_FAMILY_SUMMARY_BACK_BTN_KEY):
                st.session_state[_STREAMLIT_GROUP_COVERAGE_SELECTED_KEY] = ""
                st.session_state[_STREAMLIT_FAMILY_COVERAGE_PIN_OVERVIEW_KEY] = True  # suppress auto-restore until Resume or other main tab
                st.session_state[_FAMILY_COVERAGE_RESET_NONCE_KEY] = _reset_nonce + 1

        selected_group = str(st.session_state.get(_STREAMLIT_GROUP_COVERAGE_SELECTED_KEY) or "").strip()
        if selected_group not in fam_values:
            selected_group = ""

        st.divider()

        if not isinstance(detail, pd.DataFrame) or detail.empty:
            st.info("No family detail available yet.")
            return

        if not selected_group:
            overview = _family_coverage_summary_metrics_df(summary)
            st.markdown("**Family coverage overview**")
            # When still on Ranking & Lists after Back, pin blocks auto-restore; button is the escape hatch.
            _resume_last = str(st.session_state.get(_STREAMLIT_LAST_FAMILY_COVERAGE_KEY) or "").strip()
            _pin_overview = bool(st.session_state.get(_STREAMLIT_FAMILY_COVERAGE_PIN_OVERVIEW_KEY, False))
            if _pin_overview and _resume_last and _resume_last in fam_values:
                if st.button(
                    f"Resume last family ({_resume_last})",
                    key=_STREAMLIT_FAMILY_COVERAGE_RESUME_BTN_KEY,
                ):
                    st.session_state[_STREAMLIT_GROUP_COVERAGE_SELECTED_KEY] = _resume_last
                    st.session_state[_STREAMLIT_FAMILY_COVERAGE_PIN_OVERVIEW_KEY] = False
                    st.rerun()
            st.dataframe(overview, width="stretch", hide_index=True, height=260)
            st.markdown(
                f"**Taxonomy:** [eBird]({_EBIRD_TAXONOMY_URL}) — species and family groups follow the eBird taxonomy."
            )
            return

        selected = detail[detail["group_name"] == selected_group].copy()
        if selected.empty:
            st.info("No species found for selected family.")
            return
        seen_n = int(selected["seen"].sum())
        total_n = int(len(selected))
        pct = (seen_n / total_n * 100.0) if total_n else 0.0
        st.markdown(f"**{selected_group}: {seen_n}/{total_n} species seen ({pct:.1f}%)**")

        selected["Species"] = selected.apply(
            lambda r: (
                f'<a href="{r["species_url"]}" target="_blank" rel="noopener">{r["common_name"]}</a>'
                if str(r["species_url"]).strip()
                else str(r["common_name"])
            ),
            axis=1,
        )
        selected = selected.sort_values(["seen", "common_name"], ascending=[False, True])
        html_rows = []
        for _, r in selected.iterrows():
            first_cell = r["first_seen"] or "—"
            if str(r.get("first_sid", "")).strip() and first_cell != "—":
                first_cell = f'<a href="https://ebird.org/checklist/{r["first_sid"]}" target="_blank" rel="noopener">{first_cell}</a>'
            last_cell = r["last_seen"] or "—"
            if str(r.get("last_sid", "")).strip() and last_cell != "—":
                last_cell = f'<a href="https://ebird.org/checklist/{r["last_sid"]}" target="_blank" rel="noopener">{last_cell}</a>'
            html_rows.append(
                "<tr>"
                f'<td>{r["Species"]}</td>'
                f'<td style="text-align:right">{int(r["checklists"]):,}</td>'
                f'<td style="text-align:right">{int(r["individuals"]):,}</td>'
                f"<td>{first_cell}</td>"
                f"<td>{last_cell}</td>"
                "</tr>"
            )
        st.markdown(
            (
                f'<div class="{_STREAMLIT_TABLE_SCOPE} {_RANKINGS_SCOPE_EXTRA}">'
                "<table class='stats-tbl rankings-tbl'>"
                "<thead><tr><th>Species</th><th>Checklists</th><th>Individuals</th>"
                "<th>First seen</th><th>Last seen</th></tr></thead>"
                f"<tbody>{''.join(html_rows)}</tbody></table></div>"
            ),
            unsafe_allow_html=True,
        )


@st.fragment
def run_rankings_streamlit_tab_fragment() -> None:
    """Partial reruns when Rankings expanders/widgets change (same pattern as Country / Yearly)."""
    bundle = st.session_state.get(RANKINGS_TAB_BUNDLE_KEY) or {}
    if not bundle.get("rankings_sections_top_n") and not bundle.get("rankings_sections_other"):
        st.info("Load checklist data to use Ranking & Lists.")
        return
    render_rankings_streamlit_tab_from_bundle(bundle)


def build_rankings_tab_bundle(
    df_full: pd.DataFrame,
    *,
    country_sort: str,
    taxonomy_locale: str,
    high_count_sort: str,
    high_count_tie_break: str,
) -> dict[str, Any]:
    """Compute cached Rankings bundle (call from main script alongside other full-export prep)."""
    bundle = _cached_rankings_stats_bundle(
        df_full,
        int(st.session_state.streamlit_rankings_top_n),
        int(st.session_state.streamlit_rankings_visible_rows),
        country_sort,
        taxonomy_locale,
        high_count_sort,
        high_count_tie_break,
    )
    coverage_error = ""
    try:
        summary_df, detail_df = _build_group_coverage_tables(df_full, taxonomy_locale)
    except Exception as exc:
        summary_df, detail_df = pd.DataFrame(), pd.DataFrame()
        coverage_error = str(exc)
    bundle[_GROUP_COVERAGE_SUMMARY_KEY] = summary_df
    bundle[_GROUP_COVERAGE_DETAIL_KEY] = detail_df
    bundle[_GROUP_COVERAGE_ERROR_KEY] = coverage_error
    return bundle
