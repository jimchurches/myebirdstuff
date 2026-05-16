import React, { useEffect, useRef } from "react";
import L from "leaflet";
import "leaflet/dist/leaflet.css";
import "leaflet.markercluster/dist/MarkerCluster.css";
import "leaflet.markercluster/dist/MarkerCluster.Default.css";
import "leaflet.markercluster/dist/leaflet.markercluster.js";
import "./AllLocationsMapPopup.css";
import {
  ComponentProps,
  Streamlit,
  withStreamlitConnection,
} from "streamlit-component-lib";

interface ClusterOptionsPayload {
  enabled?: boolean;
  max_cluster_radius?: number;
  disable_clustering_at_zoom?: number;
  spiderfy_on_max_zoom?: boolean;
  remove_outside_visible_bounds?: boolean;
}

interface CircleMarkerStylePayload {
  fill_hex?: string;
  stroke_hex?: string;
  radius_px?: number;
  stroke_weight?: number;
  fill_opacity?: number;
}

/** Folium ``_marker_cluster_icon_create_function_from_scheme`` parity — from :func:`all_locations_cluster_icon_style_payload`. */
interface ClusterIconStylePayload {
  fills_rgba: string[];
  borders_rgba: string[];
  halos_rgba: string[];
  border_width_px: number;
  halo_spread_px: number;
}

/** Folium `MAP_POPUP_MAX_WIDTH_PX` (`explorer/app/streamlit/defaults.py`). */
const POPUP_MAX_WIDTH_PX = 420;

/** Leaflet runs ``autoPan`` inside ``popup.update()`` — stacked updates caused large vertical pans (#222). Disabled globally; ``maybePanPopupIntoView`` pans once when needed after layout settles. */
const POPUP_BIND_OPTIONS: L.PopupOptions = {
  maxWidth: POPUP_MAX_WIDTH_PX,
  autoPan: false,
};

/** Folium ``_apply_go_to_gps_pin_view`` popup body (`explorer/core/map_overlay_visit_map.py`). */
const GO_TO_GPS_POPUP_HTML =
  "<div style='font-size:13px'><strong>Temporary GPS marker</strong></div>";

/** Default gap below location title row — matches ``build_location_popup_html(..., location_heading_margin_px=4)``. */
const POPUP_LOCATION_HEADING_MARGIN_PX = 4;

/** Extra px on shrink width — ``scrollWidth`` can sit slightly under painted text (subpixel / fonts / padding). */
const POPUP_SHRINK_WIDTH_BUFFER_PX = 40;

/** Never apply a narrower content box than this — guards bad measures / font glitches (#222). */
const POPUP_SHRINK_MIN_CONTENT_WIDTH_PX = 140;

/** Rows included when measuring intrinsic popup width (All locations + species + lifer). */
const POPUP_WIDE_MEASURE_SELECTOR =
  ".pebird-map-popup__visit-dates a, .pebird-map-popup__visit-list-inner a, " +
  "a.pebird-map-popup__location-heading, span.pebird-map-popup__location-heading, .pebird-map-popup__summary-line, " +
  ".pebird-map-popup__obs-line, .pebird-map-popup__species-seen > summary, .pebird-map-popup__all-visits > summary";

/** Max of inner and wide text rows while inner is ``max-content`` for measure (#222). */
function measurePebirdPopupInnerWidthPx(inner: HTMLElement): number {
  void inner.offsetWidth;
  let w = Math.max(inner.scrollWidth, inner.getBoundingClientRect().width);
  const wideEls = inner.querySelectorAll(POPUP_WIDE_MEASURE_SELECTOR);
  wideEls.forEach((el) => {
    const he = el as HTMLElement;
    w = Math.max(w, he.scrollWidth, he.getBoundingClientRect().width);
  });
  return Math.ceil(Math.max(w, 1));
}

/** Shrink-wrap Leaflet popup width to ``.pebird-map-popup`` intrinsic width (same idea as Folium ``map_popup_width_fix_script``; this iframe runs TS only).

Uses map pixel width (not ``window``) for cap. Parents use ``cap`` px during measure so ``width:100%`` rows do not collapse (#222).
After width changes, callers invoke ``popup.update()`` to keep the tip on the marker (#145).
*/
function capPopupInnerWidthPxForMap(map: L.Map): number {
  const px = Math.max(1, map.getSize().x);
  return Math.min(POPUP_MAX_WIDTH_PX, Math.max(80, px - 24));
}

/** Once width is applied for a given map cap, skip remeasuring — avoids a second visible resize when
 * iframe/RFO bumps run later at ~50–500ms (#222). Remeasure only when ``cap`` changes (map container width). */
const POPUP_WIDTH_COMMIT_ATTR = "data-pebird-popup-width-commit";
const POPUP_WIDTH_CAP_ATTR = "data-pebird-shrink-applied-cap";

/** Shrink-wrap ``.leaflet-popup-content`` to intrinsic width; commit per (popup, map cap) to avoid repeat work. */
function shrinkPebirdLeafletPopups(map: L.Map): void {
  const pops = document.querySelectorAll(".leaflet-popup-pane .leaflet-popup");
  const cap = capPopupInnerWidthPxForMap(map);
  const capStr = `${cap}`;
  pops.forEach((pop) => {
    const content = pop.querySelector(".leaflet-popup-content") as HTMLElement | null;
    const wrap = pop.querySelector(".leaflet-popup-content-wrapper") as HTMLElement | null;
    const inner = pop.querySelector(".pebird-map-popup") as HTMLElement | null;
    if (!content || !wrap || !inner) {
      return;
    }
    if (content.getAttribute(POPUP_WIDTH_COMMIT_ATTR) === "1" && content.getAttribute(POPUP_WIDTH_CAP_ATTR) === capStr) {
      return;
    }

    /* Shrink-to-fit cycle: inner has max-width:100% of .leaflet-popup-content while that node uses
     * width:fit-content — cyclic percentage resolves tiny, so scrollWidth was ~min-content (refs #222).
     * Size inner to max-content for measurement only, then restore so final layout still respects cap.
     *
     * Never strip content/wrapper width **without** substituting ``cap``: descendants such as
     * ``.pebird-map-popup__heading-row { width:100% }`` lose their percentage base and collapse to a
     * min-content column — ``scrollWidth`` then matches a character-wide strip (#222). */
    inner.style.setProperty("max-width", "none", "important");
    inner.style.setProperty("width", "max-content", "important");
    content.style.setProperty("width", `${cap}px`, "important");
    content.style.setProperty("max-width", `${cap}px`, "important");
    wrap.style.setProperty("width", `${cap}px`, "important");
    wrap.style.setProperty("max-width", `${cap}px`, "important");
    content.style.removeProperty("white-space");
    const innerPx = measurePebirdPopupInnerWidthPx(inner);
    inner.style.removeProperty("max-width");
    inner.style.removeProperty("width");
    const target = Math.max(
      POPUP_SHRINK_MIN_CONTENT_WIDTH_PX,
      Math.min(innerPx + POPUP_SHRINK_WIDTH_BUFFER_PX, cap),
    );
    const nextTargetStr = `${target}`;
    const prevTargetStr = content.dataset.pebirdShrinkTarget ?? "";
    const changed = prevTargetStr !== nextTargetStr;

    if (changed) {
      content.dataset.pebirdShrinkTarget = nextTargetStr;
      content.style.setProperty("width", `${target}px`, "important");
      content.style.setProperty("max-width", `${cap}px`, "important");
      wrap.style.setProperty("width", `${target}px`, "important");
      wrap.style.setProperty("max-width", `${cap}px`, "important");
    }
    content.setAttribute(POPUP_WIDTH_COMMIT_ATTR, "1");
    content.setAttribute(POPUP_WIDTH_CAP_ATTR, capStr);
  });
}

/** Margin inside the map container when deciding if the popup clips (#222 — replaces Leaflet ``autoPan``). */
const POPUP_VIEWPORT_PAD_PX = 12;

/** Pan the map only when the open popup’s bounding box exceeds the container inset — minimal correction, no Leaflet ``autoPan`` stack. */
function maybePanPopupIntoView(map: L.Map, popup: L.Popup): void {
  const mapEl = map.getContainer();
  const popupEl = popup.getElement();
  if (!popupEl) {
    return;
  }
  const mr = mapEl.getBoundingClientRect();
  const pr = popupEl.getBoundingClientRect();
  const insetLeft = mr.left + POPUP_VIEWPORT_PAD_PX;
  const insetTop = mr.top + POPUP_VIEWPORT_PAD_PX;
  const insetRight = mr.right - POPUP_VIEWPORT_PAD_PX;
  const insetBottom = mr.bottom - POPUP_VIEWPORT_PAD_PX;

  const overflowLeft = insetLeft - pr.left;
  const overflowRight = pr.right - insetRight;
  const overflowTop = insetTop - pr.top;
  const overflowBottom = pr.bottom - insetBottom;

  let dx = 0;
  let dy = 0;
  if (overflowLeft > 0 && overflowRight <= 0) {
    dx = -overflowLeft;
  } else if (overflowRight > 0 && overflowLeft <= 0) {
    dx = overflowRight;
  } else if (overflowLeft > 0 && overflowRight > 0) {
    dx = (overflowRight - overflowLeft) / 2;
  }
  if (overflowTop > 0 && overflowBottom <= 0) {
    dy = -overflowTop;
  } else if (overflowBottom > 0 && overflowTop <= 0) {
    dy = overflowBottom;
  } else if (overflowTop > 0 && overflowBottom > 0) {
    dy = (overflowBottom - overflowTop) / 2;
  }

  if (dx !== 0 || dy !== 0) {
    map.panBy(L.point(dx, dy), { animate: false });
  }
}

function scheduleShrinkPebirdLeafletPopups(map: L.Map, popup?: L.Popup): void {
  /** Wait for web fonts before measuring — fallback metrics used to lock ``data-pebird-popup-width-commit``
   * produced cards that were tens of px too narrow (lines broke after commas, visit rows split date/time).
   * One double-rAF after ``fonts.ready`` keeps a single width commit with no follow-up resize (#222). */
  const finalize = () => {
    shrinkPebirdLeafletPopups(map);
    if (popup && typeof popup.update === "function") {
      popup.update();
      maybePanPopupIntoView(map, popup);
    }
  };
  const runAfterLayout = () => {
    requestAnimationFrame(() => {
      requestAnimationFrame(finalize);
    });
  };
  try {
    const ready = document.fonts?.ready;
    if (ready && typeof ready.then === "function") {
      void ready.then(runAfterLayout).catch(runAfterLayout);
    } else {
      runAfterLayout();
    }
  } catch {
    runAfterLayout();
  }
}

/** Structured popup from Python (`explorer/core/all_locations_geojson.py`) — extend for classic parity. */
interface PopupLinkV1 {
  label?: string;
  href?: string;
}

interface PopupPayloadV1 {
  v: 1;
  summary_lines?: string[];
  links?: PopupLinkV1[];
  visited?: {
    label?: string;
    entries?: PopupLinkV1[];
  };
  visited_truncated?: boolean;
  visited_total?: number;
  visited_omitted?: number;
}

interface MapArgs {
  revision: string;
  geojson: {
    type: "FeatureCollection";
    features: Array<{
      type: "Feature";
      geometry: { type: "Point"; coordinates: [number, number] };
      properties?: Record<string, unknown>;
    }>;
  };
  height: number;
  cluster_options?: ClusterOptionsPayload;
  circle_marker_style?: CircleMarkerStylePayload;
  /** Tier rgba + border/spread for ``iconCreateFunction`` (Folium cluster parity). */
  cluster_icon_style?: ClusterIconStylePayload | Record<string, unknown>;
  /** Injected into iframe ``<head>`` — same as Folium ``map_overlay_theme_stylesheet`` (#222). */
  map_theme_css?: string;
  /** Injected once — optional; leave empty. Folium ``map_popup_width_fix_script`` schedules extra shrink passes and is **not** used in the component iframe (TS owns width; #222). */
  map_popup_width_script?: string;
  /** Fixed-position banner HTML (viewport = iframe), e.g. top-right ``pebird-map-banner`` (#222). */
  banner_html?: string;
  /** Fixed-position legend HTML, e.g. bottom-left ``pebird-map-legend`` (#222). */
  legend_html?: string;
  /** Camera recipe from Python `all_locations_leaflet_viewport_recipe` (#222). */
  viewport?: Record<string, unknown>;
  /** Basemap keys match Python `create_map`: `default` (OSM), `google`, `carto` (CartoDB Positron). */
  map_style?: string;
}

/** Matches Folium all-locations defaults from explorer.app.streamlit.defaults. */
const DEFAULT_CLUSTER_PAYLOAD: ClusterOptionsPayload = {
  enabled: true,
  max_cluster_radius: 40,
  disable_clustering_at_zoom: 9,
  spiderfy_on_max_zoom: false,
  remove_outside_visible_bounds: false,
};

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

function applyBasemapToMap(
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

function mergeClusterPayload(raw: ClusterOptionsPayload | undefined): ClusterOptionsPayload {
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

function markerClusterGroupOptionsWithOptionalIconStyle(
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

type ViewportV1GoToGps = {
  mode: "go_to_gps";
  lat: number;
  lon: number;
  padding_px: number;
  epsilon_delta: number;
  max_zoom: number;
};

type ViewportV1CenterZoom = {
  mode: "center_zoom";
  center: L.LatLngTuple;
  zoom: number;
};

type ViewportV1FitBoundsSingle = {
  mode: "fit_bounds";
  single_point: true;
  lat: number;
  lon: number;
  epsilon_delta: number;
  padding_px: number;
  max_zoom: number;
};

type ViewportV1FitBoundsMulti = {
  mode: "fit_bounds";
  single_point: false;
  pairs: L.LatLngTuple[];
  padding_px: number;
  max_zoom: number;
};

type ViewportV1 = ViewportV1GoToGps | ViewportV1CenterZoom | ViewportV1FitBoundsSingle | ViewportV1FitBoundsMulti;

function parseViewportV1(raw: unknown): ViewportV1 | null {
  if (!raw || typeof raw !== "object") {
    return null;
  }
  const o = raw as Record<string, unknown>;
  if (o.v !== 1) {
    return null;
  }
  const mode = typeof o.mode === "string" ? o.mode : "";
  if (mode === "go_to_gps") {
    const lat = Number(o.lat);
    const lon = Number(o.lon);
    const padding_px = Number(o.padding_px);
    const epsilon_delta = Number(o.epsilon_delta);
    const max_zoom = Number(o.max_zoom);
    if (![lat, lon, padding_px, epsilon_delta, max_zoom].every((x) => Number.isFinite(x))) {
      return null;
    }
    return { mode: "go_to_gps", lat, lon, padding_px, epsilon_delta, max_zoom };
  }
  if (mode === "center_zoom") {
    const c = o.center;
    if (!Array.isArray(c) || c.length !== 2) {
      return null;
    }
    const la = Number(c[0]);
    const lo = Number(c[1]);
    const zoom = Number(o.zoom);
    if (![la, lo, zoom].every((x) => Number.isFinite(x))) {
      return null;
    }
    return { mode: "center_zoom", center: [la, lo], zoom: Math.round(zoom) };
  }
  if (mode === "fit_bounds") {
    const padding_px = Number(o.padding_px);
    const max_zoom = Number(o.max_zoom);
    if (!Number.isFinite(padding_px) || !Number.isFinite(max_zoom)) {
      return null;
    }
    if (o.single_point === true) {
      const lat = Number(o.lat);
      const lon = Number(o.lon);
      const epsilon_delta = Number(o.epsilon_delta);
      if (![lat, lon, epsilon_delta].every((x) => Number.isFinite(x))) {
        return null;
      }
      return {
        mode: "fit_bounds",
        single_point: true,
        lat,
        lon,
        epsilon_delta,
        padding_px,
        max_zoom: Math.round(max_zoom),
      };
    }
    if (o.single_point === false) {
      const pairsRaw = o.pairs;
      if (!Array.isArray(pairsRaw) || pairsRaw.length === 0) {
        return null;
      }
      const pairs: L.LatLngTuple[] = [];
      for (const pr of pairsRaw) {
        if (!Array.isArray(pr) || pr.length !== 2) {
          return null;
        }
        const la = Number(pr[0]);
        const lo = Number(pr[1]);
        if (!Number.isFinite(la) || !Number.isFinite(lo)) {
          return null;
        }
        pairs.push([la, lo]);
      }
      return {
        mode: "fit_bounds",
        single_point: false,
        pairs,
        padding_px,
        max_zoom: Math.round(max_zoom),
      };
    }
  }
  return null;
}

function applyGoToGpsViewportCamera(map: L.Map, vp: ViewportV1GoToGps): void {
  const d = vp.epsilon_delta;
  const b = L.latLngBounds([vp.lat - d, vp.lon - d], [vp.lat + d, vp.lon + d]);
  map.fitBounds(b, { padding: L.point(vp.padding_px, vp.padding_px), maxZoom: vp.max_zoom, animate: false });
}

/** Red pin approximating Folium ``folium.Icon(color='red', icon='map-marker', prefix='fa')`` (#222). */
function goToGpsMarkerIcon(): L.DivIcon {
  return L.divIcon({
    className: "all-locations-gps-marker",
    html: '<span class="all-locations-gps-marker__glyph" aria-hidden="true"></span>',
    iconSize: [30, 40],
    iconAnchor: [15, 40],
    popupAnchor: [0, -34],
  });
}

/** Folium ``_apply_go_to_gps_pin_view`` marker on the map (not inside MarkerCluster) (#222). */
function syncGoToGpsMarker(map: L.Map, viewportRaw: unknown, markerRef: React.MutableRefObject<L.Marker | null>): void {
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

/** Folium ``build_visit_overlay_map`` camera for All locations (#222). */
function applyAllLocationsViewport(map: L.Map, viewportRaw: unknown, gjLayer: L.GeoJSON | null): void {
  const vp = parseViewportV1(viewportRaw);
  const padPt = (px: number) => L.point(px, px);
  if (!vp) {
    if (gjLayer) {
      try {
        const b = gjLayer.getBounds();
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

function escapeHtml(text: string): string {
  const div = document.createElement("div");
  div.textContent = text;
  return div.innerHTML;
}

/** Allow only http(s) in popup anchors — blocks ``javascript:``, ``data:``, etc. (#222 review). */
function safeHttpUrlForAnchor(raw: string): string {
  const t = raw.trim();
  if (!t) {
    return "";
  }
  try {
    const u = new URL(t);
    if (u.protocol === "https:" || u.protocol === "http:") {
      return u.href;
    }
  } catch {
    /* ignore */
  }
  return "";
}

function parsePopupV1(raw: unknown): PopupPayloadV1 | null {
  if (!raw || typeof raw !== "object") {
    return null;
  }
  const o = raw as Record<string, unknown>;
  if (o.v !== 1) {
    return null;
  }
  const summary_lines = Array.isArray(o.summary_lines)
    ? o.summary_lines.filter((x): x is string => typeof x === "string")
    : undefined;
  const linksRaw = Array.isArray(o.links) ? o.links : [];
  const links: PopupLinkV1[] = linksRaw
    .filter((x): x is Record<string, unknown> => !!x && typeof x === "object")
    .map((item) => ({
      label: typeof item.label === "string" ? item.label : "",
      href: typeof item.href === "string" ? item.href : "",
    }));
  let visited: PopupPayloadV1["visited"];
  const visRaw = o.visited;
  if (visRaw && typeof visRaw === "object") {
    const vo = visRaw as Record<string, unknown>;
    const vLabel = typeof vo.label === "string" ? vo.label : "Visited:";
    const entRaw = Array.isArray(vo.entries) ? vo.entries : [];
    const entries: PopupLinkV1[] = entRaw
      .filter((x): x is Record<string, unknown> => !!x && typeof x === "object")
      .map((item) => ({
        label: typeof item.label === "string" ? item.label : "",
        href: typeof item.href === "string" ? item.href : "",
      }));
    visited = { label: vLabel, entries };
  }
  const visited_truncated = o.visited_truncated === true;
  const visited_total =
    typeof o.visited_total === "number" && Number.isFinite(o.visited_total) ? o.visited_total : undefined;
  const visited_omitted =
    typeof o.visited_omitted === "number" && Number.isFinite(o.visited_omitted)
      ? o.visited_omitted
      : undefined;
  return { v: 1, summary_lines, links, visited, visited_truncated, visited_total, visited_omitted };
}

/** Lifer map — structured lines from ``lifer_locations_geojson.py`` (#222). */
interface LiferPopupLineV1 {
  label: string;
  date: string;
  checklist_href: string;
}

interface LiferPopupPayloadV1 {
  v: 1;
  lines: LiferPopupLineV1[];
}

function parseLiferPopupV1(raw: unknown): LiferPopupPayloadV1 | null {
  if (!raw || typeof raw !== "object") {
    return null;
  }
  const o = raw as Record<string, unknown>;
  if (o.v !== 1) {
    return null;
  }
  const linesRaw = Array.isArray(o.lines) ? o.lines : [];
  const lines: LiferPopupLineV1[] = [];
  for (const row of linesRaw) {
    if (!row || typeof row !== "object") {
      continue;
    }
    const r = row as Record<string, unknown>;
    lines.push({
      label: typeof r.label === "string" ? r.label : "",
      date: typeof r.date === "string" ? r.date : "?",
      checklist_href: typeof r.checklist_href === "string" ? r.checklist_href : "#",
    });
  }
  return { v: 1, lines };
}

/** Species map — structured sections from ``species_locations_geojson.py`` (#222). */
interface SpeciesObservationV1 {
  datetime_label: string;
  checklist_href: string;
  observed_count: string;
  media_href: string;
}

interface SpeciesSectionV1 {
  common_name: string;
  observation_count: number;
  open_by_default: boolean;
  observations: SpeciesObservationV1[];
}

interface SpeciesVisitsBlockV1 {
  summary_label: string;
  entries: PopupLinkV1[];
  open_by_default: boolean;
}

interface SpeciesPopupPayloadV1 {
  v: 1;
  location_heading_margin_px?: number;
  species_sections: SpeciesSectionV1[];
  visits: SpeciesVisitsBlockV1;
}

function parseSpeciesPopupV1(raw: unknown): SpeciesPopupPayloadV1 | null {
  if (!raw || typeof raw !== "object") {
    return null;
  }
  const o = raw as Record<string, unknown>;
  if (o.v !== 1) {
    return null;
  }
  const sectionsRaw = Array.isArray(o.species_sections) ? o.species_sections : [];
  const species_sections: SpeciesSectionV1[] = [];
  for (const sec of sectionsRaw) {
    if (!sec || typeof sec !== "object") {
      continue;
    }
    const s = sec as Record<string, unknown>;
    const obsRaw = Array.isArray(s.observations) ? s.observations : [];
    const observations: SpeciesObservationV1[] = [];
    for (const row of obsRaw) {
      if (!row || typeof row !== "object") {
        continue;
      }
      const r = row as Record<string, unknown>;
      observations.push({
        datetime_label: typeof r.datetime_label === "string" ? r.datetime_label : "",
        checklist_href: typeof r.checklist_href === "string" ? r.checklist_href : "",
        observed_count: typeof r.observed_count === "string" ? r.observed_count : "",
        media_href: typeof r.media_href === "string" ? r.media_href : "",
      });
    }
    species_sections.push({
      common_name: typeof s.common_name === "string" ? s.common_name : "",
      observation_count:
        typeof s.observation_count === "number" && Number.isFinite(s.observation_count)
          ? s.observation_count
          : observations.length,
      open_by_default: s.open_by_default === true,
      observations,
    });
  }
  const visRaw = o.visits;
  if (!visRaw || typeof visRaw !== "object") {
    return null;
  }
  const vo = visRaw as Record<string, unknown>;
  const entRaw = Array.isArray(vo.entries) ? vo.entries : [];
  const entries: PopupLinkV1[] = entRaw
    .filter((x): x is Record<string, unknown> => !!x && typeof x === "object")
    .map((item) => ({
      label: typeof item.label === "string" ? item.label : "",
      href: typeof item.href === "string" ? item.href : "",
    }));
  const visits: SpeciesVisitsBlockV1 = {
    summary_label: typeof vo.summary_label === "string" ? vo.summary_label : "Visited:",
    entries,
    open_by_default: vo.open_by_default === true,
  };
  const margin =
    typeof o.location_heading_margin_px === "number" && Number.isFinite(o.location_heading_margin_px)
      ? o.location_heading_margin_px
      : 6;
  return { v: 1, location_heading_margin_px: margin, species_sections, visits };
}

/** Species-map matching pin — mirrors ``assemble_species_map_location_popup_html`` (#222). */
function popupHtmlSpeciesLayout(
  name: string,
  lifelistUrl: string,
  payload: SpeciesPopupPayloadV1,
): string {
  const margin =
    typeof payload.location_heading_margin_px === "number" &&
    Number.isFinite(payload.location_heading_margin_px)
      ? payload.location_heading_margin_px
      : 6;
  const hlSafe = safeHttpUrlForAnchor(lifelistUrl.trim());
  const locHeading =
    hlSafe.length > 0
      ? `<a class="pebird-map-popup__location-heading" href="${escapeHtml(hlSafe)}" target="_blank" rel="noopener noreferrer">${escapeHtml(name)}</a>`
      : `<span class="pebird-map-popup__location-heading">${escapeHtml(name)}</span>`;

  const sectionParts: string[] = [];
  for (const sec of payload.species_sections) {
    const openAttr = sec.open_by_default ? " open" : "";
    const summaryLabel = `${sec.common_name}: (${sec.observation_count})`;
    const obsLines: string[] = [];
    for (const obs of sec.observations) {
      const hrefSafe = safeHttpUrlForAnchor(obs.checklist_href.trim());
      const dt = escapeHtml(obs.datetime_label.trim() || "—");
      const count = escapeHtml(obs.observed_count.trim());
      let line =
        hrefSafe.length > 0
          ? `<a href="${escapeHtml(hrefSafe)}" target="_blank" rel="noopener noreferrer">${dt}</a>`
          : `<span>${dt}</span>`;
      line += ` <span class="pebird-map-popup__obs-count">(Observed: ${count})</span>`;
      const mediaSafe = safeHttpUrlForAnchor(obs.media_href.trim());
      if (mediaSafe) {
        line += ` <a class="pebird-map-popup__media-link" href="${escapeHtml(mediaSafe)}" target="_blank" rel="noopener noreferrer" title="media">↗</a>`;
      }
      obsLines.push(`<div class="pebird-map-popup__obs-line">${line}</div>`);
    }
    sectionParts.push(
      `<details class="pebird-map-popup__species-seen"${openAttr}>` +
        `<summary class="pebird-map-popup__section-label">${escapeHtml(summaryLabel)}</summary>` +
        `<div class="pebird-map-popup__obs-list">${obsLines.join("")}</div>` +
        `</details>`,
    );
  }

  const visitAnchors: string[] = [];
  for (const e of payload.visits.entries) {
    const href = e.href?.trim() ?? "";
    const linkLabel = e.label?.trim() || href;
    if (href) {
      const hrefSafe = safeHttpUrlForAnchor(href);
      if (hrefSafe) {
        visitAnchors.push(
          `<a href="${escapeHtml(hrefSafe)}" target="_blank" rel="noopener noreferrer">${escapeHtml(linkLabel)}</a>`,
        );
      } else {
        visitAnchors.push(`<span class="pebird-map-popup__visit-link-text">${escapeHtml(linkLabel)}</span>`);
      }
    }
  }
  const visitsOpen = payload.visits.open_by_default ? " open" : "";
  const visitsBlock =
    `<details class="pebird-map-popup__all-visits"${visitsOpen}>` +
    `<summary class="pebird-map-popup__section-label">${escapeHtml(payload.visits.summary_label)}</summary>` +
    `<div class="pebird-map-popup__visit-list-inner">${visitAnchors.join("<br>")}</div>` +
    `</details>`;

  return (
    `<div class="pebird-map-popup popup-scroll-wrapper" style="position:relative;">` +
    `<div class="pebird-map-popup__heading-row" style="margin-bottom:${margin}px;">${locHeading}</div>` +
    `<div class="pebird-map-popup__scroll" style="max-height:300px;overflow-y:auto;">` +
    sectionParts.join("") +
    visitsBlock +
    `</div></div>`
  );
}

/** Per-pin circle resolved in Python (``circle_pin``) for Lifer vs subspecies colours (#222). */
interface CirclePinPayload {
  stroke_hex?: string;
  fill_hex?: string;
  radius_px?: number;
  stroke_weight?: number;
  fill_opacity?: number;
}

function parseCirclePin(raw: unknown): CirclePinPayload | null {
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
  };
}

function resolvedCircleStylesFromPinPayload(pin: CirclePinPayload): Pick<
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

/** Lifer popup: location heading + species checklist lines (parity with ``format_lifer_popup_lines``). */
function popupHtmlLiferLayout(name: string, lifelistUrl: string, payload: LiferPopupPayloadV1): string {
  const hlSafe = safeHttpUrlForAnchor(lifelistUrl.trim());
  const margin = POPUP_LOCATION_HEADING_MARGIN_PX;
  const locHeading =
    hlSafe.length > 0
      ? `<a class="pebird-map-popup__location-heading" href="${escapeHtml(hlSafe)}" target="_blank" rel="noopener noreferrer">${escapeHtml(name)}</a>`
      : `<span class="pebird-map-popup__location-heading">${escapeHtml(name)}</span>`;
  const lineParts: string[] = [];
  for (let i = 0; i < payload.lines.length; i += 1) {
    const ln = payload.lines[i];
    const prefix = i > 0 ? "<br>" : "";
    const hrefRaw = ln.checklist_href.trim() || "#";
    const hrefSafe = safeHttpUrlForAnchor(hrefRaw);
    const label = ln.label.trim() || "—";
    const dateStr = ln.date.trim() || "?";
    if (hrefSafe) {
      lineParts.push(
        `${prefix}<a href="${escapeHtml(hrefSafe)}" target="_blank" rel="noopener noreferrer">${escapeHtml(
          label,
        )} : ${escapeHtml(dateStr)}</a>`,
      );
    } else {
      lineParts.push(`${prefix}<span>${escapeHtml(label)} : ${escapeHtml(dateStr)}</span>`);
    }
  }
  const inner = lineParts.join("");
  return (
    `<div class="pebird-map-popup popup-scroll-wrapper" style="position:relative;">` +
    `<div class="pebird-map-popup__heading-row" style="margin-bottom:${margin}px;">${locHeading}</div>` +
    `<div class="pebird-map-popup__scroll" style="max-height:300px;overflow-y:auto;">` +
    `<div class="pebird-map-popup__visited-block">` +
    `<div class="pebird-map-popup__visit-dates">${inner}</div>` +
    `</div></div></div>`
  );
}

/** Classic All locations card — DOM mirrors ``assemble_location_popup_html`` / ``LocationPopupModel`` (``map_popup_models``). */
function popupHtmlVisitedLayout(
  name: string,
  lifelistUrl: string,
  visited: NonNullable<PopupPayloadV1["visited"]>,
  trunc?: Pick<PopupPayloadV1, "visited_truncated" | "visited_total" | "visited_omitted">,
): string {
  const label = visited.label?.trim() || "Visited:";
  const entries = visited.entries ?? [];
  const hl = lifelistUrl.trim();
  const hlSafe = safeHttpUrlForAnchor(hl);
  const margin = POPUP_LOCATION_HEADING_MARGIN_PX;
  const locHeading =
    hlSafe.length > 0
      ? `<a class="pebird-map-popup__location-heading" href="${escapeHtml(hlSafe)}" target="_blank" rel="noopener noreferrer">${escapeHtml(name)}</a>`
      : `<span class="pebird-map-popup__location-heading">${escapeHtml(name)}</span>`;

  const visitAnchors: string[] = [];
  for (const e of entries) {
    const href = e.href?.trim() ?? "";
    const linkLabel = e.label?.trim() || href;
    if (href) {
      const hrefSafe = safeHttpUrlForAnchor(href);
      if (hrefSafe) {
        visitAnchors.push(
          `<a href="${escapeHtml(hrefSafe)}" target="_blank" rel="noopener noreferrer">${escapeHtml(linkLabel)}</a>`,
        );
      } else {
        visitAnchors.push(`<span class="pebird-map-popup__visit-link-text">${escapeHtml(linkLabel)}</span>`);
      }
    }
  }
  /** Mirrors Folium ``build_visit_info_html``: ``<br>`` between *inline* checklist links — not ``display:block`` anchors (#222). */
  const visitInner = visitAnchors.join("<br>");

  let truncBlock = "";
  if (trunc?.visited_truncated && (trunc.visited_omitted ?? 0) > 0 && hlSafe) {
    const total = trunc.visited_total ?? entries.length + (trunc.visited_omitted ?? 0);
    const omit = trunc.visited_omitted ?? 0;
    truncBlock =
      `<div class="pebird-map-popup__trunc-hint">` +
      `${escapeHtml(String(entries.length))} of ${escapeHtml(String(total))} checklists shown. ` +
      `<a href="${escapeHtml(hlSafe)}" target="_blank" rel="noopener noreferrer">Open lifelist</a> ` +
      `for full history (${escapeHtml(String(omit))} more).` +
      `</div>`;
  }

  return (
    `<div class="pebird-map-popup popup-scroll-wrapper" style="position:relative;">` +
    `<div class="pebird-map-popup__heading-row" style="margin-bottom:${margin}px;">${locHeading}</div>` +
    `<div class="pebird-map-popup__scroll" style="max-height:300px;overflow-y:auto;">` +
    `<div class="pebird-map-popup__visited-block">` +
    `<div class="pebird-map-popup__section-label">${escapeHtml(label)}</div>` +
    `<div class="pebird-map-popup__visit-dates">${visitInner}</div>` +
    `</div>${truncBlock}` +
    `</div></div>`
  );
}

/** Single Leaflet popup layout for structured `popup_v1` (+ legacy fallback). */
function popupHtmlFromFeatureProps(props: Record<string, unknown> | undefined): string {
  const name = String(props?.name ?? "Location");
  const lifelistUrl = String(props?.lifelist_url ?? "");
  const liferPop = parseLiferPopupV1(props?.lifer_popup_v1);
  if (liferPop) {
    return popupHtmlLiferLayout(name, lifelistUrl, liferPop);
  }
  const speciesPop = parseSpeciesPopupV1(props?.species_popup_v1);
  if (speciesPop) {
    return popupHtmlSpeciesLayout(name, lifelistUrl, speciesPop);
  }
  const popup = parsePopupV1(props?.popup_v1);
  if (popup?.visited) {
    const trunc =
      popup.visited_truncated === true
        ? {
            visited_truncated: true,
            visited_total: popup.visited_total,
            visited_omitted: popup.visited_omitted,
          }
        : undefined;
    return popupHtmlVisitedLayout(name, lifelistUrl, popup.visited, trunc);
  }
  if (popup) {
    const margin = POPUP_LOCATION_HEADING_MARGIN_PX;
    const hl = lifelistUrl.trim();
    const hlSafe = safeHttpUrlForAnchor(hl);
    const locHeading =
      hlSafe.length > 0
        ? `<a class="pebird-map-popup__location-heading" href="${escapeHtml(hlSafe)}" target="_blank" rel="noopener noreferrer">${escapeHtml(name)}</a>`
        : `<span class="pebird-map-popup__location-heading">${escapeHtml(name)}</span>`;
    let html =
      `<div class="pebird-map-popup">` +
      `<div class="pebird-map-popup__heading-row" style="margin-bottom:${margin}px;">${locHeading}</div>`;
    for (const line of popup.summary_lines ?? []) {
      html += `<span class="pebird-map-popup__summary-line">${escapeHtml(line)}</span>`;
    }
    for (const link of popup.links ?? []) {
      const href = link.href?.trim() ?? "";
      const label = link.label?.trim() || "Link";
      if (href) {
        const hrefSafe = safeHttpUrlForAnchor(href);
        if (hrefSafe) {
          html += `<span class="pebird-map-popup__summary-line"><a href="${escapeHtml(hrefSafe)}" target="_blank" rel="noopener noreferrer">${escapeHtml(
            label,
          )}</a></span>`;
        } else {
          html += `<span class="pebird-map-popup__summary-line">${escapeHtml(label)}</span>`;
        }
      }
    }
    html += "</div>";
    return html;
  }
  const visits = props?.visit_checklists;
  const url = String(props?.lifelist_url ?? "").trim();
  const urlSafe = safeHttpUrlForAnchor(url);
  const margin = POPUP_LOCATION_HEADING_MARGIN_PX;
  const locHeading =
    urlSafe.length > 0
      ? `<a class="pebird-map-popup__location-heading" href="${escapeHtml(urlSafe)}" target="_blank" rel="noopener noreferrer">${escapeHtml(name)}</a>`
      : `<span class="pebird-map-popup__location-heading">${escapeHtml(name)}</span>`;
  let legacy =
    `<div class="pebird-map-popup">` +
    `<div class="pebird-map-popup__heading-row" style="margin-bottom:${margin}px;">${locHeading}</div>`;
  if (visits != null && visits !== "") {
    legacy += `<span class="pebird-map-popup__summary-line">Checklists: ${escapeHtml(String(visits))}</span>`;
  }
  legacy += "</div>";
  return legacy;
}

function isHex6(s: string | undefined): boolean {
  return typeof s === "string" && /^#[0-9a-fA-F]{6}$/.test(s);
}

/** Folium-equivalent CircleMarker options from Python or legacy GeoJSON ``colour``. */
function resolvedCircleStyles(
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

function injectHeadFragments(mapThemeCss: string, mapPopupWidthScript: string): void {
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

function AllLocationsMap(props: ComponentProps): React.ReactElement {
  const args = props.args as MapArgs;
  const wrapperRef = useRef<HTMLDivElement | null>(null);
  const mapPaneRef = useRef<HTMLDivElement | null>(null);
  const mapRef = useRef<L.Map | null>(null);
  /** Overlay layer: MarkerClusterGroup when clustering on, else plain LayerGroup. */
  const overlayRef = useRef<L.LayerGroup | null>(null);
  /** Folium ``_apply_go_to_gps_pin_view`` red pin — map root, not inside MarkerCluster (#222). */
  const goToGpsMarkerRef = useRef<L.Marker | null>(null);
  /** OSM / Carto / Google tile layer — swapped when ``map_style`` changes without GeoJSON revision. */
  const baseTileLayerRef = useRef<L.TileLayer | null>(null);
  /** Leaflet ``Popup`` instance when open — used to ``update()`` after iframe resize / width shrink (#145 / #222). */
  const openLeafletPopupRef = useRef<L.Popup | null>(null);
  const lastRevisionRef = useRef<string | null>(null);

  useEffect(() => {
    injectHeadFragments(args.map_theme_css ?? "", args.map_popup_width_script ?? "");
  }, [args.map_theme_css, args.map_popup_width_script]);

  /** Streamlit iframe height is applied after first paint; Leaflet must re-read container size or popups anchor wrong pixels (#222). */
  useEffect(() => {
    const map = mapRef.current;
    const el = wrapperRef.current;
    if (!map || !el) {
      return;
    }
    const bump = () => {
      map.invalidateSize({ debounceMoveend: true });
      shrinkPebirdLeafletPopups(map);
      const p = openLeafletPopupRef.current;
      if (p && typeof (p as unknown as { update?: () => void }).update === "function") {
        (p as unknown as { update: () => void }).update();
        maybePanPopupIntoView(map, p);
      }
    };
    const ro = new ResizeObserver(() => {
      bump();
    });
    ro.observe(el);
    bump();
    const timers = [50, 200, 500].map((ms) => window.setTimeout(bump, ms));
    return () => {
      ro.disconnect();
      timers.forEach((t) => window.clearTimeout(t));
    };
  }, [args.height, args.revision, args.geojson, args.cluster_options, args.circle_marker_style, args.cluster_icon_style, args.viewport]);

  useEffect(() => {
    const map = mapRef.current;
    if (!map) {
      return;
    }
    applyBasemapToMap(map, args.map_style, baseTileLayerRef);
    map.invalidateSize({ debounceMoveend: true });
  }, [args.map_style]);

  useEffect(() => {
    const height = Number(args.height) || 420;
    Streamlit.setFrameHeight(height);

    if (!mapPaneRef.current) {
      return;
    }

    if (!mapRef.current) {
      const map = L.map(mapPaneRef.current, {
        zoomControl: true,
        attributionControl: true,
      });
      mapRef.current = map;
      map.on("popupopen", (ev: L.LeafletEvent) => {
        const raw = ev as unknown as { popup?: L.Popup };
        const popup = raw.popup;
        openLeafletPopupRef.current = popup ?? null;
        if (popup) {
          scheduleShrinkPebirdLeafletPopups(map, popup);
        } else {
          scheduleShrinkPebirdLeafletPopups(map);
        }
      });
      map.on("popupclose", () => {
        openLeafletPopupRef.current = null;
      });
      applyBasemapToMap(map, args.map_style, baseTileLayerRef);
    }

    const map = mapRef.current!;
    const clusterPayload = mergeClusterPayload(args.cluster_options);
    const clusterEnabled = clusterPayload.enabled !== false;
    const rev = String(args.revision ?? "");

    if (lastRevisionRef.current === rev && rev !== "") {
      console.debug("[all_locations_map] revision unchanged; skipping layer rebuild", rev);
      map.invalidateSize();
      return;
    }
    lastRevisionRef.current = rev;

    if (overlayRef.current !== null) {
      map.removeLayer(overlayRef.current);
      overlayRef.current = null;
    }

    const gj = args.geojson;
    if (!gj || !gj.features || gj.features.length === 0) {
      const vpEmpty = parseViewportV1(args.viewport);
      if (vpEmpty?.mode === "go_to_gps") {
        applyGoToGpsViewportCamera(map, vpEmpty);
      } else {
        map.setView([20, 0], 2);
      }
      syncGoToGpsMarker(map, args.viewport, goToGpsMarkerRef);
      map.invalidateSize();
      return () => {
        const m = mapRef.current;
        if (m && goToGpsMarkerRef.current) {
          m.removeLayer(goToGpsMarkerRef.current);
          goToGpsMarkerRef.current = null;
        }
      };
    }

    let overlay: L.LayerGroup;
    if (clusterEnabled) {
      overlay = L.markerClusterGroup(
        markerClusterGroupOptionsWithOptionalIconStyle(clusterPayload, args.cluster_icon_style),
      ) as unknown as L.LayerGroup;
    } else {
      overlay = L.layerGroup();
    }
    overlay.addTo(map);
    overlayRef.current = overlay;

    const gjLayer = L.geoJSON(gj, {
      pointToLayer(feature, latlng) {
        const pin = parseCirclePin(feature.properties?.circle_pin);
        const featureColour = feature.properties?.colour as string | undefined;
        const rs = pin
          ? resolvedCircleStylesFromPinPayload(pin)
          : resolvedCircleStyles(args.circle_marker_style, featureColour);
        const opts: L.CircleMarkerOptions = {
          radius: rs.radius,
          stroke: true,
          weight: rs.weight,
          color: rs.color,
          fillColor: rs.fillColor,
          fillOpacity: rs.fillOpacity,
        };
        return L.circleMarker(latlng, opts);
      },
      onEachFeature(feature, lyr) {
        const html = popupHtmlFromFeatureProps(feature.properties as Record<string, unknown> | undefined);
        lyr.bindPopup(html, POPUP_BIND_OPTIONS);
      },
    });

    overlay.addLayer(gjLayer);

    applyAllLocationsViewport(map, args.viewport, gjLayer);
    syncGoToGpsMarker(map, args.viewport, goToGpsMarkerRef);

    map.invalidateSize();

    return () => {
      const m = mapRef.current;
      if (m && goToGpsMarkerRef.current) {
        m.removeLayer(goToGpsMarkerRef.current);
        goToGpsMarkerRef.current = null;
      }
    };
    // map_style is applied in the basemap-only effect above; do not rebuild markers/clusters here.
    // eslint-disable-next-line react-hooks/exhaustive-deps -- overlay keyed on revision, not tiles
  }, [
    args.revision,
    args.geojson,
    args.height,
    args.cluster_options,
    args.circle_marker_style,
    args.cluster_icon_style,
    args.viewport,
  ]);

  const h = Number(args.height) || 420;
  const banner = (args.banner_html ?? "").trim();
  const legend = (args.legend_html ?? "").trim();
  return (
    <div
      ref={wrapperRef}
      className="all-locations-map-frame"
      style={{
        position: "relative",
        width: "100%",
        height: h,
        minHeight: h,
      }}
    >
      <div
        ref={mapPaneRef}
        className="all-locations-leaflet-pane"
        style={{
          position: "absolute",
          left: 0,
          top: 0,
          right: 0,
          bottom: 0,
          zIndex: 0,
        }}
      />
      {banner ? <div key="banner-overlay" dangerouslySetInnerHTML={{ __html: banner }} /> : null}
      {legend ? <div key="legend-overlay" dangerouslySetInnerHTML={{ __html: legend }} /> : null}
    </div>
  );
}

export default withStreamlitConnection(AllLocationsMap);
