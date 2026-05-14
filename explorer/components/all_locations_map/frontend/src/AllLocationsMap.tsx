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

/** Folium `MAP_POPUP_MAX_WIDTH_PX` (`explorer/app/streamlit/defaults.py`). */
const POPUP_MAX_WIDTH_PX = 420;

/** Default gap below location title row — matches ``build_location_popup_html(..., location_heading_margin_px=4)``. */
const POPUP_LOCATION_HEADING_MARGIN_PX = 4;

/** Shrink-wrap Leaflet popup width to ``.pebird-map-popup`` intrinsic width (``map_popup_width_fix_script``). */
function capPopupInnerWidthPx(): number {
  return Math.min(POPUP_MAX_WIDTH_PX, Math.max(80, window.innerWidth - 40));
}

function shrinkPebirdLeafletPopups(): void {
  const pops = document.querySelectorAll(".leaflet-popup-pane .leaflet-popup");
  const cap = capPopupInnerWidthPx();
  pops.forEach((pop) => {
    const content = pop.querySelector(".leaflet-popup-content") as HTMLElement | null;
    const wrap = pop.querySelector(".leaflet-popup-content-wrapper") as HTMLElement | null;
    const inner = pop.querySelector(".pebird-map-popup") as HTMLElement | null;
    if (!content || !wrap || !inner) {
      return;
    }
    content.style.removeProperty("width");
    content.style.removeProperty("white-space");
    wrap.style.removeProperty("width");

    let innerPx = Math.ceil(inner.scrollWidth);
    if (innerPx < 2) {
      innerPx = Math.ceil(inner.getBoundingClientRect().width);
    }
    const target = Math.min(innerPx, cap);
    content.style.setProperty("width", `${target}px`, "important");
    content.style.setProperty("max-width", `${cap}px`, "important");
    wrap.style.setProperty("width", `${target}px`, "important");
    wrap.style.setProperty("max-width", `${cap}px`, "important");
  });
}

function scheduleShrinkPebirdLeafletPopups(): void {
  requestAnimationFrame(() => {
    requestAnimationFrame(() => shrinkPebirdLeafletPopups());
  });
  const delays = [0, 30, 80, 150, 260, 400];
  for (let k = 0; k < delays.length; k++) {
    window.setTimeout(shrinkPebirdLeafletPopups, delays[k]);
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
  /** Injected into iframe ``<head>`` — same as Folium ``map_overlay_theme_stylesheet`` (#222). */
  map_theme_css?: string;
  /** Injected once — Folium ``map_popup_width_fix_script`` (#222). */
  map_popup_width_script?: string;
  /** Fixed-position banner HTML (viewport = iframe), e.g. top-right ``pebird-map-banner`` (#222). */
  banner_html?: string;
  /** Fixed-position legend HTML, e.g. bottom-left ``pebird-map-legend`` (#222). */
  legend_html?: string;
}

/** Matches Folium all-locations defaults from explorer.app.streamlit.defaults. */
const DEFAULT_CLUSTER_PAYLOAD: ClusterOptionsPayload = {
  enabled: true,
  max_cluster_radius: 40,
  disable_clustering_at_zoom: 9,
  spiderfy_on_max_zoom: false,
  remove_outside_visible_bounds: false,
};

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

function escapeHtml(text: string): string {
  const div = document.createElement("div");
  div.textContent = text;
  return div.innerHTML;
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
  const margin = POPUP_LOCATION_HEADING_MARGIN_PX;
  const locHeading =
    hl.length > 0
      ? `<a class="pebird-map-popup__location-heading" href="${escapeHtml(hl)}" target="_blank" rel="noopener noreferrer">${escapeHtml(name)}</a>`
      : `<span class="pebird-map-popup__location-heading">${escapeHtml(name)}</span>`;

  const visitAnchors: string[] = [];
  for (const e of entries) {
    const href = e.href?.trim() ?? "";
    const linkLabel = e.label?.trim() || href;
    if (href) {
      visitAnchors.push(
        `<a href="${escapeHtml(href)}" target="_blank" rel="noopener noreferrer">${escapeHtml(linkLabel)}</a>`,
      );
    }
  }
  const visitInner = visitAnchors.join("<br>");

  let truncBlock = "";
  if (trunc?.visited_truncated && (trunc.visited_omitted ?? 0) > 0 && hl) {
    const total = trunc.visited_total ?? entries.length + (trunc.visited_omitted ?? 0);
    const omit = trunc.visited_omitted ?? 0;
    truncBlock =
      `<div class="pebird-map-popup__trunc-hint">` +
      `${escapeHtml(String(entries.length))} of ${escapeHtml(String(total))} checklists shown. ` +
      `<a href="${escapeHtml(hl)}" target="_blank" rel="noopener noreferrer">Open lifelist</a> ` +
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
    const locHeading =
      hl.length > 0
        ? `<a class="pebird-map-popup__location-heading" href="${escapeHtml(hl)}" target="_blank" rel="noopener noreferrer">${escapeHtml(name)}</a>`
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
        html += `<span class="pebird-map-popup__summary-line"><a href="${escapeHtml(href)}" target="_blank" rel="noopener noreferrer">${escapeHtml(
          label,
        )}</a></span>`;
      }
    }
    html += "</div>";
    return html;
  }
  const visits = props?.visit_checklists;
  const url = String(props?.lifelist_url ?? "").trim();
  const margin = POPUP_LOCATION_HEADING_MARGIN_PX;
  const locHeading =
    url.length > 0
      ? `<a class="pebird-map-popup__location-heading" href="${escapeHtml(url)}" target="_blank" rel="noopener noreferrer">${escapeHtml(name)}</a>`
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
  }, [args.height, args.revision, args.geojson, args.cluster_options, args.circle_marker_style]);

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
      map.on("popupopen", scheduleShrinkPebirdLeafletPopups);
      L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
        maxZoom: 19,
        attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>',
      }).addTo(map);
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
      map.setView([20, 0], 2);
      map.invalidateSize();
      return;
    }

    let overlay: L.LayerGroup;
    if (clusterEnabled) {
      overlay = L.markerClusterGroup(toLeafletClusterOptions(clusterPayload)) as unknown as L.LayerGroup;
    } else {
      overlay = L.layerGroup();
    }
    overlay.addTo(map);
    overlayRef.current = overlay;

    const gjLayer = L.geoJSON(gj, {
      pointToLayer(feature, latlng) {
        const featureColour = feature.properties?.colour as string | undefined;
        const rs = resolvedCircleStyles(args.circle_marker_style, featureColour);
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
        lyr.bindPopup(html, { maxWidth: POPUP_MAX_WIDTH_PX });
      },
    });

    overlay.addLayer(gjLayer);

    try {
      const b = gjLayer.getBounds();
      if (b.isValid()) {
        map.fitBounds(b.pad(0.12));
      }
    } catch {
      map.setView([20, 0], 2);
    }

    map.invalidateSize();
  }, [args.revision, args.geojson, args.height, args.cluster_options, args.circle_marker_style]);

  const h = Number(args.height) || 420;
  const banner = (args.banner_html ?? "").trim();
  const legend = (args.legend_html ?? "").trim();
  return (
    <div
      ref={wrapperRef}
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
