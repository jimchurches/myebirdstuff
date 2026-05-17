/** Standalone Leaflet viewer for exported HTML (#222). Popups use pre-rendered export_popup_html from Python. */
(function () {
  "use strict";
  var DEFAULT_CLUSTER = {
    enabled: true,
    max_cluster_radius: 40,
    disable_clustering_at_zoom: 9,
    spiderfy_on_max_zoom: false,
    remove_outside_visible_bounds: false,
  };
  var BASEMAPS = {
    default: {
      url: "https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png",
      opts: { maxZoom: 19, attribution: "&copy; OpenStreetMap contributors" },
    },
    google: {
      url: "https://mt1.google.com/vt/lyrs=y&x={x}&y={y}&z={z}",
      opts: { maxZoom: 22, attribution: "Google" },
    },
    carto: {
      url: "https://{s}.basemaps.cartocdn.com/light_all/{z}/{x}/{y}{r}.png",
      opts: {
        maxZoom: 20,
        subdomains: "abcd",
        attribution: "&copy; OpenStreetMap &copy; CARTO",
      },
    },
  };

  function basemap(style) {
    var s = String(style || "default").toLowerCase();
    return BASEMAPS[s === "google" || s === "carto" ? s : "default"];
  }

  function mergeCluster(raw) {
    var o = {};
    var k;
    for (k in DEFAULT_CLUSTER) o[k] = DEFAULT_CLUSTER[k];
    if (raw && typeof raw === "object") {
      for (k in raw) if (Object.prototype.hasOwnProperty.call(raw, k)) o[k] = raw[k];
    }
    return o;
  }

  function clusterOpts(p) {
    return {
      maxClusterRadius: Number(p.max_cluster_radius) || 40,
      disableClusteringAtZoom: Number(p.disable_clustering_at_zoom) || 9,
      spiderfyOnMaxZoom: !!p.spiderfy_on_max_zoom,
      removeOutsideVisibleBounds: !!p.remove_outside_visible_bounds,
      chunkedLoading: true,
    };
  }

  function parseVp(raw) {
    if (!raw || raw.v !== 1) return null;
    return raw;
  }

  function applyVp(map, vp, layer) {
    var pad = function (n) {
      return L.point(n, n);
    };
    if (!vp) {
      if (layer) {
        try {
          var b = layer.getBounds();
          if (b.isValid()) map.fitBounds(b.pad(0.12));
          else map.setView([20, 0], 2);
        } catch (e) {
          map.setView([20, 0], 2);
        }
      } else map.setView([20, 0], 2);
      return;
    }
    if (vp.mode === "go_to_gps") {
      var d = vp.epsilon_delta;
      map.fitBounds(
        [
          [vp.lat - d, vp.lon - d],
          [vp.lat + d, vp.lon + d],
        ],
        { padding: pad(vp.padding_px), maxZoom: vp.max_zoom, animate: false },
      );
    } else if (vp.mode === "center_zoom") {
      map.setView(vp.center, vp.zoom, { animate: false });
    } else if (vp.mode === "fit_bounds") {
      if (vp.single_point) {
        var e = vp.epsilon_delta;
        map.fitBounds(
          [
            [vp.lat - e, vp.lon - e],
            [vp.lat + e, vp.lon + e],
          ],
          { padding: pad(vp.padding_px), maxZoom: vp.max_zoom, animate: false },
        );
      } else if (vp.pairs && vp.pairs.length) {
        map.fitBounds(
          vp.pairs.map(function (p) {
            return L.latLng(p[0], p[1]);
          }),
          { padding: pad(vp.padding_px), maxZoom: vp.max_zoom, animate: false },
        );
      }
    }
  }

  function pinOpts(props, cm) {
    function hex(s, fb) {
      return typeof s === "string" && /^#[0-9a-fA-F]{6}$/.test(s) ? s : fb;
    }
    var pin = props.circle_pin;
    return {
      radius:
        (pin && pin.radius_px) || (cm && cm.radius_px) || 7,
      weight:
        (pin && pin.stroke_weight) || (cm && cm.stroke_weight) || 1,
      color: hex(pin && pin.stroke_hex, hex(cm && cm.stroke_hex, "#1c2630")),
      fillColor: hex(
        pin && pin.fill_hex,
        hex(cm && cm.fill_hex, hex(props.colour, "#3388ff")),
      ),
      fillOpacity:
        pin && pin.fill_opacity != null ? pin.fill_opacity : 0.88,
    };
  }

  function init() {
    var el = document.getElementById("pebird-map-export-config");
    if (!el || !window.L) return;
    var cfg = JSON.parse(el.textContent || "{}");
    var mapNode = document.getElementById("pebird-export-map");
    if (!mapNode) return;
    var h = Number(cfg.height) || 500;
    mapNode.style.height = h + "px";
    var map = L.map(mapNode, { zoomControl: true, attributionControl: true });
    mapNode.classList.add("pebird-export-map-pane");
    var bm = basemap(cfg.map_style);
    L.tileLayer(bm.url, bm.opts).addTo(map);
    var clusterCfg = mergeCluster(cfg.cluster_options);
    var overlay;
    if (clusterCfg.enabled !== false) {
      var opts = clusterOpts(clusterCfg);
      var ics = cfg.cluster_icon_style;
      if (ics && ics.fills_rgba && ics.fills_rgba.length === 3) {
        opts.iconCreateFunction = function (cluster) {
          var n = cluster.getChildCount();
          var i = n < 10 ? 0 : n < 100 ? 1 : 2;
          var html =
            '<div style="background:' +
            ics.fills_rgba[i] +
            ";border:" +
            ics.border_width_px +
            "px solid " +
            ics.borders_rgba[i] +
            ";box-shadow:0 0 0 " +
            ics.halo_spread_px +
            "px " +
            ics.halos_rgba[i] +
            ';"><span>' +
            n +
            "</span></div>";
          var cls =
            n < 10
              ? "marker-cluster-small"
              : n < 100
                ? "marker-cluster-medium"
                : "marker-cluster-large";
          return L.divIcon({
            html: html,
            className: "marker-cluster " + cls,
            iconSize: L.point(40, 40),
          });
        };
      }
      overlay = L.markerClusterGroup(opts);
    } else {
      overlay = L.layerGroup();
    }
    overlay.addTo(map);
    var gj = L.geoJSON(cfg.geojson || { type: "FeatureCollection", features: [] }, {
      pointToLayer: function (f, latlng) {
        var pr = f.properties || {};
        var o = pinOpts(pr, cfg.circle_marker_style || {});
        var main = L.circleMarker(latlng, {
          radius: o.radius,
          weight: o.weight,
          color: o.color,
          fillColor: o.fillColor,
          fillOpacity: o.fillOpacity,
          stroke: true,
        });
        var halo = pr.highlight_halo_circle;
        if (halo) {
          var ho = pinOpts({ circle_pin: halo }, {});
          var haloM = L.circleMarker(latlng, {
            radius: ho.radius,
            weight: ho.weight,
            color: ho.color,
            fillColor: ho.fillColor,
            fillOpacity: ho.fillOpacity,
            stroke: true,
          });
          return L.layerGroup([haloM, main]);
        }
        return main;
      },
      onEachFeature: function (f, layer) {
        var pr = f.properties || {};
        var html = pr.export_popup_html || pr.name || "Location";
        layer.bindPopup(html, { maxWidth: 420 });
      },
    });
    overlay.addLayer(gj);
    applyVp(map, parseVp(cfg.viewport), gj);
    var vp = parseVp(cfg.viewport);
    if (vp && vp.mode === "go_to_gps") {
      var gm = L.marker([vp.lat, vp.lon], {
        icon: L.divIcon({
          className: "all-locations-gps-marker",
          html: '<span class="all-locations-gps-marker__glyph"></span>',
          iconSize: [30, 40],
          iconAnchor: [15, 40],
        }),
      });
      gm.bindPopup(
        "<div style='font-size:13px'><strong>Temporary GPS marker</strong></div>",
      );
      gm.addTo(map);
    }
    map.invalidateSize();
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }
})();
