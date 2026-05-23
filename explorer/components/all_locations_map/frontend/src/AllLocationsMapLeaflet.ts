/** Basemap, viewport, clusters, marker styles, head injection (R14 split). */

import type { MutableRefObject } from "react";
import L from "leaflet";
import {
  parseViewportV1,
  type ViewportV1GoToGps,
} from "./mapComponentParsers";
import {
  DEFAULT_CLUSTER_PAYLOAD,
  type ClusterIconStylePayload,
  type ClusterOptionsPayload,
  type CircleMarkerStylePayload,
} from "./allLocationsMapTypes";
import {
  GO_TO_GPS_POPUP_HTML,
  POPUP_BIND_OPTIONS,
} from "./AllLocationsMapPopupSizing";


/** Must stay aligned with `create_map` in `explorer/presentation/map_renderer.py`. */
type BasemapId = "default" | "google" | "carto";

function normalizeBasemapId(raw: string | undefined): BasemapId {
  const s = String(raw ?? "default").trim().toLowerCase();
  if (s === "google" || s === "carto") {
    return s;
  }
  return "default";
}

const ALL_LOCATIONS_BASEMAPS: Record<BasemapId, { url: string; opts: L.TileLayerOptions }> = {
  default: {
    url: "https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png",
    opts: {
      maxZoom: 19,
      attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>',
    },
  },
  google: {
    url: "https://mt1.google.com/vt/lyrs=y&x={x}&y={y}&z={z}",
    opts: {
      maxZoom: 22,
      attribution: "Google",
    },
  },
  carto: {
    url: "https://{s}.basemaps.cartocdn.com/light_all/{z}/{x}/{y}{r}.png",
    opts: {
      maxZoom: 20,
      subdomains: "abcd",
      attribution:
        '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors &copy; <a href="https://carto.com/attributions">CARTO</a>',
    },
  },
};

export function applyBasemapToMap(
  map: L.Map,
  mapStyleRaw: string | undefined,
  baseTileRef: React.MutableRefObject<L.TileLayer | null>,
): void {
  const id = normalizeBasemapId(mapStyleRaw);
  const spec = ALL_LOCATIONS_BASEMAPS[id];
  if (baseTileRef.current) {
    map.removeLayer(baseTileRef.current);
    baseTileRef.current = null;
  }
  const tile = L.tileLayer(spec.url, spec.opts);
  tile.addTo(map);
  tile.bringToBack();
  baseTileRef.current = tile;
}

export function mergeClusterPayload(raw: ClusterOptionsPayload | undefined): ClusterOptionsPayload {
  return { ...DEFAULT_CLUSTER_PAYLOAD, ...raw };
}

function toLeafletClusterOptions(payload: ClusterOptionsPayload): L.MarkerClusterGroupOptions {
  return {
    maxClusterRadius: Number(payload.max_cluster_radius) || DEFAULT_CLUSTER_PAYLOAD.max_cluster_radius!,
    disableClusteringAtZoom:
      Number(payload.disable_clustering_at_zoom) ||
      DEFAULT_CLUSTER_PAYLOAD.disable_clustering_at_zoom!,
    spiderfyOnMaxZoom: Boolean(payload.spiderfy_on_max_zoom),
    removeOutsideVisibleBounds: Boolean(payload.remove_outside_visible_bounds),
    chunkedLoading: true,
  };
}

function parseClusterIconStyle(raw: unknown): ClusterIconStylePayload | null {
  if (!raw || typeof raw !== "object") {
    return null;
  }
  const o = raw as Record<string, unknown>;
  const fills = o.fills_rgba;
  const borders = o.borders_rgba;
  const halos = o.halos_rgba;
  if (!Array.isArray(fills) || !Array.isArray(borders) || !Array.isArray(halos)) {
    return null;
  }
  if (fills.length !== 3 || borders.length !== 3 || halos.length !== 3) {
    return null;
  }
  if (!fills.every((x) => typeof x === "string")) {
    return null;
  }
  if (!borders.every((x) => typeof x === "string")) {
    return null;
  }
  if (!halos.every((x) => typeof x === "string")) {
    return null;
  }
  const bw = Number(o.border_width_px);
  const spread = Number(o.halo_spread_px);
  if (!Number.isFinite(bw) || !Number.isFinite(spread)) {
    return null;
  }
  return {
    fills_rgba: fills as string[],
    borders_rgba: borders as string[],
    halos_rgba: halos as string[],
    border_width_px: bw,
    halo_spread_px: spread,
  };
}

export function markerClusterGroupOptionsWithOptionalIconStyle(
  payload: ClusterOptionsPayload,
  clusterIconStyleRaw: unknown,
): L.MarkerClusterGroupOptions {
  const base = toLeafletClusterOptions(payload);
  const style = parseClusterIconStyle(clusterIconStyleRaw);
  if (!style) {
    return base;
  }
  return {
    ...base,
    iconCreateFunction(cluster: L.MarkerCluster) {
      const count = cluster.getChildCount();
      const i = count < 10 ? 0 : count < 100 ? 1 : 2;
      const html = `<div style="background-color:${style.fills_rgba[i]};border:${style.border_width_px}px solid ${style.borders_rgba[i]};box-shadow:0 0 0 ${style.halo_spread_px}px ${style.halos_rgba[i]};"><span>${count}</span></div>`;
      const sizeClass =
        count < 10 ? "marker-cluster-small" : count < 100 ? "marker-cluster-medium" : "marker-cluster-large";
      return L.divIcon({
        html,
        className: `marker-cluster ${sizeClass}`,
        iconSize: L.point(40, 40),
      });
    },
  };
}

export function applyGoToGpsViewportCamera(map: L.Map, vp: ViewportV1GoToGps): void {
  const d = vp.epsilon_delta;
  const b = L.latLngBounds([vp.lat - d, vp.lon - d], [vp.lat + d, vp.lon + d]);
  map.fitBounds(b, { padding: L.point(vp.padding_px, vp.padding_px), maxZoom: vp.max_zoom, animate: false });
}

/** Red DivIcon pin for go-to-GPS viewport mode. */
function goToGpsMarkerIcon(): L.DivIcon {
  return L.divIcon({
    className: "all-locations-gps-marker",
    html: '<span class="all-locations-gps-marker__glyph" aria-hidden="true"></span>',
    iconSize: [30, 40],
    iconAnchor: [15, 40],
    popupAnchor: [0, -34],
  });
}

/** Temporary GPS marker on the map root (not inside MarkerCluster). */
export function syncGoToGpsMarker(
  map: L.Map,
  viewportRaw: unknown,
  markerRef: MutableRefObject<L.Marker | null>,
): void {
  if (markerRef.current) {
    map.removeLayer(markerRef.current);
    markerRef.current = null;
  }
  const vp = parseViewportV1(viewportRaw);
  if (!vp || vp.mode !== "go_to_gps") {
    return;
  }
  const m = L.marker([vp.lat, vp.lon], { icon: goToGpsMarkerIcon(), zIndexOffset: 2500 });
  m.bindPopup(GO_TO_GPS_POPUP_HTML, POPUP_BIND_OPTIONS);
  m.addTo(map);
  markerRef.current = m;
}

/** All locations camera from Python ``all_locations_leaflet_viewport_recipe`` payload. */
export function applyAllLocationsViewport(map: L.Map, viewportRaw: unknown, boundsLayer: L.Layer | null): void {
  const vp = parseViewportV1(viewportRaw);
  const padPt = (px: number) => L.point(px, px);
  if (!vp) {
    if (boundsLayer && typeof (boundsLayer as L.FeatureGroup).getBounds === "function") {
      try {
        const b = (boundsLayer as L.FeatureGroup).getBounds();
        if (b.isValid()) {
          map.fitBounds(b.pad(0.12));
        }
      } catch {
        map.setView([20, 0], 2);
      }
    } else {
      map.setView([20, 0], 2);
    }
    return;
  }
  if (vp.mode === "go_to_gps") {
    applyGoToGpsViewportCamera(map, vp);
    return;
  }
  if (vp.mode === "center_zoom") {
    map.setView(vp.center, vp.zoom, { animate: false });
    return;
  }
  if (vp.mode === "fit_bounds") {
    if (vp.single_point) {
      const d = vp.epsilon_delta;
      const b = L.latLngBounds([vp.lat - d, vp.lon - d], [vp.lat + d, vp.lon + d]);
      map.fitBounds(b, { padding: padPt(vp.padding_px), maxZoom: vp.max_zoom, animate: false });
      return;
    }
    const latlngs = vp.pairs.map((p) => L.latLng(p[0], p[1]));
    const b = L.latLngBounds(latlngs);
    map.fitBounds(b, { padding: padPt(vp.padding_px), maxZoom: vp.max_zoom, animate: false });
  }
}


function isHex6(s: string | undefined): boolean {
  return typeof s === "string" && /^#[0-9a-fA-F]{6}$/.test(s);
}

/** CircleMarker options from Python ``circle_marker_style`` or legacy GeoJSON ``colour``. */
export function resolvedCircleStyles(
  cm: CircleMarkerStylePayload | undefined,
  featureColour: string | undefined,
): Pick<L.CircleMarkerOptions, "radius" | "weight" | "color" | "fillColor" | "fillOpacity"> {
  const fillHex = isHex6(cm?.fill_hex)
    ? cm!.fill_hex!
    : isHex6(featureColour)
      ? featureColour!
      : "#3388ff";
  const strokeHex = isHex6(cm?.stroke_hex) ? cm!.stroke_hex! : "#1c2630";
  const radius =
    typeof cm?.radius_px === "number" && Number.isFinite(cm.radius_px) && cm.radius_px > 0
      ? cm.radius_px
      : 7;
  const weight =
    typeof cm?.stroke_weight === "number" &&
    Number.isFinite(cm.stroke_weight) &&
    cm.stroke_weight >= 1
      ? cm.stroke_weight
      : 1;
  let fillOp = 0.88;
  if (typeof cm?.fill_opacity === "number" && Number.isFinite(cm.fill_opacity)) {
    fillOp = Math.min(1, Math.max(0, cm.fill_opacity));
  }
  return {
    radius,
    weight,
    color: strokeHex,
    fillColor: fillHex,
    fillOpacity: fillOp,
  };
}

/** Per-pin circle resolved in Python (``circle_pin``) for Lifer vs subspecies colours. */
interface CirclePinPayload {
  stroke_hex?: string;
  fill_hex?: string;
  radius_px?: number;
  stroke_weight?: number;
  fill_opacity?: number;
  stroke_opacity?: number;
}

export function parseCirclePin(raw: unknown): CirclePinPayload | null {
  if (!raw || typeof raw !== "object") {
    return null;
  }
  const o = raw as Record<string, unknown>;
  return {
    stroke_hex: typeof o.stroke_hex === "string" ? o.stroke_hex : undefined,
    fill_hex: typeof o.fill_hex === "string" ? o.fill_hex : undefined,
    radius_px: typeof o.radius_px === "number" && Number.isFinite(o.radius_px) ? o.radius_px : undefined,
    stroke_weight:
      typeof o.stroke_weight === "number" && Number.isFinite(o.stroke_weight) ? o.stroke_weight : undefined,
    fill_opacity:
      typeof o.fill_opacity === "number" && Number.isFinite(o.fill_opacity) ? o.fill_opacity : undefined,
    stroke_opacity:
      typeof o.stroke_opacity === "number" && Number.isFinite(o.stroke_opacity)
        ? o.stroke_opacity
        : undefined,
  };
}

export function resolvedCircleStylesFromPinPayload(pin: CirclePinPayload): Pick<
  L.CircleMarkerOptions,
  "radius" | "weight" | "color" | "fillColor" | "fillOpacity"
> {
  const okHex = (s: string | undefined, fb: string) =>
    typeof s === "string" && /^#[0-9a-fA-F]{6}$/.test(s) ? s : fb;
  const fillHex = okHex(pin.fill_hex, "#3388ff");
  const strokeHex = okHex(pin.stroke_hex, "#1c2630");
  const radius =
    typeof pin.radius_px === "number" && Number.isFinite(pin.radius_px) && pin.radius_px > 0
      ? pin.radius_px
      : 7;
  const weight =
    typeof pin.stroke_weight === "number" && Number.isFinite(pin.stroke_weight) && pin.stroke_weight >= 1
      ? pin.stroke_weight
      : 1;
  let fillOp = 0.88;
  if (typeof pin.fill_opacity === "number" && Number.isFinite(pin.fill_opacity)) {
    fillOp = Math.min(1, Math.max(0, pin.fill_opacity));
  }
  return {
    radius,
    weight,
    color: strokeHex,
    fillColor: fillHex,
    fillOpacity: fillOp,
  };
}

const STYLE_ID = "pebird-map-overlay-theme";
const POPUP_WIDTH_SCRIPT_ID = "pebird-map-popup-width-fix";

/** Join inner CSS from every ``<style>...</style>`` block (Python concatenates popup + banner/legend sheets). */
function extractAllStyleInnerCss(html: string): string {
  const s = html.trim();
  if (!s) {
    return "";
  }
  const parts: string[] = [];
  const re = /<style[^>]*>([\s\S]*?)<\/style>/gi;
  let m: RegExpExecArray | null;
  while ((m = re.exec(s)) !== null) {
    parts.push(m[1].trim());
  }
  if (parts.length > 0) {
    return parts.join("\n");
  }
  /* Fallback: legacy single-block strip */
  return s
    .replace(/^\s*<style[^>]*>\s*/i, "")
    .replace(/\s*<\/style>\s*$/i, "")
    .trim();
}

/** Inner JS from ``<script>...</script>`` (single block from Python). */
function extractScriptInnerJs(html: string): string {
  const s = html.trim();
  if (!s) {
    return "";
  }
  const m = /<script[^>]*>([\s\S]*?)<\/script>/i.exec(s);
  return m ? m[1].trim() : s.replace(/^\s*<script[^>]*>\s*/i, "").replace(/\s*<\/script>\s*$/i, "").trim();
}

/** Live zoom readout overlay (parity with ``MAP_DEBUG_SHOW_ZOOM_LEVEL`` / ``defaults.py``). */
export function syncZoomLevelDebugOverlay(
  map: L.Map,
  enabled: boolean,
  controlRef: MutableRefObject<L.Control | null>,
  onZoomRef: MutableRefObject<(() => void) | null>,
): void {
  const existing = controlRef.current;
  if (existing) {
    map.removeControl(existing);
    controlRef.current = null;
  }
  const onZoom = onZoomRef.current;
  if (onZoom) {
    map.off("zoom", onZoom);
    map.off("zoomend", onZoom);
    onZoomRef.current = null;
  }
  if (!enabled) {
    return;
  }
  const div = L.DomUtil.create("div", "ebird-zoom-debug-overlay");
  div.style.cssText = [
    "background:rgba(255,255,255,0.92)",
    "border:1px solid #1f6f54",
    "padding:4px 8px",
    "font:12px/1.25 ui-monospace, SFMono-Regular, Menlo, monospace",
    "border-radius:4px",
    "box-shadow:0 1px 3px rgba(0,0,0,0.2)",
    "min-width:7ch",
    "text-align:right",
    "z-index:1001",
  ].join(";");
  const ZoomDebugControl = L.Control.extend({
    onAdd: () => div,
  });
  const ctrl = new ZoomDebugControl({ position: "bottomright" });
  ctrl.addTo(map);
  const update = () => {
    div.textContent = `zoom: ${map.getZoom()}`;
  };
  map.on("zoom", update);
  map.on("zoomend", update);
  update();
  controlRef.current = ctrl;
  onZoomRef.current = update;
}

export function injectHeadFragments(mapThemeCss: string, mapPopupWidthScript: string): void {
  const css = (mapThemeCss ?? "").trim();
  if (css) {
    let styleEl = document.getElementById(STYLE_ID) as HTMLStyleElement | null;
    if (!styleEl) {
      styleEl = document.createElement("style");
      styleEl.id = STYLE_ID;
      document.head.appendChild(styleEl);
    }
    const inner = extractAllStyleInnerCss(css);
    styleEl.textContent = inner;
  }
  const scr = (mapPopupWidthScript ?? "").trim();
  if (scr && !document.getElementById(POPUP_WIDTH_SCRIPT_ID)) {
    const inner = extractScriptInnerJs(scr);
    const s = document.createElement("script");
    s.id = POPUP_WIDTH_SCRIPT_ID;
    s.textContent = inner;
    document.head.appendChild(s);
  }
}
