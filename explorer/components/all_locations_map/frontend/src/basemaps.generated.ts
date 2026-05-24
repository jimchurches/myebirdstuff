/** AUTO-GENERATED from explorer/data/basemaps.yaml — do not edit. */
/** Regenerate: python3 scripts/generate_basemap_assets.py */

import type { TileLayerOptions } from "leaflet";

export type BasemapId = "default" | "voyager" | "carto" | "esri_topo" | "google";

export const BASEMAP_IDS = ["default", "voyager", "carto", "esri_topo", "google"] as const;

export const BASEMAP_DEFAULT: BasemapId = "default";

export type BasemapTileConfig = { url: string; opts: TileLayerOptions };

export const ALL_LOCATIONS_BASEMAPS: Record<BasemapId, BasemapTileConfig> = {
  "default": {
    url: "https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png",
    opts: { maxZoom: 19, attribution: "&copy; <a href=\"https://www.openstreetmap.org/copyright\">OpenStreetMap</a>" },
  },
  "voyager": {
    url: "https://{s}.basemaps.cartocdn.com/rastertiles/voyager/{z}/{x}/{y}{r}.png",
    opts: { maxZoom: 20, subdomains: "abcd", attribution: "&copy; <a href=\"https://www.openstreetmap.org/copyright\">OpenStreetMap</a> contributors &copy; <a href=\"https://carto.com/attributions\">CARTO</a>" },
  },
  "carto": {
    url: "https://{s}.basemaps.cartocdn.com/light_all/{z}/{x}/{y}{r}.png",
    opts: { maxZoom: 20, subdomains: "abcd", attribution: "&copy; <a href=\"https://www.openstreetmap.org/copyright\">OpenStreetMap</a> contributors &copy; <a href=\"https://carto.com/attributions\">CARTO</a>" },
  },
  "esri_topo": {
    url: "https://server.arcgisonline.com/ArcGIS/rest/services/World_Topo_Map/MapServer/tile/{z}/{y}/{x}",
    opts: { maxZoom: 19, attribution: "Tiles &copy; Esri &mdash; Esri, DeLorme, NAVTEQ, TomTom, Intermap, iPC, USGS, FAO, NPS, NRCAN, GeoBase, Kadaster NL, Ordnance Survey, Esri Japan, METI, Esri China (Hong Kong), and the GIS User Community" },
  },
  "google": {
    url: "https://mt1.google.com/vt/lyrs=y&x={x}&y={y}&z={z}",
    opts: { maxZoom: 22, attribution: "Google" },
  },
};
