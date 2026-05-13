import React, { useEffect, useRef } from "react";
import L from "leaflet";
import "leaflet/dist/leaflet.css";
import "leaflet.markercluster/dist/MarkerCluster.css";
import "leaflet.markercluster/dist/MarkerCluster.Default.css";
import "leaflet.markercluster/dist/leaflet.markercluster.js";
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

/** Classic All locations card: lifelist heading + scrollable ``Visited:`` links (``map_popup_models``). */
function popupHtmlVisitedLayout(
  name: string,
  lifelistUrl: string,
  visited: NonNullable<PopupPayloadV1["visited"]>,
  trunc?: Pick<PopupPayloadV1, "visited_truncated" | "visited_total" | "visited_omitted">,
): string {
  const label = visited.label?.trim() || "Visited:";
  const entries = visited.entries ?? [];
  let html =
    `<div class="pebird-map-popup popup-scroll-wrapper" style="position:relative;font-family:system-ui,sans-serif;font-size:13px;">` +
    `<div style="margin-bottom:4px;">`;
  const hl = lifelistUrl.trim();
  if (hl) {
    html += `<a href="${escapeHtml(hl)}" target="_blank" rel="noopener noreferrer" style="font-weight:600;color:#0066cc;text-decoration:underline;">${escapeHtml(
      name,
    )}</a>`;
  } else {
    html += `<strong>${escapeHtml(name)}</strong>`;
  }
  html +=
    `</div>` +
    `<div style="max-height:300px;overflow-y:auto;">` +
    `<div style="font-weight:600;margin-bottom:4px;">${escapeHtml(label)}</div>` +
    `<div class="pebird-map-popup__visit-dates">`;
  for (const e of entries) {
    const href = e.href?.trim() ?? "";
    const linkLabel = e.label?.trim() || href;
    if (href) {
      html += `<div style="margin:0 0 5px 0;line-height:1.35;">` +
        `<a href="${escapeHtml(href)}" target="_blank" rel="noopener noreferrer">${escapeHtml(linkLabel)}</a>` +
        `</div>`;
    }
  }
  html += `</div>`;
  if (trunc?.visited_truncated && (trunc.visited_omitted ?? 0) > 0 && hl) {
    const total = trunc.visited_total ?? entries.length + (trunc.visited_omitted ?? 0);
    const omit = trunc.visited_omitted ?? 0;
    html +=
      `<div style="margin-top:8px;color:#555;font-size:12px;line-height:1.35;">` +
      `${escapeHtml(String(entries.length))} of ${escapeHtml(String(total))} checklists shown.` +
      ` <a href="${escapeHtml(hl)}" target="_blank" rel="noopener noreferrer">Open lifelist</a>` +
      ` for full history (${escapeHtml(String(omit))} more).` +
      `</div>`;
  }
  html += `</div></div>`;
  return html;
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
    let html = `<div class="pebird-map-popup" style="font-family:system-ui,sans-serif;font-size:13px;">`;
    html += `<strong>${escapeHtml(name)}</strong>`;
    for (const line of popup.summary_lines ?? []) {
      html += `<br/><span style="color:#444;">${escapeHtml(line)}</span>`;
    }
    for (const link of popup.links ?? []) {
      const href = link.href?.trim() ?? "";
      const label = link.label?.trim() || "Link";
      if (href) {
        html += `<br/><a href="${escapeHtml(href)}" target="_blank" rel="noopener noreferrer">${escapeHtml(
          label,
        )}</a>`;
      }
    }
    html += "</div>";
    return html;
  }
  const visits = props?.visit_checklists;
  const url = String(props?.lifelist_url ?? "");
  let legacy = `<div style="font-family:system-ui,sans-serif;font-size:13px;"><strong>${escapeHtml(name)}</strong>`;
  if (visits != null && visits !== "") {
    legacy += `<br/><span style="color:#444;">Checklists: ${escapeHtml(String(visits))}</span>`;
  }
  if (url) {
    legacy += `<br/><a href="${escapeHtml(url)}" target="_blank" rel="noopener noreferrer">Lifelist</a>`;
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

function AllLocationsMap(props: ComponentProps): React.ReactElement {
  const args = props.args as MapArgs;
  const containerRef = useRef<HTMLDivElement | null>(null);
  const mapRef = useRef<L.Map | null>(null);
  /** Overlay layer: MarkerClusterGroup when clustering on, else plain LayerGroup. */
  const overlayRef = useRef<L.LayerGroup | null>(null);
  const lastRevisionRef = useRef<string | null>(null);

  useEffect(() => {
    const height = Number(args.height) || 420;
    Streamlit.setFrameHeight(height);

    if (!containerRef.current) {
      return;
    }

    if (!mapRef.current) {
      const map = L.map(containerRef.current, {
        zoomControl: true,
        attributionControl: true,
      });
      mapRef.current = map;
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
  return (
    <div
      ref={containerRef}
      style={{
        width: "100%",
        height: h,
        minHeight: h,
      }}
    />
  );
}

export default withStreamlitConnection(AllLocationsMap);
