"""
HTML builders for rankings tables in the Personal eBird Explorer.

Scroll-wrapper and table builders used when rendering the Checklist Statistics
rankings sections. Uses region_display for country/state names.
"""

import html as _html_module

from personal_ebird_explorer.region_display import country_for_display, state_for_display

# Middle column in ``rankings_table_with_rank`` was historically unused (stats emit "—"); omit when safe.
_PLACEHOLDER_MIDDLE_VALUES = frozenset({"", "—", "–", "-"})


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
        return f"<h4 style='margin:0 0 8px;'>{title}</h4>{no_data}" if include_heading else no_data
    body = "".join(
        f"<tr><td>{r[0]}</td><td>{r[1]}</td><td style='text-align:right;font-weight:600;'>{r[2]}</td></tr>"
        for r in rows
    )
    tbl = f"<table class='stats-tbl rankings-tbl'><thead><tr><th>{headers[0]}</th><th>{headers[1]}</th><th>{headers[2]}</th></tr></thead><tbody>{body}</tbody></table>"
    scroll_wrapper = rankings_scroll_wrapper(tbl, scroll_hint, visible_rows)
    content = f"<h4 style='margin:0 0 8px;'>{title}</h4>{scroll_wrapper}" if include_heading else scroll_wrapper
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
        return f"<h4 style='margin:0 0 8px;'>{title}</h4>{no_data}" if include_heading else no_data
    rows_html = []
    for r in rows:
        species_esc = _html_module.escape(str(r[0]), quote=True)
        species_url = link_urls_fn(r[0])[0] if link_urls_fn else None
        species_cell = (
            f'<a href="{_html_module.escape(species_url, quote=True)}" target="_blank" rel="noopener">{species_esc}</a>'
            if species_url
            else species_esc
        )
        rows_html.append(
            f"<tr><td>{species_cell}</td><td>{r[1]}</td>"
            f"<td style='text-align:right;font-weight:600;'>{r[2]}</td></tr>"
        )
    body = "".join(rows_html)
    tbl = (
        f"<table class='stats-tbl rankings-tbl'>"
        f"<thead><tr><th>{headers[0]}</th><th>{headers[1]}</th><th>{headers[2]}</th></tr></thead>"
        f"<tbody>{body}</tbody></table>"
    )
    scroll_wrapper = rankings_scroll_wrapper(tbl, scroll_hint, visible_rows)
    content = f"<h4 style='margin:0 0 8px;'>{title}</h4>{scroll_wrapper}" if include_heading else scroll_wrapper
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
        return f"<h4 style='margin:0 0 8px;'>{title}</h4>{no_data}" if include_heading else no_data
    tbl_classes = "stats-tbl rankings-tbl location-cols-tbl"
    if leading_rank_column:
        tbl_classes += " rank-col-soft-accent"
    if leading_rank_column:
        body = "".join(
            f"<tr><td>{i}</td><td>{r[0]}</td><td>{state_for_display(r[2], r[1])}</td><td>{country_for_display(r[2])}</td>"
            f"<td>{r[3]}</td><td style='text-align:right;font-weight:600;'>{r[4]}</td></tr>"
            for i, r in enumerate(rows, start=1)
        )
        head_cells = "".join(f"<th>{hdr}</th>" for hdr in ("Rank", *headers_5))
    else:
        body = "".join(
            f"<tr><td>{r[0]}</td><td>{state_for_display(r[2], r[1])}</td><td>{country_for_display(r[2])}</td>"
            f"<td>{r[3]}</td><td style='text-align:right;font-weight:600;'>{r[4]}</td></tr>"
            for r in rows
        )
        head_cells = "".join(f"<th>{hdr}</th>" for hdr in headers_5)
    tbl = (
        f"<table class='{tbl_classes}'>"
        f"<thead><tr>{head_cells}</tr></thead><tbody>{body}</tbody></table>"
    )
    scroll_wrapper = rankings_scroll_wrapper(tbl, scroll_hint, visible_rows)
    content = f"<h4 style='margin:0 0 8px;'>{title}</h4>{scroll_wrapper}" if include_heading else scroll_wrapper
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
        return f"<h4 style='margin:0 0 8px;'>{title}</h4>{no_data}" if include_heading else no_data
    omit_middle = _omit_placeholder_middle_column(headers_3col, rows_3col)
    rows_html = []
    metric_style = "text-align:right;font-weight:600;"
    for i, r in enumerate(rows_3col, start=1):
        cell1_esc = _html_module.escape(str(r[0]), quote=True)
        species_url = None
        lifelist_url = None
        if link_urls_fn:
            species_url, lifelist_url = link_urls_fn(r[0])
        else:
            if species_url_fn:
                species_url = species_url_fn(r[0])
            if lifelist_url_fn:
                lifelist_url = lifelist_url_fn(r[0])
        cell1 = f'<a href="{_html_module.escape(species_url, quote=True)}" target="_blank" rel="noopener">{cell1_esc}</a>' if species_url else cell1_esc
        cell3 = str(r[2])
        if lifelist_url and (add_lifelist_link or lifelist_url_fn):
            count_esc = _html_module.escape(cell3, quote=True)
            cell3 = f"<a href=\"{_html_module.escape(lifelist_url, quote=True)}\" target=\"_blank\" rel=\"noopener\">{count_esc}</a>"
        if omit_middle:
            rows_html.append(
                f"<tr><td>{i}</td><td>{cell1}</td><td style='{metric_style}'>{cell3}</td></tr>"
            )
        else:
            rows_html.append(
                f"<tr><td>{i}</td><td>{cell1}</td><td>{r[1]}</td><td style='{metric_style}'>{cell3}</td></tr>"
            )
    body = "".join(rows_html)
    if omit_middle:
        thead = (
            f"<thead><tr><th>Rank</th><th>{headers_3col[0]}</th><th>{headers_3col[2]}</th></tr></thead>"
        )
    else:
        thead = (
            f"<thead><tr><th>Rank</th><th>{headers_3col[0]}</th><th>{headers_3col[1]}</th>"
            f"<th>{headers_3col[2]}</th></tr></thead>"
        )
    tbl_classes = "stats-tbl rankings-tbl rank-tbl"
    if rank_column_soft_accent:
        tbl_classes += " rank-col-soft-accent"
    tbl = f"<table class='{tbl_classes}'>{thead}<tbody>{body}</tbody></table>"
    scroll_wrapper = rankings_scroll_wrapper(tbl, scroll_hint, visible_rows)
    content = f"<h4 style='margin:0 0 8px;'>{title}</h4>{scroll_wrapper}" if include_heading else scroll_wrapper
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
            f"<tr><td>{i}</td><td>{r[0]}</td><td>{state_for_display(r[2], r[1])}</td><td>{country_for_display(r[2])}</td>"
            f"<td>{r[3]}</td><td>{r[4]}</td><td style='text-align:right;font-weight:600;'>{r[5]}</td></tr>"
            for i, r in enumerate(rows, start=1)
        )
        thead = (
            "<thead><tr><th>Rank</th><th>Location</th><th>State</th><th>Country</th>"
            "<th>First visit</th><th>Last visit</th><th>Visits</th></tr></thead>"
        )
    else:
        body = "".join(
            f"<tr><td>{r[0]}</td><td>{state_for_display(r[2], r[1])}</td><td>{country_for_display(r[2])}</td>"
            f"<td>{r[3]}</td><td>{r[4]}</td><td style='text-align:right;font-weight:600;'>{r[5]}</td></tr>"
            for r in rows
        )
        thead = (
            "<thead><tr><th>Location</th><th>State</th><th>Country</th>"
            "<th>First visit</th><th>Last visit</th><th>Visits</th></tr></thead>"
        )
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
        species_esc = _html_module.escape(str(r[0]), quote=True)
        if link_urls_fn:
            species_url = link_urls_fn(r[0])[0]
        elif species_url_fn:
            species_url = species_url_fn(r[0])
        else:
            species_url = None
        species_cell = f'<a href="{_html_module.escape(species_url, quote=True)}" target="_blank" rel="noopener">{species_esc}</a>' if species_url else species_esc
        rows_html.append(
            f"<tr><td>{species_cell}</td><td>{r[1]}</td><td>{state_for_display(r[3], r[2])}</td><td>{country_for_display(r[3])}</td><td>{r[4]}</td><td style='text-align:right;font-weight:600;'>{r[5]}</td></tr>"
        )
    body = "".join(rows_html)
    tbl = (
        "<table class='stats-tbl rankings-tbl seen-once-tbl'>"
        "<thead><tr>"
        "<th>Species</th><th>Location</th><th>State</th><th>Country</th><th>Visited date/time</th><th>Count</th>"
        "</tr></thead><tbody>"
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
        species_esc = _html_module.escape(str(r[0]), quote=True)
        species_url = link_urls_fn(r[0])[0] if link_urls_fn else None
        species_cell = (
            f'<a href="{_html_module.escape(species_url, quote=True)}" target="_blank" rel="noopener">{species_esc}</a>'
            if species_url
            else species_esc
        )
        rows_html.append(
            f"<tr><td>{species_cell}</td><td>{r[1]}</td><td>{state_for_display(r[3], r[2])}</td><td>{country_for_display(r[3])}</td><td>{r[4]}</td><td style='text-align:right;font-weight:600;'>{r[5]}</td></tr>"
        )
    body = "".join(rows_html)
    tbl = (
        "<table class='stats-tbl rankings-tbl seen-once-tbl'>"
        "<thead><tr>"
        "<th>Species</th><th>Location</th><th>State</th><th>Country</th><th>High-count checklist</th><th>Count</th>"
        "</tr></thead><tbody>"
        f"{body}</tbody></table>"
    )
    caption = (
        f"<p style='margin:4px 0;color:#6b7280;font-size:12px;'>{order_label}. "
        f"{winner} when count ties.</p>"
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
        return f"<h4 style='margin:0 0 8px;'>{title}</h4>{no_data}" if include_heading else no_data

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
            total_count_html = (
                f"<a href=\"{_html_module.escape(lifelist_url, quote=True)}\" "
                f'target="_blank" rel="noopener">{total_count}</a>'
            )
        else:
            total_count_html = total_count
        link_suffix = ""
        if species_url:
            link_suffix = (
                " "
                f"<a href=\"{_html_module.escape(species_url, quote=True)}\" "
                'target="_blank" rel="noopener" '
                'style="color:inherit;text-decoration:none;">⧉</a>'
            )
        if frac is not None:
            pct = f"{frac * 100:.0f}% subspecies identified"
            total_line = f"{total_count_html} ({pct}){link_suffix}"
        else:
            total_line = f"{total_count_html}{link_suffix}"

        header_parts = [_html_module.escape(str(species_common))]
        if species_sci:
            esc_sci = _html_module.escape(str(species_sci))
            header_parts.append(f'<span class="subspecies-sci-secondary">({esc_sci})</span>')
        header_text = " ".join(header_parts)

        subspecies_rows = []
        for sub in block.get("subspecies", []):
            label = sub.get("subspecies_common", "")
            sub_sci = sub.get("subspecies_scientific", "")
            count = sub.get("individuals", 0)
            label_raw = label or sub.get("subspecies_common_full", "") or ""
            label_html = _html_module.escape(str(label_raw))
            sci_html = (
                f'<span class="subspecies-sci-secondary">{_html_module.escape(str(sub_sci))}</span>'
                if sub_sci
                else ""
            )
            subspecies_rows.append(
                f"<tr><td>{label_html}</td><td>{sci_html}</td>"
                f"<td style='text-align:right;font-weight:600;'>{count:,}</td></tr>"
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

    # Reuse scroll wrapper so long lists remain usable
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
        return f"<h4 style='margin:0 0 8px;'>{title}</h4>{content}"
    return content
