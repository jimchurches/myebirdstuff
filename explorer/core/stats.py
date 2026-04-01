"""
Statistics, rankings, and summary calculations for Personal eBird Explorer.

Pure calculation functions: accept DataFrames and explicit parameters, return
data structures (dicts, lists of tuples, DataFrames). No widget, display, or
HTML-rendering dependencies. Some functions return row tuples that include
HTML links (eBird checklist/lifelist URLs) because those are part of the data
contract the UI expects; separating them would be a redesign.
"""

import html as _html

import numpy as np
import pandas as pd

from explorer.core.species_logic import countable_species_vectorized


# ---------------------------------------------------------------------------
# Shared utility
# ---------------------------------------------------------------------------

def safe_count(x):
    """Parse an eBird count value to int.

    eBird exports use ``X`` to mean "present" (no quantity provided). For
    individual totals, treat ``X`` as 0 so sums align with eBird species-page
    individual counts.
    """
    if pd.isna(x):
        return 0
    if isinstance(x, str) and x.strip().upper() == "X":
        return 0
    try:
        return int(x)
    except (ValueError, TypeError):
        return 0


# ---------------------------------------------------------------------------
# Region helpers
# ---------------------------------------------------------------------------

def region_column(df, prefer_country=True):
    """Return the first column name present in *df* for region (country/state).

    Prefer full country name if *prefer_country* is True.
    """
    cols_lower = {c.strip().lower(): c for c in df.columns}
    candidates_country = ("country", "country name", "country code", "countrycode")
    candidates_region = ("state/province", "state", "state_province", "province", "county")
    if prefer_country:
        for key in candidates_country:
            if key in cols_lower:
                return cols_lower[key]
    for key in candidates_region:
        if key in cols_lower:
            return cols_lower[key]
    if not prefer_country:
        for key in candidates_country:
            if key in cols_lower:
                return cols_lower[key]
    return None


def format_region_parts(value):
    """Split combined State/Province (e.g. 'AU-NSW') into (country, state).

    Either part may be None.
    """
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return (None, None)
    s = str(value).strip()
    if not s:
        return (None, None)
    if "-" in s:
        parts = s.split("-", 1)
        return (parts[0].strip() or None, parts[1].strip() or None)
    return (None, s)


# ---------------------------------------------------------------------------
# Longest streak
# ---------------------------------------------------------------------------

def _row_lid_str(row) -> str:
    """Normalize Location ID from a checklist row for lifelist URLs."""
    if row is None:
        return ""
    lid = row.get("Location ID", "")
    if lid is None or (isinstance(lid, float) and pd.isna(lid)):
        return ""
    s = str(lid).strip()
    return s


def _row_loc_str(row) -> str:
    """Normalize Location display string from a checklist row."""
    if row is None:
        return ""
    loc = row.get("Location", "")
    if loc is None or (isinstance(loc, float) and pd.isna(loc)):
        return ""
    return str(loc).strip()


def longest_streak(unique_dates, cl):
    """Find longest streak of consecutive days with a checklist.

    Returns (streak, start_date, start_loc, start_sid, start_lid, end_date, end_loc, end_sid, end_lid).
    *start_lid* / *end_lid* are eBird Location IDs for lifelist links (empty if unknown).
    """
    streak = 0
    streak_start_date = ""
    streak_start_loc = ""
    streak_start_sid = ""
    streak_start_lid = ""
    streak_end_date = ""
    streak_end_loc = ""
    streak_end_sid = ""
    streak_end_lid = ""
    if len(unique_dates) == 0:
        return (
            streak,
            streak_start_date,
            streak_start_loc,
            streak_start_sid,
            streak_start_lid,
            streak_end_date,
            streak_end_loc,
            streak_end_sid,
            streak_end_lid,
        )

    arr = np.asarray(pd.to_datetime(unique_dates)).astype("datetime64[D]")
    day_ints = np.unique(arr.view("int64"))
    diffs = np.diff(day_ints)
    gaps = np.where(diffs > 1)[0]
    best_start, best_end = day_ints[0], day_ints[-1]

    if len(gaps) == 0:
        streak = len(day_ints)
        if streak > 0:
            streak_start_date = pd.Timestamp(day_ints[0], unit="D").strftime("%d %b %Y")
            streak_end_date = pd.Timestamp(day_ints[-1], unit="D").strftime("%d %b %Y")
    else:
        indices = np.arange(len(diffs))
        segments = np.split(indices, gaps + 1)
        best_len = 0
        for i, seg in enumerate(segments):
            seg = list(seg)
            if i == 0 and len(seg) > 0 and seg[-1] in gaps:
                seg = seg[:-1]
            n = len(seg) + 1 if len(seg) > 0 else 1
            if n > best_len:
                best_len = n
                start_idx = seg[0] if seg else 0
                end_idx = (seg[-1] + 1) if seg else 0
                best_start = day_ints[start_idx]
                best_end = day_ints[min(end_idx, len(day_ints) - 1)]
        streak = best_len
        if best_start is not None and best_end is not None:
            streak_start_date = pd.Timestamp(best_start, unit="D").strftime("%d %b %Y")
            streak_end_date = pd.Timestamp(best_end, unit="D").strftime("%d %b %Y")

    if streak > 0 and "Date" in cl.columns:
        first_day = best_start if len(gaps) > 0 else day_ints[0]
        last_day = best_end if len(gaps) > 0 else day_ints[-1]
        first_d = pd.Timestamp(first_day, unit="D").normalize()
        last_d = pd.Timestamp(last_day, unit="D").normalize()
        cl_copy = cl.copy()
        cl_copy["_d"] = cl_copy["Date"].dt.normalize()
        start_m = cl_copy[cl_copy["_d"] == first_d]
        end_m = cl_copy[cl_copy["_d"] == last_d]
        sort_col = "datetime" if "datetime" in cl_copy.columns else None
        if not start_m.empty:
            start_sorted = start_m.sort_values(sort_col) if sort_col and start_m[sort_col].notna().any() else start_m
            start_row = start_sorted.iloc[0]
            streak_start_loc = _row_loc_str(start_row)
            streak_start_sid = str(start_row.get("Submission ID", ""))
            streak_start_lid = _row_lid_str(start_row)
        if not end_m.empty:
            end_sorted = end_m.sort_values(sort_col) if sort_col and end_m[sort_col].notna().any() else end_m
            end_row = end_sorted.iloc[-1]
            streak_end_loc = _row_loc_str(end_row)
            streak_end_sid = str(end_row.get("Submission ID", ""))
            streak_end_lid = _row_lid_str(end_row)

    return (
        streak,
        streak_start_date,
        streak_start_loc,
        streak_start_sid,
        streak_start_lid,
        streak_end_date,
        streak_end_loc,
        streak_end_sid,
        streak_end_lid,
    )


# ---------------------------------------------------------------------------
# Ranking helpers
# ---------------------------------------------------------------------------

def rankings_by_value(df_sub, value_col, date_col, loc_col, loc_id_col, sid_col, fmt, limit):
    """Top N by value desc, date asc; ties show oldest.

    Returns list of (loc_link, state_str, country_str, dt_link, val).
    """
    if df_sub.empty or value_col not in df_sub.columns:
        return []
    use_col = "datetime" if "datetime" in df_sub.columns else date_col
    cols = [use_col, loc_col, sid_col, value_col]
    if loc_id_col and loc_id_col in df_sub.columns:
        cols.append(loc_id_col)
    reg_col = region_column(df_sub, prefer_country=True)
    if reg_col and reg_col in df_sub.columns:
        cols.append(reg_col)
    d = df_sub[cols].dropna(subset=[value_col]).drop_duplicates()
    d = d.sort_values(by=[value_col, use_col], ascending=[False, True]).head(limit)
    rows = []
    for _, r in d.iterrows():
        dt = r[use_col]
        dt_str = pd.Timestamp(dt).strftime("%d %b %Y %H:%M") if pd.notna(dt) else "—"
        loc = r.get(loc_col, "")
        sid = r.get(sid_col, "")
        lid = r.get(loc_id_col, "")
        val = fmt(r[value_col])
        loc_link = f'<a href="https://ebird.org/lifelist/{lid}" target="_blank">{loc}</a>' if lid else loc
        dt_link = f'<a href="https://ebird.org/checklist/{sid}" target="_blank">{dt_str}</a>' if sid else dt_str
        state_str = ""
        country_str = ""
        if reg_col and reg_col in r.index:
            country, state = format_region_parts(r.get(reg_col))
            state_str = state if state else ""
            country_str = country if country else ""
        rows.append((loc_link, state_str, country_str, dt_link, val))
    return rows


def rankings_by_location(df_obs, cl_sub, mode, fmt, limit):
    """Top N locations by total species or individuals.

    *mode*: ``'species'`` or ``'individuals'``. Ties by first visit date.
    """
    if df_obs.empty or cl_sub.empty:
        return []
    if mode == "species":
        agg = df_obs.groupby("Location ID", group_keys=False).apply(
            lambda g: countable_species_vectorized(g).dropna().nunique(),
            include_groups=False,
        ).reset_index(name="_val")
    else:
        agg = df_obs.groupby("Location ID", group_keys=False).apply(
            lambda g: g["Count"].apply(safe_count).sum(),
            include_groups=False,
        ).reset_index(name="_val")
    dt_col = "datetime" if "datetime" in cl_sub.columns else "Date"
    loc_info = cl_sub.groupby("Location ID").agg(
        Location=("Location", "first"),
        Checklists=("Submission ID", "nunique"),
    ).reset_index()
    reg_col = region_column(cl_sub, prefer_country=True)
    if reg_col:
        loc_info = loc_info.merge(
            cl_sub.groupby("Location ID")[reg_col].first().reset_index(),
            on="Location ID", how="left",
        )
    first_dates = cl_sub.groupby("Location ID")[dt_col].min().reset_index().rename(columns={dt_col: "_first"})
    merged = agg.merge(loc_info, on="Location ID", how="inner").merge(first_dates, on="Location ID", how="left")
    merged = merged.sort_values(by=["_val", "_first", "Location"], ascending=[False, True, True]).head(limit)
    rows = []
    for _, r in merged.iterrows():
        lid = r["Location ID"]
        loc_link = f'<a href="https://ebird.org/lifelist/{lid}" target="_blank">{r["Location"]}</a>' if lid else r["Location"]
        state_str = ""
        country_str = ""
        if reg_col and reg_col in merged.columns:
            country, state = format_region_parts(r.get(reg_col))
            state_str = state if state else ""
            country_str = country if country else ""
        rows.append((loc_link, state_str, country_str, f"{int(r['Checklists']):,}", fmt(r["_val"])))
    return rows


def rankings_by_individuals(df_obs, limit):
    """Top N species by total individuals. Subspecies rolled into main species."""
    if df_obs.empty:
        return []
    df_s = df_obs.copy()
    df_s["_base"] = countable_species_vectorized(df_s)
    df_s = df_s.dropna(subset=["_base"])
    df_s["_count"] = df_s["Count"].apply(safe_count)
    by_base = df_s.groupby("_base").agg(
        total=("_count", "sum"),
        common_name=("Common Name", lambda s: s.value_counts().index[0] if len(s) > 0 else ""),
    ).reset_index()
    by_base = by_base.sort_values(by=["total", "_base"], ascending=[False, True])
    if limit is not None:
        by_base = by_base.head(limit)
    rows = []
    for _, r in by_base.iterrows():
        name = r["common_name"] if pd.notna(r["common_name"]) else r["_base"]
        rows.append((str(name), "—", f"{int(r['total']):,}"))
    return rows


def rankings_by_checklists(df_obs, limit):
    """Top N species by number of checklists. Subspecies rolled into main species."""
    if df_obs.empty:
        return []
    df_s = df_obs.copy()
    df_s["_base"] = countable_species_vectorized(df_s)
    df_s = df_s.dropna(subset=["_base"])
    by_base = df_s.groupby("_base").agg(
        n_checklists=("Submission ID", "nunique"),
        common_name=("Common Name", lambda s: s.value_counts().index[0] if len(s) > 0 else ""),
    ).reset_index()
    by_base = by_base.sort_values(by=["n_checklists", "_base"], ascending=[False, True])
    if limit is not None:
        by_base = by_base.head(limit)
    rows = []
    for _, r in by_base.iterrows():
        name = r["common_name"] if pd.notna(r["common_name"]) else r["_base"]
        rows.append((str(name), "—", f"{int(r['n_checklists']):,}"))
    return rows


def rankings_subspecies_hierarchical(df_obs, limit=None):
    """Hierarchical subspecies occurrence data grouped by parent species.

    Returns a list of dicts, one per parent species, in the form:

    {
        "species_common": str,
        "species_scientific": str,
        "total_individuals": int,
        "species_only_individuals": int,
        "subspecies_total_individuals": int,
        "subspecies_fraction": float or None,  # 0–1
        "subspecies": [
            {
                "subspecies_common": str,          # label only, e.g. "Black-backed"
                "subspecies_common_full": str,     # e.g. "Australian Magpie (Black-backed)"
                "subspecies_scientific": str,      # full trinomial
                "individuals": int,
            },
            ...
        ],
    }

    Only species that have at least one true subspecies record are included.
    Species and subspecies are both sorted alphabetically by common name.
    """
    if df_obs.empty:
        return []

    df = df_obs.copy()
    sci = df["Scientific Name"].fillna("").astype(str).str.strip()
    common = df["Common Name"].fillna("").astype(str).str.strip()

    # Exclude spuhs, hybrids, domestic types, and species-level slash taxa
    spuh = sci.str.contains(r" sp\.", case=False, na=False) | sci.str.lower().str.endswith(" sp")
    hybrid = sci.str.contains(" x ", na=False) | common.str.lower().str.contains(r"\(hybrid\)", na=False)
    domestic = common.str.contains("Domestic", na=False) | common.str.contains(r"\(Domestic type\)", na=False)
    parts = sci.str.split()
    is_subspecies = parts.apply(lambda p: len(p) >= 3 if isinstance(p, list) else False)
    species_level_slash = parts.apply(lambda p: len(p) > 1 and "/" in str(p[1]) if isinstance(p, list) else False)

    keep_valid = ~spuh & ~hybrid & ~domestic & ~species_level_slash
    if not keep_valid.any():
        return []

    df = df.loc[keep_valid].copy()
    sci = df["Scientific Name"].fillna("").astype(str).str.strip()
    common = df["Common Name"].fillna("").astype(str).str.strip()
    parts = sci.str.split()
    is_sub = parts.apply(lambda p: len(p) >= 3 if isinstance(p, list) else False)

    # Species-level scientific name (first two parts) used for grouping
    def _base_sci(p):
        if isinstance(p, list) and len(p) >= 2:
            return f"{p[0]} {p[1]}"
        if isinstance(p, list) and len(p) == 1:
            return p[0]
        return ""

    df["_base_sci"] = parts.apply(_base_sci)
    df["_is_subspecies"] = is_sub
    df["_count"] = df["Count"].apply(safe_count)

    # Common-name normalisation: parent species common name = before " ("
    def _species_common_from_common(name: str) -> str:
        s = (name or "").strip()
        if not s:
            return ""
        idx = s.find(" (")
        return s[:idx] if idx != -1 else s

    def _subspecies_label_from_common(name: str) -> str:
        s = (name or "").strip()
        if not s:
            return ""
        start = s.find(" (")
        end = s.rfind(")")
        if start != -1 and end != -1 and end > start + 2:
            return s[start + 2 : end].strip()
        return s

    df["_species_common_base"] = common.apply(_species_common_from_common)
    df["_sub_label"] = common.apply(_subspecies_label_from_common)

    species_blocks = []

    # Group by species (base scientific name)
    for base_sci, g in df.groupby("_base_sci"):
        # Subspecies rows for this species
        g_sub = g[g["_is_subspecies"]]
        if g_sub.empty:
            # Skip species that never appear as true subspecies
            continue

        # Species-level rows (recorded without subspecies)
        g_species_only = g[~g["_is_subspecies"]]
        species_only_count = int(g_species_only["_count"].sum()) if not g_species_only.empty else 0

        # Subspecies aggregation by full scientific name
        subspecies_rows = []
        for subsci, sg in g_sub.groupby("Scientific Name"):
            total_ind = int(sg["_count"].sum())
            # Pick a representative common name for this subspecies
            common_vals = sg["Common Name"].dropna().astype(str)
            common_full = common_vals.value_counts().index[0] if not common_vals.empty else ""
            label = _subspecies_label_from_common(common_full) or common_full
            subspecies_rows.append(
                {
                    "subspecies_common": str(label),
                    "subspecies_common_full": str(common_full),
                    "subspecies_scientific": str(subsci),
                    "individuals": total_ind,
                }
            )

        if not subspecies_rows:
            continue

        # Sort subspecies alphabetically by label
        subspecies_rows.sort(key=lambda d: d["subspecies_common"].lower())

        subspecies_total = sum(d["individuals"] for d in subspecies_rows)
        total = species_only_count + subspecies_total
        frac = (subspecies_total / total) if total > 0 else None

        # Species common name: most frequent base common name across all rows in this group
        base_common_vals = g["_species_common_base"].dropna().astype(str)
        if not base_common_vals.empty:
            species_common = base_common_vals.value_counts().index[0]
        else:
            # Fallback to any common name in the group
            species_common = g["Common Name"].dropna().astype(str).value_counts().index[0]

        species_blocks.append(
            {
                "species_common": str(species_common),
                "species_scientific": str(base_sci),
                "total_individuals": int(total),
                "species_only_individuals": int(species_only_count),
                "subspecies_total_individuals": int(subspecies_total),
                "subspecies_fraction": float(frac) if frac is not None else None,
                "subspecies": subspecies_rows,
            }
        )

    if not species_blocks:
        return []

    # Sort species alphabetically by common name
    species_blocks.sort(key=lambda d: d["species_common"].lower())

    if limit is not None and limit > 0:
        species_blocks = species_blocks[:limit]

    return species_blocks


def rankings_seen_once(df_obs, limit=None):
    """Species in exactly 1 checklist.

    Returns list of (species, location_link, state, country, date_time_link, count).
    """
    if df_obs.empty:
        return []
    df_s = df_obs.copy()
    df_s["_base"] = countable_species_vectorized(df_s)
    df_s = df_s.dropna(subset=["_base"])
    df_s["_count"] = df_s["Count"].apply(safe_count)
    dt_col = "datetime" if "datetime" in df_s.columns else "Date"
    by_base = df_s.groupby("_base").agg(
        n_checklists=("Submission ID", "nunique"),
        checklist_count=("_count", "sum"),
        common_name=("Common Name", lambda s: s.value_counts().index[0] if len(s) > 0 else ""),
        Location=("Location", "first"),
        Location_ID=("Location ID", "first"),
        Submission_ID=("Submission ID", "first"),
        _dt=(dt_col, "first"),
    ).reset_index()
    reg_col = region_column(df_s, prefer_country=True)
    if reg_col:
        region_by_base = (
            df_s.groupby("_base")[reg_col]
            .first()
            .reset_index()
            .rename(columns={reg_col: "_region"})
        )
        by_base = by_base.merge(region_by_base, on="_base", how="left")
    seen_once = by_base[by_base["n_checklists"] == 1].sort_values("common_name")
    if limit is not None:
        seen_once = seen_once.head(limit)
    rows = []
    for _, r in seen_once.iterrows():
        name = r["common_name"] if pd.notna(r["common_name"]) else r["_base"]
        lid = r.get("Location_ID")
        loc = r.get("Location", "")
        sid = r.get("Submission_ID")
        dt = r.get("_dt")
        dt_str = pd.Timestamp(dt).strftime("%d %b %Y %H:%M") if pd.notna(dt) else "—"
        loc_link = f'<a href="https://ebird.org/lifelist/{lid}" target="_blank">{loc}</a>' if lid else loc
        dt_link = f'<a href="https://ebird.org/checklist/{sid}" target="_blank">{dt_str}</a>' if sid else dt_str
        state_str = ""
        country_str = ""
        if "_region" in r.index:
            country, state = format_region_parts(r.get("_region"))
            state_str = state if state else ""
            country_str = country if country else ""
        rows.append((str(name), loc_link, state_str, country_str, dt_link, f"{int(r['checklist_count']):,}"))
    return rows


def rankings_high_counts(df_obs, tie_break="last", sort_mode="total_count"):
    """Highest checklist count per countable species.

    Returns rows ``(species, location_link, state, country, date_time_link, count)``.
    For ties on ``Count``, *tie_break* chooses earliest (``"first"``) or latest
    (``"last"``) checklist date/time.
    """
    if df_obs.empty:
        return []
    tie_mode = str(tie_break).strip().lower()
    if tie_mode not in ("first", "last"):
        tie_mode = "last"
    sort_key_mode = str(sort_mode).strip().lower()
    if sort_key_mode not in ("total_count", "alphabetical"):
        sort_key_mode = "total_count"

    df_s = df_obs.copy()
    df_s["_base"] = countable_species_vectorized(df_s)
    df_s = df_s.dropna(subset=["_base"])
    if df_s.empty:
        return []

    dt_col = "datetime" if "datetime" in df_s.columns else "Date"
    if dt_col in df_s.columns:
        df_s["_dt"] = pd.to_datetime(df_s[dt_col], errors="coerce")
    else:
        df_s["_dt"] = pd.NaT
    df_s["_count"] = df_s["Count"].apply(safe_count)
    reg_col = region_column(df_s, prefer_country=True)

    rows = []
    for _base, grp in df_s.groupby("_base", sort=False):
        max_count = int(grp["_count"].max())
        top = grp[grp["_count"] == max_count].copy()
        if top.empty:
            continue
        top["_dt_sort"] = pd.to_datetime(top["_dt"], errors="coerce")
        top["_dt_sort"] = top["_dt_sort"].fillna(
            pd.Timestamp.max if tie_mode == "first" else pd.Timestamp.min
        )
        top = top.sort_values(
            by=["_dt_sort", "Submission ID"],
            ascending=[tie_mode == "first", True],
        )
        r = top.iloc[0]
        name = r["Common Name"] if pd.notna(r.get("Common Name")) else _base
        lid = r.get("Location ID")
        loc = r.get("Location", "")
        sid = r.get("Submission ID")
        dt = r.get("_dt")
        dt_str = pd.Timestamp(dt).strftime("%d %b %Y %H:%M") if pd.notna(dt) else "—"
        loc_link = f'<a href="https://ebird.org/lifelist/{lid}" target="_blank">{loc}</a>' if lid else loc
        dt_link = f'<a href="https://ebird.org/checklist/{sid}" target="_blank">{dt_str}</a>' if sid else dt_str
        state_str = ""
        country_str = ""
        if reg_col and reg_col in r.index:
            country, state = format_region_parts(r.get(reg_col))
            state_str = state if state else ""
            country_str = country if country else ""
        rows.append((str(name), loc_link, state_str, country_str, dt_link, f"{max_count:,}"))

    if sort_key_mode == "alphabetical":
        rows.sort(key=lambda x: str(x[0]).lower())
    else:
        rows.sort(
            key=lambda x: (
                -int(str(x[5]).replace(",", "")),
                str(x[0]).lower(),
            )
        )
    return rows


def rankings_by_visits(cl_sub, limit):
    """Top N most visited locations; ties by oldest first.

    Returns list of (loc_link, state, country, first_link, last_link, count).
    """
    if cl_sub.empty:
        return []
    dt_col = "datetime" if "datetime" in cl_sub.columns else "Date"
    first_idx = cl_sub.groupby("Location ID")[dt_col].idxmin().dropna()
    last_idx = cl_sub.groupby("Location ID")[dt_col].idxmax().dropna()
    first_rows = cl_sub.loc[first_idx, ["Location ID", "Location", dt_col, "Submission ID"]].rename(
        columns={dt_col: "First", "Submission ID": "First_SID"}
    )
    last_rows = cl_sub.loc[last_idx, ["Location ID", "Location", dt_col, "Submission ID"]].rename(
        columns={dt_col: "Last", "Submission ID": "Last_SID"}
    )
    vc = cl_sub.groupby("Location ID").agg(Count=("Submission ID", "nunique")).reset_index()
    vc = vc.merge(first_rows, on="Location ID").merge(last_rows[["Location ID", "Last", "Last_SID"]], on="Location ID")
    reg_col = region_column(cl_sub, prefer_country=True)
    if reg_col:
        vc = vc.merge(
            cl_sub.groupby("Location ID")[reg_col].first().reset_index(),
            on="Location ID", how="left",
        )
    vc = vc.sort_values(by=["Count", "First"], ascending=[False, True]).head(limit)
    rows = []
    for _, r in vc.iterrows():
        lid = r["Location ID"]
        # For visit-focused tables, link to the user's checklists at that location (refs #59).
        loc_link = f'<a href="https://ebird.org/mychecklists/{lid}" target="_blank">{r["Location"]}</a>' if lid else r["Location"]
        state_str = ""
        country_str = ""
        if reg_col and reg_col in vc.columns:
            country, state = format_region_parts(r.get(reg_col))
            state_str = state if state else ""
            country_str = country if country else ""
        first_str = pd.Timestamp(r["First"]).strftime("%d %b %Y %H:%M") if pd.notna(r["First"]) else "—"
        last_str = pd.Timestamp(r["Last"]).strftime("%d %b %Y %H:%M") if pd.notna(r["Last"]) else "—"
        first_sid = r.get("First_SID")
        last_sid = r.get("Last_SID")
        first_link = f'<a href="https://ebird.org/checklist/{first_sid}" target="_blank">{first_str}</a>' if pd.notna(first_sid) and first_sid else first_str
        last_link = f'<a href="https://ebird.org/checklist/{last_sid}" target="_blank">{last_str}</a>' if pd.notna(last_sid) and last_sid else last_str
        rows.append((loc_link, state_str, country_str, first_link, last_link, f"{int(r['Count']):,}"))
    return rows


def rankings_not_seen_recently(df_obs, reference_date=None):
    """Countable base species whose last global observation was before the past 12 months.

    Rows are sorted by longest gap first (descending days since last seen). There is no row cap;
    scroll/window height comes from Rankings **visible rows** settings.

    Returns rows ``(common_name, last_seen_html, days_str)`` for
    :func:`explorer.presentation.rankings_display.rankings_not_seen_recently_table`.
    *last_seen_html* is the visit date/time linking to the checklist of that observation.

    *reference_date* defaults to local today (normalized); set for deterministic tests (refs #106).
    """
    if df_obs.empty:
        return []
    df_s = df_obs.copy()
    df_s["_base"] = countable_species_vectorized(df_s)
    df_s = df_s.dropna(subset=["_base"])
    if df_s.empty:
        return []
    dt_col = "datetime" if "datetime" in df_s.columns else "Date"
    if dt_col not in df_s.columns:
        return []
    dts = pd.to_datetime(df_s[dt_col], errors="coerce")
    df_s = df_s.assign(_dt=dts).dropna(subset=["_dt"])
    if df_s.empty:
        return []
    idx = df_s.groupby("_base")["_dt"].idxmax()
    last_rows = df_s.loc[idx].copy()
    if reference_date is None:
        ref = pd.Timestamp.now(tz=None).normalize()
    else:
        ref = pd.Timestamp(reference_date).normalize()
    cutoff = ref - pd.DateOffset(months=12)
    last_rows = last_rows[last_rows["_dt"] < cutoff]
    if last_rows.empty:
        return []
    last_rows["_days"] = (ref - last_rows["_dt"].dt.normalize()).dt.days
    last_rows = last_rows.sort_values("_days", ascending=False)
    rows = []
    for _, r in last_rows.iterrows():
        common = r.get("Common Name")
        name = str(common) if pd.notna(common) else str(r["_base"])
        sid = r.get("Submission ID")
        dt_str = pd.Timestamp(r["_dt"]).strftime("%d %b %Y %H:%M") if pd.notna(r["_dt"]) else "—"
        if sid:
            last_link = (
                f'<a href="https://ebird.org/checklist/{sid}" target="_blank" rel="noopener noreferrer">'
                f"{dt_str}</a>"
            )
        else:
            last_link = dt_str
        d = int(r["_days"])
        days_str = f"{d:,} days"
        rows.append((name, last_link, days_str))
    return rows


# ---------------------------------------------------------------------------
# Rankings orchestrator
# ---------------------------------------------------------------------------

def compute_rankings(
    df,
    cl,
    limit,
    dur_col,
    dist_col,
    high_count_tie_break="last",
    high_count_sort="total_count",
):
    """Compute all Top N rankings data.

    Returns dict of section key → list of row tuples.
    """
    cl_with_dur = cl.dropna(subset=[dur_col]).copy() if dur_col else pd.DataFrame()
    if dur_col and not cl_with_dur.empty:
        cl_with_dur["_dur"] = pd.to_numeric(cl_with_dur[dur_col], errors="coerce").fillna(0)
    cl_with_dist = cl.dropna(subset=[dist_col]).copy() if dist_col else pd.DataFrame()
    if dist_col and not cl_with_dist.empty:
        cl_with_dist["_dist"] = pd.to_numeric(cl_with_dist[dist_col], errors="coerce").fillna(0)
    if df.empty:
        return {k: [] for k in ("time", "dist", "species", "individuals",
                                 "species_loc", "individuals_loc", "visited",
                                 "species_individuals", "species_checklists",
                                 "species_high_counts", "seen_once", "subspecies", "not_seen_recently")}
    species_per_cl = df.groupby("Submission ID", group_keys=False).apply(
        lambda g: countable_species_vectorized(g).dropna().nunique(),
        include_groups=False,
    ).reset_index(name="_nsp")
    ind_per_cl = df.groupby("Submission ID", group_keys=False).apply(
        lambda g: g["Count"].apply(safe_count).sum(),
        include_groups=False,
    ).reset_index(name="_nind")
    cl_species = cl.merge(species_per_cl, on="Submission ID", how="inner")
    cl_individuals = cl.merge(ind_per_cl, on="Submission ID", how="inner")

    return {
        "time": rankings_by_value(cl_with_dur, "_dur", "Date", "Location", "Location ID", "Submission ID", lambda x: f"{int(round(x))} min", limit) if dur_col and not cl_with_dur.empty else [],
        "dist": rankings_by_value(cl_with_dist, "_dist", "Date", "Location", "Location ID", "Submission ID", lambda x: f"{x:,.2f} km", limit) if dist_col and not cl_with_dist.empty else [],
        "species": rankings_by_value(cl_species, "_nsp", "Date", "Location", "Location ID", "Submission ID", lambda x: f"{int(x):,}", limit) if not cl_species.empty else [],
        "individuals": rankings_by_value(cl_individuals, "_nind", "Date", "Location", "Location ID", "Submission ID", lambda x: f"{int(x):,}", limit) if not cl_individuals.empty else [],
        "species_loc": rankings_by_location(df, cl, "species", lambda x: f"{int(x):,}", limit),
        "individuals_loc": rankings_by_location(df, cl, "individuals", lambda x: f"{int(x):,}", limit),
        "visited": rankings_by_visits(cl, limit),
        "species_individuals": rankings_by_individuals(df, limit=None),
        "species_checklists": rankings_by_checklists(df, limit=None),
        "species_high_counts": rankings_high_counts(
            df,
            tie_break=high_count_tie_break,
            sort_mode=high_count_sort,
        ),
        "seen_once": rankings_seen_once(df, limit=None),
        "subspecies": rankings_subspecies_hierarchical(df, limit=None),
        "not_seen_recently": rankings_not_seen_recently(df),
    }


# ---------------------------------------------------------------------------
# Yearly summary
# ---------------------------------------------------------------------------

def yearly_summary_stats(df, cl, dur_col, dist_col):
    """Compute per-year stats.

    Returns (years_sorted, rows, incomplete_by_year).

    *rows* is a list of (label, [val_per_year, ...]).
    *incomplete_by_year* is dict year → list of (sid, date_str, location).
    """
    cl = cl.dropna(subset=["Date"])
    if cl.empty:
        return [], [], {}
    cl["_year"] = cl["Date"].dt.year
    years_sorted = sorted(cl["_year"].dropna().astype(int).unique())
    if not years_sorted:
        return [], [], {}
    df_with_yr = df.copy()
    df_with_yr["_year"] = df_with_yr["Date"].dt.year

    has_protocol = "Protocol" in df.columns
    has_all_obs = "All Obs Reported" in df.columns
    proto_lower = cl["Protocol"].astype(str).str.strip().str.lower() if has_protocol else None
    traveling_mask = proto_lower.str.contains("traveling|travelling", na=False) if has_protocol else pd.Series(False, index=cl.index)
    stationary_mask = proto_lower.str.contains("stationary", na=False) if has_protocol else pd.Series(False, index=cl.index)
    incidental_mask = proto_lower.str.contains("incidental|casual observation", na=False, regex=True) if has_protocol else pd.Series(False, index=cl.index)
    completed_mask = pd.Series(True, index=cl.index)
    if has_all_obs:
        a = cl["All Obs Reported"]
        completed_mask = a.notna() & (
            (pd.to_numeric(a, errors="coerce") == 1) |
            (a.astype(str).str.strip().str.upper().isin(["TRUE", "YES", "Y"]))
        )
    traveling_complete = traveling_mask & completed_mask if has_protocol else traveling_mask
    stationary_complete = stationary_mask & completed_mask if has_protocol else stationary_mask
    incomplete_not_incidental = ~completed_mask & ~incidental_mask if has_all_obs and has_protocol else pd.Series(False, index=cl.index)
    incomplete_hint = _html.escape("Incomplete checklists not counted.", quote=True)
    info_icon = f' <span class="stats-info-icon"><span class="stats-info-glyph">&#9432;</span><span class="stats-info-tooltip">{incomplete_hint}</span></span>' if has_all_obs else ""

    sp_series = countable_species_vectorized(df_with_yr)
    df_with_yr["_base"] = sp_series
    df_with_yr["_count"] = df_with_yr["Count"].apply(safe_count)

    rows = []

    # 1. Total species
    by_yr_sp = df_with_yr.dropna(subset=["_base"]).groupby("_year")["_base"].nunique()
    vals = [int(by_yr_sp.get(y, 0)) for y in years_sorted]
    rows.append(("Total species", [f"{v:,}" for v in vals]))

    # 2. Total individuals
    by_yr_ind = df_with_yr.groupby("_year")["_count"].sum()
    vals = [int(by_yr_ind.get(y, 0)) for y in years_sorted]
    rows.append(("Total individuals", [f"{v:,}" for v in vals]))

    # 3. Lifers
    first_seen = df_with_yr.dropna(subset=["_base"]).groupby("_base")["Date"].min()
    first_seen_year = first_seen.dt.year
    lifers_per_year = first_seen_year.value_counts()
    vals = [int(lifers_per_year.get(y, 0)) for y in years_sorted]
    rows.append(("Lifers", [f"{v:,}" for v in vals]))

    # 4. Traveling checklists (complete only)
    if has_protocol:
        trav_count = cl[traveling_complete].groupby("_year").size()
        vals = [int(trav_count.get(y, 0)) for y in years_sorted]
        rows.append((f"Traveling checklists{info_icon}", [f"{v:,}" for v in vals]))
    else:
        rows.append(("Traveling checklists", ["—"] * len(years_sorted)))

    # 5. Stationary checklists (complete only)
    if has_protocol:
        stat_count = cl[stationary_complete].groupby("_year").size()
        vals = [int(stat_count.get(y, 0)) for y in years_sorted]
        rows.append((f"Stationary checklists{info_icon}", [f"{v:,}" for v in vals]))
    else:
        rows.append(("Stationary checklists", ["—"] * len(years_sorted)))

    # 6. Incidental checklists
    if has_protocol:
        inc_count = cl[incidental_mask].groupby("_year").size()
        vals = [int(inc_count.get(y, 0)) for y in years_sorted]
        rows.append(("Incidental checklists", [f"{v:,}" for v in vals]))
    else:
        rows.append(("Incidental checklists", ["—"] * len(years_sorted)))

    # 7. Total checklists
    by_yr_cl = cl.groupby("_year").size()
    vals = [int(by_yr_cl.get(y, 0)) for y in years_sorted]
    rows.append(("Total checklists", [f"{v:,}" for v in vals]))

    # 8. Completed checklists
    if has_all_obs:
        completed = cl[completed_mask]
        by_yr = completed.groupby("_year").size()
        vals = [int(by_yr.get(y, 0)) for y in years_sorted]
        rows.append(("Completed checklists", [f"{v:,}" for v in vals]))
    else:
        rows.append(("Completed checklists", ["—"] * len(years_sorted)))

    # 9. Incomplete checklists (not incidental)
    if has_all_obs and has_protocol:
        inc_count = cl[incomplete_not_incidental].groupby("_year").size()
        vals = [int(inc_count.get(y, 0)) for y in years_sorted]
        rows.append(("Incomplete checklists", [f"{v:,}" for v in vals]))
    else:
        rows.append(("Incomplete checklists", ["—"] * len(years_sorted)))

    # 10. Days with checklist
    by_yr_dates = cl.groupby("_year")["Date"].apply(lambda s: s.dt.normalize().nunique())
    vals = [int(by_yr_dates.get(y, 0)) for y in years_sorted]
    rows.append(("Days with checklist", [f"{v:,}" for v in vals]))

    # 11. Cumulative days eBird on
    all_dates = cl["Date"].dt.normalize()
    cum = [int(all_dates[all_dates.dt.year <= y].nunique()) for y in years_sorted]
    rows.append(("Cumulative days eBird on", [f"{v:,}" for v in cum]))

    # 12. Total birding hours
    if dur_col:
        timed = cl.dropna(subset=[dur_col]).copy()
        timed["_dur"] = pd.to_numeric(timed[dur_col], errors="coerce").fillna(0)
        timed["_year"] = timed["Date"].dt.year
        if has_protocol:
            excl = timed["Protocol"].astype(str).str.strip().str.lower().str.contains("incidental|historical|casual observation", na=False, regex=True)
            timed = timed[~excl]
        by_yr_min = timed.groupby("_year")["_dur"].sum()
        vals = [by_yr_min.get(y, 0) / 60 for y in years_sorted]
        rows.append(("Total birding hours", [f"{v:.1f}" if v else "—" for v in vals]))
    else:
        rows.append(("Total birding hours", ["—"] * len(years_sorted)))

    # 13. Unique locations
    by_yr_loc = cl.groupby("_year")["Location ID"].nunique()
    vals = [int(by_yr_loc.get(y, 0)) for y in years_sorted]
    rows.append(("Unique locations", [f"{v:,}" for v in vals]))

    # 14–15. Shared checklists / Days birding with others
    if "Number of Observers" in cl.columns:
        shared_cl = cl.dropna(subset=["Number of Observers"]).copy()
        shared_cl["_nobs"] = pd.to_numeric(shared_cl["Number of Observers"], errors="coerce").fillna(0)
        shared_mask = shared_cl["_nobs"] > 1
        shared_sub = shared_cl[shared_mask]
        if not shared_sub.empty:
            by_yr_shared = shared_sub.groupby("_year").size()
            vals_shared = [int(by_yr_shared.get(y, 0)) for y in years_sorted]
            rows.append(("Shared checklists", [f"{v:,}" for v in vals_shared]))
            shared_sub = shared_sub.copy()
            shared_sub["_date"] = shared_sub["Date"].dt.normalize()
            by_yr_days = shared_sub.groupby("_year")["_date"].nunique()
            vals_days = [int(by_yr_days.get(y, 0)) for y in years_sorted]
            rows.append(("Days birding with others", [f"{v:,}" for v in vals_days]))
        else:
            rows.append(("Shared checklists", ["—"] * len(years_sorted)))
            rows.append(("Days birding with others", ["—"] * len(years_sorted)))
    else:
        rows.append(("Shared checklists", ["—"] * len(years_sorted)))
        rows.append(("Days birding with others", ["—"] * len(years_sorted)))

    # 16. Total distance (km)
    if dist_col:
        cl["_dist"] = pd.to_numeric(cl[dist_col], errors="coerce").fillna(0)
        by_yr_km = cl.groupby("_year")["_dist"].sum()
        vals = [by_yr_km.get(y, 0) for y in years_sorted]
        rows.append(("Total distance (km)", [f"{v:,.1f}" if v else "—" for v in vals]))
    else:
        rows.append(("Total distance (km)", ["—"] * len(years_sorted)))

    # 17–18. Traveling checklist: Total distance, Average distance
    if dist_col and has_protocol:
        trav = cl[traveling_complete].copy()
        trav["_year"] = trav["Date"].dt.year
        trav["_dist"] = pd.to_numeric(trav[dist_col], errors="coerce").fillna(0)
        by_yr = trav.groupby("_year")["_dist"].sum()
        n_trav = trav.groupby("_year").size()
        vals_km = [by_yr.get(y, 0) for y in years_sorted]
        vals_n = [int(n_trav.get(y, 0)) for y in years_sorted]
        rows.append((f"Traveling checklist: Total distance (km){info_icon}", [f"{v:,.1f}" if v else "—" for v in vals_km]))
        avg_dist = ["—" if n == 0 else f"{(vals_km[i] / n):.1f}" for i, n in enumerate(vals_n)]
        rows.append((f"Traveling checklist: Average distance (km){info_icon}", avg_dist))
    else:
        rows.append(("Traveling checklist: Total distance (km)", ["—"] * len(years_sorted)))
        rows.append(("Traveling checklist: Average distance (km)", ["—"] * len(years_sorted)))

    # 19–20. Traveling checklist: Total hours, Average minutes
    if dur_col and has_protocol:
        trav = cl[traveling_complete].dropna(subset=[dur_col]).copy()
        trav["_year"] = trav["Date"].dt.year
        trav["_min"] = pd.to_numeric(trav[dur_col], errors="coerce").fillna(0)
        by_yr_min = trav.groupby("_year")["_min"].sum()
        n_trav = trav.groupby("_year").size()
        vals_min = [by_yr_min.get(y, 0) for y in years_sorted]
        vals_n = [int(n_trav.get(y, 0)) for y in years_sorted]
        rows.append((f"Traveling checklist: Total hours{info_icon}", [f"{v / 60:.1f}" if v else "—" for v in vals_min]))
        avg_min = ["—" if n == 0 else f"{vals_min[i] / n:.1f}" for i, n in enumerate(vals_n)]
        rows.append((f"Traveling checklist: Average minutes{info_icon}", avg_min))
    else:
        rows.append(("Traveling checklist: Total hours", ["—"] * len(years_sorted)))
        rows.append(("Traveling checklist: Average minutes", ["—"] * len(years_sorted)))

    # 20b–20c. Traveling checklist: Average species, Average individuals
    if has_protocol:
        trav_cl = cl[traveling_complete]
        trav_sids = set(trav_cl["Submission ID"])
        trav_obs = df_with_yr[df_with_yr["Submission ID"].isin(trav_sids)].copy()
        trav_obs["_year"] = trav_obs["Date"].dt.year
        sp_means, ind_means = [], []
        for y in years_sorted:
            o = trav_obs[trav_obs["_year"] == y]
            if o.empty:
                sp_means.append("—")
                ind_means.append("—")
            else:
                sp_per_cl = o.dropna(subset=["_base"]).groupby("Submission ID")["_base"].nunique()
                ind_per_cl = o.groupby("Submission ID")["_count"].sum()
                sp_means.append(f"{sp_per_cl.mean():.1f}" if len(sp_per_cl) else "—")
                ind_means.append(f"{ind_per_cl.mean():.1f}" if len(ind_per_cl) else "—")
        rows.append((f"Traveling checklist: Average species{info_icon}", sp_means))
        rows.append((f"Traveling checklist: Average individuals{info_icon}", ind_means))
    else:
        rows.append(("Traveling checklist: Average species", ["—"] * len(years_sorted)))
        rows.append(("Traveling checklist: Average individuals", ["—"] * len(years_sorted)))

    # 21–24. Stationary checklist stats
    if has_protocol and dur_col:
        stat_cl = cl[stationary_complete]
        stat_sids = set(stat_cl["Submission ID"])
        stat_obs = df_with_yr[df_with_yr["Submission ID"].isin(stat_sids)].copy()
        stat_obs["_year"] = stat_obs["Date"].dt.year
        sp_means, ind_means = [], []
        for y in years_sorted:
            o = stat_obs[stat_obs["_year"] == y]
            if o.empty:
                sp_means.append("—")
                ind_means.append("—")
            else:
                sp_per_cl = o.dropna(subset=["_base"]).groupby("Submission ID")["_base"].nunique()
                ind_per_cl = o.groupby("Submission ID")["_count"].sum()
                sp_means.append(f"{sp_per_cl.mean():.1f}" if len(sp_per_cl) else "—")
                ind_means.append(f"{ind_per_cl.mean():.1f}" if len(ind_per_cl) else "—")
        rows.append((f"Stationary checklist: Average species{info_icon}", sp_means))
        rows.append((f"Stationary checklist: Average individuals{info_icon}", ind_means))
        stat_cl = stat_cl.dropna(subset=[dur_col]).copy()
        stat_cl["_year"] = stat_cl["Date"].dt.year
        stat_cl["_min"] = pd.to_numeric(stat_cl[dur_col], errors="coerce").fillna(0)
        by_yr_min = stat_cl.groupby("_year")["_min"].sum()
        n_stat = stat_cl.groupby("_year").size()
        vals_min = [by_yr_min.get(y, 0) for y in years_sorted]
        vals_n = [int(n_stat.get(y, 0)) for y in years_sorted]
        rows.append((f"Stationary checklist: Total hours{info_icon}", [f"{v / 60:.1f}" if v else "—" for v in vals_min]))
        avg_min = ["—" if n == 0 else f"{vals_min[i] / n:.1f}" for i, n in enumerate(vals_n)]
        rows.append((f"Stationary checklist: Average minutes{info_icon}", avg_min))
    else:
        rows.append(("Stationary checklist: Average species", ["—"] * len(years_sorted)))
        rows.append(("Stationary checklist: Average individuals", ["—"] * len(years_sorted)))
        rows.append(("Stationary checklist: Total hours", ["—"] * len(years_sorted)))
        rows.append(("Stationary checklist: Average minutes", ["—"] * len(years_sorted)))

    # Incomplete checklists by year
    incomplete_by_year = {}
    if has_all_obs and has_protocol:
        use_dt_col = "datetime" if "datetime" in cl.columns else "Date"
        cols = ["_year", "Submission ID", use_dt_col, "Location"]
        inc_sub = cl[incomplete_not_incidental][cols].drop_duplicates()
        for y in years_sorted:
            sub = inc_sub[inc_sub["_year"] == y].sort_values(use_dt_col)
            list_y = []
            for _, r in sub.iterrows():
                sid = r.get("Submission ID")
                dt = r.get(use_dt_col)
                loc = r.get("Location") or ""
                date_str = pd.Timestamp(dt).strftime("%d %b %Y %H:%M") if pd.notna(dt) else "—"
                list_y.append((sid, date_str, str(loc)))
            if list_y:
                incomplete_by_year[int(y)] = list_y

    return years_sorted, rows, incomplete_by_year


# ---------------------------------------------------------------------------
# Country summary (per-country yearly-style tables for Country tab)
# ---------------------------------------------------------------------------


def checklist_country_keys(cl: pd.DataFrame) -> pd.Series:
    """Return a stable grouping key per checklist row (index aligned with *cl*).

    Prefer ``Country`` when present; otherwise derive ISO-like codes from
    ``State/Province`` (e.g. ``AU-NSW`` → ``AU``). Missing/blank → ``_UNKNOWN``.
    """
    if cl.empty:
        return pd.Series(dtype=object)

    def _from_country_col(val):
        if val is None or (isinstance(val, float) and pd.isna(val)):
            return "_UNKNOWN"
        s = str(val).strip()
        if not s:
            return "_UNKNOWN"
        if len(s) == 2 and s.isalpha():
            return s.upper()
        return s

    def _from_state_province(val):
        if val is None or (isinstance(val, float) and pd.isna(val)):
            return "_UNKNOWN"
        cc, st = format_region_parts(val)
        if cc:
            return str(cc).strip().upper()
        if st:
            return f"_R:{str(st).strip()}"
        return "_UNKNOWN"

    if "Country" in cl.columns:
        keys = cl["Country"].map(_from_country_col)
    elif "State/Province" in cl.columns:
        keys = cl["State/Province"].map(_from_state_province)
    else:
        keys = pd.Series(["_UNKNOWN"] * len(cl), index=cl.index)
    keys = keys.fillna("_UNKNOWN")
    keys = keys.replace("", "_UNKNOWN")
    return keys


def country_summary_stats(df, cl):
    """Compute per-country yearly blocks for the Country tab.

    Returns a list of ``(country_key, years_sorted, rows)`` where *rows* is a
    list of ``(label, [formatted value per year, ...])``. Only years that
    appear in that country's checklists are included (no empty year columns).

    When there is more than one year, each row includes a final **Total**
    column: sums for lifers / individuals / checklists / days; distinct
    species across all those years for **Total species**; last year's value
    for **Cumulative days eBird on** (unique checklist days in the country
    through the end of the range).

    Lifers (world): species whose first-ever sighting in the dataset occurred
    in this country and calendar year.

    Lifers (country): species whose first sighting *in this country* occurred
    in that calendar year.

    Cumulative days eBird on: unique dates with a checklist in this country,
    for all years up to and including each column year (same spirit as yearly
    summary, but restricted to that country).
    """
    cl = cl.dropna(subset=["Date"])
    if cl.empty or df.empty:
        return []

    cl = cl.copy()
    cl["_country_key"] = checklist_country_keys(cl)
    cl["_year"] = cl["Date"].dt.year

    df_m = df.copy()
    df_m["_base"] = countable_species_vectorized(df_m)
    df_m["_count"] = df_m["Count"].apply(safe_count)
    key_map = cl.set_index("Submission ID")["_country_key"]
    df_m["_country_key"] = df_m["Submission ID"].map(key_map).fillna("_UNKNOWN")
    df_m["_year"] = df_m["Date"].dt.year

    country_keys = sorted(cl["_country_key"].dropna().unique(), key=lambda k: str(k))
    blocks = []  # order finalized alphabetically by display name in checklist_stats_display

    obs = df_m.dropna(subset=["_base"])
    if not obs.empty:
        idx_world = obs.groupby("_base")["Date"].idxmin()
        first_world = obs.loc[idx_world].copy()
        first_world["_yr"] = first_world["Date"].dt.year
    else:
        first_world = pd.DataFrame()

    for ck in country_keys:
        cl_c = cl[cl["_country_key"] == ck]
        years_sorted = sorted(cl_c["_year"].dropna().astype(int).unique())
        if not years_sorted:
            continue

        if not first_world.empty:
            fw = first_world[(first_world["_country_key"] == ck)]
            lifers_world = fw.groupby("_yr").size()
        else:
            lifers_world = pd.Series(dtype=int)

        obs_c = obs[obs["_country_key"] == ck]
        if not obs_c.empty:
            idx_c = obs_c.groupby(["_base", "_country_key"])["Date"].idxmin()
            first_c = obs_c.loc[idx_c].copy()
            first_c["_yr"] = first_c["Date"].dt.year
            lifers_country = first_c.groupby("_yr").size()
        else:
            lifers_country = pd.Series(dtype=int)

        rows = []
        multi_year = len(years_sorted) > 1

        obs_ck = obs[(obs["_country_key"] == ck)]

        vals_w_i = [int(lifers_world.get(y, 0)) for y in years_sorted]
        vals_w = [f"{v:,}" for v in vals_w_i]
        if multi_year:
            vals_w.append(f"{sum(vals_w_i):,}")
        rows.append(("Lifers (world)", vals_w))

        vals_c_i = [int(lifers_country.get(y, 0)) for y in years_sorted]
        vals_c = [f"{v:,}" for v in vals_c_i]
        if multi_year:
            vals_c.append(f"{sum(vals_c_i):,}")
        rows.append(("Lifers (country)", vals_c))

        by_yr_sp = obs_ck.groupby("_year")["_base"].nunique()
        vals_sp = [int(by_yr_sp.get(y, 0)) for y in years_sorted]
        vals_sp_fmt = [f"{v:,}" for v in vals_sp]
        if multi_year:
            total_sp = int(obs_ck["_base"].nunique()) if not obs_ck.empty else 0
            vals_sp_fmt.append(f"{total_sp:,}")
        rows.append(("Total species", vals_sp_fmt))

        by_yr_ind = df_m[df_m["_country_key"] == ck].groupby("_year")["_count"].sum()
        vals_ind_i = [int(by_yr_ind.get(y, 0)) for y in years_sorted]
        vals_ind = [f"{v:,}" for v in vals_ind_i]
        if multi_year:
            vals_ind.append(f"{sum(vals_ind_i):,}")
        rows.append(("Total individuals", vals_ind))

        by_yr_cl = cl_c.groupby("_year").size()
        vals_cl_i = [int(by_yr_cl.get(y, 0)) for y in years_sorted]
        vals_cl = [f"{v:,}" for v in vals_cl_i]
        if multi_year:
            vals_cl.append(f"{sum(vals_cl_i):,}")
        rows.append(("Total checklists", vals_cl))

        by_yr_dates = cl_c.groupby("_year")["Date"].apply(lambda s: s.dt.normalize().nunique())
        vals_days_i = [int(by_yr_dates.get(y, 0)) for y in years_sorted]
        vals_days = [f"{v:,}" for v in vals_days_i]
        if multi_year:
            vals_days.append(f"{sum(vals_days_i):,}")
        rows.append(("Days with a checklist", vals_days))

        dates_c = cl_c["Date"].dt.normalize()
        cum = []
        for y in years_sorted:
            mask = cl_c["Date"].dt.year <= y
            cum.append(int(dates_c[mask].nunique()))
        vals_cum = [f"{v:,}" for v in cum]
        if multi_year:
            vals_cum.append(f"{cum[-1]:,}" if cum else "0")
        rows.append(("Cumulative days eBird on", vals_cum))

        blocks.append((ck, years_sorted, rows))

    return blocks


# ---------------------------------------------------------------------------
# Sex notation in checklist comments (maintenance report)
# ---------------------------------------------------------------------------

def _observation_details_is_sex_notation(s: str) -> bool:
    """True if the whole field looks like sex/age shorthand (conservative; refs #58).

    Matches:
    - Legacy: runs of M, F, J, ? only (e.g. ``MF``, ``MFFF``, ``MMF??``).
    - Count + letter runs with no separators (e.g. ``2M2F2?``).
    - Same tokens separated by whitespace and/or ``+`` (e.g. ``1M 1F``, ``M + F``).

    Does not scan inside longer prose — the *entire* string must match. Prefer missing
    odd cases over matching free text.
    """
    import re

    # pandas 3 may pass missing values into the mapper as float('nan') even
    # when the source Series is string-like (e.g. ArrowStringArray).
    if s is None or pd.isna(s):
        return False

    s = str(s).strip()
    if not s or s.lower() == "nan":
        return False
    # One or more tokens: optional digits then exactly one of M,F,J,?
    token = r"\d*[MFJ?]"
    compact = re.compile(rf"^({token})+$")
    # Two or more tokens separated only by whitespace or "+" (with optional spaces)
    spaced = re.compile(rf"^(?:{token})(?:(?:\s+|\s*\+\s*){token})+$")
    return bool(compact.match(s) or spaced.match(s))


def get_sex_notation_by_year(df):
    """Find rows where Observation Details matches sex/age shorthand (M, F, J, ?).

    Returns dict year -> list of (sid, date_str, location, species, protocol, notation).
    Used by the Maintenance tab to list checklists that may need Age/Sex table updates.
    """
    if "Observation Details" not in df.columns or df.empty:
        return {}
    col = df["Observation Details"].astype(str).str.strip()
    mask = col.ne("") & col.ne("nan") & col.apply(_observation_details_is_sex_notation)
    use_dt = "datetime" if "datetime" in df.columns else "Date"
    cols = ["Date", "Submission ID", "Location", "Common Name", "Protocol", "Observation Details"]
    if use_dt in df.columns:
        cols = [use_dt] + cols
    sub = df.loc[mask, cols].copy()
    if sub.empty:
        return {}
    sub["_year"] = sub["Date"].dt.year
    by_year = {}
    for y in sub["_year"].dropna().astype(int).unique():
        rows = sub[sub["_year"] == y].sort_values(use_dt)
        list_y = []
        for _, r in rows.iterrows():
            sid = r.get("Submission ID")
            dt = r.get(use_dt)
            date_str = pd.Timestamp(dt).strftime("%d %b %Y %H:%M") if pd.notna(dt) else "—"
            loc = str(r.get("Location") or "")
            species = str(r.get("Common Name") or "")
            protocol = str(r.get("Protocol") or "")
            notation = str(r.get("Observation Details") or "").strip()
            list_y.append((sid, date_str, loc, species, protocol, notation))
        if list_y:
            by_year[int(y)] = list_y
    return by_year