# Code Review: personal_ebird_explorer

**Date:** 2025-02-22  
**Scope:** `notebooks/personal_ebird_explorer.py`

---

## 1. Variables whose purpose has drifted (names no longer relevant)

### `selected_species_name` — **Misleading**
- **Current use:** Holds the **scientific** name (e.g. `"Tyto javanica"`).
- **Evidence:** `selected_species_name = name_map.get(selected, "").strip()` — `name_map` maps common → scientific.
- **Recommendation:** Rename to `selected_species_scientific` or `selected_scientific_name` for clarity. Update `selected_species_common_name` → `selected_species_common` if desired for consistency.

### `_full` (lifer/last-seen cell)
- **Current use:** Sorted, filtered dataframe used for lifer and last-seen lookups.
- **Issue:** Name is vague; "full" could mean unfiltered, but it's actually the processed/sorted subset.
- **Recommendation:** Rename to `_full_sorted_for_lifer` or `_lifer_lookup_df`.

### `# Top 10 data` (line 1503)
- **Issue:** Comment says "Top 10" but `limit = TOP_N_TABLE_LIMIT` (default 200).
- **Recommendation:** Change to `# Top N rankings data` or `# Rankings data (limit from TOP_N_TABLE_LIMIT)`.

---

## 2. Code that could be extracted for doco/readability

### A. Duplicated scroll-wrapper logic
`_rankings_table`, `_rankings_visited_table`, and `_rankings_seen_once_table` each contain ~25 lines of identical JavaScript for scroll hints (chevrons/shading). 

**Recommendation:** Extract to a helper, e.g.:
```python
def _rankings_scroll_wrapper(table_html, scroll_hint, max_height_px):
    """Return HTML for scrollable table with chevron/shading hints."""
```

### B. `_compute_checklist_stats` is very large (~430 lines)
It contains:
- Overview, protocol, distance, time, shared, streak logic
- Six nested ranking helpers (`_rankings_by_value`, `_rankings_by_location`, etc.)
- Three nested table builders (`_rankings_table`, `_rankings_visited_table`, `_rankings_seen_once_table`)
- HTML assembly

**Recommendation:** 
- Move ranking helpers (`_rankings_by_value`, `_rankings_by_location`, `_rankings_by_individuals`, etc.) to a separate cell/function, e.g. `_compute_rankings(df, cl, limit)`.
- Move the scroll-wrapper and table builders to a shared helper cell.
- Keep `_compute_checklist_stats` focused on overview stats and delegating to these helpers.

### C. Streak calculation (lines 1296–1349)
~55 lines of numpy logic for longest consecutive-day streak.

**Recommendation:** Extract to `def _longest_streak(unique_dates, cl):` in its own cell with a short docstring. Improves readability and testability.

### D. Popup scroll script (~70 lines) in `draw_map_with_species_overlay`
The inline `<script>` for popup scroll hints is long and could live in a constant or small helper.

**Recommendation:** Extract to something like `_popup_scroll_script(POPUP_SCROLL_HINT, POPUP_SORT_ORDER)` for clarity.

### E. `format_sighting_row` (nested in `draw_map_with_species_overlay`)
**Recommendation:** Move to module level (e.g. near `_safe_count`) so it can be reused and documented independently.

---

## 3. Orphaned code

- **Display UI cell (lines 1085–1090):** Effectively empty; only a comment. Not orphaned, but could be removed or repurposed if it adds no value.
- No obvious dead code paths or unused variables found.

---

## 4. Performance

- **`records_by_loc` / `filtered_by_loc`:** Good use of `groupby` → dict for O(1) lookups instead of repeated scans.
- **BallTree for haversine:** Appropriate for close-location detection.
- **Streak calculation:** Uses numpy; efficient.
- **`_base_species_for_lifer`:** Uses `.apply()` on a column; `_countable_species_vectorized` exists for similar logic. The lifer version intentionally does not exclude spuh/hybrid; keeping it separate is fine.
- **Multiple groupbys in rankings:** Each table does its own groupby; acceptable for a notebook. Could be optimized later if needed.

No major performance issues identified.

---

## 5. Comments that are inaccurate or outdated

### A. Line 1632
```python
# Compute stats from full dataset (respects date filter via df, but we use df_full for 'all time' stats)
```
- **Issue:** We pass `df_full`; stats are always all-time. The phrase "respects date filter via df" is misleading.
- **Recommendation:**  
  `# Stats use df_full for all-time totals (unfiltered by date). Map uses df, which may be date-filtered.`

### B. Line 1503
- **Issue:** `# Top 10 data` — limit is `TOP_N_TABLE_LIMIT` (200).
- **Recommendation:** `# Top N rankings data` or similar.

### C. Line 619–621
```python
# --------------------------------------------
# ✅ Build True Lifer Table (from full dataset)
# --------------------------------------------
```
- **Issue:** We build both lifer and last-seen tables.
- **Recommendation:** `# Build True Lifer and Last-Seen Tables (from full dataset)`

### D. Line 1632 (duplicate)
The `checklist_data` assignment comment could also mention that rankings are computed from the same `df_full` for consistency.

---

## Summary of recommended changes

| Priority | Item | Effort |
|----------|------|--------|
| High | Rename `selected_species_name` → `selected_species_scientific` (or similar) | Low |
| High | Fix "Top 10" comment → "Top N" | Trivial |
| High | Fix "Compute stats from full dataset" comment | Trivial |
| Medium | Fix "Build True Lifer Table" → include last-seen | Trivial |
| Medium | Extract scroll-wrapper helper (reduce duplication) | Medium |
| Medium | Extract streak calculation to `_longest_streak()` | Low |
| Low | Rename `_full` → `_lifer_lookup_df` | Low |
| Low | Extract ranking helpers from `_compute_checklist_stats` | Medium |
| Low | Extract popup scroll script to helper | Low |
