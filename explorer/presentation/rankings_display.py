"""
HTML builders for rankings tables in the Personal eBird Explorer.

Scroll-wrapper and table builders used when rendering the Checklist Statistics
rankings sections. Uses region_display for country/state names.
Cell/row helpers: :mod:`explorer.presentation.stats_html_helpers` (refs #117).
"""

from explorer.presentation.stats_html_helpers import (
    METRIC_CELL_STYLE,
    a_external,
    esc_attr,
    esc_text,
    td_html,
    td_plain,
    th_plain,
    tr_row,
)

# Middle column in ``rankings_table_with_rank`` was historically unused (stats emit "—"); omit when safe.
_PLACEHOLDER_MIDDLE_VALUES = frozenset({"", "—", "–", "-"})


def _td_trusted_html(cell: object) -> str:
    """``<td>`` for cell content already HTML from stats formatters (links, etc.) (refs #117)."""
    return td_html(str(cell))


def _region_country(code):
    """Lazy import avoids ``explorer.core`` ↔ ``rankings_display`` circular import (refs #117)."""
    from explorer.core.region_display import country_for_display as _cfd

    return _cfd(code)


def _region_state(country_code, state_code):
    from explorer.core.region_display import state_for_display as _sfd

    return _sfd(country_code, state_code)


def _omit_placeholder_middle_column(headers_3col, rows_3col) -> bool:
    """True when middle header is blank and every row's middle cell is a placeholder (refs #81)."""
    if len(headers_3col) < 3:
        return False
    if str(headers_3col[1]).strip():
        return False
    for r in rows_3col:
        if len(r) < 2:
            return False
        mid = str(r[1]).strip()
        if mid not in _PLACEHOLDER_MIDDLE_VALUES:
            return False
    return True


def rankings_scroll_wrapper(table_html, scroll_hint, visible_rows):
    """Wrap table HTML in scrollable div with shading hints. Pure CSS (ipywidgets HTML does not run scripts).

    Top and bottom fades when ``scroll_hint`` is ``"shading"`` or ``"both"``. Padding on
    ``.rankings-scroll-inner`` (CSS) offsets the table slightly so the top gradient is less harsh on
    the header row. Scroll-position–aware shading would need JavaScript (refs #81).
    """
    max_h = visible_rows * 38  # ~38px per row
    shade_css = "position:absolute;left:0;right:0;height:24px;pointer-events:none;z-index:5;"
    top_shade = f'<div class="rankings-scroll-shade-top" style="{shade_css}top:0;background:linear-gradient(to bottom,rgba(255,255,255,0.95),transparent);"></div>'
    bot_shade = f'<div class="rankings-scroll-shade-bot" style="{shade_css}bottom:0;background:linear-gradient(to top,rgba(255,255,255,0.95),transparent);"></div>'
    show_shade = scroll_hint in ("shading", "both")
    shades = (top_shade + bot_shade) if show_shade else ""
    return f"""
<div class="rankings-scroll-wrapper" style="position:relative;">
  <div class="rankings-scroll-inner" style="max-height:{max_h}px;overflow-y:auto;">
    {table_html}
  </div>
  {shades}
</div>"""


def rankings_table(title, headers, rows, include_heading=True, scroll_hint="shading", visible_rows=16):
    """Build a 3-column rankings table with scrollable body."""
    if not rows:
        no_data = "<p style='margin:4px 0;color:#666;'>No data.</p>"
        return f"<h4 style='margin:0 0 8px;'>{esc_text(title)}</h4>{no_data}" if include_heading else no_data
    body = "".join(
        tr_row(
            td_plain(r[0]),
            td_plain(r[1]),
            td_plain(r[2], style=METRIC_CELL_STYLE),
        )
        for r in rows
    )
    head = "".join(th_plain(h) for h in headers)
    tbl = f"<table class='stats-tbl rankings-tbl'><thead><tr>{head}</tr></thead><tbody>{body}</tbody></table>"
    scroll_wrapper = rankings_scroll_wrapper(tbl, scroll_hint, visible_rows)
    content = f"<h4 style='margin:0 0 8px;'>{esc_text(title)}</h4>{scroll_wrapper}" if include_heading else scroll_wrapper
    return content


def rankings_not_seen_recently_table(
    title,
    headers,
    rows,
    include_heading=True,
    scroll_hint="shading",
    visible_rows=16,
    link_urls_fn=None,
):
    """3-column table: Species (linked) | Last seen (HTML) | Days since (refs #106)."""
    if not rows:
        no_data = "<p style='margin:4px 0;color:#666;'>No data.</p>"
        return f"<h4 style='margin:0 0 8px;'>{esc_text(title)}</h4>{no_data}" if include_heading else no_data
    rows_html = []
    for r in rows:
        species_url = link_urls_fn(r[0])[0] if link_urls_fn else None
        species_cell = (
            td_html(a_external(species_url, r[0], rel="noopener"))
            if species_url
            else td_plain(r[0])
        )
        rows_html.append(
            tr_row(
                species_cell,
                _td_trusted_html(r[1]),
                td_plain(r[2], style=METRIC_CELL_STYLE),
            )
        )
    body = "".join(rows_html)
    head = "".join(th_plain(h) for h in headers)
    tbl = (
        f"<table class='stats-tbl rankings-tbl'>"
        f"<thead><tr>{head}</tr></thead>"
        f"<tbody>{body}</tbody></table>"
    )
    scroll_wrapper = rankings_scroll_wrapper(tbl, scroll_hint, visible_rows)
    content = f"<h4 style='margin:0 0 8px;'>{esc_text(title)}</h4>{scroll_wrapper}" if include_heading else scroll_wrapper
    return content


def rankings_table_location_5col(
    title,
    headers_5,
    rows,
    include_heading=True,
    scroll_hint="shading",
    visible_rows=16,
    *,
    leading_rank_column=False,
):
    """5-column table: Location, State, Country, then two more (Top Lists tab).

    *leading_rank_column*: prepend Rank (1..n) with soft accent styling (refs #83).
    """
    if not rows:
        no_data = "<p style='margin:4px 0;color:#666;'>No data.</p>"
        return f"<h4 style='margin:0 0 8px;'>{esc_text(title)}</h4>{no_data}" if include_heading else no_data
    tbl_classes = "stats-tbl rankings-tbl location-cols-tbl"
    if leading_rank_column:
        tbl_classes += " rank-col-soft-accent"
    if leading_rank_column:
        body = "".join(
            tr_row(
                td_plain(i),
                _td_trusted_html(r[0]),
                td_plain(_region_state(r[2], r[1])),
                td_plain(_region_country(r[2])),
                _td_trusted_html(r[3]),
                td_html(str(r[4]), style=METRIC_CELL_STYLE),
            )
            for i, r in enumerate(rows, start=1)
        )
        head_cells = "".join(th_plain(h) for h in ("Rank", *headers_5))
    else:
        body = "".join(
            tr_row(
                _td_trusted_html(r[0]),
                td_plain(_region_state(r[2], r[1])),
                td_plain(_region_country(r[2])),
                _td_trusted_html(r[3]),
                td_html(str(r[4]), style=METRIC_CELL_STYLE),
            )
            for r in rows
        )
        head_cells = "".join(th_plain(h) for h in headers_5)
    tbl = (
        f"<table class='{tbl_classes}'>"
        f"<thead><tr>{head_cells}</tr></thead><tbody>{body}</tbody></table>"
    )
    scroll_wrapper = rankings_scroll_wrapper(tbl, scroll_hint, visible_rows)
    content = f"<h4 style='margin:0 0 8px;'>{esc_text(title)}</h4>{scroll_wrapper}" if include_heading else scroll_wrapper
    return content


def rankings_table_with_rank(
    title,
    headers_3col,
    rows_3col,
    include_heading=True,
    scroll_hint="shading",
    visible_rows=16,
    species_url_fn=None,
    lifelist_url_fn=None,
    link_urls_fn=None,
    add_lifelist_link=False,
    *,
    rank_column_soft_accent=False,
):
    """Build a rankings table with Rank as first column (1..n). rows_3col are (col1, col2, col3).

    If the middle header is blank and every middle cell is a placeholder (e.g. "—"), that column is
    omitted so only Rank + two data columns remain (refs #81).

    Optional link helpers (refs #56). Prefer link_urls_fn(common_name) -> (species_url, lifelist_url)
    so one lookup per row; when provided, add_lifelist_link controls whether the last column gets the
    lifelist link. Fallback: species_url_fn and lifelist_url_fn (two lookups per row when both used).

    *rank_column_soft_accent*: add a class so scoped CSS can style the rank column (mock-up, refs #83).
    """
    if not rows_3col:
        no_data = "<p style='margin:4px 0;color:#666;'>No data.</p>"
        return f"<h4 style='margin:0 0 8px;'>{esc_text(title)}</h4>{no_data}" if include_heading else no_data
    omit_middle = _omit_placeholder_middle_column(headers_3col, rows_3col)
    rows_html = []
    for i, r in enumerate(rows_3col, start=1):
        species_url = None
        lifelist_url = None
        if link_urls_fn:
            species_url, lifelist_url = link_urls_fn(r[0])
        else:
            if species_url_fn:
                species_url = species_url_fn(r[0])
            if lifelist_url_fn:
                lifelist_url = lifelist_url_fn(r[0])
        cell1 = (
            td_html(a_external(species_url, r[0], rel="noopener"))
            if species_url
            else td_plain(r[0])
        )
        cell3_raw = str(r[2])
        if lifelist_url and (add_lifelist_link or lifelist_url_fn):
            cell3 = td_html(a_external(lifelist_url, cell3_raw, rel="noopener"), style=METRIC_CELL_STYLE)
        else:
            cell3 = td_plain(cell3_raw, style=METRIC_CELL_STYLE)
        if omit_middle:
            rows_html.append(tr_row(td_plain(i), cell1, cell3))
        else:
            rows_html.append(tr_row(td_plain(i), cell1, _td_trusted_html(r[1]), cell3))
    body = "".join(rows_html)
    if omit_middle:
        thead = "<thead><tr>" + "".join(
            th_plain(h) for h in ("Rank", headers_3col[0], headers_3col[2])
        ) + "</tr></thead>"
    else:
        thead = "<thead><tr>" + "".join(
            th_plain(h) for h in ("Rank", headers_3col[0], headers_3col[1], headers_3col[2])
        ) + "</tr></thead>"
    tbl_classes = "stats-tbl rankings-tbl rank-tbl"
    if rank_column_soft_accent:
        tbl_classes += " rank-col-soft-accent"
    tbl = f"<table class='{tbl_classes}'>{thead}<tbody>{body}</tbody></table>"
    scroll_wrapper = rankings_scroll_wrapper(tbl, scroll_hint, visible_rows)
    content = f"<h4 style='margin:0 0 8px;'>{esc_text(title)}</h4>{scroll_wrapper}" if include_heading else scroll_wrapper
    return content


def rankings_visited_table(
    rows,
    include_heading=True,
    scroll_hint="shading",
    visible_rows=16,
    *,
    leading_rank_column=False,
):
    """Location | State | Country | First visit | Last visit | Visits; optional leading Rank (refs #83)."""
    if not rows:
        no_data = "<p style='margin:4px 0;color:#666;'>No data.</p>"
        return f"<h4 style='margin:0 0 8px;'>Most visited locations</h4>{no_data}" if include_heading else no_data
    tbl_classes = "stats-tbl rankings-tbl location-cols-tbl"
    if leading_rank_column:
        tbl_classes += " rank-col-soft-accent"
    if leading_rank_column:
        body = "".join(
            tr_row(
                td_plain(i),
                _td_trusted_html(r[0]),
                td_plain(_region_state(r[2], r[1])),
                td_plain(_region_country(r[2])),
                _td_trusted_html(r[3]),
                _td_trusted_html(r[4]),
                td_plain(r[5], style=METRIC_CELL_STYLE),
            )
            for i, r in enumerate(rows, start=1)
        )
        thead = "<thead><tr>" + "".join(
            th_plain(h)
            for h in (
                "Rank",
                "Location",
                "State",
                "Country",
                "First visit",
                "Last visit",
                "Visits",
            )
        ) + "</tr></thead>"
    else:
        body = "".join(
            tr_row(
                _td_trusted_html(r[0]),
                td_plain(_region_state(r[2], r[1])),
                td_plain(_region_country(r[2])),
                _td_trusted_html(r[3]),
                _td_trusted_html(r[4]),
                td_plain(r[5], style=METRIC_CELL_STYLE),
            )
            for r in rows
        )
        thead = "<thead><tr>" + "".join(
            th_plain(h)
            for h in ("Location", "State", "Country", "First visit", "Last visit", "Visits")
        ) + "</tr></thead>"
    tbl = (
        f"<table class='{tbl_classes}'>"
        f"{thead}<tbody>{body}</tbody></table>"
    )
    scroll_wrapper = rankings_scroll_wrapper(tbl, scroll_hint, visible_rows)
    return f"<h4 style='margin:0 0 8px;'>Most visited locations</h4>{scroll_wrapper}" if include_heading else scroll_wrapper


def rankings_seen_once_table(
    rows,
    include_heading=True,
    scroll_hint="shading",
    visible_rows=16,
    species_url_fn=None,
    link_urls_fn=None,
):
    """6-column table: Species | Location | State | Country | Visited date/time | Count.

    Optional link (refs #56): link_urls_fn(common_name) -> (species_url, lifelist_url) uses first
    element (one lookup per row). Fallback: species_url_fn(common_name) -> url.
    """
    if not rows:
        no_data = "<p style='margin:4px 0;color:#666;'>No data.</p>"
        return f"<h4 style='margin:0 0 8px;'>Species: Seen only once</h4>{no_data}" if include_heading else no_data
    rows_html = []
    for r in rows:
        if link_urls_fn:
            species_url = link_urls_fn(r[0])[0]
        elif species_url_fn:
            species_url = species_url_fn(r[0])
        else:
            species_url = None
        species_cell = (
            td_html(a_external(species_url, r[0], rel="noopener"))
            if species_url
            else td_plain(r[0])
        )
        rows_html.append(
            tr_row(
                species_cell,
                _td_trusted_html(r[1]),
                td_plain(_region_state(r[3], r[2])),
                td_plain(_region_country(r[3])),
                _td_trusted_html(r[4]),
                td_plain(r[5], style=METRIC_CELL_STYLE),
            )
        )
    body = "".join(rows_html)
    tbl = (
        "<table class='stats-tbl rankings-tbl seen-once-tbl'>"
        "<thead><tr>"
        + "".join(
            th_plain(h)
            for h in (
                "Species",
                "Location",
                "State",
                "Country",
                "Visited date/time",
                "Count",
            )
        )
        + "</tr></thead><tbody>"
        f"{body}</tbody></table>"
    )
    scroll_wrapper = rankings_scroll_wrapper(tbl, scroll_hint, visible_rows)
    return scroll_wrapper


def rankings_high_counts_table(
    rows,
    include_heading=True,
    scroll_hint="shading",
    visible_rows=16,
    link_urls_fn=None,
    sort_mode="total_count",
    tie_break="last",
):
    """6-column table: Species | Location | State | Country | High-count checklist | Count."""
    if not rows:
        no_data = "<p style='margin:4px 0;color:#666;'>No data.</p>"
        return f"<h4 style='margin:0 0 8px;'>Species: High counts</h4>{no_data}" if include_heading else no_data
    winner = "Most recent winner" if str(tie_break).strip().lower() == "last" else "Earliest winner"
    order_label = "Sorted by count" if str(sort_mode).strip().lower() == "total_count" else "Sorted alphabetically"
    rows_html = []
    for r in rows:
        species_url = link_urls_fn(r[0])[0] if link_urls_fn else None
        species_cell = (
            td_html(a_external(species_url, r[0], rel="noopener"))
            if species_url
            else td_plain(r[0])
        )
        rows_html.append(
            tr_row(
                species_cell,
                _td_trusted_html(r[1]),
                td_plain(_region_state(r[3], r[2])),
                td_plain(_region_country(r[3])),
                _td_trusted_html(r[4]),
                td_plain(r[5], style=METRIC_CELL_STYLE),
            )
        )
    body = "".join(rows_html)
    tbl = (
        "<table class='stats-tbl rankings-tbl seen-once-tbl'>"
        "<thead><tr>"
        + "".join(
            th_plain(h)
            for h in (
                "Species",
                "Location",
                "State",
                "Country",
                "High-count checklist",
                "Count",
            )
        )
        + "</tr></thead><tbody>"
        f"{body}</tbody></table>"
    )
    caption = (
        f"<p style='margin:4px 0;color:#6b7280;font-size:12px;'>{esc_text(order_label)}. "
        f"{esc_text(winner)} when count ties.</p>"
    )
    scroll_wrapper = rankings_scroll_wrapper(tbl, scroll_hint, visible_rows)
    content = f"{caption}{scroll_wrapper}"
    return f"<h4 style='margin:0 0 8px;'>Species: High counts</h4>{content}" if include_heading else content


def rankings_subspecies_hierarchical_table(
    title,
    species_blocks,
    include_heading=True,
    scroll_hint="shading",
    visible_rows=16,
    lifelist_url_fn=None,
    species_url_fn=None,
):
    """Render hierarchical subspecies occurrence as accordion-style HTML.

    *species_blocks* is the structure returned by stats.rankings_subspecies_hierarchical.
    """
    if not species_blocks:
        no_data = "<p style='margin:4px 0;color:#666;'>No data.</p>"
        return f"<h4 style='margin:0 0 8px;'>{esc_text(title)}</h4>{no_data}" if include_heading else no_data

    rows_html = []
    for block in species_blocks:
        species_common = block.get("species_common", "")
        species_sci = block.get("species_scientific", "")
        total = block.get("total_individuals", 0)
        species_only = block.get("species_only_individuals", 0)
        subspecies_total = block.get("subspecies_total_individuals", 0)
        frac = block.get("subspecies_fraction", None)
        lifelist_url = lifelist_url_fn(species_common) if lifelist_url_fn else None
        species_url = species_url_fn(species_common) if species_url_fn else None
        total_count = f"{total:,}"
        if lifelist_url:
            total_count_html = a_external(lifelist_url, total_count, rel="noopener")
        else:
            total_count_html = esc_text(total_count)
        link_suffix = ""
        if species_url:
            link_suffix = (
                " "
                f' <a href="{esc_attr(species_url)}" target="_blank" rel="noopener" '
                'style="color:inherit;text-decoration:none;">⧉</a>'
            )
        if frac is not None:
            pct = f"{frac * 100:.0f}% subspecies identified"
            total_line = f"{total_count_html} ({pct}){link_suffix}"
        else:
            total_line = f"{total_count_html}{link_suffix}"

        header_parts = [esc_text(str(species_common))]
        if species_sci:
            esc_sci = esc_text(str(species_sci))
            header_parts.append(f'<span class="subspecies-sci-secondary">({esc_sci})</span>')
        header_text = " ".join(header_parts)

        subspecies_rows = []
        for sub in block.get("subspecies", []):
            label = sub.get("subspecies_common", "")
            sub_sci = sub.get("subspecies_scientific", "")
            count = sub.get("individuals", 0)
            label_raw = label or sub.get("subspecies_common_full", "") or ""
            label_html = esc_text(str(label_raw))
            sci_html = (
                f'<span class="subspecies-sci-secondary">{esc_text(str(sub_sci))}</span>'
                if sub_sci
                else ""
            )
            subspecies_rows.append(
                tr_row(
                    td_html(label_html),
                    td_html(sci_html),
                    td_plain(f"{count:,}", style=METRIC_CELL_STYLE),
                )
            )
        subspecies_table = (
            "<table class='stats-tbl rankings-tbl subspecies-tbl'>"
            "<thead><tr>"
            "<th>Subspecies</th><th>Scientific name</th><th>Individuals</th>"
            "</tr></thead><tbody>"
            + "".join(subspecies_rows)
            + "</tbody></table>"
        )

        body_html = (
            f"<p style='margin:4px 0 8px;color:#6b7280;font-size:12px;'>"
            f"Total individuals: {total_line}<br>"
            f"Listed as species (no subspecies specified): {species_only:,}<br>"
            f"Individuals with subspecies recorded: {subspecies_total:,}"
            f"</p>"
            f"{subspecies_table}"
        )

        rows_html.append(
            "<details class='subspecies-section'>"
            f"<summary>{header_text} — Total: {total:,}</summary>"
            f"<div class='subspecies-body'>{body_html}</div>"
            "</details>"
        )

    all_html = (
        "<div class='subspecies-accordion'>"
        + "".join(rows_html)
        + "</div>"
    )

    wrapped = rankings_scroll_wrapper(all_html, scroll_hint, visible_rows)

    css = """
/* Typography inherits from parent (e.g. Streamlit ``.streamlit-checklist-html-ab``); do not override
   font-size here — that mismatched other rankings tables (refs #81). */
.subspecies-section {
  margin-bottom: 6px;
  border: 1px solid #e5e7eb;
  border-radius: 6px;
  background: #f9fafb;
  padding: 4px 10px;
}
.subspecies-section > summary {
  cursor: pointer;
  font-weight: 600;
  padding: 4px 0;
  color: #374151;
}
.subspecies-body {
  margin-top: 6px;
}
.subspecies-tbl {
  margin-top: 6px;
}
"""
    content = f"<style>{css}</style>{wrapped}"
    if include_heading:
        return f"<h4 style='margin:0 0 8px;'>{esc_text(title)}</h4>{content}"
    return content
