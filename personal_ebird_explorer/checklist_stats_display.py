"""
HTML rendering for checklist statistics, yearly summary, and rankings sections.

Consumes :class:`ChecklistStatsPayload` from ``checklist_stats_compute`` (refs #68).
"""

from __future__ import annotations

import html as html_module
import re
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


def _ebird_country_region_page_url(country_key: str) -> Optional[str]:
    """eBird region hub for a country, e.g. ``https://ebird.org/region/US``."""
    k = _ebird_country_region_iso2(country_key)
    if not k:
        return None
    return f"https://ebird.org/region/{k}"


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


def country_display_name_plain(country_key: str) -> str:
    """Human-readable country/region label for UI widgets (not HTML-escaped)."""
    if country_key == "_UNKNOWN":
        return "Unknown"
    if str(country_key).startswith("_R:"):
        return str(country_key)[3:]
    k = str(country_key).strip()
    if len(k) == 2 and k.isalpha():
        return country_for_display(k) or k
    return k


def _country_accordion_title(country_key: str) -> str:
    """Plain-text title for a country ``<summary>`` (HTML-escaped)."""
    return html_module.escape(country_display_name_plain(country_key), quote=False)


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
        # Same table fragment as :func:`format_country_yearly_table_html` (refs #75, single source of truth).
        table_html = format_country_yearly_table_html(
            country_key, years_list, rows, inline_statistic_links=True
        )
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


def format_country_yearly_table_html(
    country_key: str,
    years_list: List[Any],
    rows: List[Tuple[str, List[str]]],
    *,
    inline_statistic_links: bool = True,
) -> str:
    """HTML table for one country's yearly statistics (same structure as Country tab accordion).

    *inline_statistic_links*: when ``True`` (default), *Lifers (country)* and *Total checklists* get ⧉
    links like the notebook Country tab. Set ``False`` when those URLs are shown above the table
    (e.g. Streamlit Country tab).
    """
    if not years_list or not rows:
        return (
            "<p style='font-family:sans-serif;color:#666;padding:8px 0;'>No yearly rows for this country.</p>"
        )
    n_years = len(years_list)
    multi_year = n_years > 1
    n_cols = n_years + (1 if multi_year else 0)
    min_w = "280px" if n_cols <= 2 else "360px" if n_cols <= 3 else "400px"
    year_headers = "".join(
        f"<th style='text-align:right;'>{html_module.escape(str(y), quote=False)}</th>" for y in years_list
    )
    if multi_year:
        year_headers += "<th style='text-align:right;'>Total</th>"

    def _first_col(label: str) -> str:
        if inline_statistic_links:
            return _country_table_statistic_label_cell(label, country_key)
        return html_module.escape(label, quote=False)

    body_rows = "".join(
        f"<tr><td>{_first_col(label)}</td>"
        + "".join(
            f"<td style='text-align:right;'>{html_module.escape(str(v), quote=False)}</td>" for v in vals
        )
        + "</tr>"
        for label, vals in rows
    )
    return f"""  <div class="yearly-tbl-scroll" style="overflow-x:auto;width:100%;max-width:100%;">
  <table class="stats-tbl stats-tbl-yearly" style="min-width:{min_w};width:100%;">
    <thead><tr><th>Statistic</th>{year_headers}</tr></thead>
    <tbody>{body_rows}</tbody>
  </table>
  </div>"""


def country_yearly_links_bar_html(country_key: str) -> str:
    """Optional row of links for ISO countries: page → lifers → checklists; empty for regions/unknown."""
    parts: List[str] = []
    region_page = _ebird_country_region_page_url(country_key)
    life = _ebird_country_lifelist_url(country_key)
    my_ck = _ebird_country_mychecklists_url(country_key)
    if region_page:
        esc = html_module.escape(region_page, quote=True)
        parts.append(
            f'<a href="{esc}" target="_blank" rel="noopener noreferrer" '
            'title="eBird region page">'
            '<span class="stats-link-icon" aria-hidden="true">⧉</span> Country page</a>'
        )
    if life:
        esc = html_module.escape(life, quote=True)
        parts.append(
            f'<a href="{esc}" target="_blank" rel="noopener noreferrer" '
            'title="eBird life list (this country/region)">'
            '<span class="stats-link-icon" aria-hidden="true">⧉</span> Country lifers</a>'
        )
    if my_ck:
        esc = html_module.escape(my_ck, quote=True)
        parts.append(
            f'<a href="{esc}" target="_blank" rel="noopener noreferrer" '
            'title="eBird my checklists (this country)">'
            '<span class="stats-link-icon" aria-hidden="true">⧉</span> Country checklists</a>'
        )
    if not parts:
        return ""
    sep = ' <span class="stats-link-sep" aria-hidden="true">·</span> '
    return f'<p class="stats-links-row">{sep.join(parts)}</p>'


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
    /* Scroll area: slight top inset so header sits below strongest part of top fade (refs #81). */
    .rankings-scroll-inner { box-sizing: border-box; padding-top: 0.5rem; }
    /* Subspecies: scientific names share table/summary font size; muted color only (refs #81). */
    .subspecies-sci-secondary { color: #6b7280; font-size: inherit; line-height: inherit; font-weight: inherit; }
    """

# Injected once by ``streamlit_app/checklist_stats_streamlit_html`` around checklist sub-tabs only.
# Scoped under ``.streamlit-checklist-html-ab`` so Jupyter ``stats_html`` / notebook layout stay unchanged.
#
# **Default:** green accents + zebra (``#1f6f54`` — aligns with ``.streamlit/config.toml`` primary).
# **Alternate:** ``CHECKLIST_STATS_STREAMLIT_HTML_TAB_CSS_BLUE`` (eBird-style blue); enable via
# ``_USE_EBIRD_BLUE_HTML_TAB_THEME`` in ``checklist_stats_streamlit_html.py``.
#
# Typography aligned with Streamlit nested ``st.tabs`` labels (~13px / normal weight in default theme).
def _streamlit_checklist_html_tab_css(*, blue_theme: bool) -> str:
    """Build scoped Streamlit HTML-tab CSS (blue or green accent + zebra rows)."""
    if blue_theme:
        # eBird-ish blue (links / nav on eBird.org lean this way; tweak if you standardise on brand specs).
        acc = "21, 101, 168"  # #1565a8
        acc_rgb = (21, 101, 168)
        link = "#1565a8"
        text_fb = "#1a2e22"
        p_fallback = "26, 46, 34"
    else:
        acc = "31, 111, 84"  # #1f6f54 — matches Streamlit config.toml primary / prior green tab
        acc_rgb = (31, 111, 84)
        link = "#1f6f54"
        text_fb = "#1a2e22"
        p_fallback = "26, 46, 34"
    # Opaque zebra/header fills for sticky yearly first column (semi-transparent rgba shows
    # scrolling cells through; blend accent onto same base as .stats-tbl background — refs #85).
    _base_tbl = (250, 252, 250)  # #fafcfa — matches var(--background-color, #fafcfa)

    def _opaque_accent_on_base(alpha: float) -> str:
        r = round(_base_tbl[0] * (1.0 - alpha) + acc_rgb[0] * alpha)
        g = round(_base_tbl[1] * (1.0 - alpha) + acc_rgb[1] * alpha)
        b = round(_base_tbl[2] * (1.0 - alpha) + acc_rgb[2] * alpha)
        return f"#{r:02x}{g:02x}{b:02x}"

    freeze_odd = _opaque_accent_on_base(0.04)
    freeze_even = _opaque_accent_on_base(0.085)
    freeze_head = _opaque_accent_on_base(0.09)
    freeze_hover = _opaque_accent_on_base(0.14)
    return f"""
.streamlit-checklist-html-ab {{
  display: block;
  width: 100%;
  max-width: min(68rem, 100%);
  min-width: min(100%, 20rem);
  box-sizing: border-box;
  font-family: "Source Sans Pro", -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
  font-size: 0.8125rem;
  line-height: 1.45;
  font-weight: 400;
  letter-spacing: normal;
  -webkit-font-smoothing: antialiased;
  -moz-osx-font-smoothing: grayscale;
  color: var(--text-color, {text_fb});
}}
.streamlit-checklist-html-ab .stats-tbl {{
  width: 100%;
  table-layout: fixed;
  border-collapse: separate;
  border-spacing: 0;
  font-size: 1em;
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
  font-size: 0.923em;
  line-height: 1.45;
  font-weight: 400;
}}
@supports not (color: color-mix(in srgb, black 50%, white)) {{
  .streamlit-checklist-html-ab > p {{
    color: rgba({p_fallback}, 0.7);
  }}
}}
/* Multi-column yearly tables (country + global Yearly Summary): undo fixed layout squeeze.
   Default .stats-tbl uses table-layout:fixed + width:100%, which splits many year columns
   equally and wraps headers/values; use content-sized columns + nowrap (refs #85). */
.streamlit-checklist-html-ab .stats-tbl.stats-tbl-yearly {{
  table-layout: auto;
  width: max-content;
  min-width: 100%;
  max-width: none;
  font-size: 0.92em;
  /* Sticky first column needs a non-clipping overflow (default .stats-tbl is hidden). */
  overflow: visible;
}}
.streamlit-checklist-html-ab .stats-tbl.stats-tbl-yearly thead th {{
  padding: 0.4rem 0.5rem;
  border-bottom: 1px solid rgba({acc}, 0.2);
  vertical-align: bottom;
  font-weight: 600;
  background: rgba({acc}, 0.09);
}}
.streamlit-checklist-html-ab .stats-tbl.stats-tbl-yearly tbody td {{
  vertical-align: middle;
}}
/* Yearly Summary tab: use full Streamlit main-column width (default .streamlit-checklist-html-ab caps at 68rem). */
.streamlit-checklist-html-ab.streamlit-yearly-summary-ab {{
  max-width: 100%;
}}
/* First column: statistic labels + sticky “freeze” while scrolling horizontally (refs #85). */
.streamlit-checklist-html-ab .stats-tbl.stats-tbl-yearly th:first-child,
.streamlit-checklist-html-ab .stats-tbl.stats-tbl-yearly td:first-child {{
  width: 16rem;
  min-width: 16rem;
  max-width: 16rem;
  box-sizing: border-box;
  word-wrap: break-word;
  overflow-wrap: break-word;
  position: sticky;
  left: 0;
  z-index: 2;
  border-right: 1px solid rgba({acc}, 0.2);
  box-shadow: 4px 0 12px -6px rgba(0, 0, 0, 0.18);
}}
.streamlit-checklist-html-ab .stats-tbl.stats-tbl-yearly thead th:first-child {{
  text-align: left;
  z-index: 4;
  background-color: {freeze_head} !important;
}}
.streamlit-checklist-html-ab .stats-tbl.stats-tbl-yearly tbody tr:nth-child(odd) td:first-child {{
  background-color: {freeze_odd} !important;
}}
.streamlit-checklist-html-ab .stats-tbl.stats-tbl-yearly tbody tr:nth-child(even) td:first-child {{
  background-color: {freeze_even} !important;
}}
.streamlit-checklist-html-ab .stats-tbl.stats-tbl-yearly tbody tr:hover td:first-child {{
  background-color: {freeze_hover} !important;
}}
.streamlit-checklist-html-ab .stats-tbl.stats-tbl-yearly th:last-child,
.streamlit-checklist-html-ab .stats-tbl.stats-tbl-yearly td:last-child {{
  width: auto;
}}
.streamlit-checklist-html-ab .stats-tbl.stats-tbl-yearly th:not(:first-child),
.streamlit-checklist-html-ab .stats-tbl.stats-tbl-yearly td:not(:first-child) {{
  text-align: right;
  font-variant-numeric: tabular-nums;
  white-space: nowrap;
  min-width: 5.5rem;
  padding-left: 0.45rem;
  padding-right: 0.45rem;
  box-sizing: border-box;
}}
/* Maintenance tab: multi-column tables share stats-tbl chrome; undo 2-col KV widths (refs #79). */
.streamlit-checklist-html-ab .stats-tbl.stats-tbl-maint th {{
  padding: 0.45rem 0.7rem;
  border-bottom: 1px solid rgba({acc}, 0.2);
  vertical-align: bottom;
  text-align: left;
  font-weight: 600;
  background: rgba({acc}, 0.09);
}}
.streamlit-checklist-html-ab .stats-tbl.stats-tbl-maint td:first-child,
.streamlit-checklist-html-ab .stats-tbl.stats-tbl-maint td:last-child {{
  width: auto;
  min-width: 0;
  max-width: none;
  text-align: left;
  font-weight: 400;
  font-variant-numeric: normal;
}}
.streamlit-checklist-html-ab .stats-tbl.stats-tbl-maint tbody tr.maint-spacer td {{
  background: transparent !important;
  border-bottom: none !important;
  height: 12px;
  padding: 0;
  line-height: 0;
}}
.streamlit-checklist-html-ab .stats-tbl.stats-tbl-maint.maint-pair-tbl {{
  max-width: 600px;
}}
.streamlit-checklist-html-ab .maint-close-pair-stack {{
  display: flex;
  flex-direction: column;
  gap: 1.35rem;
  max-width: 600px;
}}
.streamlit-checklist-html-ab .maint-close-pair-wrap {{
  margin: 0;
}}
.streamlit-checklist-html-ab .maint-close-pair-wrap:not(:first-child) {{
  padding-top: 1rem;
  border-top: 1px solid rgba({acc}, 0.22);
}}
.streamlit-checklist-html-ab .maint-html-blurb {{
  margin-top: 0;
  margin-bottom: 1rem;
  max-width: min(37.5rem, 100%);
  box-sizing: border-box;
  color: color-mix(in srgb, var(--text-color, {text_fb}) 64%, transparent);
  font-size: 0.923em;
  line-height: 1.45;
  font-weight: 400;
  text-align: left;
  overflow-wrap: break-word;
  word-break: break-word;
}}
.streamlit-checklist-html-ab .maint-html-blurb code {{
  font-size: 0.94em;
}}
.streamlit-checklist-html-ab .maint-html-blurb p {{
  margin: 0 0 0.65em;
  font-size: inherit;
  line-height: inherit;
}}
.streamlit-checklist-html-ab .maint-html-blurb p:last-child {{
  margin-bottom: 0;
}}
.streamlit-checklist-html-ab .maint-caution-symbol {{
  display: inline-block;
  margin-right: 0.35em;
  font-size: 0.92em;
  opacity: 0.88;
  vertical-align: 0.06em;
  font-family: "Segoe UI Symbol", "Arial Unicode MS", sans-serif;
}}
@supports not (color: color-mix(in srgb, black 50%, white)) {{
  .streamlit-checklist-html-ab .maint-html-blurb {{
    color: rgba({p_fallback}, 0.7);
  }}
}}
.streamlit-checklist-html-ab p.maint-html-caption {{
  margin: 0.35rem 0 0.65rem;
  color: color-mix(in srgb, var(--text-color, {text_fb}) 64%, transparent);
  font-size: 0.923em;
  line-height: 1.45;
  font-weight: 400;
}}
@supports not (color: color-mix(in srgb, black 50%, white)) {{
  .streamlit-checklist-html-ab p.maint-html-caption {{
    color: rgba({p_fallback}, 0.7);
  }}
}}
/* Rankings & lists (refs #81): ``.stats-tbl`` defaults assume 2-col KV tables — rankings use 3–6 columns.
   Reset widths + match maintenance-style header band so expanders match other Streamlit HTML tabs. */
.streamlit-checklist-html-ab .stats-tbl.rankings-tbl thead th {{
  padding: 0.45rem 0.7rem;
  border-bottom: 1px solid rgba({acc}, 0.2);
  vertical-align: bottom;
  text-align: left;
  font-weight: 600;
  background: rgba({acc}, 0.09);
}}
/* Scroll area: match notebook — top padding under scroll fade (refs #81). */
.streamlit-checklist-html-ab .rankings-scroll-inner {{
  box-sizing: border-box;
  padding-top: 0.5rem;
}}
/* Undo 2-col KV widths for rankings tables except ``rank-tbl`` (narrow rank column set below). */
.streamlit-checklist-html-ab .stats-tbl.rankings-tbl:not(.rank-tbl) td:first-child,
.streamlit-checklist-html-ab .stats-tbl.rankings-tbl:not(.rank-tbl) td:last-child {{
  width: auto !important;
  min-width: 0;
  max-width: none;
}}
/* Location / visited rankings: align plain-text columns with Checklist Statistics KV labels
   (proportional numerals, 400). Checklist uses tabular-nums only on the value column; we were
   applying tabular-nums to every cell here, which subtly changes state/country (refs #81). */
.streamlit-checklist-html-ab .stats-tbl.location-cols-tbl th {{
  text-align: left;
  font-variant-numeric: normal;
}}
.streamlit-checklist-html-ab .stats-tbl.location-cols-tbl td {{
  text-align: left;
  font-variant-numeric: normal;
  font-weight: 400;
}}
.streamlit-checklist-html-ab .stats-tbl.location-cols-tbl td:nth-child(n + 4) {{
  font-variant-numeric: tabular-nums;
}}
.streamlit-checklist-html-ab .stats-tbl.location-cols-tbl td:last-child {{
  text-align: right;
  font-weight: 600;
}}
/* Species rankings (Rank | … | metric): keep rank column index-narrow; metric column medium weight. */
.streamlit-checklist-html-ab .stats-tbl.rank-tbl {{
  table-layout: fixed;
  width: 100%;
}}
.streamlit-checklist-html-ab .stats-tbl.rank-tbl th:nth-child(1),
.streamlit-checklist-html-ab .stats-tbl.rank-tbl td:nth-child(1) {{
  width: 3.25rem;
  max-width: 4rem;
  min-width: 2.5rem;
  padding-left: 0.45rem;
  padding-right: 0.45rem;
  box-sizing: border-box;
  white-space: nowrap;
  text-align: right !important;
  font-variant-numeric: tabular-nums;
  font-weight: 500;
}}
.streamlit-checklist-html-ab .stats-tbl.rank-tbl th:nth-child(2),
.streamlit-checklist-html-ab .stats-tbl.rank-tbl td:nth-child(2) {{
  width: auto;
  min-width: 0;
}}
.streamlit-checklist-html-ab .stats-tbl.rank-tbl th:last-child,
.streamlit-checklist-html-ab .stats-tbl.rank-tbl td:last-child {{
  width: 8.5rem;
  max-width: 11rem;
  text-align: right;
  font-weight: 600;
  font-variant-numeric: tabular-nums;
}}
.streamlit-checklist-html-ab .stats-tbl.seen-once-tbl td:last-child {{
  text-align: right;
  font-weight: 600;
}}
.streamlit-checklist-html-ab .stats-tbl.subspecies-tbl thead th {{
  padding: 0.45rem 0.7rem;
  border-bottom: 1px solid rgba({acc}, 0.2);
  font-weight: 600;
  background: rgba({acc}, 0.09);
}}
.streamlit-checklist-html-ab .stats-tbl.subspecies-tbl tbody td:nth-child(1),
.streamlit-checklist-html-ab .stats-tbl.subspecies-tbl tbody td:nth-child(2) {{
  text-align: left;
  font-variant-numeric: normal;
  font-weight: 400;
}}
.streamlit-checklist-html-ab .stats-tbl.subspecies-tbl tbody td:last-child {{
  text-align: right;
  font-weight: 600;
  font-variant-numeric: tabular-nums;
}}
.streamlit-checklist-html-ab .subspecies-sci-secondary {{
  color: color-mix(in srgb, var(--text-color, {text_fb}) 58%, transparent);
  font-size: inherit;
  line-height: inherit;
  font-weight: inherit;
}}
@supports not (color: color-mix(in srgb, black 50%, transparent)) {{
  .streamlit-checklist-html-ab .subspecies-sci-secondary {{
    color: #6b7280;
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
    """Six ``(tab_label, inner_html)`` blocks for Streamlit nested checklist tabs (fixed section order).

    Order: Overview, Checklist types, Total distance, Time eBirded, eBirding with Others, Checklist streak.
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


# Matches the nested spans emitted in ``stats.py`` (glyph + tooltip inside stats-info-icon).
_YEARLY_INFO_ICON_RE = re.compile(
    r'\s*<span class="stats-info-icon">\s*'
    r'<span class="stats-info-glyph">.*?</span>\s*'
    r'<span class="stats-info-tooltip">.*?</span>\s*'
    r"</span>",
    re.DOTALL,
)

# Order for traveling / stationary detail rows (same as notebook yearly expanders; refs #85).
_YEARLY_TRAVELING_ORDER = [
    "Total distance (km)",
    "Average distance (km)",
    "Total hours",
    "Average minutes",
    "Average species",
    "Average individuals",
]
_YEARLY_STATIONARY_ORDER = [
    "Total hours",
    "Average minutes",
    "Average species",
    "Average individuals",
]

_YEARLY_STREAMLIT_CAPTION_STYLE = (
    "margin:10px 0 0;color:#6b7280;font-size:12px;line-height:1.5;max-width:52rem;"
)

# Streamlit Yearly Summary: default to the most recent N calendar years when count exceeds this (refs #85).
YEARLY_STREAMLIT_RECENT_YEAR_COUNT = 10

# Shown below the Yearly Summary toggle in ``yearly_summary_streamlit_html`` (not embedded in All-tab HTML).
YEARLY_STREAMLIT_ALL_TAB_PROTOCOL_NOTE = (
    "Travelling and Stationary checklist counts in this table include only complete checklists "
    "(incomplete submissions are excluded).",
    "Use the Travelling and Stationary tabs for protocol-specific metrics.",
)


def format_yearly_streamlit_all_tab_protocol_note_html() -> str:
    """HTML for the protocol note below the Yearly Summary toggle (refs #85).

    Wrapped in ``.streamlit-checklist-html-ab`` so the ``<p>`` picks up the same scoped ``> p`` rules
    as tables in this tab, with ``_YEARLY_STREAMLIT_CAPTION_STYLE`` inline (same as old footnotes).
    """
    line_a, line_b = YEARLY_STREAMLIT_ALL_TAB_PROTOCOL_NOTE
    inner = (
        f'<p style="{_YEARLY_STREAMLIT_CAPTION_STYLE}">'
        f"{html_module.escape(line_a, quote=False)}<br/>"
        f"{html_module.escape(line_b, quote=False)}</p>"
    )
    return (
        f'<div class="streamlit-checklist-html-ab streamlit-yearly-summary-ab">{inner}</div>'
    )


def strip_yearly_stats_info_icons(label_html: str) -> str:
    """Remove inline ``stats-info-icon`` spans from yearly row labels (Streamlit yearly tab; refs #85)."""
    return _YEARLY_INFO_ICON_RE.sub("", label_html or "").strip()


def _partition_yearly_rows(
    yearly_rows: List[Tuple[str, List[str]]],
) -> Tuple[
    List[Tuple[str, List[str]]],
    List[Tuple[str, List[str]]],
    List[Tuple[str, List[str]]],
    Optional[List[str]],
    Optional[List[str]],
]:
    """Split ``yearly_rows`` into main-table rows, protocol detail rows, and count value rows."""
    static_rows: List[Tuple[str, List[str]]] = []
    traveling_detail: List[Tuple[str, List[str]]] = []
    stationary_detail: List[Tuple[str, List[str]]] = []
    traveling_count_vals: Optional[List[str]] = None
    stationary_count_vals: Optional[List[str]] = None
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
    return static_rows, traveling_detail, stationary_detail, traveling_count_vals, stationary_count_vals


def _any_yearly_value(vals: List[str]) -> bool:
    return any(v != "—" for v in vals)


def _yearly_short_name(full_label: str, prefix: str) -> str:
    name = full_label.strip()
    if name.startswith(prefix):
        name = name[len(prefix) :].strip()
    if " <span" in name:
        name = name.split(" <span")[0].strip()
    return name or full_label


def _yearly_ordered_detail_rows(
    detail_rows: List[Tuple[str, List[str]]],
    order_list: List[str],
    prefix: str,
    years_list: List[Any],
) -> List[Tuple[str, List[str]]]:
    by_suffix: Dict[str, List[str]] = {}
    for label, vals in detail_rows:
        short = _yearly_short_name(label, prefix)
        by_suffix[short] = vals
    return [(name, by_suffix.get(name, ["—"] * len(years_list))) for name in order_list if name in by_suffix]


def yearly_streamlit_year_window_slice(
    years_list: List[Any],
    *,
    show_full_history: bool,
    recent_count: int = YEARLY_STREAMLIT_RECENT_YEAR_COUNT,
) -> slice:
    """Return a ``slice`` into *years_list* and aligned per-year value lists.

    When ``len(years_list) <= recent_count`` or *show_full_history* is true, returns
    ``slice(None)`` (all years). Otherwise returns the last *recent_count* entries
    (data-sorted years are ascending — see :func:`yearly_summary_stats`).
    """
    n = len(years_list)
    if n <= recent_count or show_full_history:
        return slice(None)
    return slice(n - recent_count, n)


def _parse_yearly_display_int(cell: str) -> Optional[int]:
    """Parse a stats table cell like ``1,234`` for recomputing sliced totals; non-numeric → ``None``."""
    t = str(cell).strip().replace(",", "")
    if t in ("—", "-", "", "N/A", "n/a") or t.lower() == "nan":
        return None
    try:
        return int(float(t))
    except ValueError:
        return None


def _slice_yearly_row_vals(vals: List[str], years_list: List[Any], s: slice) -> List[str]:
    """Slice per-year cells in lockstep with *years_list*.

    Country yearly rows often end with a **Total** column (``len(vals) == len(years_list) + 1``).
    That tail must be dropped, sliced, or recomputed so headers stay aligned (#85).
    """
    n = len(years_list)
    n_disp = len(years_list[s])
    if len(vals) == n:
        return vals[s]
    if len(vals) == n + 1:
        year_part, tail = vals[:-1], vals[-1]
        year_sliced = year_part[s]
        if n_disp <= 1:
            return year_sliced
        nums = [_parse_yearly_display_int(x) for x in year_part]
        tnum = _parse_yearly_display_int(tail)
        if all(v is not None for v in nums) and tnum is not None and tnum == sum(nums):
            sn = [_parse_yearly_display_int(x) for x in year_sliced]
            if all(v is not None for v in sn):
                return year_sliced + [f"{sum(sn):,}"]
        if nums and nums[-1] is not None and tnum is not None and tnum == nums[-1]:
            sl = _parse_yearly_display_int(year_sliced[-1])
            if sl is not None:
                return year_sliced + [f"{sl:,}"]
        return year_sliced + [tail]
    return vals


def slice_yearly_table_rows(
    rows: List[Tuple[str, List[str]]],
    years_list: List[Any],
    s: slice,
) -> List[Tuple[str, List[str]]]:
    """Slice each row's per-year values in lockstep with *years_list* (e.g. Country yearly table; #85)."""
    return [(lab, _slice_yearly_row_vals(vals, years_list, s)) for lab, vals in rows]


def _yearly_streamlit_wide_table_html(
    years_list: List[Any],
    rows: List[Tuple[str, List[str]]],
) -> str:
    """Wide yearly table: first column plain text (escaped), value cells escaped."""
    if not rows:
        return ""
    year_headers = "".join(
        f"<th style='text-align:right;'>{html_module.escape(str(y), quote=False)}</th>"
        for y in years_list
    )
    body = []
    for label, vals in rows:
        lab_esc = html_module.escape(str(label), quote=False)
        cells = "".join(
            f"<td style='text-align:right;'>{html_module.escape(str(v), quote=False)}</td>"
            for v in vals
        )
        body.append(f"<tr><td>{lab_esc}</td>{cells}</tr>")
    return (
        '<div class="yearly-tbl-scroll" style="overflow-x:auto;width:100%;max-width:100%;">'
        '<table class="stats-tbl stats-tbl-yearly" style="min-width:min(100%,400px);">'
        f"<thead><tr><th>Statistic</th>{year_headers}</tr></thead>"
        f"<tbody>{''.join(body)}</tbody>"
        "</table></div>"
    )


def _yearly_streamlit_protocol_table_html(
    years_list: List[Any],
    *,
    count_vals: Optional[List[str]],
    ordered_detail_rows: List[Tuple[str, List[str]]],
) -> str:
    body_rows: List[Tuple[str, List[str]]] = []
    if count_vals is not None:
        body_rows.append(("Total checklists", count_vals))
    body_rows.extend(ordered_detail_rows)
    return _yearly_streamlit_wide_table_html(years_list, body_rows)


def build_yearly_summary_streamlit_tab_html_dict(
    payload: ChecklistStatsPayload,
    *,
    show_full_history: bool = False,
    recent_year_count: int = YEARLY_STREAMLIT_RECENT_YEAR_COUNT,
) -> Optional[Dict[str, str]]:
    """Build inner HTML for Streamlit Yearly Summary nested tabs (All / Travelling / Stationary; refs #85).

    When ``len(years_list) > recent_year_count`` and *show_full_history* is false, only the most
    recent *recent_year_count* years are shown (columns), preserving notebook ordering.

    Returns ``None`` when there is no yearly grid. Icons are stripped from labels; incomplete-checklist
    guidance for protocol tabs is consolidated into the note below the Yearly Summary toggle in Streamlit.
    """
    years_list = payload.years_list
    yearly_rows = payload.yearly_rows
    if not years_list or not yearly_rows:
        return None

    y_slice = yearly_streamlit_year_window_slice(
        years_list,
        show_full_history=show_full_history,
        recent_count=recent_year_count,
    )
    display_years = years_list[y_slice]

    static_rows, traveling_detail, stationary_detail, traveling_count_vals, stationary_count_vals = (
        _partition_yearly_rows(yearly_rows)
    )

    visible_static_plain = []
    for label, vals in static_rows:
        if not _any_yearly_value(vals):
            continue
        sliced = _slice_yearly_row_vals(vals, years_list, y_slice)
        if not _any_yearly_value(sliced):
            continue
        visible_static_plain.append((strip_yearly_stats_info_icons(label), sliced))

    all_table = _yearly_streamlit_wide_table_html(display_years, visible_static_plain)
    if all_table:
        all_html = all_table
    else:
        all_html = (
            "<p style=\"color:#6b7280;font-size:14px;\">No yearly summary statistics in this view.</p>"
        )

    ordered_trav = _yearly_ordered_detail_rows(
        traveling_detail,
        _YEARLY_TRAVELING_ORDER,
        "Traveling checklist:",
        years_list,
    )
    ordered_trav_sliced = [
        (name, _slice_yearly_row_vals(vals, years_list, y_slice)) for name, vals in ordered_trav
    ]
    trav_count_sliced = (
        _slice_yearly_row_vals(traveling_count_vals, years_list, y_slice)
        if traveling_count_vals is not None
        else None
    )
    trav_table = _yearly_streamlit_protocol_table_html(
        display_years,
        count_vals=trav_count_sliced,
        ordered_detail_rows=ordered_trav_sliced,
    )
    if trav_table:
        travelling_html = trav_table
    elif traveling_detail or traveling_count_vals is not None:
        travelling_html = (
            "<p style=\"color:#6b7280;font-size:14px;\">No travelling checklist statistics to display.</p>"
        )
    else:
        travelling_html = (
            "<p style=\"color:#6b7280;font-size:14px;\">No travelling checklist data for this selection.</p>"
        )

    ordered_stat = _yearly_ordered_detail_rows(
        stationary_detail,
        _YEARLY_STATIONARY_ORDER,
        "Stationary checklist:",
        years_list,
    )
    ordered_stat_sliced = [
        (name, _slice_yearly_row_vals(vals, years_list, y_slice)) for name, vals in ordered_stat
    ]
    stat_count_sliced = (
        _slice_yearly_row_vals(stationary_count_vals, years_list, y_slice)
        if stationary_count_vals is not None
        else None
    )
    stat_table = _yearly_streamlit_protocol_table_html(
        display_years,
        count_vals=stat_count_sliced,
        ordered_detail_rows=ordered_stat_sliced,
    )
    if stat_table:
        stationary_html = stat_table
    elif stationary_detail or stationary_count_vals is not None:
        stationary_html = (
            "<p style=\"color:#6b7280;font-size:14px;\">No stationary checklist statistics to display.</p>"
        )
    else:
        stationary_html = (
            "<p style=\"color:#6b7280;font-size:14px;\">No stationary checklist data for this selection.</p>"
        )

    return {
        "all": all_html,
        "travelling": travelling_html,
        "stationary": stationary_html,
    }


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
        (
            static_rows,
            traveling_detail,
            stationary_detail,
            traveling_count_vals,
            stationary_count_vals,
        ) = _partition_yearly_rows(yearly_rows)
        visible_static = [(label, vals) for label, vals in static_rows if _any_yearly_value(vals)]
        year_headers = "".join(f"<th style='text-align:right;'>{y}</th>" for y in years_list)
        yearly_css = """
    .yearly-maint-section { margin-bottom:8px; border:1px solid #e5e7eb; border-radius:6px; background:#f9fafb; padding:4px 10px; }
    .yearly-maint-section > summary { font-weight:600; padding:6px 0; color:#374151; cursor:pointer; }
"""
        _yearly_comment_style = "margin:4px 0 8px;color:#6b7280;font-size:12px;line-height:1.5;"
        _traveling_comment = "Incomplete checklists not counted."
        _stationary_comment = "Incomplete checklists not counted."

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
            ordered_trav = _yearly_ordered_detail_rows(
                traveling_detail,
                _YEARLY_TRAVELING_ORDER,
                "Traveling checklist:",
                years_list,
            )
            if ordered_trav or traveling_count_vals is not None:
                body = _yearly_accordion_body(_traveling_comment, traveling_count_vals, ordered_trav)
                if body:
                    parts.append(f"""
  <details class="yearly-maint-section">
    <summary>Traveling checklists</summary>
{body}  </details>""")
        if stationary_detail or stationary_count_vals is not None:
            ordered_stat = _yearly_ordered_detail_rows(
                stationary_detail,
                _YEARLY_STATIONARY_ORDER,
                "Stationary checklist:",
                years_list,
            )
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
