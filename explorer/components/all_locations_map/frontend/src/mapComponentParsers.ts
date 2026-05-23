/** Pure parsers for Streamlit → component args (unit-testable without Leaflet mount). */

export type LatLngTuple = [number, number];

export type ViewportV1GoToGps = {
  mode: "go_to_gps";
  lat: number;
  lon: number;
  padding_px: number;
  epsilon_delta: number;
  max_zoom: number;
};

export type ViewportV1CenterZoom = {
  mode: "center_zoom";
  center: LatLngTuple;
  zoom: number;
};

export type ViewportV1FitBoundsSingle = {
  mode: "fit_bounds";
  single_point: true;
  lat: number;
  lon: number;
  epsilon_delta: number;
  padding_px: number;
  max_zoom: number;
};

export type ViewportV1FitBoundsMulti = {
  mode: "fit_bounds";
  single_point: false;
  pairs: LatLngTuple[];
  padding_px: number;
  max_zoom: number;
};

export type ViewportV1 =
  | ViewportV1GoToGps
  | ViewportV1CenterZoom
  | ViewportV1FitBoundsSingle
  | ViewportV1FitBoundsMulti;

export function parseViewportV1(raw: unknown): ViewportV1 | null {
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
      const pairs: LatLngTuple[] = [];
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
