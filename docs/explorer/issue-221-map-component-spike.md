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
- **Pop-ups (spike slice):** Each feature includes **`popup_v1`** — with **`records_by_loc`** wired from the experimental tab, **`visited`** mirrors classic **All locations** (`build_visit_info_html` semantics: deduped checklist links + sort order from sidebar popup sort). Compact **`summary_lines` + `links`** fallback remains when no per-location rows are passed (tests). Seen/lifer species blocks deferred.

### Performance notes (real export, JSONL — All locations, ~5721 pins)

Two regimes matter: **compact GeoJSON** (early spike, lifelist + checklist count only) vs **full structured visit lists** per pin (current spike slice). Always capture **`EXPLORER_PERF=1`** with optional **`EXPLORER_PERF_LOG_FILE`** (see `explorer/app/streamlit/README.md`); example archive path used in spike: `benchmarks/map_perf/tmp/explorer_perf.jsonl`.

#### A — Early spike (compact `popup_v1`, cold `main_run_id` 1)

~**46k** rows, **5721** pins. Experimental payload stayed ~**1.6 s** because GeoJSON carried minimal popup fields.

**Classic (cold):** `prep.build_species_overlay_map` dominated by **`popup_build_total_ms`** (~5.5–6.5 s) + Folium HTML serialise + **`prep.map_iframe_embed`** (~6–7 s).

**Experimental (cold):** **`map.experimental.payload`** ~**1.5–1.6 s**, **`map.experimental.component_embed`** ~**14–25 ms** (Python only — not tiles / browser paint).

#### B — After visit-list parity (structured **`visited.entries`** per pin, 2026-05-13)

Same dataset scale (~46k rows, 5721 locations, ~7605 unique checklists). **`map.experimental.payload` rises to ~6.0–6.3 s** (cold and warm): Python rebuilds **full GeoJSON including every checklist row** each Streamlit rerun — cost moves from **HTML×N** into **structured JSON×N** + hashing/revision.

**Cold (`main_run_id` 1):** Classic still pays **`prep.build_species_overlay_map`** (**`popup_build_total_ms`** ~5.5 s) + **`prep.folium_map_to_html_bytes`** ~2.9 s + **`prep.map_iframe_embed`** ~6.2 s; experimental **`map.experimental.payload`** ~**6.0 s**, **`map.experimental.component_embed`** ~**23 ms**.

**Warm (`main_run_id` ≥3, map HTML cache hit):** Classic **`prep.map_cache_hit`** / **`prep.map_html_cache_hit`** — overlay **not** rebuilt; **`prep.map_iframe_embed`** remains ~**6.15–6.25 s** every rerun. Experimental **`map.experimental.payload`** still ~**6.25–6.32 s** (no Python-side reuse yet), **`map.experimental.component_embed`** ~**23–25 ms**.

**How to read B:** Visit parity eroded the “tiny experimental payload” advantage on warm reruns: Folium **reuses cached map HTML**, while experimental **recomputes the whole payload** each run — roughly **parity with iframe embed cost alone**, not an automatic win. **`fragment.country`** warm ~**4.6–5.2 s** on the same reruns — map is not the only large slice.

**Cold non-map runway (unchanged):** `prep.cache_checklist_stats` ~**28 s**, `prep.cache_maint_rankings_sex_notation` ~**33 s** → warm drops to **~50–210 ms** each.

### Caching vs lazy pop-ups (strategy)

They address **different** problems; **use both** when needed:

| Lever | What it fixes | UX impact |
|--------|----------------|-----------|
| **Cache structured payload** (e.g. memo by stable key / same **`revision`** + inputs as Folium map cache) | Warm reruns recomputing ~6 s of GeoJSON + visit rows when **nothing relevant changed** | None if invalidation matches data/settings |
| **Lazy / on-open detail** | Bytes + Python work for **pins never opened**; caps worst-case payload | Small delay or extra step on open **only if** implemented without a **full Streamlit rerun per click** |

**Suggested order:** Pursue **payload caching first** (same user-visible behaviour as today, targets warm **`map.experimental.payload`**). Add **lazy `visited` (or cap + lazy)** if profiling still shows pain at scale, or to trim initial transfer — complementary, not either/or.

**Implemented (2026-05-13 evening):** Session cache **`EXPERIMENTAL_ALL_LOCATIONS_PAYLOAD_CACHE_KEY`** — hit skips **`prepare_all_locations_map_context`** + **`build_all_locations_geojson_payload`** when the tuple **`(static_map_cache_key(…), revision_extra_json, visits_inline_cap)`** matches; cleared alongside Folium map cache invalidation. Optional env **`EXPLORER_EXPERIMENTAL_VISITS_INLINE_CAP=N`** truncates ``visited.entries`` per pin (popup shows lifelist link for full history). Per-popup fetch without Python rerun not implemented (would need iframe-only transport).

→ Copy **§ B** (Performance notes — paragraph B) into a [#221](https://github.com/jimchurches/myebirdstuff/issues/221) comment when sharing results with collaborators.

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

- **`popup_v1`** on each GeoJSON feature (`explorer/core/all_locations_geojson.py`): production path **`visited.entries`** (classic visit list); compact **`summary_lines` + `links`** when `records_by_location` omitted. TS: `AllLocationsMap.tsx`. Seen/lifer sections later.

### TODO / next (for a future “real” issue on `beta-next`)

- [x] Warm-cache perf repeat — **done** (see **§ B**); session **payload cache** addresses warm **`map.experimental.payload`** rebuilds when inputs unchanged.
- [x] **Python-side cache** — **`EXPERIMENTAL_ALL_LOCATIONS_PAYLOAD_CACHE_KEY`** (Folium **`static_map_cache_key`** + `revision_extra` + visits cap); nuked with Folium cache.
- [ ] Browser-side sanity (DevTools / subjective) alongside Python timers.
- [ ] Optional **lazy `visited`** (iframe-only / no full rerun per open) if cap + cache insufficient.
- [ ] Structured popup — extend for species/hotspot/history/Macaulay when in scope (seen/lifer).
- [ ] Optional: cluster icon styling parity with Folium tiers (`iconCreateFunction`).
- [ ] Decide cut-over scope vs parallel experimental tab; spike branch **does not merge** to `beta-next` per agreement — spawn **new issue(s)** when promoting.

---

## Milestone summary (step-by-step capture for #221)

Chronological notes mirrored on [#221](https://github.com/jimchurches/myebirdstuff/issues/221); detail lives in **Running log** and **Status snapshot** above.

| Step | What landed |
|------|----------------|
| 1 | **Experimental tab** — `Map (experimental)` after Map; GeoJSON + `revision`; Leaflet + `streamlit-component-lib`; clustering per defaults; iframe skips marker rebuild when `revision` unchanged (console log). |
| 2 | **Markers** — Preset **1 (Eucalypt)** circle styling from Python (`circle_marker_style`); sidebar marker scheme not applied on experimental yet. |
| 3 | **`popup_v1`** — Structured payload + TS template; compact `summary_lines` + `links` when no `records_by_location`. |
| 4 | **Visit list parity** — `visited.entries` from `records_by_loc`, sort from sidebar popup order; TS lifelist heading + scrollable Visited block (`build_visit_info_html` semantics). |
| 5 | **Perf §A / §B** — Compact GeoJSON ~1.6 s vs classic Folium+popup path; full visits ~**6 s** `map.experimental.payload` pre-cache (cold + warm rebuild); classic warm **`prep.map_iframe_embed` ~6.2 s** with map HTML cache hit; **`fragment.country` ~4.6–5 s** warm. |
| 6 | **Strategy** — Prefer **session payload cache** before heavier lazy designs; optional **`EXPLORER_EXPERIMENTAL_VISITS_INLINE_CAP`** truncates inlined rows (lifelist for full history). |
| 7 | **Payload cache** — **`EXPERIMENTAL_ALL_LOCATIONS_PAYLOAD_CACHE_KEY`** keyed like **`static_map_cache_key`** + `revision_extra` + visits cap; invalidated with Folium map cache; **`payload_cache_hit`** in perf `extra`. |
| 8 | **Validated** — Warm reruns: **`map.experimental.payload` ~0.01 ms** when cache hits (`payload_cache_hit: true` in JSONL). **`prep.map_context_prepare` ~1.4 s** still runs for shared Map prep. |

**Minimal local perf + JSONL (nothing else required):**

```bash
mkdir -p benchmarks/map_perf/tmp
EXPLORER_PERF=1 EXPLORER_PERF_LOG_FILE="$PWD/benchmarks/map_perf/tmp/explorer_perf.jsonl" \
  streamlit run explorer/app/streamlit/app.py
```

Optional: **`EXPLORER_EXPERIMENTAL_VISITS_INLINE_CAP=N`** (positive int). Optional: **`EXPLORER_PERF_LOG=1`** for root logger. Archive a run: **`python scripts/snapshot_explorer_perf_log.py benchmarks/map_perf/tmp/explorer_perf.jsonl --label my-label`** → **`benchmarks/map_perf/snapshots/`** (gitignored).

Example archived snapshot (visit-list era, pre payload-cache): **`benchmarks/map_perf/snapshots/2026-05-13T22-57-46Z_issue221-visit-list-cold-warm.json`** — re-snapshot after big changes for local diffs.

---

## Running log

### 2026-05-13 (evening)

- **Perf JSONL:** Archived `benchmarks/map_perf/tmp/explorer_perf.jsonl` → **`benchmarks/map_perf/snapshots/2026-05-13T22-57-46Z_issue221-visit-list-cold-warm.json`** via **`scripts/snapshot_explorer_perf_log.py`**; **`benchmarks/map_perf/tmp/`** gitignored; removed duplicate JSONL from **`tmp/`**.
- **Experimental map:** Session-state **payload cache** (same key inputs as Folium **All locations** cache path + cluster bundle + visits cap); **`EXPLORER_EXPERIMENTAL_VISITS_INLINE_CAP`** for truncated visit lists + TS lifelist hint.
- **Post-cache JSONL check:** Warm **`map.experimental.payload`** ~**0.01 ms**, **`payload_cache_hit: true`**; cold miss still ~**6 s** GeoJSON build. **`prep.map_iframe_embed`** warm classic ~**6.2 s** unchanged; **`prep.map_context_prepare`** warm ~**1.4 s**. **`Milestone summary`** table + **`benchmarks/map_perf/README.md`** § typical perf command added for issue handoff.

### 2026-05-13 (later)

- **Perf (visit-list parity):** Documented **§ B** in Status snapshot — structured visits pushed **`map.experimental.payload`** to ~**6.3 s** cold/warm; warm classic uses cached Folium HTML but **`prep.map_iframe_embed`** ~**6.2 s**; **caching vs lazy** strategy subsection added (prefer cache first, then lazy if needed).

### 2026-05-13

- **Pop-ups:** Captured priorities (like-for-like first, perf second), **~7k pins vs tens–low hundreds of opens per session**, hybrid **embed light / lazy heavy** strategy, and **Streamlit rerun** caveat under **Payload strategy** in the Status snapshot above; README + code comments aligned.
- **Rules of the road:** Wide-ranging exploratory work; timebox ~few days. Commentary on [#221](https://github.com/jimchurches/myebirdstuff/issues/221) plus this file. E2E/perf when they clarify design — manual comparison between maps is acceptable for spike conclusions.
- **Merge policy:** Spike branch not merged back to `beta-next`; success leads to **new issue(s)** for real implementation. Spike hygiene intentionally looser than prod branches; doc stays under `docs/explorer/issue-221-map-component-spike.md`.
- **Prototype landed (branch `221-streamlit-custom-map-component-spike`):** New main tab **Map (experimental)** after **Map**. Uses `prepare_all_locations_map_context` + `build_all_locations_geojson_payload` (revision hash + GeoJSON). Frontend: `explorer/components/all_locations_map/frontend` (Leaflet + `streamlit-component-lib`); committed **`frontend/build`** for Streamlit. Component skips marker rebuild when `revision` matches (see browser console). Works when sidebar **Map view** is **All locations**; otherwise shows an info panel.
- **Later same day:** Marker clustering (Leaflet.markercluster + sidebar toggle); **`EXPLORER_PERF`** map comparison rows in sidebar; perf/pop-up strategy captured in **Status snapshot** above.
