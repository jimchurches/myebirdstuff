# Issue #205 — map performance investigation backlog

> Per-branch only. **This file lives on `205-investigation-main` and is not destined for `beta-next`.**
> See [#205](https://github.com/jimchurches/myebirdstuff/issues/205) for the parent issue. Batch 1
> notes (decisions, baseline timings) are posted as comments on that issue, not in this repo.

The list below is the broader menu of things worth trying. Batches are kept small (1–2 active
experiments at a time) so we can decide *go / drop / shelve* with evidence rather than running
everything in parallel.

| Status | Meaning |
| --- | --- |
| **batch 1** | currently being worked on (this branch) |
| backlog | candidate, not started |
| done | tried; result captured as a #205 comment |
| dropped | tried or considered and rejected; reason captured as a #205 comment |

Performance instrumentation already in place is described in
[docs/AI_CONTEXT.md](AI_CONTEXT.md) and [docs/development.md](../development.md). The canonical
stages exposed by [explorer/app/streamlit/perf_instrumentation.py](../../explorer/app/streamlit/perf_instrumentation.py)
(via `EXPLORER_PERF=1` + `EXPLORER_PERF_LOG_FILE`) are:

- `prep.data_signature`
- `prep.map_context_prepare`
- `prep.build_species_overlay_map` (rebuild path; cache miss only)
- `prep.cached_family_map_bundle`, `prep.family_map_composition_with_pins`
- `prep.folium_map_to_html_bytes`
- `prep.map_iframe_embed`
- `prep.map_cache_hit` / `prep.map_cache_miss`
- `prep.map_html_cache_hit` / `prep.map_html_cache_miss`
- `prep.cache_checklist_stats`, `prep.cache_maint_rankings_sex_notation`, `prep.tab_session_sync`

---

## Within the current architecture (Streamlit + Folium)

| # | Idea | Hypothesis | Expected gain | Risk | Measurement | Done means | Status |
| --- | --- | --- | --- | --- | --- | --- | --- |
| W1 | Wrap the Map-tab live embed in `@st.fragment` | Sidebar widget changes that don't affect map keys still trigger a full rerun, including a fresh `st_folium` render pass. A fragment isolates the map. | Removes 1 × `prep.map_iframe_embed` per off-map rerun. | `@st.fragment` interactions with the existing `_spinner_emoji_placeholder` and the dual-spinner story may be subtle. | Compare `prep.map_iframe_embed` count + total per "change non-map setting" journey. | A/B median across 3 runs on real CSV; recommendation comment on #205. | backlog |
| W2 | Lite-popup A/B | Popup HTML assembly + Folium injection is a hidden cost in `prep.build_species_overlay_map` and `prep.folium_map_to_html_bytes`. | If popups dominate, a debug "tooltip-only" mode should cut both stages noticeably. | Cannot ship as default; popups + eBird links are a feature. Useful purely as a measurement. | Add `EXPLORER_MAP_LITE_POPUPS=1` flag; diff stage medians vs default. | A/B medians on real CSV; finding posted on #205 (kept or shelved). | backlog |
| W3 | Marker thinning A/B | At large datasets the per-marker Folium cost is linear; clustering already helps for "all locations" but not for "species". | If marker count is the cost, a cap (e.g. random N=2000) should isolate it. | Lossy by definition; debug-only. | Same flag pattern; record `prep.build_species_overlay_map` vs marker count. | Recommendation on whether to invest in client-side clustering. | backlog |
| W4 | Cache-key churn audit | Some session settings may accidentally bust the map cache more often than they should (`_render_opts_sig` in `app_prep_map_ui.py`). | Identifying gratuitous misses is a high-ROI fix. | None (read-only logging). | One-shot logging of `_ck` components and hit/miss outcome over a manual journey. | Comment on #205 with offending key components, if any. | **next batch** — measured during batch 1 (see [baseline comment](https://github.com/jimchurches/myebirdstuff/issues/205#issuecomment-4365804280)): All→Lifer→All journey produced 9 misses / 0 hits across 6 runs on both datasets. Diagnosis (which key component is changing) deliberately deferred to a future batch |
| W5 | `map_height` debounce | Dragging the height slider causes a rerun storm; each rerun pays full embed cost. | Debounce / "apply" pattern reduces reruns to 1 per setting change. | Existing apply/spinner UX must not regress. | Wall-clock timing of "drag slider 100→700 → release". | Decision: keep slider live, add apply, or debounce. | backlog |
| W6 | Defer non-map prep further | Dual sidebar spinner already runs map prep first, but `prep.cache_checklist_stats` etc. still block the next rerun. | Pushing more work behind the visible map could improve perceived UX further. | Easy to introduce stale-data bugs. | Compare time-to-banner-visible (Playwright) vs total-prep-done. | Recommendation on whether further deferral is worth the complexity. | backlog |

## Hybrid (Streamlit shell + JS / new transport)

| # | Idea | Hypothesis | Expected gain | Risk | Measurement | Done means | Status |
| --- | --- | --- | --- | --- | --- | --- | --- |
| H1 | `components.html(html_bytes)` live embed re-attempt, behind `EXPLORER_MAP_EMBED` flag | Cached `html_bytes` already exists for export; reusing it for the live iframe avoids `st_folium`'s extra render pass on every rerun. | Cuts `prep.map_iframe_embed` toward zero on warm reruns. | This is the **#190 regression path** (banner/legend shrunk; popups detached). Flag-gated, default off. | A/B medians for `prep.map_iframe_embed`; Playwright marker-popup-anchored check. | A/B comment on #205 + drop / save-branch / new-issue decision. | **dropped — #190 reproduced** during manual validation on All-locations cluster + popup path (banner shrunk, popup detached from marker). [Validation outcome comment](https://github.com/jimchurches/myebirdstuff/issues/205) and screenshots under `benchmarks/map_perf/snapshots/issue-205-batch-1/manual-validation-*`. The Lifer-view screenshot test from batch 1 missed it because the DOM differs (CircleMarker vs cluster + folium.Marker). The flag stays in the branch as a reference; default behaviour is unchanged. |
| H2 | Persistent client iframe, data-only updates | Most of the cost is *re-mounting* the Leaflet map; if it stays mounted and we only push diff'd GeoJSON, reruns become trivial. | Order-of-magnitude gain for warm reruns. | New component boundary; needs careful Streamlit↔component messaging. Significant build effort. | First-paint timing + per-rerun delta when only a filter changes. | Working spike on a save-branch + recommendation. | backlog |
| H3 | Partial Folium → GeoJSON overlay for the *selected species only* | The base map could be cached once; only the species overlay changes on most interactions. | Skips full Folium rebuild when only species selection changes. | Two-layer architecture; risk of overlay/base drift in popups + cluster behaviour. | Stage timings split between "base map build" and "overlay update". | Spike result + go/no-go on #205. | backlog |
| H4 | Pre-render multiple map variants on first load | All / Lifer / Family-blank maps are predictable. Pre-building them in the cold prep window may erase the first-switch wait. | Removes the first "All → Lifer" wait users notice. | Larger memory footprint; longer cold start. | Compare cold prep time vs first-switch time on real CSV. | Recommendation on the trade-off. | backlog |

## Outside the current Streamlit shell

| # | Idea | Hypothesis | Expected gain | Risk | Measurement | Done means | Status |
| --- | --- | --- | --- | --- | --- | --- | --- |
| O1 | Custom Streamlit Component wrapping Leaflet / MapLibre | Maximum control of mount lifetime + payload; only re-renders on data hash changes. | Largest potential gain; matches the issue's "phase 3" prototype suggestion. | Largest scope; maintenance burden; JS toolchain enters the repo. | Side-by-side render of identical dataset; first-paint + warm-rerun timings. | Working minimal component on a save-branch + comment on #205 with effort/benefit estimate. | backlog |
| O2 | Full client-side renderer; Streamlit only ships data + controls | Long-term horizon if the Streamlit rerun model continues to be the limiter. | UX parity with hand-rolled web maps. | Architectural rewrite; conflicts with current "stay Streamlit-first" stance — would need explicit agreement first per #205. | Same as O1 but for a fuller prototype. | Would only be opened as a separate issue if O1 indicates strong gains. | backlog |
| O3 | Tile / basemap pre-warming | First-paint pause includes external tile fetches. | Faster perceived load. | Mostly hosting-dependent; limited applicability for personal Streamlit Cloud deploys. | Time-to-first-tile-visible. | Recommendation; likely shelved for hosted environments. | backlog |

## Instrumentation gaps (enables better evidence for the above)

| # | Idea | Why it helps | Effort | Status |
| --- | --- | --- | --- | --- |
| I1 | Per-popup build timing + count, recorded in `extra` | Lets us isolate popup cost from marker cost in `prep.build_species_overlay_map`. | small | backlog |
| I2 | Marker count per build, recorded in `extra` | Without this, A/B comparisons across different dataset slices are hard to read. | small | backlog |
| I3 | Cluster vs no-cluster A/B knob | The current `STREAMLIT_MAP_CLUSTER_ALL_LOCATIONS_KEY` already exists, but isn't exercised by E2E. Add to perf journey. | small | backlog |
| I4 | First-paint timing in Playwright (`page.goto` → banner-visible) | Stage timings miss the time the user actually waits. | small | backlog |
| I5 | JSONL aggregator helper that prints per-stage `n / median / max / p95` | Cuts manual aggregation work for every batch. | small | backlog |
| I6 | E2E parity coverage on All-locations cluster + popup click | Batch 1's Lifer-view screenshot test missed the H1 #190 regression because that DOM differs from the cluster path. Any future embed-mode experiment needs at least one All-locations cluster + popup-click assertion before the screenshot test is trusted. | small | backlog (lesson from H1) |

---

## How a backlog item becomes "done"

1. Create a focused branch off `205-investigation-main` (e.g. `205-investigation-popup-cost`) so each
   experiment stays inspectable later.
2. Implement behind a flag where possible (env var + sane default), so the change is reversible and
   measurable side-by-side.
3. Capture **medians of 3** runs on the integration fixture and on the local real CSV
   (`tests/fixtures/MyEBirdData.csv`, gitignored).
4. Post a #205 comment with the table, the parity observations, and a *drop / save / open-issue*
   recommendation.
5. Update the **Status** column in this file (the file moves with the branch — it's fine if it
   never reaches `beta-next`).
