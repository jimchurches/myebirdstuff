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
        const c = feature.properties?.colour as string | undefined;
        const opts: L.CircleMarkerOptions = {
          radius: 7,
          stroke: true,
          weight: 1,
          color: "#1c2630",
          fillColor: c && /^#[0-9a-fA-F]{6}$/.test(c) ? c : "#3388ff",
          fillOpacity: 0.88,
        };
        return L.circleMarker(latlng, opts);
      },
      onEachFeature(feature, lyr) {
        const name = String(feature.properties?.name ?? "Location");
        const visits = feature.properties?.visit_checklists;
        const url = String(feature.properties?.lifelist_url ?? "");
        let html = `<div style="font-family:system-ui,sans-serif;font-size:13px;"><strong>${escapeHtml(
          name,
        )}</strong>`;
        if (visits != null && visits !== "") {
          html += `<br/><span style="color:#444;">Checklists: ${escapeHtml(String(visits))}</span>`;
        }
        if (url) {
          html += `<br/><a href="${escapeHtml(url)}" target="_blank" rel="noopener noreferrer">Lifelist</a>`;
        }
        html += "</div>";
        lyr.bindPopup(html);
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
  }, [args.revision, args.geojson, args.height, args.cluster_options]);

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
