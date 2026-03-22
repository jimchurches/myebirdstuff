"""
HTML builders for the Maintenance tab (map duplicates, incomplete checklists, sex notation).

Extracted from the notebook UI layer for reuse (e.g. Streamlit); refs #69, #79.
"""

from __future__ import annotations

import html as html_module
from typing import Any, Callable, Dict, Iterator, List, Optional, Tuple

import pandas as pd

from personal_ebird_explorer.duplicate_checks import get_map_maintenance_data

# eBird location edit URL (merge/delete personal locations), not lifelist.
EBIRD_LOCATION_EDIT_BASE = "https://ebird.org/mylocations/edit/"

# Shared with notebook; Streamlit ``stats-tbl`` / ``stats-tbl-maint`` rules live in
# ``checklist_stats_display._streamlit_checklist_html_tab_css`` (refs #79).
MAINTENANCE_TABLE_CLASSES = "maint-tbl stats-tbl stats-tbl-maint"
MAINTENANCE_PAIR_TABLE_CLASSES = "maint-tbl stats-tbl stats-tbl-maint maint-pair-tbl"

# --- CSS (notebook accordions + Streamlit can inject once) ---

_MAINT_TEXT_CSS = """
    .maint-html-blurb {
      margin-top:0;
      margin-bottom:16px;
      max-width:600px;
      box-sizing:border-box;
      color:#6b7280;
      font-size:13px;
      font-weight:normal;
      line-height:1.6;
      text-align:left;
      overflow-wrap:break-word;
      word-break:break-word;
    }
    .maint-html-caption {
      margin:4px 0 8px;
      color:#6b7280;
      font-size:13px;
      line-height:1.45;
      font-weight:normal;
    }
    .maint-html-blurb p {
      margin:0 0 0.65em;
    }
    .maint-html-blurb p:last-child {
      margin-bottom:0;
    }
    .maint-caution-symbol {
      display:inline-block;
      margin-right:0.35em;
      font-size:0.92em;
      opacity:0.88;
      vertical-align:0.06em;
      font-family:"Segoe UI Symbol","Arial Unicode MS",sans-serif;
    }
"""

MAP_MAINTENANCE_CSS = (
    _MAINT_TEXT_CSS
    + """
    .maint-tbl.maint-single-col td { text-align:left; font-weight:normal; }
    .maint-pair-tbl { max-width:600px; }
    .maint-pair-tbl tbody tr.maint-spacer { background:transparent; }
    .maint-close-pair-stack {
      display:flex;
      flex-direction:column;
      gap:1.35rem;
      max-width:600px;
    }
    .maint-close-pair-wrap { margin:0; }
    .maint-close-pair-wrap:not(:first-child) {
      padding-top:1rem;
      border-top:1px solid #e5e7eb;
    }
    .maint-section {
      margin-bottom:8px;
      border:1px solid #e5e7eb;
      border-radius:6px;
      background:#f9fafb;
      padding:4px 10px;
    }
    .maint-section > summary {
      font-weight:600;
      padding:6px 0;
      color:#374151;
      cursor:pointer;
    }
    .maint-subsection { margin-top:8px; margin-bottom:4px; margin-left:8px; }
    .maint-subsection > summary {
      font-weight:600;
      padding:4px 0;
      color:#374151;
      cursor:pointer;
      font-size:13px;
    }
"""
)

# Used by incomplete + sex notation notebook wrappers (details/summary).
MAINTENANCE_YEAR_SECTION_CSS = (
    _MAINT_TEXT_CSS
    + """
    details { margin-bottom:8px; }
    summary { cursor:pointer; font-weight:600; padding:6px 0; color:#374151; }
    .maint-section {
      margin-bottom:8px;
      border:1px solid #e5e7eb;
      border-radius:6px;
      background:#f9fafb;
      padding:4px 10px;
    }
    .maint-section > summary {
      font-weight:600;
      padding:6px 0;
      color:#374151;
      cursor:pointer;
    }
"""
)


def map_maintenance_intro_html() -> str:
    """Introductory copy for Location maintenance (HTML fragment)."""
    # U+26A0 WARNING SIGN + U+FE0E text presentation (avoid colourful emoji where supported).
    caution_glyph = (
        '<span class="maint-caution-symbol" aria-hidden="true" title="Caution">'
        "&#9888;&#xFE0E;</span>"
    )
    return f"""
  <div class="maint-html-blurb">
    <p>These tables highlight duplicate locations and locations that are very close to each other (within the configured distance) to help you keep your personal eBird locations organised. This is most useful if you regularly create new locations and build a large catalogue of them; if you mainly use hotspots it may be less relevant. Locations can be merged on the eBird website, though directly merging duplicates can sometimes be awkward. Often the simplest approach is to move checklists to the preferred location and then delete the now-empty duplicate. See eBird for details.</p>
    <p>{caution_glyph}Update eBird locations with caution.</p>
    <p>This data is provided here to help the author with a particular use case related to his own location data.</p>
  </div>"""


def map_maintenance_exact_duplicates_body_html(exact_rows: List[Tuple[Any, ...]]) -> str:
    """Table HTML for exact duplicate locations (one ``get_map_maintenance_data`` result)."""
    if not exact_rows:
        return """
  <p class="maint-html-caption">None detected.</p>"""
    dup_body = ""
    for loc_name, loc_id, count, lat, lon in exact_rows:
        link = (
            f'<a href="{EBIRD_LOCATION_EDIT_BASE}{loc_id}" target="_blank">{loc_name}</a>'
            if loc_id
            else loc_name
        )
        coords = f"({lat:.6f}, {lon:.6f})" if pd.notna(lat) and pd.notna(lon) else "—"
        dup_body += f"<tr><td>{link}</td><td>{coords}</td><td>{count}</td></tr>"
    return f"""
  <p class="maint-html-caption">Different Location IDs at the same coordinates. Same name listed once; different names listed separately.</p>
  <table class="{MAINTENANCE_TABLE_CLASSES}">
    <thead><tr><th>Location</th><th>Latitude/Longitude</th><th>Number of duplicates</th></tr></thead>
    <tbody>{dup_body}</tbody>
  </table>"""


def map_maintenance_close_locations_body_html(near_pairs: List[Any], threshold_m: int) -> str:
    """One table per close pair (or per group if a pair list ever has >2 rows); same columns/styling each."""
    if not near_pairs:
        return f"""
  <p class="maint-html-caption">None detected within the current threshold ({threshold_m} m).</p>"""

    def _one_pair_table(pair: List[Any]) -> str:
        pair_rows = "".join(
            (
                f'<tr class="pair-first"><td><a href="{EBIRD_LOCATION_EDIT_BASE}{lid}" target="_blank">{name}</a></td><td>{f"({lat:.6f}, {lon:.6f})" if pd.notna(lat) and pd.notna(lon) else "—"}</td></tr>'
                if idx == 0
                else f'<tr class="pair-second"><td><a href="{EBIRD_LOCATION_EDIT_BASE}{lid}" target="_blank">{name}</a></td><td>{f"({lat:.6f}, {lon:.6f})" if pd.notna(lat) and pd.notna(lon) else "—"}</td></tr>'
            )
            for idx, (lid, name, lat, lon) in enumerate(pair)
        )
        return (
            f'<table class="{MAINTENANCE_PAIR_TABLE_CLASSES}">'
            '<thead><tr><th>Location</th><th>Latitude/Longitude</th></tr></thead>'
            f"<tbody>{pair_rows}</tbody></table>"
        )

    blocks = "".join(
        f'<div class="maint-close-pair-wrap">{_one_pair_table(pair)}</div>' for pair in near_pairs
    )
    return f"""
  <p class="maint-html-caption">Locations within {threshold_m} m of each other (excluding exact duplicates).</p>
  <div class="maint-close-pair-stack">
{blocks}
  </div>"""


def map_maintenance_table_sections_html(loc_df: pd.DataFrame, threshold_m: int) -> Tuple[str, str, str]:
    """Location maintenance: intro + exact-duplicates block + close-locations block (inner HTML only).

    Single call to :func:`get_map_maintenance_data` (refs #79).
    """
    exact_rows, near_pairs = get_map_maintenance_data(loc_df, threshold_m)
    intro = map_maintenance_intro_html()
    exact = map_maintenance_exact_duplicates_body_html(exact_rows)
    close_ = map_maintenance_close_locations_body_html(near_pairs, threshold_m)
    return intro, exact, close_


def format_map_maintenance_html(loc_df: pd.DataFrame, threshold_m: int) -> str:
    """Build HTML for Map maintenance: exact duplicates and close-location pairs (notebook accordion)."""
    intro, exact_dup_content, close_loc_content = map_maintenance_table_sections_html(loc_df, threshold_m)
    return f"""
<style>{MAP_MAINTENANCE_CSS}</style>
<div style="font-family:sans-serif;font-size:13px;line-height:1.6;max-width:800px;">
<details class="maint-section">
  <summary>Location Maintenance</summary>
{intro}
  <details class="maint-subsection">
    <summary>Exact duplicates</summary>
{exact_dup_content}
  </details>
  <details class="maint-subsection">
    <summary>Close locations</summary>
{close_loc_content}
  </details>
</details>
</div>"""


def sex_notation_intro_html() -> str:
    """Intro HTML for sex-notation maintenance."""
    return """
  <div class="maint-html-blurb">
    Some checklists contain shorthand sex or age notation (for example <code>MF</code>, <code>MFFF</code>, or <code>MMF??F</code>) entered in the field notes. These should ideally be converted into the structured Age/Sex table on the eBird website. The following lists identify checklists where this shorthand was detected.
  </div>"""


def sex_notation_year_table_html(
    year: Any,
    items: List[Tuple[Any, ...]],
    species_url_fn: Optional[Callable[[str], Optional[str]]] = None,
) -> str:
    """HTML table for one year's sex-notation rows (no wrapper)."""
    rows = []
    for sid, date_str, loc, species, protocol, notation in items:
        loc_esc = html_module.escape(loc, quote=True)
        date_esc = html_module.escape(date_str, quote=True)
        species_esc = html_module.escape(species, quote=True)
        protocol_esc = html_module.escape(protocol, quote=True)
        notation_esc = html_module.escape(notation, quote=True)
        species_url = species_url_fn(species) if species_url_fn else None
        species_cell = (
            f'<a href="{html_module.escape(species_url, quote=True)}" target="_blank" rel="noopener">{species_esc}</a>'
            if species_url
            else species_esc
        )
        url = f"https://ebird.org/checklist/{sid}" if sid else "#"
        loc_link = f'<a href="{url}" target="_blank">{loc_esc}</a>' if url != "#" else loc_esc
        rows.append(
            f"<tr><td>{date_esc}</td><td>{protocol_esc}</td><td>{species_cell}</td>"
            f"<td>{notation_esc}</td><td>{loc_link}</td></tr>"
        )
    table_body = "".join(rows)
    return (
        f'<table class="{MAINTENANCE_TABLE_CLASSES}"><thead><tr><th>Date</th><th>Protocol</th><th>Species</th>'
        f"<th>Sex Notation</th><th>Location</th></tr></thead><tbody>{table_body}</tbody></table>"
    )


def iter_sex_notation_years_desc(
    sex_notation_by_year: Dict[Any, List[Tuple[Any, ...]]],
) -> Iterator[Tuple[Any, List[Tuple[Any, ...]]]]:
    """Years descending with items."""
    for y in sorted(sex_notation_by_year.keys(), reverse=True):
        yield y, sex_notation_by_year[y]


def format_sex_notation_maintenance_html(
    sex_notation_by_year: Dict[Any, List[Tuple[Any, ...]]],
    species_url_fn: Optional[Callable[[str], Optional[str]]] = None,
) -> str:
    """HTML for sex-notation strings in checklist comments, grouped by year (refs #56)."""
    if not sex_notation_by_year:
        return ""
    explanation = sex_notation_intro_html()
    sections = []
    for y, items in iter_sex_notation_years_desc(sex_notation_by_year):
        table = sex_notation_year_table_html(y, items, species_url_fn=species_url_fn)
        sections.append(f"<details><summary>{y} ({len(items)})</summary>{table}</details>")
    return f"""
<style>{MAINTENANCE_YEAR_SECTION_CSS}</style>
<div style="font-family:sans-serif;font-size:13px;line-height:1.6;max-width:800px;">
<details class="maint-section">
  <summary>Sex notation in checklist comments</summary>
{explanation}
  <div style="margin-top:16px;">
{"".join(sections)}
  </div>
</details>
</div>"""


def incomplete_checklists_intro_html() -> str:
    """Intro HTML for incomplete travelling/stationary checklists."""
    return """
  <div class="maint-html-blurb">
    Incomplete travelling and stationary checklists often occur when submitting a checklist in the eBird mobile app. The default setting is incomplete, and if you move quickly through the submission prompts you may accidentally answer "No" to the question asking whether the list is complete.<br><br>
    Incomplete checklists can certainly be intentional and acceptable (for example, when other species were present but not recorded). These checklists tables below are provided so you can review your data for checklists that may have been marked incomplete by mistake. Incidental checklists are not included.<br><br>
    Reference: <a href="https://support.ebird.org/en/support/solutions/articles/48000950859-guide-to-ebird-protocols" target="_blank">Guide to eBird Protocols</a>
  </div>"""


def incomplete_checklists_year_table_html(year: Any, items: List[Tuple[Any, ...]]) -> str:
    """HTML table for one year's incomplete checklist rows (no wrapper)."""
    rows = []
    for sid, date_str, loc in items:
        loc_esc = html_module.escape(loc, quote=True)
        date_esc = html_module.escape(date_str, quote=True)
        url = f"https://ebird.org/checklist/{sid}" if sid else "#"
        rows.append(f'<tr><td>{date_esc}</td><td><a href="{url}" target="_blank">{loc_esc}</a></td></tr>')
    table_body = "".join(rows)
    return (
        f'<table class="{MAINTENANCE_TABLE_CLASSES}"><thead><tr><th>Date</th><th>Location</th></tr></thead>'
        f"<tbody>{table_body}</tbody></table>"
    )


def iter_incomplete_checklists_years_desc(
    incomplete_by_year: Dict[Any, List[Tuple[Any, ...]]],
) -> Iterator[Tuple[Any, List[Tuple[Any, ...]]]]:
    for y in sorted(incomplete_by_year.keys(), reverse=True):
        yield y, incomplete_by_year[y]


def format_incomplete_checklists_maintenance_html(incomplete_by_year: Dict[Any, List[Tuple[Any, ...]]]) -> str:
    """HTML for incomplete travelling/stationary checklists by year (notebook accordion)."""
    if not incomplete_by_year:
        return ""
    explanation = incomplete_checklists_intro_html()
    sections = []
    for y, items in iter_incomplete_checklists_years_desc(incomplete_by_year):
        table = incomplete_checklists_year_table_html(y, items)
        sections.append(f"<details><summary>{y} ({len(items)})</summary>{table}</details>")
    return f"""
<style>{MAINTENANCE_YEAR_SECTION_CSS}</style>
<div style="font-family:sans-serif;font-size:13px;line-height:1.6;max-width:800px;">
<details class="maint-section">
  <summary>Incomplete checklists (Traveling or Stationary)</summary>
{explanation}
  <div style="margin-top:16px;">
{"".join(sections)}
  </div>
</details>
</div>"""
