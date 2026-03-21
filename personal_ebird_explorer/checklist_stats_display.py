"""
HTML rendering for checklist statistics, yearly summary, and rankings sections.

Consumes :class:`ChecklistStatsPayload` from ``checklist_stats_compute`` (refs #68).
"""

from __future__ import annotations

import html as html_module
from typing import Any, Callable, Dict, List, Optional, Tuple
from urllib.parse import quote as url_quote

from personal_ebird_explorer.checklist_stats_compute import ChecklistStatsPayload
from personal_ebird_explorer.region_display import country_for_display
from personal_ebird_explorer.rankings_display import (
    rankings_seen_once_table,
    rankings_subspecies_hierarchical_table,
    rankings_table_location_5col,
    rankings_table_with_rank,
    rankings_visited_table,
)

LinkUrlsFn = Optional[Callable[[str], Tuple[Optional[str], Optional[str]]]]

# Country tab accordion order (Settings → Tables & lists)
COUNTRY_TAB_SORT_ALPHABETICAL = "alphabetical"
COUNTRY_TAB_SORT_LIFERS_WORLD = "lifers_world"
COUNTRY_TAB_SORT_TOTAL_SPECIES = "total_species"


def _ebird_country_region_iso2(country_key: str) -> Optional[str]:
    """Uppercased ISO alpha-2 when *country_key* can drive eBird country URLs; else ``None``."""
    if country_key == "_UNKNOWN" or str(country_key).startswith("_R:"):
        return None
    k = str(country_key).strip().upper()
    if len(k) == 2 and k.isalpha():
        return k
    return None


def _ebird_country_lifelist_url(country_key: str) -> Optional[str]:
    """eBird life list filtered by region, e.g. ``https://ebird.org/lifelist?r=AU``."""
    k = _ebird_country_region_iso2(country_key)
    if not k:
        return None
    return f"https://ebird.org/lifelist?r={k}"


def _ebird_country_mychecklists_url(country_key: str) -> Optional[str]:
    """eBird “my checklists” for a country, e.g. ``https://ebird.org/mychecklists/FR``."""
    k = _ebird_country_region_iso2(country_key)
    if not k:
        return None
    return f"https://ebird.org/mychecklists/{k}"


def _country_table_statistic_label_cell(label: str, country_key: str) -> str:
    """First-column cell HTML: plain text, or ⧉ links for *Lifers (country)* / *Total checklists*."""
    esc_label = html_module.escape(label, quote=False)
    if label == "Lifers (country)":
        url = _ebird_country_lifelist_url(country_key)
        title = "eBird life list (this country/region)"
    elif label == "Total checklists":
        url = _ebird_country_mychecklists_url(country_key)
        title = "eBird my checklists (this country)"
    else:
        return esc_label
    if not url:
        return esc_label
    esc_url = html_module.escape(url, quote=True)
    link = (
        f' <a href="{esc_url}" target="_blank" rel="noopener noreferrer" '
        'style="color:inherit;text-decoration:none;" '
        f'title="{html_module.escape(title, quote=True)}">⧉</a>'
    )
    return esc_label + link


def _country_accordion_title(country_key: str) -> str:
    """Plain-text title for a country ``<summary>`` (HTML-escaped)."""
    if country_key == "_UNKNOWN":
        t = "Unknown"
    elif str(country_key).startswith("_R:"):
        t = str(country_key)[3:]
    else:
        k = str(country_key).strip()
        if len(k) == 2 and k.isalpha():
            t = country_for_display(k) or k
        else:
            t = k
    return html_module.escape(t, quote=False)


def _country_heading_sort_key(country_key: str) -> Tuple[int, str]:
    """Sort key: alphabetical by resolved display name; Unknown last."""
    if country_key == "_UNKNOWN":
        return (2, "")
    if str(country_key).startswith("_R:"):
        return (0, str(country_key)[3:].lower())
    k = str(country_key).strip()
    if len(k) == 2 and k.isalpha():
        return (0, (country_for_display(k) or k).lower())
    return (0, k.lower())


def _country_metric_from_rows(
    rows: List[Tuple[str, List[str]]],
    sort_mode: str,
) -> int:
    """Numeric metric for sorting: uses the **Total** column when present, else the sole year cell."""
    by_label = {label: vals for label, vals in rows}
    if sort_mode == COUNTRY_TAB_SORT_LIFERS_WORLD:
        label = "Lifers (world)"
    elif sort_mode == COUNTRY_TAB_SORT_TOTAL_SPECIES:
        label = "Total species"
    else:
        return 0
    vals = by_label.get(label)
    if not vals:
        return 0
    try:
        return int(str(vals[-1]).replace(",", "").strip())
    except ValueError:
        return 0


def _country_section_sort_key_metric(
    section: Tuple[str, List[Any], List[Tuple[str, List[str]]]],
    sort_mode: str,
) -> Tuple[int, int, Tuple[int, str]]:
    """Sort key: Unknown last; then descending metric; tie-break alphabetical by display name."""
    ck, _years, rows = section
    tier = 1 if ck == "_UNKNOWN" else 0
    m = _country_metric_from_rows(rows, sort_mode)
    return (tier, -m, _country_heading_sort_key(ck))


def _sort_country_sections(
    country_sections: List[Tuple[str, List[Any], List[Tuple[str, List[str]]]]],
    country_sort: str,
) -> List[Tuple[str, List[Any], List[Tuple[str, List[str]]]]]:
    if country_sort == COUNTRY_TAB_SORT_LIFERS_WORLD:
        return sorted(
            country_sections,
            key=lambda s: _country_section_sort_key_metric(s, COUNTRY_TAB_SORT_LIFERS_WORLD),
        )
    if country_sort == COUNTRY_TAB_SORT_TOTAL_SPECIES:
        return sorted(
            country_sections,
            key=lambda s: _country_section_sort_key_metric(s, COUNTRY_TAB_SORT_TOTAL_SPECIES),
        )
    # Default: alphabetical by display name (Unknown last)
    return sorted(country_sections, key=lambda s: _country_heading_sort_key(s[0]))


def _format_country_summary_html(
    country_sections: List[Tuple[str, List[Any], List[Tuple[str, List[str]]]]],
    *,
    country_sort: str = COUNTRY_TAB_SORT_ALPHABETICAL,
) -> str:
    """Per-country accordions + yearly-style stats tables (sparse year columns).

    *country_sort*: ``alphabetical`` | ``lifers_world`` | ``total_species`` — order of accordions only.
    """
    if not country_sections:
        return (
            "<p style='font-family:sans-serif;color:#666;padding:16px;'>"
            "No country data (add Country or State/Province to your export).</p>"
        )

    yearly_css = """
    .yearly-maint-section { margin-bottom:8px; border:1px solid #e5e7eb; border-radius:6px; background:#f9fafb; padding:4px 10px; }
    .yearly-maint-section > summary { font-weight:600; padding:6px 0; color:#374151; cursor:pointer; }
"""
    blocks = []
    sorted_sections = _sort_country_sections(country_sections, country_sort)
    for country_key, years_list, rows in sorted_sections:
        if not years_list or not rows:
            continue
        title = _country_accordion_title(country_key)
        n_years = len(years_list)
        multi_year = n_years > 1
        n_cols = n_years + (1 if multi_year else 0)
        min_w = "280px" if n_cols <= 2 else "360px" if n_cols <= 3 else "400px"
        year_headers = "".join(f"<th style='text-align:right;'>{y}</th>" for y in years_list)
        if multi_year:
            year_headers += "<th style='text-align:right;'>Total</th>"
        body_rows = "".join(
            f"<tr><td>{_country_table_statistic_label_cell(label, country_key)}</td>"
            + "".join(f"<td style='text-align:right;'>{html_module.escape(v, quote=False)}</td>" for v in vals)
            + "</tr>"
            for label, vals in rows
        )
        table_html = f"""  <div style="overflow-x:auto;">
  <table class="stats-tbl" style="min-width:{min_w};">
    <thead><tr><th>Statistic</th>{year_headers}</tr></thead>
    <tbody>{body_rows}</tbody>
  </table>
  </div>"""
        blocks.append(f"""
  <details class="yearly-maint-section">
    <summary>{title}</summary>
{table_html}  </details>""")

    inner = "".join(blocks)
    return f"""
  <style>{yearly_css}</style>
  <div style="width:100%;max-width:1400px;padding:0 clamp(16px,3vw,32px) 24px;box-sizing:border-box;">
  <h4 style="margin-top:0;margin-bottom:8px;padding-bottom:6px;border-bottom:1px solid #e5e7eb;">By country</h4>
{inner}
    </div>"""


# Shared with notebook stats panel HTML and Streamlit HTML tab (refs #70).
CHECKLIST_STATS_TABLE_CSS = """
    .stats-info-icon { position:relative; display:inline-block; margin-left:4px; }
    .stats-info-glyph { cursor:help; opacity:0.7; }
    .stats-info-tooltip { position:absolute; bottom:100%; top:auto; margin-bottom:6px; margin-top:0; padding:10px 14px; background:#374151; color:#fff; font-size:12px; font-weight:normal; line-height:1.5; white-space:normal; max-width:min(320px,85vw); min-width:180px; border-radius:6px; box-shadow:0 4px 12px rgba(0,0,0,0.15); opacity:0; visibility:hidden; transition:opacity 0.15s; pointer-events:none; z-index:9999; right:0; left:auto; }
    .stats-info-icon:hover .stats-info-tooltip { opacity:1; visibility:visible; }
    .stats-col:first-child .stats-info-tooltip { right:0; left:auto; }
    .stats-col:last-child .stats-info-tooltip { left:0; right:auto; }
    .stats-tbl-3 th:nth-child(2), .stats-tbl-3 td:nth-child(2) { text-align:center; }
    .rankings-tbl td:first-child { font-weight:normal; }
    """

# Injected once by ``streamlit_app/checklist_stats_streamlit_html`` around checklist sub-tabs only.
# Scoped under ``.streamlit-checklist-html-ab`` so Jupyter ``stats_html`` / notebook layout stay unchanged.
#
# **Default:** green accents + zebra (``#1f6f54`` — aligns with ``.streamlit/config.toml`` primary).
# **Alternate:** ``CHECKLIST_STATS_STREAMLIT_HTML_TAB_CSS_BLUE`` (eBird-style blue); enable via
# ``_USE_EBIRD_BLUE_HTML_TAB_THEME`` in ``checklist_stats_streamlit_html.py``.
#
# Typography is slightly smaller than 1rem so body matches Streamlit sub-tab labels (which read ~14px / normal weight).
def _streamlit_checklist_html_tab_css(*, blue_theme: bool) -> str:
    """Build scoped Streamlit HTML-tab CSS (blue or green accent + zebra rows)."""
    if blue_theme:
        # eBird-ish blue (links / nav on eBird.org lean this way; tweak if you standardise on brand specs).
        acc = "21, 101, 168"  # #1565a8
        link = "#1565a8"
        text_fb = "#1a2e22"
        p_fallback = "26, 46, 34"
    else:
        acc = "31, 111, 84"  # #1f6f54 — matches Streamlit config.toml primary / prior green tab
        link = "#1f6f54"
        text_fb = "#1a2e22"
        p_fallback = "26, 46, 34"
    return f"""
.streamlit-checklist-html-ab {{
  display: block;
  width: 100%;
  max-width: min(68rem, 100%);
  min-width: min(100%, 20rem);
  box-sizing: border-box;
  font-family: "Source Sans Pro", -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
  font-size: 0.875rem;
  line-height: 1.5;
  font-weight: 400;
  color: var(--text-color, {text_fb});
}}
.streamlit-checklist-html-ab .stats-tbl {{
  width: 100%;
  table-layout: fixed;
  border-collapse: separate;
  border-spacing: 0;
  font-size: inherit;
  font-weight: 400;
  background: var(--background-color, #fafcfa);
  color: var(--text-color, {text_fb});
  border: 1px solid rgba({acc}, 0.22);
  border-radius: 0.5rem;
  overflow: hidden;
  box-shadow: 0 1px 2px rgba(0, 0, 0, 0.06);
}}
.streamlit-checklist-html-ab .stats-tbl td {{
  padding: 0.45rem 0.7rem;
  border-bottom: 1px solid rgba({acc}, 0.12);
  vertical-align: top;
}}
.streamlit-checklist-html-ab .stats-tbl tbody tr:nth-child(odd) td {{
  background: rgba({acc}, 0.04);
}}
.streamlit-checklist-html-ab .stats-tbl tbody tr:nth-child(even) td {{
  background: rgba({acc}, 0.085);
}}
.streamlit-checklist-html-ab .stats-tbl tr:last-child td {{
  border-bottom: none;
}}
.streamlit-checklist-html-ab .stats-tbl td:first-child {{
  width: 58%;
  font-weight: 400;
  padding-right: 1rem;
  word-wrap: break-word;
  overflow-wrap: break-word;
}}
.streamlit-checklist-html-ab .stats-tbl td:last-child {{
  width: 42%;
  text-align: right;
  font-weight: 400;
  font-variant-numeric: tabular-nums;
}}
.streamlit-checklist-html-ab .stats-tbl tbody tr:hover td {{
  background: rgba({acc}, 0.14) !important;
}}
.streamlit-checklist-html-ab a {{
  color: var(--primary-color, {link});
  text-decoration: none;
  font-weight: 400;
}}
.streamlit-checklist-html-ab a:hover {{
  text-decoration: underline;
}}
.streamlit-checklist-html-ab > p {{
  margin: 0.5rem 0 0;
  color: color-mix(in srgb, var(--text-color, {text_fb}) 64%, transparent);
  font-size: 0.75rem;
  line-height: 1.5;
}}
@supports not (color: color-mix(in srgb, black 50%, white)) {{
  .streamlit-checklist-html-ab > p {{
    color: rgba({p_fallback}, 0.7);
  }}
}}
"""


# Canonical Streamlit HTML-tab surface (green — app default).
CHECKLIST_STATS_STREAMLIT_HTML_TAB_CSS = _streamlit_checklist_html_tab_css(blue_theme=False)
CHECKLIST_STATS_STREAMLIT_HTML_TAB_CSS_BLUE = _streamlit_checklist_html_tab_css(blue_theme=True)
# Back-compat: same string as ``CHECKLIST_STATS_STREAMLIT_HTML_TAB_CSS``.
CHECKLIST_STATS_STREAMLIT_HTML_TAB_CSS_GREEN = CHECKLIST_STATS_STREAMLIT_HTML_TAB_CSS

_AUDUBON_4BBRW_ARTICLE_URL = (
    "https://www.audubon.org/news/these-mighty-shorebirds-keep-breaking-flight-records-and-you-can-follow-along"
)


def _checklist_stats_kv_row(label: str, value: str) -> str:
    return f"<tr><td>{label}</td><td>{value}</td></tr>"


def _checklist_stats_tbody_table(rows: List[Tuple[str, str]]) -> str:
    body = "".join(_checklist_stats_kv_row(lab, val) for lab, val in rows)
    return f"<table class=\"stats-tbl\"><tbody>{body}</tbody></table>"


def _checklist_stats_hint_paragraph(plain_text: str) -> str:
    return (
        "<p style=\"margin:4px 0 0;color:#6b7280;font-size:12px;line-height:1.5;\">"
        f"{html_module.escape(plain_text)}</p>"
    )


def checklist_stats_streamlit_tab_sections_html(payload: ChecklistStatsPayload) -> List[Tuple[str, str]]:
    """Six ``(tab_label, inner_html)`` blocks for Streamlit nested tabs — same order as ``checklist_stats_streamlit_native``.

    *inner_html* is table + optional caption ``<p>`` only (no ``<h4>``; the tab supplies the title).
    """
    time_hint = (
        "Incidental, historical and other untimed checklists don't count towards total time, "
        "but do count towards Days with a checklist."
    )
    incomplete_checklist_hint = (
        "Incidental, historical and other untimed checklists don't count towards the incomplete checklist total."
    )
    godwit_hint = (
        "4BBRW: Bar-tailed Godwit, Alaska→Tasmania, ~13,560 km nonstop (2022). 11 days without landing."
    )

    def _esc(s: Any) -> str:
        return html_module.escape(str(s) if s is not None else "")

    def _checklist_date_cell(date_str: str, sid: str) -> str:
        if sid:
            href = f"https://ebird.org/checklist/{url_quote(str(sid), safe='')}"
            return f'<a href="{href}" target="_blank" rel="noopener noreferrer">{_esc(date_str)}</a>'
        return _esc(date_str)

    def _lifelist_loc_cell(loc: str, lid: str) -> str:
        if lid:
            href = f"https://ebird.org/lifelist/{url_quote(str(lid), safe='')}"
            return f'<a href="{href}" target="_blank" rel="noopener noreferrer">{_esc(loc)}</a>'
        return _esc(loc)

    streak_start_date_cell = _checklist_date_cell(payload.streak_start_date, payload.streak_start_sid)
    streak_end_date_cell = _checklist_date_cell(payload.streak_end_date, payload.streak_end_sid)
    streak_start_loc_cell = _lifelist_loc_cell(payload.streak_start_loc, payload.streak_start_lid)
    streak_end_loc_cell = _lifelist_loc_cell(payload.streak_end_loc, payload.streak_end_lid)

    godwit_caption_p = (
        "<p style=\"margin:8px 0 0;color:#6b7280;font-size:12px;line-height:1.5;\">"
        f"{html_module.escape(godwit_hint)} "
        f'<a href="{html_module.escape(_AUDUBON_4BBRW_ARTICLE_URL, quote=True)}" '
        'target="_blank" rel="noopener noreferrer">Audubon article</a>.</p>'
    )

    overview_rows: List[Tuple[str, str]] = [
        ("Total checklists", f"{payload.n_checklists:,}"),
        ("Total species", f"{payload.n_species:,}"),
        ("Total individuals", f"{payload.n_individuals:,}"),
    ]
    dist_rows: List[Tuple[str, str]] = [
        ("Kilometers traveled", f"{payload.total_km:,.2f}"),
        ("Parkruns (5 km)", f"{payload.parkruns:,.2f}"),
        ("Marathons (42.195 km)", f"{payload.marathons:,.2f}"),
        ("Longest Flight (4BBRW)", f"{payload.times_godwit:,.2f}"),
        ("Times around the equator", f"{payload.times_equator:,.2f}"),
    ]
    time_rows: List[Tuple[str, str]] = [
        ("Total minutes", f"{payload.total_minutes:,.2f}"),
        ("Total hours", f"{payload.total_hours:,.2f}"),
        ("Total days", f"{payload.total_days_dec:,.2f}"),
        ("Months", f"{payload.total_months:,.2f}"),
        ("Total years", f"{payload.total_years:,.2f}"),
        ("Days with a checklist", f"{payload.n_days_with_checklist:,}"),
    ]
    others_rows: List[Tuple[str, str]] = [
        ("Shared checklists", f"{payload.n_shared:,}"),
        ("Minutes eBirding with others", f"{payload.shared_minutes:,.0f}"),
        ("Hours eBirding with others", f"{payload.shared_hours:,.2f}"),
        ("Days birding with others", f"{payload.n_days_birding_with_others:,}"),
    ]
    streak_rows: List[Tuple[str, str]] = [
        ("Longest streak (consecutive days)", str(payload.streak)),
        ("Start date", streak_start_date_cell),
        ("Start location", streak_start_loc_cell),
        ("End date", streak_end_date_cell),
        ("End location", streak_end_loc_cell),
    ]

    return [
        ("Overview", _checklist_stats_tbody_table(overview_rows)),
        (
            "Checklist types",
            _checklist_stats_tbody_table(list(payload.protocol_rows))
            + _checklist_stats_hint_paragraph(incomplete_checklist_hint),
        ),
        ("Total distance", _checklist_stats_tbody_table(dist_rows) + godwit_caption_p),
        (
            "Time eBirded",
            _checklist_stats_tbody_table(time_rows) + _checklist_stats_hint_paragraph(time_hint),
        ),
        ("eBirding with Others", _checklist_stats_tbody_table(others_rows)),
        ("Checklist streak", _checklist_stats_tbody_table(streak_rows)),
    ]


def _checklist_stats_panel_h4_block(title: str, inner_html: str, *, first: bool) -> str:
    mt = "0" if first else "16px"
    title_esc = html_module.escape(title, quote=False)
    return f"""  <h4 style="margin-top:{mt};margin-bottom:8px;padding-bottom:6px;border-bottom:1px solid #e5e7eb;">{title_esc}</h4>
  {inner_html}
"""


def format_checklist_stats_bundle(
    payload: Optional[ChecklistStatsPayload],
    *,
    link_urls_fn: LinkUrlsFn = None,
    scroll_hint: int,
    visible_rows: int,
    country_sort: str = COUNTRY_TAB_SORT_ALPHABETICAL,
) -> Dict[str, Any]:
    """Build the same dict the notebook expects: stats HTML, yearly HTML, rankings sections, incomplete map.

    *payload* is ``None`` when the source DataFrame was empty.
    """
    if payload is None:
        return {
            "stats_html": "<p>No data.</p>",
            "yearly_summary_html": (
                "<p style='font-family:sans-serif;color:#666;padding:16px;'>No yearly data.</p>"
            ),
            "country_summary_html": (
                "<p style='font-family:sans-serif;color:#666;padding:16px;'>No country data.</p>"
            ),
            "rankings_sections_top_n": [],
            "rankings_sections_other": [],
            "incomplete_by_year": {},
        }

    rankings = payload.rankings
    years_list = payload.years_list
    yearly_rows = payload.yearly_rows

    yearly_table_html = ""
    if years_list and yearly_rows:
        def _any_value(vals):
            return any(v != "—" for v in vals)

        static_rows = []
        traveling_detail = []
        stationary_detail = []
        traveling_count_vals = None
        stationary_count_vals = None
        for label, vals in yearly_rows:
            ls = label.strip()
            if ls.startswith("Traveling checklist:"):
                traveling_detail.append((label, vals))
            elif ls.startswith("Stationary checklist:"):
                stationary_detail.append((label, vals))
            else:
                static_rows.append((label, vals))
                if ls.startswith("Traveling checklists") and "Traveling checklist: " not in ls:
                    traveling_count_vals = vals
                if ls.startswith("Stationary checklists") and "Stationary checklist: " not in ls:
                    stationary_count_vals = vals
        visible_static = [(label, vals) for label, vals in static_rows if _any_value(vals)]
        year_headers = "".join(f"<th style='text-align:right;'>{y}</th>" for y in years_list)
        yearly_css = """
    .yearly-maint-section { margin-bottom:8px; border:1px solid #e5e7eb; border-radius:6px; background:#f9fafb; padding:4px 10px; }
    .yearly-maint-section > summary { font-weight:600; padding:6px 0; color:#374151; cursor:pointer; }
"""
        _yearly_comment_style = "margin:4px 0 8px;color:#6b7280;font-size:12px;line-height:1.5;"
        _traveling_comment = "Incomplete checklists not counted."
        _stationary_comment = "Incomplete checklists not counted."
        _traveling_order = [
            "Total distance (km)",
            "Average distance (km)",
            "Total hours",
            "Average minutes",
            "Average species",
            "Average individuals",
        ]
        _stationary_order = ["Total hours", "Average minutes", "Average species", "Average individuals"]

        def _short_name(full_label, prefix):
            name = full_label.strip()
            if name.startswith(prefix):
                name = name[len(prefix) :].strip()
            if " <span" in name:
                name = name.split(" <span")[0].strip()
            return name or full_label

        def _ordered_detail_rows(detail_rows, order_list, prefix):
            by_suffix = {}
            for label, vals in detail_rows:
                short = _short_name(label, prefix)
                by_suffix[short] = vals
            return [(name, by_suffix.get(name, ["—"] * len(years_list))) for name in order_list if name in by_suffix]

        parts = []
        if visible_static:
            body_rows = "".join(
                f"<tr><td>{label}</td>" + "".join(f"<td style='text-align:right;'>{v}</td>" for v in vals) + "</tr>"
                for label, vals in visible_static
            )
            parts.append(f"""
  <h4 style="margin-top:24px;margin-bottom:8px;padding-bottom:6px;border-bottom:1px solid #e5e7eb;">Yearly Summary Statistics</h4>
  <div style="overflow-x:auto;">
  <table class="stats-tbl" style="min-width:400px;">
    <thead><tr><th>Statistic</th>{year_headers}</tr></thead>
    <tbody>{body_rows}</tbody>
  </table>
  </div>""")
        elif traveling_detail or stationary_detail:
            parts.append(
                '\n  <h4 style="margin-top:24px;margin-bottom:8px;padding-bottom:6px;border-bottom:1px solid #e5e7eb;">Yearly Summary Statistics</h4>'
            )

        def _yearly_accordion_body(comment_text, total_checklists_vals, ordered_detail_rows):
            rows_html = []
            if total_checklists_vals is not None:
                rows_html.append(
                    "<tr><td>Total checklists</td>"
                    + "".join(f"<td style='text-align:right;'>{v}</td>" for v in total_checklists_vals)
                    + "</tr>"
                )
            for name, vals in ordered_detail_rows:
                rows_html.append(
                    f"<tr><td>{name}</td>" + "".join(f"<td style='text-align:right;'>{v}</td>" for v in vals) + "</tr>"
                )
            if not rows_html:
                return ""
            body = "\n    ".join(rows_html)
            return f"""  <p style="{_yearly_comment_style}">{comment_text}</p>
  <div style="overflow-x:auto;">
  <table class="stats-tbl" style="min-width:400px;">
    <thead><tr><th>Statistic</th>{year_headers}</tr></thead>
    <tbody>
    {body}
    </tbody>
  </table>
  </div>"""

        if traveling_detail or traveling_count_vals is not None:
            ordered_trav = _ordered_detail_rows(traveling_detail, _traveling_order, "Traveling checklist:")
            if ordered_trav or traveling_count_vals is not None:
                body = _yearly_accordion_body(_traveling_comment, traveling_count_vals, ordered_trav)
                if body:
                    parts.append(f"""
  <details class="yearly-maint-section">
    <summary>Traveling checklists</summary>
{body}  </details>""")
        if stationary_detail or stationary_count_vals is not None:
            ordered_stat = _ordered_detail_rows(stationary_detail, _stationary_order, "Stationary checklist:")
            if ordered_stat or stationary_count_vals is not None:
                body = _yearly_accordion_body(_stationary_comment, stationary_count_vals, ordered_stat)
                if body:
                    parts.append(f"""
  <details class="yearly-maint-section">
    <summary>Stationary checklists</summary>
{body}  </details>""")
        if parts:
            yearly_table_html = f"""
  <style>{yearly_css}</style>
  <div style="width:100%;max-width:1400px;padding:0 clamp(16px,3vw,32px) 24px;box-sizing:border-box;">
{"".join(parts)}
  </div>"""

    sections = checklist_stats_streamlit_tab_sections_html(payload)
    left_col = (
        _checklist_stats_panel_h4_block(sections[0][0], sections[0][1], first=True)
        + _checklist_stats_panel_h4_block(sections[1][0], sections[1][1], first=False)
        + _checklist_stats_panel_h4_block(sections[2][0], sections[2][1], first=False)
    )
    right_col = (
        _checklist_stats_panel_h4_block(sections[3][0], sections[3][1], first=True)
        + _checklist_stats_panel_h4_block(sections[4][0], sections[4][1], first=False)
        + _checklist_stats_panel_h4_block(sections[5][0], sections[5][1], first=False)
    )

    rankings_sections_top_n = [
        (
            "Checklist: Longest by time",
            rankings_table_location_5col(
                "Checklist: Longest by time",
                ["Location", "State", "Country", "Visited date/time", "Time"],
                rankings["time"],
                include_heading=False,
                scroll_hint=scroll_hint,
                visible_rows=visible_rows,
            ),
        ),
        (
            "Checklist: Longest by distance",
            rankings_table_location_5col(
                "Checklist: Longest by distance",
                ["Location", "State", "Country", "Visited date/time", "Distance"],
                rankings["dist"],
                include_heading=False,
                scroll_hint=scroll_hint,
                visible_rows=visible_rows,
            ),
        ),
        (
            "Checklist: Most species",
            rankings_table_location_5col(
                "Checklist: Most species",
                ["Location", "State", "Country", "Visited date/time", "Species"],
                rankings["species"],
                include_heading=False,
                scroll_hint=scroll_hint,
                visible_rows=visible_rows,
            ),
        ),
        (
            "Checklist: Most individuals",
            rankings_table_location_5col(
                "Checklist: Most individuals",
                ["Location", "State", "Country", "Visited date/time", "Count"],
                rankings["individuals"],
                include_heading=False,
                scroll_hint=scroll_hint,
                visible_rows=visible_rows,
            ),
        ),
        (
            "Location: Most species",
            rankings_table_location_5col(
                "Location: Most species",
                ["Location", "State", "Country", "Checklists", "Species"],
                rankings["species_loc"],
                include_heading=False,
                scroll_hint=scroll_hint,
                visible_rows=visible_rows,
            ),
        ),
        (
            "Location: Most individuals",
            rankings_table_location_5col(
                "Location: Most individuals",
                ["Location", "State", "Country", "Checklists", "Count"],
                rankings["individuals_loc"],
                include_heading=False,
                scroll_hint=scroll_hint,
                visible_rows=visible_rows,
            ),
        ),
        (
            "Location: Most visited",
            rankings_visited_table(
                rankings["visited"],
                include_heading=False,
                scroll_hint=scroll_hint,
                visible_rows=visible_rows,
            ),
        ),
    ]
    rankings_sections_other = [
        (
            "Species: Most individuals",
            rankings_table_with_rank(
                "Species: Most individuals",
                ["Species", "", "Individuals"],
                rankings["species_individuals"],
                include_heading=False,
                scroll_hint=scroll_hint,
                visible_rows=visible_rows,
                link_urls_fn=link_urls_fn,
                add_lifelist_link=False,
            ),
        ),
        (
            "Species: Most checklists",
            rankings_table_with_rank(
                "Species: Most checklists",
                ["Species", "", "Checklists"],
                rankings["species_checklists"],
                include_heading=False,
                scroll_hint=scroll_hint,
                visible_rows=visible_rows,
                link_urls_fn=link_urls_fn,
                add_lifelist_link=True,
            ),
        ),
        (
            "Species: Subspecies occurrence",
            rankings_subspecies_hierarchical_table(
                "Species: Subspecies occurrence",
                rankings["subspecies"],
                include_heading=False,
                scroll_hint=scroll_hint,
                visible_rows=visible_rows,
                lifelist_url_fn=(lambda name: link_urls_fn(name)[1] if link_urls_fn else None),
                species_url_fn=(lambda name: link_urls_fn(name)[0] if link_urls_fn else None),
            ),
        ),
        (
            "Species: Seen only once",
            rankings_seen_once_table(
                rankings["seen_once"],
                include_heading=False,
                scroll_hint=scroll_hint,
                visible_rows=visible_rows,
                link_urls_fn=link_urls_fn,
            ),
        ),
    ]

    stats_html = f"""
<style>{CHECKLIST_STATS_TABLE_CSS}</style>
<div class="stats-layout" style="font-family:sans-serif;font-size:13px;line-height:1.6;width:100%;max-width:1400px;display:flex;flex-wrap:wrap;gap:clamp(24px,4vw,48px);justify-content:flex-start;padding:0 clamp(16px,3vw,32px);box-sizing:border-box;">
  <div class="stats-col" style="flex:1 1 320px;min-width:280px;max-width:480px;padding:16px;box-sizing:border-box;">{left_col}</div>
  <div class="stats-col" style="flex:1 1 320px;min-width:280px;max-width:480px;padding:16px;box-sizing:border-box;">{right_col}</div>
</div>
"""
    yearly_summary_html = (
        f"<style>{CHECKLIST_STATS_TABLE_CSS}</style>{yearly_table_html}"
        if yearly_table_html
        else "<p style='font-family:sans-serif;color:#666;padding:16px;'>No yearly data.</p>"
    )
    country_summary_inner = _format_country_summary_html(
        payload.country_sections,
        country_sort=country_sort,
    )
    country_summary_html = f"<style>{CHECKLIST_STATS_TABLE_CSS}</style>{country_summary_inner}"
    return {
        "stats_html": stats_html,
        "yearly_summary_html": yearly_summary_html,
        "country_summary_html": country_summary_html,
        "rankings_sections_top_n": rankings_sections_top_n,
        "rankings_sections_other": rankings_sections_other,
        "incomplete_by_year": payload.incomplete_by_year,
    }


_RANKINGS_HEADING_STYLE_PRIMARY = (
    "font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif;"
    "font-size:15px;font-weight:600;margin:0 0 8px;padding:0;color:#111827;"
)


def format_rankings_tab_html(
    sections_top_n: List[Tuple[str, str]],
    sections_other: List[Tuple[str, str]],
    *,
    top_n_limit: int,
) -> str:
    """Wrap Rankings tab sections in accordions (same styling as Maintenance tab). Refs #69."""

    def _details_block(title: str, html_body: str) -> str:
        return f"""
<details class="maint-section">
  <summary>{title}</summary>
  <div style="margin-top:8px;">
{html_body}
  </div>
</details>"""

    top_html = "".join(_details_block(title, html) for title, html in sections_top_n)
    other_html = "".join(_details_block(title, html) for title, html in sections_other)
    heading_second = (
        "margin-top:24px;"
        f"{_RANKINGS_HEADING_STYLE_PRIMARY.split('margin:0 0 8px;', 1)[0]}"
    )

    return f"""
<style>
.maint-section {{
  margin-bottom:8px;
  border:1px solid #e5e7eb;
  border-radius:6px;
  background:#f9fafb;
  padding:4px 10px;
}}
.maint-section > summary {{
  font-weight:600;
  padding:6px 0;
  color:#374151;
  cursor:pointer;
}}
</style>
<div style="font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif;font-size:13px;line-height:1.6;width:100%;max-width:1400px;padding:0 clamp(16px,3vw,32px);box-sizing:border-box;">
  <h3 style="{_RANKINGS_HEADING_STYLE_PRIMARY}">Top {top_n_limit}</h3>
  {top_html}
  <h3 style="{heading_second}">Interesting Lists</h3>
  {other_html}
</div>
"""
