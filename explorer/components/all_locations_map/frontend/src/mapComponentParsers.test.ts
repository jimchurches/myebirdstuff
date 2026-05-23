import { parseViewportV1 } from "./mapComponentParsers";

describe("parseViewportV1", () => {
  it("returns null for non-objects", () => {
    expect(parseViewportV1(null)).toBeNull();
    expect(parseViewportV1("x")).toBeNull();
  });

  it("requires v === 1", () => {
    expect(parseViewportV1({ v: 2, mode: "center_zoom", center: [0, 0], zoom: 5 })).toBeNull();
  });

  it("parses go_to_gps", () => {
    const vp = parseViewportV1({
      v: 1,
      mode: "go_to_gps",
      lat: -35.1,
      lon: 149.2,
      padding_px: 40,
      epsilon_delta: 0.01,
      max_zoom: 14,
    });
    expect(vp).toEqual({
      mode: "go_to_gps",
      lat: -35.1,
      lon: 149.2,
      padding_px: 40,
      epsilon_delta: 0.01,
      max_zoom: 14,
    });
  });

  it("parses center_zoom", () => {
    const vp = parseViewportV1({ v: 1, mode: "center_zoom", center: [-33, 151], zoom: 8.7 });
    expect(vp).toEqual({ mode: "center_zoom", center: [-33, 151], zoom: 9 });
  });

  it("parses fit_bounds single point", () => {
    const vp = parseViewportV1({
      v: 1,
      mode: "fit_bounds",
      single_point: true,
      lat: 1,
      lon: 2,
      epsilon_delta: 0.05,
      padding_px: 20,
      max_zoom: 12,
    });
    expect(vp?.mode).toBe("fit_bounds");
    if (vp?.mode === "fit_bounds" && vp.single_point) {
      expect(vp.lat).toBe(1);
      expect(vp.max_zoom).toBe(12);
    }
  });

  it("parses fit_bounds multi pair", () => {
    const vp = parseViewportV1({
      v: 1,
      mode: "fit_bounds",
      single_point: false,
      pairs: [
        [0, 0],
        [1, 1],
      ],
      padding_px: 30,
      max_zoom: 11,
    });
    expect(vp).toEqual({
      mode: "fit_bounds",
      single_point: false,
      pairs: [
        [0, 0],
        [1, 1],
      ],
      padding_px: 30,
      max_zoom: 11,
    });
  });

  it("rejects fit_bounds with empty pairs", () => {
    expect(
      parseViewportV1({
        v: 1,
        mode: "fit_bounds",
        single_point: false,
        pairs: [],
        padding_px: 30,
        max_zoom: 11,
      }),
    ).toBeNull();
  });
});
