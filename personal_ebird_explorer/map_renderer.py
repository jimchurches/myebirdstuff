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
