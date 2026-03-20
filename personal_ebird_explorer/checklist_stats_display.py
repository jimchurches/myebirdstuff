"""
HTML rendering for checklist statistics, yearly summary, and rankings sections.

Consumes :class:`ChecklistStatsPayload` from ``checklist_stats_compute`` (refs #68).
"""

from __future__ import annotations

import html as html_module
from typing import Any, Callable, Dict, Optional, Tuple

from personal_ebird_explorer.checklist_stats_compute import ChecklistStatsPayload
from personal_ebird_explorer.rankings_display import (
    rankings_seen_once_table,
    rankings_subspecies_hierarchical_table,
    rankings_table_location_5col,
    rankings_table_with_rank,
    rankings_visited_table,
)

LinkUrlsFn = Optional[Callable[[str], Tuple[Optional[str], Optional[str]]]]


def format_checklist_stats_bundle(
    payload: Optional[ChecklistStatsPayload],
    *,
    link_urls_fn: LinkUrlsFn = None,
    scroll_hint: int,
    visible_rows: int,
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

    _table_css = """
    .stats-info-icon { position:relative; display:inline-block; margin-left:4px; }
    .stats-info-glyph { cursor:help; opacity:0.7; }
    .stats-info-tooltip { position:absolute; bottom:100%; top:auto; margin-bottom:6px; margin-top:0; padding:10px 14px; background:#374151; color:#fff; font-size:12px; font-weight:normal; line-height:1.5; white-space:normal; max-width:min(320px,85vw); min-width:180px; border-radius:6px; box-shadow:0 4px 12px rgba(0,0,0,0.15); opacity:0; visibility:hidden; transition:opacity 0.15s; pointer-events:none; z-index:9999; right:0; left:auto; }
    .stats-info-icon:hover .stats-info-tooltip { opacity:1; visibility:visible; }
    .stats-col:first-child .stats-info-tooltip { right:0; left:auto; }
    .stats-col:last-child .stats-info-tooltip { left:0; right:auto; }
    .stats-tbl-3 th:nth-child(2), .stats-tbl-3 td:nth-child(2) { text-align:center; }
    .rankings-tbl td:first-child { font-weight:normal; }
    """

    def _row(label, value):
        return f"<tr><td>{label}</td><td>{value}</td></tr>"

    def _info_icon(title):
        esc = html_module.escape(title, quote=True)
        return f' <span class="stats-info-icon"><span class="stats-info-glyph">&#9432;</span><span class="stats-info-tooltip">{esc}</span></span>'

    def _table(title, rows, first=False, info_title=None, show_header=False, header_left="", header_right=""):
        info = f" {_info_icon(info_title)}" if info_title else ""
        body = "".join(_row(label, value) for label, value in rows)
        mt = "0" if first else "16px"
        thead = f"<thead><tr><th>{header_left}</th><th>{header_right}</th></tr></thead>" if show_header else ""
        return f"""
  <h4 style="margin-top:{mt};margin-bottom:8px;padding-bottom:6px;border-bottom:1px solid #e5e7eb;">{title}{info}</h4>
  <table class="stats-tbl">
    {thead}<tbody>{body}</tbody>
  </table>"""

    time_hint = (
        "Incidental, historical and other untimed checklists don't count towards total time, "
        "but do count towards Days with a checklist."
    )
    godwit_hint = "4BBRW: Bar-tailed Godwit, Alaska→Tasmania, ~13,560 km nonstop (2022). 11 days without landing."
    godwit_link = '<a href="https://www.audubon.org/news/these-mighty-shorebirds-keep-breaking-flight-records-and-you-can-follow-along" target="_blank">4BBRW</a>'

    streak_start_link = (
        f'<a href="https://ebird.org/checklist/{payload.streak_start_sid}" target="_blank">{payload.streak_start_loc}</a>'
        if payload.streak_start_sid
        else payload.streak_start_loc
    )
    streak_end_link = (
        f'<a href="https://ebird.org/checklist/{payload.streak_end_sid}" target="_blank">{payload.streak_end_loc}</a>'
        if payload.streak_end_sid
        else payload.streak_end_loc
    )

    left_col = f"""
  {_table("Overview", [
    ("Total checklists", f"{payload.n_checklists:,}"),
    ("Total species", f"{payload.n_species:,}"),
    ("Total individuals", f"{payload.n_individuals:,}"),
  ], first=True)}

  {_table("Checklist types", payload.protocol_rows)}

  {_table("Total Distance", [
    ("Kilometers traveled", f"{payload.total_km:,.2f}"),
    ("Parkruns (5 km)", f"{payload.parkruns:,.2f}"),
    ("Marathons (42.195 km)", f"{payload.marathons:,.2f}"),
    (f"Longest Flight ({godwit_link}){_info_icon(godwit_hint)}", f"{payload.times_godwit:,.2f}"),
    ("Times around the equator", f"{payload.times_equator:,.2f}"),
  ])}
"""

    right_col = f"""
  {_table("Time eBirded", [
    ("Total minutes", f"{payload.total_minutes:,.2f}"),
    ("Total hours", f"{payload.total_hours:,.2f}"),
    ("Total days", f"{payload.total_days_dec:,.2f}"),
    ("Months", f"{payload.total_months:,.2f}"),
    ("Total years", f"{payload.total_years:,.2f}"),
    ("Days with a checklist", f"{payload.n_days_with_checklist:,}"),
  ], first=True)}
  <p style="margin:4px 0 0;color:#6b7280;font-size:12px;line-height:1.5;">
    {time_hint}
  </p>

  {_table("eBirding with Others", [
    ("Shared checklists", f"{payload.n_shared:,}"),
    ("Minutes eBirding with others", f"{payload.shared_minutes:,.0f}"),
    ("Hours eBirding with others", f"{payload.shared_hours:,.2f}"),
    ("Days birding with others", f"{payload.n_days_birding_with_others:,}"),
  ])}

  {_table("Checklist Streak", [
    ("Longest streak (consecutive days)", str(payload.streak)),
    ("Start date", payload.streak_start_date),
    ("Start location", streak_start_link),
    ("End date", payload.streak_end_date),
    ("End location", streak_end_link),
  ])}
"""

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
<style>{_table_css}</style>
<div class="stats-layout" style="font-family:sans-serif;font-size:13px;line-height:1.6;width:100%;max-width:1400px;display:flex;flex-wrap:wrap;gap:clamp(24px,4vw,48px);justify-content:flex-start;padding:0 clamp(16px,3vw,32px);box-sizing:border-box;">
  <div class="stats-col" style="flex:1 1 320px;min-width:280px;max-width:480px;padding:16px;box-sizing:border-box;">{left_col}</div>
  <div class="stats-col" style="flex:1 1 320px;min-width:280px;max-width:480px;padding:16px;box-sizing:border-box;">{right_col}</div>
</div>
"""
    yearly_summary_html = (
        f"<style>{_table_css}</style>{yearly_table_html}"
        if yearly_table_html
        else "<p style='font-family:sans-serif;color:#666;padding:16px;'>No yearly data.</p>"
    )
    return {
        "stats_html": stats_html,
        "yearly_summary_html": yearly_summary_html,
        "rankings_sections_top_n": rankings_sections_top_n,
        "rankings_sections_other": rankings_sections_other,
        "incomplete_by_year": payload.incomplete_by_year,
    }
