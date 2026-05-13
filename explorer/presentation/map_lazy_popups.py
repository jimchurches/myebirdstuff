"""Deferred (stub + map-level data) popup fill for **All locations** overlay (#205).

`EXPLORER_MAP_LAZY_POPUPS` (Batch B): markers carry a tiny stub; **full HTML strings** in one JSON
object, applied on Leaflet ``popupopen``.

`EXPLORER_MAP_STRUCTURED_POPUPS` (Batch C / C1): same transport, but values may be **structured**
``al1`` payloads rendered by a small client function → smaller ``html_bytes`` than inlined visit
HTML.

Default remains eager full HTML in each ``folium.Popup`` (both flags off).
"""

from __future__ import annotations

import html as html_module
import json
from typing import Any

import folium
from branca.element import MacroElement
from folium.template import Template

from explorer.presentation.map_structured_popups import ALL_LOCATIONS_POPUP_PAYLOAD_KIND


def _json_for_inline_script(obj: dict[str, Any]) -> str:
    """JSON suitable for embedding inside HTML ``<script>`` (folium-style ``\\u003c`` escapes)."""
    s = json.dumps(obj, ensure_ascii=False, separators=(",", ":"))
    return (
        s.replace("<", "\\u003c")
        .replace(">", "\\u003e")
        .replace("&", "\\u0026")
        .replace("\u2028", "\\u2028")
        .replace("\u2029", "\\u2029")
    )


def all_locations_lazy_popup_stub(location_id: Any) -> str:
    """Minimal popup body so Leaflet can open a popup before rich HTML is injected."""
    lid = html_module.escape(str(location_id), quote=True)
    return (
        f'<div class="pebird-map-popup pebird-lazy-popup-stub" data-pebird-lazy="1" data-location-id="{lid}">'
        f'<span class="pebird-lazy-popup-stub__label">Loading…</span>'
        f"</div>"
    )


def _render_al1_js() -> str:
    """Inline renderer for :data:`ALL_LOCATIONS_POPUP_PAYLOAD_KIND` payloads (keep in sync with Python)."""
    kind = json.dumps(ALL_LOCATIONS_POPUP_PAYLOAD_KIND)
    return f"""
                function renderAl1(p) {{
                    var KIND = {kind};
                    if (!p || p.k !== KIND) return "";
                    function esc(s) {{
                        return String(s).replace(/&/g,"&amp;").replace(/</g,"&lt;").replace(/>/g,"&gt;");
                    }}
                    function escAttr(s) {{
                        return String(s).replace(/&/g,"&amp;").replace(/"/g,"&quot;")
                            .replace(/'/g,"&#39;").replace(/</g,"&lt;").replace(/>/g,"&gt;");
                    }}
                    var locHref = "https://ebird.org/lifelist/" + String(p.i);
                    var locLink = '<a class="pebird-map-popup__location-heading" href="' + locHref
                        + '" target="_blank" rel="noopener noreferrer">' + esc(p.n) + "</a>";
                    var visitParts = [];
                    var vv = p.v || [];
                    for (var j = 0; j < vv.length; j++) {{
                        var pair = vv[j];
                        if (!pair || pair.length < 2) continue;
                        var sid = pair[0] != null ? String(pair[0]) : "";
                        var label = pair[1] != null ? String(pair[1]) : "";
                        var href = "https://ebird.org/checklist/" + escAttr(sid);
                        visitParts.push('<a href="' + href + '" target="_blank" rel="noopener noreferrer">'
                            + esc(label) + "</a>");
                    }}
                    var visitInner = visitParts.join("<br>");
                    var visitedSection = '<div class="pebird-map-popup__visited-block">'
                        + '<div class="pebird-map-popup__section-label">Visited:</div>'
                        + '<div class="pebird-map-popup__visit-dates">' + visitInner + "</div></div>";
                    var m = (typeof p.m === "number" && !isNaN(p.m)) ? p.m : parseInt(p.m, 10);
                    if (!isFinite(m)) m = 4;
                    return '<div class="pebird-map-popup popup-scroll-wrapper" style="position:relative;">'
                        + '<div class="pebird-map-popup__heading-row" style="margin-bottom:' + m + 'px;">'
                        + locLink + '</div><div class="pebird-map-popup__scroll" '
                        + 'style="max-height:300px;overflow-y:auto;">' + visitedSection + "</div></div>";
                }}
    """


class LazyAllLocationsPopupBridge(MacroElement):
    """Attach ``popupopen`` handler: replace stub nodes from *content_by_location_id*.

    Values are either **HTML strings** (Batch B) or structured **dict** payloads with ``k == al1``
    (Batch C).
    """

    _template = Template(
        """
        {% macro script(this, kwargs) %}
        (function() {
            {{this._render_fn|safe}}
            var DATA = {{this._data_json|safe}};
            var map = {{this._parent.get_name()}};
            if (!map || !map.on || !DATA || typeof DATA !== "object") { return; }
            map.on("popupopen", function(e) {
                var popup = e.popup;
                if (!popup || typeof popup.getContent !== "function") { return; }
                var raw = popup.getContent();
                var stub = null;
                if (typeof raw === "string") {
                    var tmp = document.createElement("div");
                    tmp.innerHTML = raw;
                    stub = tmp.querySelector('[data-pebird-lazy="1"]');
                } else if (raw && raw.nodeType === 1) {
                    if (raw.getAttribute && raw.getAttribute("data-pebird-lazy") === "1") {
                        stub = raw;
                    } else if (raw.querySelector) {
                        stub = raw.querySelector('[data-pebird-lazy="1"]');
                    }
                }
                if (!stub) { return; }
                var lid = stub.getAttribute("data-location-id");
                if (!lid || !Object.prototype.hasOwnProperty.call(DATA, lid)) { return; }
                var full = DATA[lid];
                var html = null;
                if (typeof full === "string" && full) {
                    html = full;
                } else if (full && typeof full === "object") {
                    html = renderAl1(full);
                }
                if (!html) { return; }
                if (typeof popup.setContent === "function") {
                    popup.setContent(html);
                }
            });
        })();
        {% endmacro %}
        """
    )

    def __init__(self, content_by_location_id: dict[str, Any]) -> None:
        super().__init__()
        self._name = "LazyAllLocationsPopupBridge"
        self._render_fn = _render_al1_js()
        self._data_json = _json_for_inline_script(content_by_location_id)


def add_lazy_all_locations_popup_bridge(
    map_obj: folium.Map, content_by_location_id: dict[str, Any]
) -> None:
    """No-op when *content_by_location_id* is empty."""
    if not content_by_location_id:
        return
    LazyAllLocationsPopupBridge(content_by_location_id).add_to(map_obj)
