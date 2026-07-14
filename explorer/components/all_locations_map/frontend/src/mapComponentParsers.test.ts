import { parseViewportV1 } from "./mapComponentParsers";

describe("parseViewportV1", () => {
  it("returns null for non-objects", () => {
    expect(parseViewportV1(null)).toBeNull();
    expect(parseViewportV1("x")).toBeNull();
    expect(parseViewportV1([])).toBeNull();
  });

  it("requires the supported version and mode", () => {
    expect(parseViewportV1({ v: 2, mode: "center_zoom", center: [0, 0], zoom: 5 })).toBeNull();
    expect(parseViewportV1({ v: "1", mode: "center_zoom", center: [0, 0], zoom: 5 })).toBeNull();
    expect(parseViewportV1({ v: 1, mode: "unknown" })).toBeNull();
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
    expect(vp).toEqual({
      mode: "fit_bounds",
      single_point: true,
      lat: 1,
      lon: 2,
      epsilon_delta: 0.05,
      padding_px: 20,
      max_zoom: 12,
    });
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

  it.each([
    {
      v: 1,
      mode: "go_to_gps",
      lat: "not-a-number",
      lon: 149,
      padding_px: 20,
      epsilon_delta: 0.01,
      max_zoom: 14,
    },
    { v: 1, mode: "center_zoom", center: [1], zoom: 8 },
    { v: 1, mode: "center_zoom", center: [1, 2], zoom: Infinity },
    {
      v: 1,
      mode: "fit_bounds",
      single_point: true,
      lat: 1,
      lon: 2,
      epsilon_delta: Number.NaN,
      padding_px: 20,
      max_zoom: 12,
    },
    {
      v: 1,
      mode: "fit_bounds",
      single_point: false,
      pairs: [[1, 2, 3]],
      padding_px: 20,
      max_zoom: 12,
    },
    {
      v: 1,
      mode: "fit_bounds",
      single_point: false,
      pairs: [[1, "bad"]],
      padding_px: 20,
      max_zoom: 12,
    },
  ])("rejects malformed viewport payload %#", (payload) => {
    expect(parseViewportV1(payload)).toBeNull();
  });
});
