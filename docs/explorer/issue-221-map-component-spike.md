# Issue #221 — Streamlit custom map component (spike log)

**Issue:** [#221](https://github.com/jimchurches/myebirdstuff/issues/221)  
**Context:** [#205](https://github.com/jimchurches/myebirdstuff/issues/205) map performance investigation — exploratory spike only.

## Purpose

Validate moving interactive map rendering into a Streamlit custom component (persistent client map vs Folium full rebuild on rerun). **Not** production cutover unless we decide so later.

## Branch / merge expectations

- **This spike branch is not intended to merge into `beta-next`**, even if the experiment looks promising. Outcomes feed **new issue(s)** for a proper implementation when/if we proceed.
- Treat the branch as **exploration + evidence**: notes, scratch paths, and rough edges are acceptable.

## Hygiene (spike vs “real” branches)

- Expectations here are **lighter than on integration/production work**: extra markdown, TODOs in comments, and exploratory files left in-tree are **fine** if they help thinking and handoff.
- That does **not** mean sloppy or opaque — keep enough signal that someone (including future you) can follow **what we tried** and **what to do next**.

## How we log progress

- **GitHub:** Short updates on [#221](https://github.com/jimchurches/myebirdstuff/issues/221) (decisions, blockers, “today we tried…”).
- **This file:** Slightly more detail: dated bullets, links to PRs/commits, and anything worth searching later.

Reverse chronological is fine; keep headings scannable.

## Performance / testing — when it helps

Spike first; measurement second.

- **Early spike:** Favor qualitative notes (does the map survive reruns? any obvious jank?). Avoid polishing E2E until the architecture is plausible.
- **When to add E2E or scripted timings:** After one stable path exists (e.g. experimental tab loads real data, revision/no-op behavior is defined). Then tests guard regressions and JSONL/`EXPLORER_PERF`-style hooks become meaningful.
- **Manual A/B is OK:** Same dataset and journey on **classic All Locations map** vs **experimental map** — note wall-clock or browser devtools for “feel,” and whether Streamlit reruns still replace the whole map on the classic path. One repeatable scenario beats chasing numbers during discovery.
- **Don’t optimize to metrics** until we know we’re keeping the approach; a few labeled runs plus screenshots/log excerpts are enough for the spike write-up.

---

## Status snapshot (handoff — no need to scroll chat)

### Implemented on spike branch

- **Tab:** **Map (experimental)** after **Map**; classic Map unchanged.
- **Data:** Reuses `prepare_all_locations_map_context`; GeoJSON + **`revision`** via `build_all_locations_geojson_payload`; **`revision_extra`** includes cluster JSON so toggling clustering bumps revision.
- **Frontend:** `explorer/components/all_locations_map/` — Leaflet, **`leaflet.markercluster`**, defaults aligned with `defaults.py` (radius 40, disable clustering from zoom 9, `removeOutsideVisibleBounds` false); respects sidebar **cluster all locations** toggle.
- **Warm reruns:** Component skips full marker/cluster rebuild when `revision` unchanged (browser console log).
- **Instrumentation:** With **`EXPLORER_PERF=1`**, sidebar **Performance / debug** shows map-specific spans — Folium `prep.map_iframe_embed` vs experimental payload + component embed; times are **Python-side**, **serial script order** (not simultaneous loads, not browser paint).
- **Pop-ups (spike slice):** Each feature includes **`popup_v1`** — structured `summary_lines` + `links` rendered by one TS template (parity with current experimental popup content so far; extend toward classic richness via `map_prep` / overlay builders).

### One-off performance note (real export — cold run, JSONL)

From a captured **`explorer_perf_events.jsonl`** on spike (`main_run_id` 1, cold): **All locations**, ~**46k** checklist rows, **5721** map pins (markers/popups built per pin on classic path).

**Classic (host-side, split spans — same rerun):**

| Stage | ~ms | Comment |
|--------|-----|--------|
| `prep.build_species_overlay_map` | **~7111** | Dominated by **`popup_build_total_ms` ~6505** — thousands of **rich HTML popups** built in Python |
| `prep.folium_map_to_html_bytes` | **~3275** | Serialising Folium → HTML |
| `prep.map_iframe_embed` | **~6900** | `st_folium` + **`deepcopy(result_map)`** — heavy at this size |

**Experimental (same rerun):**

| Stage | ~ms | Comment |
|--------|-----|--------|
| `map.experimental.payload` | **~1597** | Context + GeoJSON + revision |
| `map.experimental.component_embed` | **~14** | Passing JSON into component — **does not** include tiles / Leaflet paint |

**How to read it:** Strong evidence the **Folium + HTML popup + st_folium** pipeline is vastly heavier **on the server/session path** than **compact GeoJSON + component**. Not claim “whole UX is 500× faster”: browser tile/load isn’t in the ~14 ms line; classic totals exclude optional overlap with other prep work.

**Also on that file:** `prep.cache_checklist_stats` (~31 s) and rankings/maint prep (~36 s) — map isn’t the only runway on a full rerun.

### Pop-ups — agreed direction (rich eBird without “dumbing down”)

Goal: keep **the same facts and links** (lifelist, species, hotspots, history, Macaulay, etc.), **not** ship **~N × pre-built HTML strings** from Python every rerun.

1. **Structured payload** — Per-pin JSON: IDs, display strings, **URLs** (or templates + params).
2. **Client templates** — One TS/HTML/CSS “card” in the iframe renders that JSON so UX matches intent.
3. **Lazy sections** (optional) — Minimal payload by default; heavier tables/history on **popup open** if payload size matters.

This preserves **rich tie-back to eBird** while avoiding **`popup_html × N`** server cost. Next slice: extend payload builder toward existing popup **models** / fragments, then one rich popup component in TS.

### Pop-ups — priorities and payload strategy (discussion, 2026-05-13)

**Product priorities for this experiment**

1. **Like-for-like functionality first** — Same information and destinations as classic All Locations (not necessarily identical HTML).
2. **Performance second** — Measured with rich data in the experimental map vs classic; visualize results before committing to the path.
3. **Acceptable trade-offs** — If we keep functionality but deliver it slightly differently (or a different click path to the same eBird destination) and that buys a **real** gain in design or speed, consider it.

**Session shape (important for lazy vs eager)**

- The map may draw **~7k** locations, but a typical session only opens **tens to low hundreds** of popups.
- That pattern argues against paying full **heavy** popup cost for every pin—but **only if** “load on open” does **not** replace one problem with another (e.g. expensive **Streamlit full-script rerun** per popup).

**Lazy vs embed everything**

| Approach | When it fits |
|----------|----------------|
| **Embed structured data for all pins** | Payload stays compact (mostly URLs + short lines); you want zero second step after initial load. |
| **Lazy / expand-on-open for heavy slices** | Long tables, full history, rare blocks dominate bytes or Python build time; most pins never opened. |

**Default hypothesis for implementation**

- Ship **all lightweight parity fields** for every pin in the initial GeoJSON (structured, not HTML): title context, **high-value links**, short summary lines.
- Defer **heavy** sections (long tables, full history) until **popup open**, using a path that avoids **whole-app rerun per click** where possible (detail inside the iframe: extra chunk keyed by `location_id`, small `postMessage`, or a thin read-only fetch).

**Note on the classic map**

- We previously tried popup-on-demand on the Folium path and saw **little** difference; architecture there tied work to different bottlenecks. **Re-measure on this stack** (compact GeoJSON + component + TS template)—don’t assume that experiment transfers.

**Implemented slice**

- **`popup_v1`** on each GeoJSON feature (`explorer/core/all_locations_geojson.py`): structured `summary_lines` + `links[]`; TS renders one template (`AllLocationsMap.tsx`). Extend toward `map_prep` / `build_species_overlay_map` data sources without shipping HTML per pin.

### TODO / next (for a future “real” issue on `beta-next`)

- [ ] Warm-cache perf repeat (popup cache hits; compare again).
- [ ] Browser-side sanity (DevTools / subjective) alongside Python timers.
- [ ] Structured rich popup schema + TS template — **v1** encodes summary lines + links; extend fields for full classic parity (species/hotspot/history/Macaulay rows).
- [ ] Optional: cluster icon styling parity with Folium tiers (`iconCreateFunction`).
- [ ] Decide cut-over scope vs parallel experimental tab; spike branch **does not merge** to `beta-next` per agreement — spawn **new issue(s)** when promoting.

---

## Running log

### 2026-05-13

- **Pop-ups:** Captured priorities (like-for-like first, perf second), **~7k pins vs tens–low hundreds of opens per session**, hybrid **embed light / lazy heavy** strategy, and **Streamlit rerun** caveat under **Payload strategy** in the Status snapshot above; README + code comments aligned.
- **Rules of the road:** Wide-ranging exploratory work; timebox ~few days. Commentary on [#221](https://github.com/jimchurches/myebirdstuff/issues/221) plus this file. E2E/perf when they clarify design — manual comparison between maps is acceptable for spike conclusions.
- **Merge policy:** Spike branch not merged back to `beta-next`; success leads to **new issue(s)** for real implementation. Spike hygiene intentionally looser than prod branches; doc stays under `docs/explorer/issue-221-map-component-spike.md`.
- **Prototype landed (branch `221-streamlit-custom-map-component-spike`):** New main tab **Map (experimental)** after **Map**. Uses `prepare_all_locations_map_context` + `build_all_locations_geojson_payload` (revision hash + GeoJSON). Frontend: `explorer/components/all_locations_map/frontend` (Leaflet + `streamlit-component-lib`); committed **`frontend/build`** for Streamlit. Component skips marker rebuild when `revision` matches (see browser console). Works when sidebar **Map view** is **All locations**; otherwise shows an info panel.
- **Later same day:** Marker clustering (Leaflet.markercluster + sidebar toggle); **`EXPLORER_PERF`** map comparison rows in sidebar; perf/pop-up strategy captured in **Status snapshot** above.
