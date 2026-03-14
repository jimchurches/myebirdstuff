"""
Map rendering helpers for Personal eBird Explorer.

Pure helper functions used by the notebook's map overlay pipeline.
Each function takes explicit inputs and returns a value — no notebook
globals, widget references, or side effects.
"""

import folium
import pandas as pd


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


def build_location_popup_html(loc_name, loc_id, visit_info_html, sightings_html=""):
    """Build the full popup HTML for a single map marker.

    Args:
        loc_name: Display name of the location.
        loc_id: eBird Location ID (used for the lifelist link).
        visit_info_html: Pre-built visit list HTML (from ``build_visit_info_html``).
        sightings_html: Optional species-sighting rows to append after
            the visit list (from ``format_sighting_row``).

    Returns:
        Complete popup HTML string with scroll wrapper.
    """
    loc_url = f"https://ebird.org/lifelist/{loc_id}"
    loc_link = f'<a href="{loc_url}" target="_blank">{loc_name}</a>'
    seen_section = f"<br><b>Seen:</b>{sightings_html}" if sightings_html else ""
    return (
        f'<div class="popup-scroll-wrapper" style="position:relative;">'
        f'<div style="margin-bottom:6px;"><b>{loc_link}</b></div>'
        f'<div style="max-height:300px;overflow-y:auto;">'
        f'<b>Visited:</b><br>{visit_info_html}{seen_section}'
        f'</div></div>'
    )


# ---------------------------------------------------------------------------
# Banner and legend HTML builders
# ---------------------------------------------------------------------------

_BANNER_STYLE = (
    "position:fixed;top:10px;right:10px;z-index:1000;"
    "background:rgba(255,255,255,0.95);padding:10px 14px;"
    "border-radius:6px;box-shadow:0 2px 10px rgba(0,0,0,0.2);"
    "font-family:sans-serif;font-size:13px;line-height:1.5;"
)

_LEGEND_STYLE = (
    "position:fixed;bottom:10px;left:10px;z-index:1000;"
    "background:rgba(255,255,255,0.95);padding:6px 10px;"
    "border-radius:6px;box-shadow:0 2px 10px rgba(0,0,0,0.2);"
    "font-family:sans-serif;font-size:11px;line-height:1.5;"
    "display:flex;flex-wrap:wrap;gap:8px 12px;"
)


def pin_legend_item(color, fill, label):
    """Small coloured circle + label for the map legend."""
    return (
        f'<span style="display:inline-flex;align-items:center;gap:4px;white-space:nowrap;">'
        f'<span style="display:inline-block;width:8px;height:8px;border-radius:50%;'
        f'border:2px solid {color};background:{fill};"></span>'
        f'{label}</span>'
    )


def build_all_species_banner_html(total_checklists, total_species, total_individuals):
    """Return the HTML overlay banner for the all-species map view."""
    return (
        f'<div style="{_BANNER_STYLE}">'
        f'<b>All species</b><br>'
        f'{total_checklists} checklist{"s" if total_checklists != 1 else ""}'
        f' &nbsp;|&nbsp; {total_species} species'
        f' &nbsp;|&nbsp; {total_individuals} individual{"s" if total_individuals != 1 else ""}'
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
    """
    sep = " &nbsp;|&nbsp; "
    line2 = (
        f'{n_checklists} checklist{"s" if n_checklists != 1 else ""}'
        f'{sep}{n_individuals} individual{"s" if n_individuals != 1 else ""}'
    )
    line3_parts = []
    if first_seen_date:
        line3_parts.append(f"First seen: {first_seen_date}")
    if last_seen_date:
        line3_parts.append(f"Last seen: {last_seen_date}")
    line3 = sep.join(line3_parts)
    line4 = f"High count: {high_count_date} ({high_count})"
    return (
        f'<div style="{_BANNER_STYLE}">'
        f'<b>{display_name}</b><br>'
        f'{line2}<br>'
        f'{line3}<br>'
        f'{line4}'
        f'</div>'
    )


def build_legend_html(items):
    """Return the HTML overlay legend from a list of ``(color, fill, label)`` tuples.

    Each tuple is rendered via ``pin_legend_item``.
    """
    parts = "".join(pin_legend_item(c, f, l) for c, f, l in items)
    return f'<div style="{_LEGEND_STYLE}">{parts}</div>'


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
      topShade.style.cssText = 'position:absolute;top:' + scrollTop + 'px;left:0;right:0;height:24px;pointer-events:none;z-index:5;background:linear-gradient(to bottom,rgba(255,255,255,0.95),transparent);';
      var botShade = document.createElement('div');
      botShade.className = 'popup-scroll-shade-bot';
      botShade.style.cssText = 'position:absolute;bottom:0;left:0;right:0;height:24px;pointer-events:none;z-index:5;background:linear-gradient(to top,rgba(255,255,255,0.95),transparent);';
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
# Map factory
# ---------------------------------------------------------------------------

def create_map(map_center, map_style="default"):
    """Create a folium Map centred on *map_center* with the given tile style.

    Supported *map_style* values: ``"default"``, ``"satellite"``,
    ``"google"``, ``"carto"``.  Unknown values fall back to the default
    OpenStreetMap tiles.
    """
    if map_style == "satellite":
        return folium.Map(location=map_center, zoom_start=6, tiles="Esri WorldImagery", attr="Esri")
    elif map_style == "google":
        return folium.Map(
            location=map_center,
            zoom_start=6,
            tiles="https://mt1.google.com/vt/lyrs=y&x={x}&y={y}&z={z}",
            attr="Google",
        )
    elif map_style == "carto":
        return folium.Map(location=map_center, zoom_start=6, tiles="CartoDB Positron", attr="CartoDB")
    else:
        return folium.Map(location=map_center, zoom_start=6)
