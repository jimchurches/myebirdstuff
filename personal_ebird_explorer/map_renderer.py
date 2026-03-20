"""
Map rendering helpers for Personal eBird Explorer.

Pure helper functions used by the notebook's map overlay pipeline.
Each function takes explicit inputs and returns a value — no notebook
globals, widget references, or side effects.
"""

import html as _html_module
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


def build_location_popup_html(
    loc_name, loc_id, visit_info_html, sightings_html="", lifer_species_html=""
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

    Returns:
        Complete popup HTML string with scroll wrapper.
    """
    loc_url = f"https://ebird.org/lifelist/{loc_id}"
    loc_link = f'<a href="{loc_url}" target="_blank">{loc_name}</a>'
    if lifer_species_html:
        extra_section = f"<br><b>Lifers (first recorded here):</b>{lifer_species_html}"
    elif sightings_html:
        extra_section = f"<br><b>Seen:</b>{sightings_html}"
    else:
        extra_section = ""
    return (
        f'<div class="popup-scroll-wrapper" style="position:relative;">'
        f'<div style="margin-bottom:6px;"><b>{loc_link}</b></div>'
        f'<div style="max-height:300px;overflow-y:auto;">'
        f'<b>Visited:</b><br>{visit_info_html}{extra_section}'
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


def build_all_species_banner_html(
    total_checklists, total_species, total_individuals, date_filter_status=None
):
    """Return the HTML overlay banner for the all-species map view.

    If date_filter_status is provided (e.g. "Date filter: Off" or "Date filter: 2026-01-01 to 2026-12-31"),
    it is shown as a second line in the banner, smaller and lighter so it is less prominent.
    """
    date_line = (
        f'<br><span style="font-size: 0.85em; color: #999;">{date_filter_status}</span>'
        if date_filter_status
        else ""
    )
    return (
        f'<div style="{_BANNER_STYLE}">'
        f'<b>All species</b><br>'
        f'{total_checklists} checklist{"s" if total_checklists != 1 else ""}'
        f' &nbsp;|&nbsp; {total_species} species'
        f' &nbsp;|&nbsp; {total_individuals} individual{"s" if total_individuals != 1 else ""}'
        f'{date_line}'
        f'</div>'
    )


def build_lifer_locations_banner_html(
    n_lifer_species, n_locations, date_filter_status=None
):
    """Banner for lifer-only map mode (refs #71)."""
    date_line = (
        f'<br><span style="font-size: 0.85em; color: #999;">{date_filter_status}</span>'
        if date_filter_status
        else ""
    )
    loc_w = "locations" if n_locations != 1 else "location"
    return (
        f'<div style="{_BANNER_STYLE}">'
        f'<b>Lifer locations</b><br>'
        f'{n_lifer_species} lifer species'
        f' &nbsp;|&nbsp; {n_locations} {loc_w}'
        f'{date_line}'
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
    """
    sep = " &nbsp;|&nbsp; "
    title_esc = _html_module.escape(str(display_name), quote=True)
    # Match other tabs: same colour as text, dotted underline (no blue link)
    _link_style = "color:inherit;text-decoration:underline dotted;text-underline-offset:2px;"
    title_html = (
        f'<a href="{_html_module.escape(species_url, quote=True)}" target="_blank" rel="noopener" style="{_link_style}">{title_esc}</a>'
        if species_url
        else title_esc
    )
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
    date_line = (
        f'<br><span style="font-size: 0.85em; color: #999;">{date_filter_status}</span>'
        if date_filter_status
        else ""
    )
    return (
        f'<div style="{_BANNER_STYLE}">'
        f'<b>{title_html}</b><br>'
        f'{line2}<br>'
        f'{line3}<br>'
        f'{line4}'
        f'{date_line}'
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
