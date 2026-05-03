"""
**Ranking & Lists** (Streamlit): nested tabs **Top Lists** / **Interesting Lists** / **Families**
(eBird species groups under the hood; refs `#73`), expanders per list on the first two tabs.

Uses HTML from :func:`explorer.presentation.checklist_stats_display.format_checklist_stats_bundle`
(``rankings_sections_top_n`` / ``rankings_sections_other``) — same tables as the explorer’s richly-linked HTML tables,
rendered with ``st.markdown(..., unsafe_allow_html=True)``. Table styling matches **Checklist Statistics**:
:func:`~explorer.app.streamlit.streamlit_theme.inject_streamlit_checklist_css` plus Rankings width scoped under
``streamlit-checklist-html-ab`` (plus ``streamlit-rankings-html`` for width). The **Families** tab uses
``st.dataframe`` with **single-row selection** and a **bounded height** so the summary scrolls inside the grid
(compact layout). With **no family selected**, the lower panel shows **family-level coverage** in an HTML
``stats-tbl`` / ``rankings-tbl`` table (group headings + metric rows); selecting a row shows species detail the
same way.

**Top N** and **visible rows** are controlled from **Settings → Tables & lists** (session keys
``streamlit_rankings_top_n``, ``streamlit_rankings_visible_rows``; refs `#81`). **Top Lists** tables
include a narrow leading **Rank** column with soft accent styling (refs `#83`). **Species: Not seen in
the past year** is the last expander under Interesting Lists; it lists countable species with no
observation in the trailing twelve months on the **full export** and is not Top-N–capped (refs `#106`).
A hint points to the **Country** tab for the in-country, working-set–scoped variant (refs `#108`).
"""

from __future__ import annotations

import html
from typing import Any

import pandas as pd
import streamlit as st

from explorer.presentation.checklist_stats_display import (
    _YEARLY_STREAMLIT_CAPTION_STYLE,
    format_checklist_stats_bundle,
)
from explorer.core.species_family import (
    assign_group_for_taxon_order,
    load_taxonomy_groups,
    load_taxonomy_species_rows,
)
from explorer.core.species_logic import countable_species_vectorized
from explorer.core.stats import safe_count
from explorer.core.taxonomy import get_species_and_lifelist_urls, load_taxonomy

from explorer.app.streamlit.app_caches import cached_full_export_checklist_stats_payload
from explorer.app.streamlit.app_constants import RANKINGS_TAB_BUNDLE_KEY
from explorer.app.streamlit.perf_instrumentation import perf_fragment
from explorer.app.streamlit.defaults import RANKINGS_BUNDLE_SCROLL_HINT_DEFAULT, RANKINGS_TABLE_LAYOUT_MAX_WIDTH_PX
from explorer.app.streamlit.streamlit_theme import inject_streamlit_checklist_css

# Must include ``streamlit-checklist-html-ab`` — ``CHECKLIST_STATS_*`` rules are scoped to it (same as Checklist Statistics).
_STREAMLIT_TABLE_SCOPE = "streamlit-checklist-html-ab"
_RANKINGS_SCOPE_EXTRA = "streamlit-rankings-html"

# Bundle keys and widget/session keys: eBird "group" in code; nested tab label Families (refs #73).
_GROUP_COVERAGE_SUMMARY_KEY = "group_coverage_summary"
_GROUP_COVERAGE_DETAIL_KEY = "group_coverage_detail"
_GROUP_COVERAGE_ERROR_KEY = "group_coverage_error"
_STREAMLIT_GROUP_COVERAGE_SELECTED_KEY = "streamlit_group_coverage_selected_group"
_STREAMLIT_GROUP_COVERAGE_TABLE_KEY = "streamlit_group_coverage_summary_table"
_STREAMLIT_GROUP_COVERAGE_FALLBACK_KEY = "streamlit_group_coverage_selected_group_fallback"

_EBIRD_TAXONOMY_URL = "https://science.ebird.org/en/use-ebird-data/the-ebird-taxonomy"

# Summary grid height (px): scroll inside the dataframe so long family lists do not push the detail table down.
_FAMILY_COVERAGE_SUMMARY_DATAFRAME_HEIGHT_PX = 280


def _family_coverage_summary_metrics_sections(
    summary: pd.DataFrame,
) -> list[tuple[str, list[tuple[str, str]]]]:
    """(section heading, [(metric label, formatted value), ...]) for overview HTML and tests."""
    if summary.empty:
        return []
    n_total = len(summary)
    seen = summary["seen_species"].astype(int)
    total_sp = summary["total_species"].astype(int)
    pct_seen = summary["percent_seen"].astype(float)
    n_with_any = int((seen > 0).sum())
    complete = (seen >= total_sp) & (total_sp > 0)
    n_complete = int(complete.sum())
    pct_any = (n_with_any / n_total * 100.0) if n_total else 0.0
    pct_complete = (n_complete / n_total * 100.0) if n_total else 0.0
    avg_cov = float(pct_seen.mean()) if n_total else 0.0
    med_cov = float(pct_seen.median()) if n_total else 0.0
    n_ge_90 = int((pct_seen >= 90.0).sum())
    n_ge_75 = int((pct_seen >= 75.0).sum())
    n_ge_50 = int((pct_seen >= 50.0).sum())
    n_single_species_family = int((total_sp == 1).sum())
    n_zero_seen = int((seen == 0).sum())
    return [
        ("Taxonomy", [("Total families", f"{n_total:,}")]),
        (
            "Coverage",
            [
                ("Observed families (at least one species)", f"{n_with_any:,}"),
                ("Observed families (%)", f"{pct_any:.1f}%"),
                ("Fully recorded families (all species observed)", f"{n_complete:,}"),
                ("Fully recorded families (%)", f"{pct_complete:.1f}%"),
            ],
        ),
        (
            "Progress",
            [
                ("Families ≥90% complete", f"{n_ge_90:,}"),
                ("Families ≥75% complete", f"{n_ge_75:,}"),
                ("Families ≥50% complete", f"{n_ge_50:,}"),
            ],
        ),
        (
            "Distribution",
            [
                ("Average family coverage (%)", f"{avg_cov:.1f}%"),
                ("Median family coverage (%)", f"{med_cov:.1f}%"),
            ],
        ),
        (
            "Edge case",
            [
                ("Families with only one species recorded", f"{n_single_species_family:,}"),
                ("Families with no species recorded", f"{n_zero_seen:,}"),
            ],
        ),
    ]


def _family_coverage_summary_metrics_df(summary: pd.DataFrame) -> pd.DataFrame:
    """Flattened Section / Metric / Value (used by unit tests; mirrors overview rows)."""
    rows: list[dict[str, str]] = []
    for section, pairs in _family_coverage_summary_metrics_sections(summary):
        for metric, value in pairs:
            rows.append({"Section": section, "Metric": metric, "Value": value})
    return pd.DataFrame(rows)


def _family_coverage_summary_metrics_html(summary: pd.DataFrame) -> str:
    """HTML overview table with group heading rows (same ``stats-tbl`` / ``rankings-tbl`` pattern as species detail)."""
    sections = _family_coverage_summary_metrics_sections(summary)
    if not sections:
        return ""
    body_parts: list[str] = []
    for section, pairs in sections:
        body_parts.append(
            f'<tr class="family-coverage-group"><th colspan="2">{html.escape(section)}</th></tr>'
        )
        for metric, value in pairs:
            body_parts.append(
                "<tr>"
                f"<td>{html.escape(metric)}</td>"
                f'<td style="text-align:right">{html.escape(value)}</td>'
                "</tr>"
            )
    return (
        f'<div class="{_STREAMLIT_TABLE_SCOPE} {_RANKINGS_SCOPE_EXTRA}">'
        "<table class='stats-tbl rankings-tbl family-coverage-overview'>"
        "<thead><tr><th>Metric</th><th>Value</th></tr></thead>"
        f"<tbody>{''.join(body_parts)}</tbody></table></div>"
    )


def _family_coverage_taxonomy_note_html() -> str:
    """Footnote below the overview table; same caption style as Yearly Summary protocol note (refs #85)."""
    inner = (
        f'<p style="{_YEARLY_STREAMLIT_CAPTION_STYLE}">'
        "<strong>Taxonomy:</strong> "
        f'<a href="{html.escape(_EBIRD_TAXONOMY_URL)}" target="_blank" rel="noopener">eBird</a> '
        "— species and family groups follow the eBird taxonomy."
        "</p>"
    )
    return f'<div class="{_STREAMLIT_TABLE_SCOPE} {_RANKINGS_SCOPE_EXTRA}">{inner}</div>'


def _rankings_family_coverage_inject_css() -> str:
    """Rankings max-width + family overview group rows (refs #73, #81)."""
    return (
        f".{_STREAMLIT_TABLE_SCOPE}.{_RANKINGS_SCOPE_EXTRA} {{ max-width:{RANKINGS_TABLE_LAYOUT_MAX_WIDTH_PX}px;width:100%; }}"
        f" .{_STREAMLIT_TABLE_SCOPE}.{_RANKINGS_SCOPE_EXTRA} .family-coverage-overview tr.family-coverage-group th {{"
        "text-align:left;font-weight:600;padding-top:0.65em;padding-bottom:0.2em;"
        "background:transparent;border-bottom:none;"
        "}}"
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
        taxonomy_locale,
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
    """Streamlit-cached wrapper; delegates to :func:`explorer.core.species_family.load_taxonomy_species_rows`."""
    return load_taxonomy_species_rows(locale)


@st.cache_data(show_spinner=False)
def _load_taxonomy_groups(locale: str) -> list[dict[str, Any]]:
    """Streamlit-cached wrapper; delegates to :func:`explorer.core.species_family.load_taxonomy_groups`."""
    return load_taxonomy_groups(locale)


@st.cache_data(show_spinner=False)
def _build_group_coverage_tables(df_full: pd.DataFrame, taxonomy_locale: str) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Build summary/detail DataFrames for species-group coverage (eBird taxonomy + sppgroup)."""
    tax = _load_taxonomy_species_rows(taxonomy_locale)
    groups = _load_taxonomy_groups(taxonomy_locale)
    if tax.empty or not groups:
        return pd.DataFrame(), pd.DataFrame()

    tax = tax.copy()
    tax[["group_name", "group_order"]] = tax["taxon_order"].apply(
        lambda x: pd.Series(assign_group_for_taxon_order(float(x), groups))
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


def _rankings_expander_sections(sections: list[tuple[str, str]]) -> None:
    """One expander per (title, inner_html) with rankings-scoped table wrapper (refs #81)."""
    for title, inner_html in sections:
        with st.expander(title, expanded=False):
            st.markdown(
                f'<div class="{_STREAMLIT_TABLE_SCOPE} {_RANKINGS_SCOPE_EXTRA}">{inner_html}</div>',
                unsafe_allow_html=True,
            )


def render_rankings_streamlit_tab_from_bundle(bundle: dict[str, Any]) -> None:
    """Render Rankings HTML from a precomputed bundle (fragment-safe)."""
    inject_streamlit_checklist_css(_rankings_family_coverage_inject_css())

    # Third tab: species-group coverage (Families label; refs #73).
    tab_top, tab_int, tab_group = st.tabs(["Top Lists", "Interesting Lists", "Families"])

    with tab_top:
        _rankings_expander_sections(list(bundle.get("rankings_sections_top_n") or []))

    with tab_int:
        _rankings_expander_sections(list(bundle.get("rankings_sections_other") or []))

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
        _table_key = _STREAMLIT_GROUP_COVERAGE_TABLE_KEY

        selection_supported = True
        try:
            event = st.dataframe(
                display_summary,
                # Match lower HTML tables (``max-width`` on ``.streamlit-rankings-html``; defaults.py).
                width=RANKINGS_TABLE_LAYOUT_MAX_WIDTH_PX,
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
                    st.session_state[_STREAMLIT_GROUP_COVERAGE_SELECTED_KEY] = str(
                        display_summary.iloc[idx]["Family"]
                    )
            else:
                # Empty selection must clear session; otherwise the previous family sticks after deselect.
                st.session_state[_STREAMLIT_GROUP_COVERAGE_SELECTED_KEY] = ""
        except TypeError:
            selection_supported = False
            st.dataframe(
                display_summary,
                width=RANKINGS_TABLE_LAYOUT_MAX_WIDTH_PX,
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
            else:
                selected_group = pick
                st.session_state[_STREAMLIT_GROUP_COVERAGE_SELECTED_KEY] = selected_group

        selected_group = str(st.session_state.get(_STREAMLIT_GROUP_COVERAGE_SELECTED_KEY) or "").strip()
        if selected_group not in fam_values:
            selected_group = ""

        st.divider()

        if not isinstance(detail, pd.DataFrame) or detail.empty:
            st.info("No family detail available yet.")
            return

        if not selected_group:
            st.markdown("**Family coverage overview**")
            _overview_html = _family_coverage_summary_metrics_html(summary)
            if _overview_html:
                st.markdown(_overview_html, unsafe_allow_html=True)
            st.markdown('<div style="height:1rem;" aria-hidden="true"></div>', unsafe_allow_html=True)
            st.markdown(_family_coverage_taxonomy_note_html(), unsafe_allow_html=True)
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
    with perf_fragment("ranking_lists"):
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
