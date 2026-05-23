/** Shared Streamlit component arg types (R14 split). */

export interface ClusterOptionsPayload {
  enabled?: boolean;
  max_cluster_radius?: number;
  disable_clustering_at_zoom?: number;
  spiderfy_on_max_zoom?: boolean;
  remove_outside_visible_bounds?: boolean;
}

export interface CircleMarkerStylePayload {
  fill_hex?: string;
  stroke_hex?: string;
  radius_px?: number;
  stroke_weight?: number;
  fill_opacity?: number;
}

export interface ClusterIconStylePayload {
  fills_rgba: string[];
  borders_rgba: string[];
  halos_rgba: string[];
  border_width_px: number;
  halo_spread_px: number;
}

export interface PopupLinkV1 {
  label?: string;
  href?: string;
}

export interface PopupPayloadV1 {
  v: 1;
  summary_lines?: string[];
  links?: PopupLinkV1[];
  visited?: {
    label?: string;
    entries?: PopupLinkV1[];
  };
}

export interface MapArgs {
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
  cluster_icon_style?: ClusterIconStylePayload | Record<string, unknown>;
  map_theme_css?: string;
  map_popup_width_script?: string;
  /** Settings: ``chevron`` | ``shading`` | ``both`` — overflow hints on scrollable popup body. */
  popup_scroll_hint?: string;
  /** When true (visit sort ascending), scroll popup body to bottom on open. */
  popup_scroll_to_bottom?: boolean;
  banner_html?: string;
  legend_html?: string;
  viewport?: Record<string, unknown>;
  map_style?: string;
  show_zoom_debug?: boolean;
}

export const DEFAULT_CLUSTER_PAYLOAD: ClusterOptionsPayload = {
  enabled: true,
  max_cluster_radius: 40,
  disable_clustering_at_zoom: 9,
  spiderfy_on_max_zoom: false,
  remove_outside_visible_bounds: false,
};
