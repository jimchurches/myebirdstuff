"""
Duplicate and near-duplicate location detection for Personal eBird Explorer.

Pure calculation: accepts a location DataFrame and distance threshold,
returns structured data (lists of tuples). No widget, display, or HTML
dependencies.

Thresholds and matching behaviour:
- Exact duplicates: coordinates rounded to 6 decimal places.
- Near duplicates: BallTree with haversine metric, earth radius 6,371,000 m.
- Pairs closer than 0.01 m are treated as exact duplicates (excluded from
  the near-duplicate list).
"""

import numpy as np
import pandas as pd


EARTH_RADIUS_M = 6_371_000


def get_map_maintenance_data(loc_df, threshold_m):
    """Detect exact-duplicate and near-duplicate locations.

    Args:
        loc_df: DataFrame with columns Location ID, Location, Latitude, Longitude.
                Rows with missing coordinates are silently dropped.
        threshold_m: distance in metres; location pairs closer than this
                     (but farther than 0.01 m) are returned as near duplicates.

    Returns:
        (exact_dup_rows, near_pairs)

        exact_dup_rows: list of (location_name, location_id, count, lat, lon)
            for each coordinate group with >1 Location ID.  Same name listed
            once; different names listed separately.

        near_pairs: list of [(lid1, name1, lat1, lon1), (lid2, name2, lat2, lon2)]
            for each pair within *threshold_m* (excluding exact duplicates).
    """
    if "Location" not in loc_df.columns:
        return [], []

    one_per_loc = (
        loc_df[["Location ID", "Location", "Latitude", "Longitude"]]
        .drop_duplicates(subset=["Location ID"], keep="first")
        .copy()
    )
    one_per_loc["Latitude"] = pd.to_numeric(one_per_loc["Latitude"], errors="coerce")
    one_per_loc["Longitude"] = pd.to_numeric(one_per_loc["Longitude"], errors="coerce")
    one_per_loc = one_per_loc.dropna(subset=["Latitude", "Longitude"])

    if len(one_per_loc) < 2:
        return [], []

    from sklearn.neighbors import BallTree

    id_to_name = dict(zip(one_per_loc["Location ID"], one_per_loc["Location"]))
    id_to_coords = dict(
        zip(one_per_loc["Location ID"], zip(one_per_loc["Latitude"], one_per_loc["Longitude"]))
    )

    # --- Exact duplicates: group by rounded coords ---
    coord_cols = ["Latitude", "Longitude"]
    dup_coords = one_per_loc[coord_cols].round(6).duplicated(keep=False)
    dup_df = one_per_loc.loc[dup_coords]
    exact_dup_rows = []
    if not dup_df.empty:
        grouped = dup_df.groupby(dup_df[coord_cols].round(6).apply(tuple, axis=1))
        for _, grp in grouped:
            count = len(grp)
            by_name = grp.drop_duplicates(subset=["Location"], keep="first")
            for _, r in by_name.iterrows():
                exact_dup_rows.append(
                    (r["Location"], r["Location ID"], count, r["Latitude"], r["Longitude"])
                )

    # --- Near duplicates: BallTree haversine query ---
    coords = np.radians(one_per_loc[["Latitude", "Longitude"]].values)
    ids = one_per_loc["Location ID"].tolist()
    radius_rad = threshold_m / EARTH_RADIUS_M
    tree = BallTree(coords, metric="haversine")
    indices, distances = tree.query_radius(coords, r=radius_rad, return_distance=True)

    seen_pairs = set()
    near_pairs = []
    for i, (neighbors, dists) in enumerate(zip(indices, distances)):
        for k, j in enumerate(neighbors):
            if i != j and dists[k] * EARTH_RADIUS_M > 0.01:
                pair = tuple(sorted([ids[i], ids[j]]))
                if pair not in seen_pairs:
                    seen_pairs.add(pair)
                    coords_i = id_to_coords.get(ids[i], (None, None))
                    coords_j = id_to_coords.get(ids[j], (None, None))
                    near_pairs.append([
                        (ids[i], id_to_name.get(ids[i], ids[i]), coords_i[0], coords_i[1]),
                        (ids[j], id_to_name.get(ids[j], ids[j]), coords_j[0], coords_j[1]),
                    ])

    return exact_dup_rows, near_pairs
