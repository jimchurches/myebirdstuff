"""
HTML builders for the Maintenance tab (map duplicates, incomplete checklists, sex notation).

Extracted from the notebook UI layer for reuse (e.g. Streamlit); refs #69.
"""

from __future__ import annotations

import html as html_module
from typing import Any, Callable, Dict, List, Optional, Tuple

import pandas as pd

from personal_ebird_explorer.duplicate_checks import get_map_maintenance_data

# eBird location edit URL (merge/delete personal locations), not lifelist.
EBIRD_LOCATION_EDIT_BASE = "https://ebird.org/mylocations/edit/"


def format_map_maintenance_html(loc_df: pd.DataFrame, threshold_m: int) -> str:
    """Build HTML for Map maintenance: exact duplicates and close-location pairs."""
    exact_rows, near_pairs = get_map_maintenance_data(loc_df, threshold_m)
    css = """
    .maint-tbl.maint-single-col td { text-align:left; font-weight:normal; }
    .maint-pair-tbl { max-width:600px; }
    .maint-pair-tbl tbody tr.maint-spacer { background:transparent; }
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
    dup_body = ""
    if exact_rows:
        for loc_name, loc_id, count, lat, lon in exact_rows:
            link = f'<a href="{EBIRD_LOCATION_EDIT_BASE}{loc_id}" target="_blank">{loc_name}</a>' if loc_id else loc_name
            coords = f"({lat:.6f}, {lon:.6f})" if pd.notna(lat) and pd.notna(lon) else "—"
            dup_body += f"<tr><td>{link}</td><td>{coords}</td><td>{count}</td></tr>"
        exact_dup_content = f"""
  <p style="margin:4px 0 8px;color:#6b7280;font-size:13px;">Different Location IDs at the same coordinates. Same name listed once; different names listed separately.</p>
  <table class="maint-tbl">
    <thead><tr><th>Location</th><th>Latitude/Longitude</th><th>Number of duplicates</th></tr></thead>
    <tbody>{dup_body}</tbody>
  </table>"""
    else:
        exact_dup_content = """
  <p style="margin:4px 0;color:#6b7280;">None detected.</p>"""

    if near_pairs:
        all_rows = ""
        for i, pair in enumerate(near_pairs):
            pair_rows = "".join(
                (
                    f'<tr class="pair-first"><td><a href="{EBIRD_LOCATION_EDIT_BASE}{lid}" target="_blank">{name}</a></td><td>{f"({lat:.6f}, {lon:.6f})" if pd.notna(lat) and pd.notna(lon) else "—"}</td></tr>'
                    if idx == 0
                    else f'<tr class="pair-second"><td><a href="{EBIRD_LOCATION_EDIT_BASE}{lid}" target="_blank">{name}</a></td><td>{f"({lat:.6f}, {lon:.6f})" if pd.notna(lat) and pd.notna(lon) else "—"}</td></tr>'
                )
                for idx, (lid, name, lat, lon) in enumerate(pair)
            )
            all_rows += pair_rows
            if i < len(near_pairs) - 1:
                all_rows += '<tr class="maint-spacer"><td colspan="2" style="height:12px;border:none;background:transparent;"></td></tr>'
        close_loc_content = f"""
  <p style="margin:4px 0 12px;color:#6b7280;font-size:13px;">Locations within {threshold_m} m of each other (excluding exact duplicates).</p>
  <table class="maint-pair-tbl">
    <thead><tr><th>Location</th><th>Latitude/Longitude</th></tr></thead>
    <tbody>{all_rows}</tbody>
  </table>"""
    else:
        close_loc_content = f"""
  <p style="margin:4px 0;color:#6b7280;">None detected within the current threshold ({threshold_m} m).</p>"""

    explanation = """
  <div style="margin-top:0;margin-bottom:16px;max-width:600px;box-sizing:border-box;color:#6b7280;font-size:13px;font-weight:normal;line-height:1.6;text-align:left;overflow-wrap:break-word;word-break:break-word;">
    These tables highlight duplicate locations and locations that are very close to each other (within the configured distance) to help you keep your personal eBird locations organised. This is most useful if you regularly create new locations and build a large catalogue of them; if you mainly use hotspots it may be less relevant. Locations can be merged on the eBird website, though directly merging duplicates can sometimes be awkward. Often the simplest approach is to move checklists to the preferred location and then delete the now-empty duplicate. See eBird for details.
  </div>"""

    return f"""
<style>{css}</style>
<div style="font-family:sans-serif;font-size:13px;line-height:1.6;max-width:800px;">
<details class="maint-section">
  <summary>Location Maintenance</summary>
{explanation}
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


def format_sex_notation_maintenance_html(
    sex_notation_by_year: Dict[Any, List[Tuple[Any, ...]]],
    species_url_fn: Optional[Callable[[str], Optional[str]]] = None,
) -> str:
    """HTML for sex-notation strings in checklist comments, grouped by year (refs #56)."""
    if not sex_notation_by_year:
        return ""
    css = """
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
    explanation = """
  <div style="margin-top:0;margin-bottom:16px;max-width:600px;box-sizing:border-box;color:#6b7280;font-size:13px;font-weight:normal;line-height:1.6;text-align:left;overflow-wrap:break-word;word-break:break-word;">
    Some checklists contain shorthand sex or age notation (for example <code>MF</code>, <code>MFFF</code>, or <code>MMF??F</code>) entered in the field notes. These should ideally be converted into the structured Age/Sex table on the eBird website. The following lists identify checklists where this shorthand was detected.
  </div>"""
    sections = []
    for y in sorted(sex_notation_by_year.keys(), reverse=True):
        items = sex_notation_by_year[y]
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
                f"<tr><td>{date_esc}</td><td>{protocol_esc}</td><td>{species_cell}</td><td>{notation_esc}</td><td>{loc_link}</td></tr>"
            )
        table_body = "".join(rows)
        table = f'<table class="maint-tbl"><thead><tr><th>Date</th><th>Protocol</th><th>Species</th><th>Sex Notation</th><th>Location</th></tr></thead><tbody>{table_body}</tbody></table>'
        sections.append(f"<details><summary>{y} ({len(items)})</summary>{table}</details>")
    return f"""
<style>{css}</style>
<div style="font-family:sans-serif;font-size:13px;line-height:1.6;max-width:800px;">
<details class="maint-section">
  <summary>Sex notation in checklist comments</summary>
{explanation}
  <div style="margin-top:16px;">
{"".join(sections)}
  </div>
</details>
</div>"""


def format_incomplete_checklists_maintenance_html(incomplete_by_year: Dict[Any, List[Tuple[Any, ...]]]) -> str:
    """HTML for incomplete travelling/stationary checklists by year."""
    if not incomplete_by_year:
        return ""
    css = """
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
    explanation = """
  <div style="margin-top:0;margin-bottom:16px;max-width:600px;box-sizing:border-box;color:#6b7280;font-size:13px;font-weight:normal;line-height:1.6;text-align:left;overflow-wrap:break-word;word-break:break-word;">
    Incomplete travelling and stationary checklists often occur when submitting a checklist in the eBird mobile app. The default setting is incomplete, and if you move quickly through the submission prompts you may accidentally answer "No" to the question asking whether the list is complete.<br><br>
    Incomplete checklists can certainly be intentional and acceptable (for example, when other species were present but not recorded). These checklists tables below are provided so you can review your data for checklists that may have been marked incomplete by mistake. Incidental checklists are not included.<br><br>
    Reference: <a href="https://support.ebird.org/en/support/solutions/articles/48000950859-guide-to-ebird-protocols" target="_blank">Guide to eBird Protocols</a>
  </div>"""
    sections = []
    for y in sorted(incomplete_by_year.keys(), reverse=True):
        items = incomplete_by_year[y]
        rows = []
        for sid, date_str, loc in items:
            loc_esc = html_module.escape(loc, quote=True)
            date_esc = html_module.escape(date_str, quote=True)
            url = f"https://ebird.org/checklist/{sid}" if sid else "#"
            rows.append(f'<tr><td>{date_esc}</td><td><a href="{url}" target="_blank">{loc_esc}</a></td></tr>')
        table_body = "".join(rows)
        table = f'<table class="maint-tbl"><thead><tr><th>Date</th><th>Location</th></tr></thead><tbody>{table_body}</tbody></table>'
        sections.append(f"<details><summary>{y} ({len(items)})</summary>{table}</details>")
    return f"""
<style>{css}</style>
<div style="font-family:sans-serif;font-size:13px;line-height:1.6;max-width:800px;">
<details class="maint-section">
  <summary>Incomplete checklists (Traveling or Stationary)</summary>
{explanation}
  <div style="margin-top:16px;">
{"".join(sections)}
  </div>
</details>
</div>"""
