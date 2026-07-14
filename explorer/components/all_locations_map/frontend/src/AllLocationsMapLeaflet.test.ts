import { normalizeBasemapId } from "./AllLocationsMapLeaflet";
import { BASEMAP_IDS } from "./basemaps.generated";

describe("normalizeBasemapId", () => {
  it("accepts all production basemap keys", () => {
    for (const key of BASEMAP_IDS) {
      expect(normalizeBasemapId(key)).toBe(key);
      expect(normalizeBasemapId(`  ${key.toUpperCase()}  `)).toBe(key);
    }
  });

  it("falls back to default for unknown keys", () => {
    for (const value of ["voyager_nolabels", "", "   ", undefined]) {
      expect(normalizeBasemapId(value)).toBe("default");
    }
  });
});
