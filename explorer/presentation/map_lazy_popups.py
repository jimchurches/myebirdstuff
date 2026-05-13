"""Lazy (on-open) popup fill for **All locations** overlay (#205 Batch B).

Markers carry a tiny stub; full rich HTML lives in a single JSON object and is applied on
Leaflet ``popupopen``. Default remains eager full HTML in each ``folium.Popup`` (flag off).
"""

from __future__ import annotations

import html as html_module
import json
from typing import Any

import folium
from branca.element import MacroElement
from folium.template import Template


def _json_for_inline_script(obj: dict[str, str]) -> str:
    """JSON suitable for embedding inside HTML ``<script>`` (folium-style ``\\u003c`` escapes)."""
    s = json.dumps(obj, ensure_ascii=False)
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


class LazyAllLocationsPopupBridge(MacroElement):
    """Attach ``popupopen`` handler: replace stub nodes with full HTML from *html_by_location_id*."""

    _template = Template(
        """
        {% macro script(this, kwargs) %}
        (function() {
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
                if (typeof full !== "string" || !full) { return; }
                if (typeof popup.setContent === "function") {
                    popup.setContent(full);
                }
            });
        })();
        {% endmacro %}
        """
    )

    def __init__(self, html_by_location_id: dict[str, str]) -> None:
        super().__init__()
        self._name = "LazyAllLocationsPopupBridge"
        self._data_json = _json_for_inline_script(html_by_location_id)


def add_lazy_all_locations_popup_bridge(
    map_obj: folium.Map, html_by_location_id: dict[str, str]
) -> None:
    """No-op when *html_by_location_id* is empty."""
    if not html_by_location_id:
        return
    LazyAllLocationsPopupBridge(html_by_location_id).add_to(map_obj)
