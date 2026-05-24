import { normalizeBasemapId } from "./AllLocationsMapLeaflet";

describe("normalizeBasemapId", () => {
  it("accepts all production basemap keys", () => {
    for (const key of ["default", "voyager", "carto", "esri_topo", "google"]) {
      expect(normalizeBasemapId(key)).toBe(key);
    }
  });

  it("falls back to default for unknown keys", () => {
    expect(normalizeBasemapId("voyager_nolabels")).toBe("default");
    expect(normalizeBasemapId("")).toBe("default");
    expect(normalizeBasemapId(undefined)).toBe("default");
  });

  it("normalizes case and whitespace", () => {
    expect(normalizeBasemapId("  ESRI_TOPO  ")).toBe("esri_topo");
  });
});
