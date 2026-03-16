"""
HTML builders for rankings tables in the Personal eBird Explorer.

Scroll-wrapper and table builders used when rendering the Checklist Statistics
rankings sections. Uses region_display for country/state names.
"""

from personal_ebird_explorer.region_display import country_for_display, state_for_display


def rankings_scroll_wrapper(table_html, scroll_hint, visible_rows):
    """Wrap table HTML in scrollable div with shading hints. Pure CSS (ipywidgets HTML does not run scripts)."""
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
        f"<tr><td>{r[0]}</td><td>{r[1]}</td><td style='text-align:right;font-weight:bold;'>{r[2]}</td></tr>"
        for r in rows
    )
    tbl = f"<table class='stats-tbl rankings-tbl'><thead><tr><th>{headers[0]}</th><th>{headers[1]}</th><th>{headers[2]}</th></tr></thead><tbody>{body}</tbody></table>"
    scroll_wrapper = rankings_scroll_wrapper(tbl, scroll_hint, visible_rows)
    content = f"<h4 style='margin:0 0 8px;'>{title}</h4>{scroll_wrapper}" if include_heading else scroll_wrapper
    return content


def rankings_table_location_5col(title, headers_5, rows, include_heading=True, scroll_hint="shading", visible_rows=16):
    """5-column table: Location, State, Country, then two more (e.g. Checklists, Species). Last column right-aligned."""
    if not rows:
        no_data = "<p style='margin:4px 0;color:#666;'>No data.</p>"
        return f"<h4 style='margin:0 0 8px;'>{title}</h4>{no_data}" if include_heading else no_data
    body = "".join(
        f"<tr><td>{r[0]}</td><td>{state_for_display(r[2], r[1])}</td><td>{country_for_display(r[2])}</td><td>{r[3]}</td><td style='text-align:right;font-weight:bold;'>{r[4]}</td></tr>"
        for r in rows
    )
    tbl = f"<table class='stats-tbl rankings-tbl location-cols-tbl'><thead><tr><th>{headers_5[0]}</th><th>{headers_5[1]}</th><th>{headers_5[2]}</th><th>{headers_5[3]}</th><th>{headers_5[4]}</th></tr></thead><tbody>{body}</tbody></table>"
    scroll_wrapper = rankings_scroll_wrapper(tbl, scroll_hint, visible_rows)
    content = f"<h4 style='margin:0 0 8px;'>{title}</h4>{scroll_wrapper}" if include_heading else scroll_wrapper
    return content


def rankings_table_with_rank(title, headers_3col, rows_3col, include_heading=True, scroll_hint="shading", visible_rows=16):
    """Build a 4-column rankings table with Rank as first column (1..n). rows_3col are (col1, col2, col3)."""
    if not rows_3col:
        no_data = "<p style='margin:4px 0;color:#666;'>No data.</p>"
        return f"<h4 style='margin:0 0 8px;'>{title}</h4>{no_data}" if include_heading else no_data
    body = "".join(
        f"<tr><td>{i}</td><td>{r[0]}</td><td>{r[1]}</td><td style='text-align:right;font-weight:bold;'>{r[2]}</td></tr>"
        for i, r in enumerate(rows_3col, start=1)
    )
    tbl = f"<table class='stats-tbl rankings-tbl rank-tbl'><thead><tr><th>Rank</th><th>{headers_3col[0]}</th><th>{headers_3col[1]}</th><th>{headers_3col[2]}</th></tr></thead><tbody>{body}</tbody></table>"
    scroll_wrapper = rankings_scroll_wrapper(tbl, scroll_hint, visible_rows)
    content = f"<h4 style='margin:0 0 8px;'>{title}</h4>{scroll_wrapper}" if include_heading else scroll_wrapper
    return content


def rankings_visited_table(rows, include_heading=True, scroll_hint="shading", visible_rows=16):
    """6-column table: Location | State | Country | First visit | Last visit | Visits."""
    if not rows:
        no_data = "<p style='margin:4px 0;color:#666;'>No data.</p>"
        return f"<h4 style='margin:0 0 8px;'>Most visited locations</h4>{no_data}" if include_heading else no_data
    body = "".join(
        f"<tr><td>{r[0]}</td><td>{state_for_display(r[2], r[1])}</td><td>{country_for_display(r[2])}</td><td>{r[3]}</td><td>{r[4]}</td><td style='text-align:right;font-weight:bold;'>{r[5]}</td></tr>"
        for r in rows
    )
    tbl = f"<table class='stats-tbl rankings-tbl location-cols-tbl'><thead><tr><th>Location</th><th>State</th><th>Country</th><th>First visit</th><th>Last visit</th><th>Visits</th></tr></thead><tbody>{body}</tbody></table>"
    scroll_wrapper = rankings_scroll_wrapper(tbl, scroll_hint, visible_rows)
    return f"<h4 style='margin:0 0 8px;'>Most visited locations</h4>{scroll_wrapper}" if include_heading else scroll_wrapper


def rankings_seen_once_table(rows, include_heading=True, scroll_hint="shading", visible_rows=16):
    """6-column table: Species | Location | State | Country | Visited date/time | Count."""
    if not rows:
        no_data = "<p style='margin:4px 0;color:#666;'>No data.</p>"
        return f"<h4 style='margin:0 0 8px;'>Species: Seen only once</h4>{no_data}" if include_heading else no_data
    body = "".join(
        f"<tr><td>{r[0]}</td><td>{r[1]}</td><td>{state_for_display(r[3], r[2])}</td><td>{country_for_display(r[3])}</td><td>{r[4]}</td><td style='text-align:right;font-weight:bold;'>{r[5]}</td></tr>"
        for r in rows
    )
    tbl = (
        "<table class='stats-tbl rankings-tbl seen-once-tbl'>"
        "<thead><tr>"
        "<th>Species</th><th>Location</th><th>State</th><th>Country</th><th>Visited date/time</th><th>Count</th>"
        "</tr></thead><tbody>"
        f"{body}</tbody></table>"
    )
    scroll_wrapper = rankings_scroll_wrapper(tbl, scroll_hint, visible_rows)
    return scroll_wrapper


def rankings_subspecies_hierarchical_table(title, species_blocks, include_heading=True, scroll_hint="shading", visible_rows=16):
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
        if frac is not None:
            pct = f"{frac * 100:.0f}% subspecies identified"
            total_line = f"{total:,} ({pct})"
        else:
            total_line = f"{total:,}"

        header_parts = [species_common]
        if species_sci:
            header_parts.append(f"<span style='color:#6b7280;font-size:12px;'>({species_sci})</span>")
        header_text = " ".join(header_parts)

        subspecies_rows = []
        for sub in block.get("subspecies", []):
            label = sub.get("subspecies_common", "")
            sub_sci = sub.get("subspecies_scientific", "")
            count = sub.get("individuals", 0)
            label_html = label or sub.get("subspecies_common_full", "")
            sci_html = f"<span style='color:#6b7280;font-size:12px;'>{sub_sci}</span>" if sub_sci else ""
            subspecies_rows.append(
                f"<tr><td>{label_html}</td><td>{sci_html}</td>"
                f"<td style='text-align:right;font-weight:bold;'>{count:,}</td></tr>"
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
.subspecies-accordion {
  font-size: 13px;
  line-height: 1.5;
}
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
