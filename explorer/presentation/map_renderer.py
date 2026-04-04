"""
Map rendering helpers for Personal eBird Explorer.

Pure helper functions used by the map overlay pipeline.
Each function takes explicit inputs and returns a value — no UI
globals, widget references, or side effects.

Popup HTML is plain strings passed to ``folium.Popup``; typography and colours are **not** locked to
Leaflet defaults: ``map_overlay_theme_stylesheet`` (popups + top/bottom map chrome, injected once per map
in ``map_controller``) and ``EXPLORER_UI_*`` constants align with the Streamlit app and
repo-root ``.streamlit/config.toml`` (refs #70).
"""

import html as _html_module

import folium
import pandas as pd
from branca.element import MacroElement
from folium.template import Template

from explorer.app.streamlit.defaults import (
    MAP_HEIGHT_PX_DEFAULT,
    MAP_HEIGHT_PX_MAX,
    MAP_HEIGHT_PX_MIN,
    MAP_LEGEND_PIN_BORDER_PX,
    MAP_LEGEND_PIN_DOT_PX,
)

# ---------------------------------------------------------------------------
# UI theme (aligned with Streamlit Checklist Statistics HTML + ``.streamlit/config.toml``; refs #70)
# ---------------------------------------------------------------------------

EXPLORER_UI_FONT_STACK = (
    '"Source Sans Pro", -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif'
)
EXPLORER_UI_TEXT_COLOR = "#1a2e22"
EXPLORER_UI_PRIMARY_GREEN = "#1f6f54"
EXPLORER_UI_PANEL_BG = "rgba(250, 252, 250, 0.97)"
EXPLORER_UI_PANEL_BG_SOLID = "#eef4f0"
EXPLORER_UI_MUTED = "rgba(26, 46, 34, 0.55)"
EXPLORER_UI_BORDER_PANEL = "rgba(31, 111, 84, 0.18)"


def map_popup_theme_stylesheet() -> str:
    """Return a ``<style>`` block for Leaflet popups (injected once per map via ``branca.element.Element``).

    Targets ``.pebird-map-popup`` wrappers from ``build_location_popup_html``. Font size matches the
    checklist HTML tab panel (~0.8125rem); links use the same primary green as Streamlit theme fallbacks.
    """
    return f"""
<style>
.leaflet-popup-content .pebird-map-popup,
.leaflet-popup-content .pebird-map-popup * {{
  box-sizing: border-box;
}}
.pebird-map-popup {{
  font-family: {EXPLORER_UI_FONT_STACK};
  font-size: 0.8125rem;
  line-height: 1.45;
  font-weight: 400;
  color: {EXPLORER_UI_TEXT_COLOR};
  -webkit-font-smoothing: antialiased;
  -moz-osx-font-smoothing: grayscale;
}}
.pebird-map-popup b {{
  font-weight: 600;
}}
.pebird-map-popup a {{
  color: {EXPLORER_UI_PRIMARY_GREEN};
  text-decoration: none;
  font-weight: 400;
}}
.pebird-map-popup a:hover {{
  text-decoration: underline;
}}
/* Location title link: heavier than body links (refs #70). */
.pebird-map-popup a.pebird-map-popup__location-heading {{
  font-weight: 600;
}}
</style>
"""


def map_banner_and_legend_theme_stylesheet() -> str:
    """CSS for fixed top banner + bottom legend (same visual language as Streamlit sidebar)."""
    return f"""
<style>
.pebird-map-banner,
.pebird-map-legend {{
  box-sizing: border-box;
  font-family: {EXPLORER_UI_FONT_STACK};
  font-size: 0.9375rem;
  line-height: 1.5;
  font-weight: 400;
  color: {EXPLORER_UI_TEXT_COLOR};
  -webkit-font-smoothing: antialiased;
  -moz-osx-font-smoothing: grayscale;
  background: linear-gradient(180deg, {EXPLORER_UI_PANEL_BG_SOLID} 0%, {EXPLORER_UI_PANEL_BG} 100%);
  border: 1px solid {EXPLORER_UI_BORDER_PANEL};
  border-radius: 8px;
  box-shadow: 0 1px 2px rgba(26, 46, 34, 0.06), 0 4px 16px rgba(26, 46, 34, 0.08);
}}
.pebird-map-banner {{
  padding: 12px 16px;
  max-width: min(420px, calc(100vw - 24px));
}}
.pebird-map-banner__title {{
  display: block;
  font-size: 1.05rem;
  font-weight: 600;
  letter-spacing: -0.01em;
  color: {EXPLORER_UI_PRIMARY_GREEN};
  margin: 0 0 6px 0;
}}
.pebird-map-banner__title a {{
  color: {EXPLORER_UI_PRIMARY_GREEN};
  text-decoration: none;
  font-weight: 600;
}}
.pebird-map-banner__title a:hover {{
  text-decoration: underline;
  text-underline-offset: 2px;
}}
.pebird-map-banner__stats {{
  font-weight: 400;
  margin: 0;
}}
.pebird-map-banner__stats a {{
  color: inherit;
  text-decoration: none;
  font-weight: inherit;
}}
.pebird-map-banner__stats a:hover {{
  text-decoration: underline;
  text-underline-offset: 2px;
}}
.pebird-map-banner__sep {{
  color: {EXPLORER_UI_MUTED};
  font-weight: 400;
  padding: 0 0.2em;
}}
.pebird-map-banner__muted {{
  display: block;
  font-size: 0.88em;
  font-weight: 400;
  color: {EXPLORER_UI_MUTED};
  margin-top: 6px;
}}
.pebird-map-legend {{
  padding: 8px 12px;
  display: flex;
  flex-wrap: wrap;
  gap: 8px 12px;
  font-size: 0.8125rem;
}}
</style>
"""


def map_overlay_theme_stylesheet() -> str:
    """All injected map UI chrome: Leaflet popups + top banner + bottom legend (refs #70)."""
    return map_popup_theme_stylesheet() + map_banner_and_legend_theme_stylesheet()


# ---------------------------------------------------------------------------
# Popup content formatters
# ---------------------------------------------------------------------------

def format_visit_time(r):
    """Format a single visit record's date/time for popup display.

    Uses the ``datetime`` column when available so that entries without a
    recorded time sort consistently as 23:59.  Falls back to separate
    ``Date`` and ``Time`` columns.
    """
    if "datetime" in r.index and pd.notna(r.get("datetime")):
        return r["datetime"].strftime("%Y-%m-%d %H:%M")
    d = r["Date"].strftime("%Y-%m-%d") if pd.notna(r["Date"]) else "?"
    t = str(r["Time"]) if pd.notna(r["Time"]) else "unknown"
    return f"{d} {t}"


def format_sighting_row(r):
    """Format a single sighting row as popup HTML.

    Returns an HTML fragment with date, time, species, count, a checklist
    link, and an optional Macaulay Library media link.
    """
    if "datetime" in r.index and pd.notna(r.get("datetime")):
        date_str = r["datetime"].strftime("%Y-%m-%d")
        time_str = r["datetime"].strftime("%H:%M")
    else:
        date_str = r["Date"].strftime("%Y-%m-%d") if pd.notna(r["Date"]) else "unknown"
        time_str = str(r["Time"]) if pd.notna(r["Time"]) else "unknown"
    text = f"{date_str} {time_str} — {r['Common Name']} ({r['Count']})"
    cid = r.get("Submission ID", "")
    checklist_url = f"https://ebird.org/checklist/{cid}" if cid else "#"
    media_html = ""
    ml = r.get("ML Catalog Numbers")
    if pd.notna(ml) and str(ml).strip():
        first_ml = str(ml).strip().split()[0]
        media_html = (
            f' <a href="https://macaulaylibrary.org/asset/{first_ml}"'
            f' target="_blank" title="View media">📷</a>'
        )
    return f'<br><a href="{checklist_url}" target="_blank">{text}</a>{media_html}'


# ---------------------------------------------------------------------------
# Popup HTML builders
# ---------------------------------------------------------------------------

def build_visit_info_html(visit_records, format_time_fn):
    """Build the visit-list HTML fragment for a location popup.

    Args:
        visit_records: DataFrame of deduplicated visit rows, already sorted.
        format_time_fn: Callable that formats a single row's date/time
            (e.g. ``format_visit_time``).

    Returns:
        HTML string of checklist links separated by ``<br>``, or ``""``
        if *visit_records* is empty.
    """
    if visit_records.empty:
        return ""
    return "<br>".join(
        f'<a href="https://ebird.org/checklist/{r["Submission ID"]}" target="_blank">'
        f"{format_time_fn(r)}</a>"
        for _, r in visit_records.iterrows()
    )


def build_location_popup_html(
    loc_name,
    loc_id,
    visit_info_html,
    sightings_html="",
    lifer_species_html="",
    show_visit_history: bool = True,
    lifer_heading_html: str = "<b>Lifers (first recorded here):</b>",
    location_heading_margin_px: int = 6,
):
    """Build the full popup HTML for a single map marker.

    Args:
        loc_name: Display name of the location.
        loc_id: eBird Location ID (used for the lifelist link).
        visit_info_html: Pre-built visit list HTML (from ``build_visit_info_html``).
        sightings_html: Optional species-sighting rows to append after
            the visit list (from ``format_sighting_row``). Ignored if
            *lifer_species_html* is set.
        lifer_species_html: Optional HTML fragment listing lifer species first
            recorded at this location (refs #71). When non-empty, shown instead
            of the *sightings_html* "Seen:" block.
        show_visit_history: When False, omit the "Visited:" section entirely
            (used by the lifer-map popup simplification; refs #104).
        lifer_heading_html: Optional heading HTML prepended when *lifer_species_html*
            is provided. Pass ``""`` to omit the heading (used by lifer-map popups).

    Returns:
        Complete popup HTML string with scroll wrapper.
    """
    loc_url = f"https://ebird.org/lifelist/{loc_id}"
    esc_loc = _html_module.escape(str(loc_name), quote=False)
    loc_link = (
        f'<a class="pebird-map-popup__location-heading" href="{loc_url}" '
        f'target="_blank" rel="noopener noreferrer">{esc_loc}</a>'
    )
    if lifer_species_html:
        extra_section = f"{lifer_heading_html}{lifer_species_html}" if lifer_heading_html else lifer_species_html
    elif sightings_html:
        extra_section = f"<b>Seen:</b>{sightings_html}"
    else:
        extra_section = ""
    visited_section = f"<b>Visited:</b><br>{visit_info_html}" if show_visit_history else ""
    # If both sections are present, add a separator line break.
    if visited_section and extra_section:
        inner_html = visited_section + "<br>" + extra_section
    else:
        inner_html = visited_section + extra_section
    return (
        f'<div class="pebird-map-popup popup-scroll-wrapper" style="position:relative;">'
        f'<div style="margin-bottom:{int(location_heading_margin_px)}px;">{loc_link}</div>'
        f'<div style="max-height:300px;overflow-y:auto;">'
        f"{inner_html}"
        f'</div></div>'
    )


# ---------------------------------------------------------------------------
# Banner and legend HTML builders
# ---------------------------------------------------------------------------

_BANNER_POSITION = "position:fixed;top:10px;right:10px;z-index:1000;"

_LEGEND_POSITION = "position:fixed;bottom:10px;left:10px;z-index:1000;"


def _banner_sep() -> str:
    """Muted separator between stat clauses (aligned with app chrome)."""
    return '<span class="pebird-map-banner__sep" aria-hidden="true">·</span>'


def _banner_muted_line(text: str | None) -> str:
    if not text:
        return ""
    esc = _html_module.escape(str(text), quote=False)
    return f'<span class="pebird-map-banner__muted">{esc}</span>'

def pin_legend_item(color, fill, label):
    """Small coloured circle + label for the map legend."""
    d = MAP_LEGEND_PIN_DOT_PX
    bw = MAP_LEGEND_PIN_BORDER_PX
    return (
        f'<span style="display:inline-flex;align-items:center;gap:4px;white-space:nowrap;">'
        f'<span style="display:inline-block;width:{d}px;height:{d}px;border-radius:50%;'
        f'border:{bw}px solid {color};background:{fill};"></span>'
        f'{label}</span>'
    )


def build_all_species_banner_html(
    total_checklists, total_species, total_individuals, date_filter_status=None
):
    """Return the HTML overlay banner for the all-species map view.

    If date_filter_status is provided (e.g. "Date filter: Off" or "Date filter: 2026-01-01 to 2026-12-31"),
    it is shown as a second line in the banner, smaller and lighter so it is less prominent.
    """
    sep = _banner_sep()
    stats = (
        f'{total_checklists} checklist{"s" if total_checklists != 1 else ""}'
        f'{sep}{total_species} species'
        f'{sep}{total_individuals} individual{"s" if total_individuals != 1 else ""}'
    )
    date_block = _banner_muted_line(date_filter_status) if date_filter_status else ""
    return (
        f'<div class="pebird-map-banner" style="{_BANNER_POSITION}">'
        f'<span class="pebird-map-banner__title">All species</span>'
        f'<div class="pebird-map-banner__stats">{stats}</div>'
        f'{date_block}'
        f'</div>'
    )


def build_lifer_locations_banner_html(
    n_lifer_species, n_locations, date_filter_status=None, include_subspecies: bool = False
):
    """Banner for lifer-only map mode (refs #71)."""
    sep = _banner_sep()
    loc_w = "locations" if n_locations != 1 else "location"
    stats = (
        f'{n_lifer_species} lifer{"s" if n_lifer_species != 1 else ""}'
        f'{sep}{n_locations} {loc_w}'
    )
    note = _banner_muted_line("Sub-species included") if include_subspecies else ""
    date_block = _banner_muted_line(date_filter_status) if date_filter_status else ""
    if note and date_block:
        muted_stack = f"{note}<br>{date_block}"
    else:
        muted_stack = note or date_block
    return (
        f'<div class="pebird-map-banner" style="{_BANNER_POSITION}">'
        f'<span class="pebird-map-banner__title">Lifer locations</span>'
        f'<div class="pebird-map-banner__stats">{stats}</div>'
        f'{muted_stack}'
        f'</div>'
    )


def build_species_banner_html(
    display_name,
    n_checklists,
    n_individuals,
    high_count,
    first_seen_date="",
    last_seen_date="",
    high_count_date="",
    date_filter_status=None,
    species_url=None,
    first_seen_checklist_url: str | None = None,
    last_seen_checklist_url: str | None = None,
    high_count_checklist_url: str | None = None,
):
    """Return the HTML overlay banner for a species-filtered map view.

    Args:
        display_name: Species name shown as the banner title (common or scientific).
        n_checklists: Number of checklists containing this species.
        n_individuals: Total individuals counted.
        high_count: Maximum single-checklist count.
        first_seen_date: Formatted date string for first sighting (empty to omit).
        last_seen_date: Formatted date string for most recent sighting (empty to omit).
        high_count_date: Formatted date string when high count was recorded (empty to omit).
        date_filter_status: Optional string (e.g. "Date filter: Off" or range) shown on last line, smaller and lighter.
        species_url: Optional eBird species page URL; if set, display_name is rendered as a clickable link (refs #56).
        first_seen_checklist_url: Optional eBird checklist URL for the first-seen date (refs #XXX).
        last_seen_checklist_url: Optional eBird checklist URL for the last-seen date (refs #XXX).
        high_count_checklist_url: Optional eBird checklist URL for the high-count date (refs #XXX).
    """
    def _maybe_link(label: str, url: str | None) -> str:
        if not url:
            return _html_module.escape(str(label), quote=False)
        esc_url = _html_module.escape(str(url), quote=True)
        esc_label = _html_module.escape(str(label), quote=False)
        return f'<a href="{esc_url}" target="_blank" rel="noopener">{esc_label}</a>'

    title_esc = _html_module.escape(str(display_name), quote=False)
    title_html = (
        f'<a href="{_html_module.escape(species_url, quote=True)}" target="_blank" rel="noopener">'
        f'{title_esc}</a>'
        if species_url
        else title_esc
    )
    sep_dot = _banner_sep()
    line2 = (
        f'{n_checklists} checklist{"s" if n_checklists != 1 else ""}'
        f'{sep_dot}{n_individuals} individual{"s" if n_individuals != 1 else ""}'
    )
    line3_parts = []
    if first_seen_date:
        line3_parts.append(f"First seen: {_maybe_link(first_seen_date, first_seen_checklist_url)}")
    if last_seen_date:
        line3_parts.append(f"Last seen: {_maybe_link(last_seen_date, last_seen_checklist_url)}")
    line3 = sep_dot.join(line3_parts)
    line4_date = _maybe_link(high_count_date, high_count_checklist_url) if high_count_date else ""
    line4 = f"High count: {line4_date} ({high_count})"
    date_block = _banner_muted_line(date_filter_status) if date_filter_status else ""
    return (
        f'<div class="pebird-map-banner" style="{_BANNER_POSITION}">'
        f'<span class="pebird-map-banner__title">{title_html}</span>'
        f'<div class="pebird-map-banner__stats">{line2}<br>{line3}<br>{line4}</div>'
        f'{date_block}'
        f'</div>'
    )


def build_legend_html(items):
    """Return the HTML overlay legend from a list of ``(color, fill, label)`` tuples.

    Each tuple is rendered via ``pin_legend_item``.
    """
    parts = "".join(pin_legend_item(c, f, l) for c, f, l in items)
    return f'<div class="pebird-map-legend" style="{_LEGEND_POSITION}">{parts}</div>'


# ---------------------------------------------------------------------------
# Popup scroll behaviour (injected JS)
# ---------------------------------------------------------------------------

def popup_scroll_script(scroll_hint, scroll_to_bottom):
    """Return an HTML ``<script>`` block that adds scroll hints to map popups.

    Args:
        scroll_hint: One of ``"chevron"``, ``"shading"``, ``"both"``, or
            ``None``/falsy to disable.
        scroll_to_bottom: If True, popups scroll to the bottom on open
            (most-recent-first ordering).
    """
    hint_js = repr(scroll_hint)
    to_bottom_js = "true" if scroll_to_bottom else "false"
    return f"""
<script>
(function() {{
  var HINT = {hint_js};
  var SCROLL_TO_BOTTOM = {to_bottom_js};

  function updateHints(scrollable, wrapper) {{
    var st = scrollable.scrollTop;
    var maxScroll = scrollable.scrollHeight - scrollable.clientHeight;
    var hasMoreAbove = st > 0;
    var hasMoreBelow = st < maxScroll;

    if (HINT === 'chevron' || HINT === 'both') {{
      var upEl = wrapper.querySelector('.popup-scroll-up');
      var downEl = wrapper.querySelector('.popup-scroll-down');
      if (upEl) upEl.style.visibility = hasMoreAbove ? 'visible' : 'hidden';
      if (downEl) downEl.style.visibility = hasMoreBelow ? 'visible' : 'hidden';
    }}
    if (HINT === 'shading' || HINT === 'both') {{
      var topShade = wrapper.querySelector('.popup-scroll-shade-top');
      var botShade = wrapper.querySelector('.popup-scroll-shade-bot');
      if (topShade) topShade.style.visibility = hasMoreAbove ? 'visible' : 'hidden';
      if (botShade) botShade.style.visibility = hasMoreBelow ? 'visible' : 'hidden';
    }}
  }}

  function setupPopup(scrollable, wrapper) {{
    var hasOverflow = scrollable.scrollHeight > scrollable.clientHeight;
    if (!hasOverflow) return;

    scrollable.scrollTop = SCROLL_TO_BOTTOM ? scrollable.scrollHeight : 0;

    var scrollTop = scrollable.offsetTop;
    if (HINT === 'chevron' || HINT === 'both') {{
      var up = document.createElement('div');
      up.className = 'popup-scroll-up';
      up.style.cssText = 'position:absolute;top:' + scrollTop + 'px;left:50%;transform:translateX(-50%);font-size:10px;color:#888;pointer-events:none;z-index:10;';
      up.textContent = '\\u25B2';
      var down = document.createElement('div');
      down.className = 'popup-scroll-down';
      down.style.cssText = 'position:absolute;bottom:8px;left:50%;transform:translateX(-50%);font-size:10px;color:#888;pointer-events:none;z-index:10;';
      down.textContent = '\\u25BC';
      wrapper.appendChild(up);
      wrapper.appendChild(down);
    }}
    if (HINT === 'shading' || HINT === 'both') {{
      var topShade = document.createElement('div');
      topShade.className = 'popup-scroll-shade-top';
      topShade.style.cssText = 'position:absolute;top:' + scrollTop + 'px;left:0;right:0;height:24px;pointer-events:none;z-index:5;background:linear-gradient(to bottom,rgba(250,252,250,0.97),transparent);';
      var botShade = document.createElement('div');
      botShade.className = 'popup-scroll-shade-bot';
      botShade.style.cssText = 'position:absolute;bottom:0;left:0;right:0;height:24px;pointer-events:none;z-index:5;background:linear-gradient(to top,rgba(250,252,250,0.97),transparent);';
      wrapper.appendChild(topShade);
      wrapper.appendChild(botShade);
    }}

    updateHints(scrollable, wrapper);
    scrollable.addEventListener('scroll', function() {{ updateHints(scrollable, wrapper); }});
  }}

  function onPopupOpen() {{
    setTimeout(function() {{
      var scrollable = document.querySelector('.leaflet-popup-content div[style*="overflow-y"]');
      if (!scrollable) return;
      var wrapper = scrollable.parentElement;
      if (wrapper.dataset.popupSetup) return;
      wrapper.dataset.popupSetup = '1';
      setupPopup(scrollable, wrapper);
    }}, 100);
  }}

  var observer = new MutationObserver(function(mutations) {{
    for (var i = 0; i < mutations.length; i++) {{
      for (var j = 0; j < mutations[i].addedNodes.length; j++) {{
        var node = mutations[i].addedNodes[j];
        if (node.nodeType === 1 && node.classList && node.classList.contains('leaflet-popup')) {{
          onPopupOpen();
          return;
        }}
      }}
    }}
  }});
  observer.observe(document.body, {{ childList: true, subtree: true }});
}})();
</script>
"""


# ---------------------------------------------------------------------------
# Map data preparation
# ---------------------------------------------------------------------------

def resolve_lifer_last_seen(
    selected_species,
    seen_location_ids,
    lifer_lookup,
    last_seen_lookup,
    lifer_lookup_taxon,
    last_seen_lookup_taxon,
    base_species_fn,
    mark_lifer=True,
    mark_last_seen=True,
):
    """Resolve which location IDs are the lifer and last-seen for a species.

    Uses taxon-level lookup for subspecies (scientific name with 3+ parts),
    falling back to the base-species lookup.  Only returns IDs that are in
    *seen_location_ids*.  ``last_seen_location`` is never the same as
    ``lifer_location``.

    Args:
        selected_species: Scientific name of the selected species.
        seen_location_ids: Set of Location IDs where the species was observed.
        lifer_lookup: Dict mapping base species -> lifer Location ID.
        last_seen_lookup: Dict mapping base species -> last-seen Location ID.
        lifer_lookup_taxon: Dict mapping taxon key -> lifer Location ID.
        last_seen_lookup_taxon: Dict mapping taxon key -> last-seen Location ID.
        base_species_fn: Callable to extract base species from a scientific name.
        mark_lifer: Whether to resolve lifer location.
        mark_last_seen: Whether to resolve last-seen location.

    Returns:
        ``(lifer_location, last_seen_location)`` — each is a Location ID
        string or None.
    """
    lifer_location = None
    last_seen_location = None
    sci_parts = (selected_species or "").strip().split()
    is_subspecies = len(sci_parts) >= 3
    taxon_key = selected_species.strip().lower() if selected_species else None

    if mark_lifer:
        true_lifer_loc = None
        if is_subspecies and taxon_key:
            true_lifer_loc = lifer_lookup_taxon.get(taxon_key)
        if true_lifer_loc is None and sci_parts:
            base = base_species_fn(selected_species)
            true_lifer_loc = lifer_lookup.get(base) if base else None
        if true_lifer_loc in seen_location_ids:
            lifer_location = true_lifer_loc

    if mark_last_seen:
        true_last_loc = None
        if is_subspecies and taxon_key:
            true_last_loc = last_seen_lookup_taxon.get(taxon_key)
        if true_last_loc is None and sci_parts:
            base = base_species_fn(selected_species)
            true_last_loc = last_seen_lookup.get(base) if base else None
        if true_last_loc in seen_location_ids and true_last_loc != lifer_location:
            last_seen_location = true_last_loc

    return lifer_location, last_seen_location


def classify_locations(location_data, seen_location_ids, lifer_location, last_seen_location):
    """Tag and sort locations for map marker drawing order.

    Returns a copy of *location_data* with three boolean columns added:

    - ``has_species_match`` — location has sightings of the selected species
    - ``is_lifer`` — location is the lifer location
    - ``is_last_seen`` — location is the last-seen location

    Rows are sorted so that lifer is drawn last (on top), then last-seen,
    then species matches, then non-matching locations.
    """
    loc = location_data.copy()
    loc["has_species_match"] = loc["Location ID"].isin(seen_location_ids)
    loc["is_lifer"] = loc["Location ID"] == lifer_location
    loc["is_last_seen"] = loc["Location ID"] == last_seen_location
    return loc.sort_values(
        by=["has_species_match", "is_lifer", "is_last_seen"],
        ascending=[True, True, True],
    )


# ---------------------------------------------------------------------------
# Map factory
# ---------------------------------------------------------------------------


class _ZoomLevelDebugOverlay(MacroElement):
    """Leaflet control showing live zoom (debug; toggle via ``MAP_DEBUG_SHOW_ZOOM_LEVEL`` in defaults).

    Uses **bottom-right** so it stays clear of the fixed **bottom-left** legend
    (``_LEGEND_POSITION`` / ``pebird-map-legend``), which would cover a ``bottomleft`` control.
    """

    _template = Template(
        """
        {% macro script(this, kwargs) %}
        (function() {
            var map = {{ this._parent.get_name() }};
            var div = L.DomUtil.create('div', 'ebird-zoom-debug-overlay');
            div.style.cssText = [
                'background:rgba(255,255,255,0.92)',
                'border:1px solid #1f6f54',
                'padding:4px 8px',
                'font:12px/1.25 ui-monospace, SFMono-Regular, Menlo, monospace',
                'border-radius:4px',
                'box-shadow:0 1px 3px rgba(0,0,0,0.2)',
                'min-width:7ch',
                'text-align:right',
                'z-index:1001'
            ].join(';');
            var ctrl = L.control({position: 'bottomright'});
            ctrl.onAdd = function() { return div; };
            ctrl.addTo(map);
            function update() {
                div.textContent = 'zoom: ' + map.getZoom();
            }
            map.on('zoomend', update);
            map.on('zoom', update);
            update();
        })();
        {% endmacro %}
        """
    )

    def __init__(self) -> None:
        super().__init__()
        self._name = "ZoomLevelDebugOverlay"


def add_zoom_level_debug_overlay(map_obj: folium.Map, *, enabled: bool) -> None:
    """If *enabled*, add a small live zoom readout (for tuning clustering). No-op when *enabled* is False."""
    if not enabled:
        return
    _ZoomLevelDebugOverlay().add_to(map_obj)


def create_map(
    map_center,
    map_style="default",
    *,
    height_px: int | float | None = None,
):
    """Create a folium Map centred on *map_center* with the given tile style.

    Supported *map_style* values: ``"default"``, ``"google"``, ``"carto"``.
    Unknown values fall back to the default OpenStreetMap tiles.

    *height_px*: pixel height for the map pane. Folium defaults to ``100%``, which
    depends on parent layout; inside ``streamlit-folium`` that can collapse to a thin
    strip. Pass the same value as the Streamlit **Map height** slider when embedding.
    """
    # Default initial zoom for first render. Lower = more zoomed out.
    zoom_start = 5
    h = float(height_px if height_px is not None else MAP_HEIGHT_PX_DEFAULT)
    h = max(float(MAP_HEIGHT_PX_MIN), min(float(MAP_HEIGHT_PX_MAX), h))
    common = {"location": map_center, "zoom_start": zoom_start, "height": h, "width": "100%"}
    if map_style == "google":
        return folium.Map(
            tiles="https://mt1.google.com/vt/lyrs=y&x={x}&y={y}&z={z}",
            attr="Google",
            **common,
        )
    elif map_style == "carto":
        return folium.Map(tiles="CartoDB Positron", attr="CartoDB", **common)
    else:
        return folium.Map(**common)
