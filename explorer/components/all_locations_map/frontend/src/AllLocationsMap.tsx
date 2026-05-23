import React, { useEffect, useRef } from "react";
import L from "leaflet";
import "leaflet/dist/leaflet.css";
import "leaflet.markercluster/dist/MarkerCluster.css";
import "leaflet.markercluster/dist/MarkerCluster.Default.css";
import "leaflet.markercluster/dist/leaflet.markercluster.js";
import "./AllLocationsMapPopup.css";
import { parseViewportV1 } from "./mapComponentParsers";
import {
  ComponentProps,
  Streamlit,
  withStreamlitConnection,
} from "streamlit-component-lib";
import type { MapArgs } from "./allLocationsMapTypes";
import {
  applyAllLocationsViewport,
  applyBasemapToMap,
  applyGoToGpsViewportCamera,
  injectHeadFragments,
  markerClusterGroupOptionsWithOptionalIconStyle,
  mergeClusterPayload,
  parseCirclePin,
  resolvedCircleStyles,
  resolvedCircleStylesFromPinPayload,
  syncGoToGpsMarker,
  syncZoomLevelDebugOverlay,
} from "./AllLocationsMapLeaflet";
import { popupHtmlFromFeatureProps } from "./AllLocationsMapPopupHtml";
import {
  POPUP_BIND_OPTIONS,
  maybePanPopupIntoView,
  scheduleShrinkPebirdLeafletPopups,
  shrinkPebirdLeafletPopups,
} from "./AllLocationsMapPopupSizing";
import { schedulePopupScrollHints } from "./AllLocationsMapPopupScrollHints";

declare global {
  interface Window {
    /** Playwright E2E hook: Leaflet map in this component iframe (not on window by default). */
    __pebirdLeafletMap?: L.Map;
  }
}

function AllLocationsMap(props: ComponentProps): React.ReactElement {
  const args = props.args as MapArgs;
  const wrapperRef = useRef<HTMLDivElement | null>(null);
  const mapPaneRef = useRef<HTMLDivElement | null>(null);
  const mapRef = useRef<L.Map | null>(null);
  /** Overlay layer: MarkerClusterGroup when clustering on, else plain LayerGroup. */
  const overlayRef = useRef<L.LayerGroup | null>(null);
  /** Pins with ``skip_cluster`` (design utility role markers) — sibling layer, not clustered. */
  const standaloneOverlayRef = useRef<L.GeoJSON | null>(null);
  /** Temporary GPS marker — map root, not inside MarkerCluster (``go_to_gps`` viewport). */
  const goToGpsMarkerRef = useRef<L.Marker | null>(null);
  /** OSM / Carto / Google tile layer — swapped when ``map_style`` changes without GeoJSON revision. */
  const baseTileLayerRef = useRef<L.TileLayer | null>(null);
  /** Leaflet ``Popup`` instance when open — used to ``update()`` after iframe resize / width shrink (#145). */
  const openLeafletPopupRef = useRef<L.Popup | null>(null);
  const lastRevisionRef = useRef<string | null>(null);
  const zoomDebugControlRef = useRef<L.Control | null>(null);
  const zoomDebugOnZoomRef = useRef<(() => void) | null>(null);
  const popupScrollHintRef = useRef(args.popup_scroll_hint ?? "");
  const popupScrollToBottomRef = useRef(Boolean(args.popup_scroll_to_bottom));

  useEffect(() => {
    popupScrollHintRef.current = args.popup_scroll_hint ?? "";
    popupScrollToBottomRef.current = Boolean(args.popup_scroll_to_bottom);
  }, [args.popup_scroll_hint, args.popup_scroll_to_bottom]);

  useEffect(() => {
    injectHeadFragments(args.map_theme_css ?? "", args.map_popup_width_script ?? "");
  }, [args.map_theme_css, args.map_popup_width_script]);

  /** Streamlit iframe height is applied after first paint; Leaflet must re-read container size or popups anchor wrong pixels. */
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
      window.__pebirdLeafletMap = map;
      map.on("popupopen", (ev: L.LeafletEvent) => {
        const raw = ev as unknown as { popup?: L.Popup };
        const popup = raw.popup;
        openLeafletPopupRef.current = popup ?? null;
        if (popup) {
          scheduleShrinkPebirdLeafletPopups(map, popup);
          schedulePopupScrollHints(
            popup,
            popupScrollHintRef.current,
            popupScrollToBottomRef.current,
          );
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
    if (standaloneOverlayRef.current !== null) {
      map.removeLayer(standaloneOverlayRef.current);
      standaloneOverlayRef.current = null;
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

    const allFeatures = gj.features ?? [];
    const clusterableFeatures = allFeatures.filter((f) => !f.properties?.skip_cluster);
    const standaloneFeatures = allFeatures.filter((f) => Boolean(f.properties?.skip_cluster));

    const geoJsonOptions: L.GeoJSONOptions = {
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
        const main = L.circleMarker(latlng, opts);
        const haloPin = parseCirclePin(feature.properties?.highlight_halo_circle);
        if (!haloPin) {
          return main;
        }
        const hs = resolvedCircleStylesFromPinPayload(haloPin);
        let strokeOp = 1;
        if (typeof haloPin.stroke_opacity === "number" && Number.isFinite(haloPin.stroke_opacity)) {
          strokeOp = Math.min(1, Math.max(0, haloPin.stroke_opacity));
        }
        const haloMarker = L.circleMarker(latlng, {
          radius: hs.radius,
          stroke: true,
          weight: hs.weight,
          color: hs.color,
          fillColor: hs.fillColor,
          fillOpacity: hs.fillOpacity,
          opacity: strokeOp,
        });
        return L.layerGroup([haloMarker, main]);
      },
      onEachFeature(feature, lyr) {
        const html = popupHtmlFromFeatureProps(feature.properties as Record<string, unknown> | undefined);
        lyr.bindPopup(html, POPUP_BIND_OPTIONS);
      },
    };

    const boundsLayers: L.Layer[] = [];

    if (standaloneFeatures.length > 0) {
      const standaloneLayer = L.geoJSON(
        { ...gj, features: standaloneFeatures } as typeof gj,
        geoJsonOptions,
      );
      standaloneLayer.addTo(map);
      standaloneOverlayRef.current = standaloneLayer;
      boundsLayers.push(standaloneLayer);
    }

    let overlay: L.LayerGroup;
    if (clusterEnabled && clusterableFeatures.length > 0) {
      overlay = L.markerClusterGroup(
        markerClusterGroupOptionsWithOptionalIconStyle(clusterPayload, args.cluster_icon_style),
      ) as unknown as L.LayerGroup;
    } else {
      overlay = L.layerGroup();
    }
    overlay.addTo(map);
    overlayRef.current = overlay;

    if (clusterableFeatures.length > 0) {
      const gjLayer = L.geoJSON(
        { ...gj, features: clusterableFeatures } as typeof gj,
        geoJsonOptions,
      );
      overlay.addLayer(gjLayer);
      boundsLayers.push(gjLayer);
    }

    const viewportLayer: L.Layer | null =
      boundsLayers.length === 0
        ? null
        : boundsLayers.length === 1
          ? boundsLayers[0]!
          : L.featureGroup(boundsLayers);

    applyAllLocationsViewport(map, args.viewport, viewportLayer);
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

  useEffect(() => {
    const map = mapRef.current;
    if (!map) {
      return;
    }
    syncZoomLevelDebugOverlay(
      map,
      Boolean(args.show_zoom_debug),
      zoomDebugControlRef,
      zoomDebugOnZoomRef,
    );
    return () => {
      syncZoomLevelDebugOverlay(map, false, zoomDebugControlRef, zoomDebugOnZoomRef);
    };
  }, [args.show_zoom_debug]);

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
