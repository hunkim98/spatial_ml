"""Zone sampling utilities — no arcpy dependency.

Functions for building zone plans and selecting connected polygon subsets.
"""

import random

import geopandas as gpd
import pandas as pd


def build_zone_plan(
    n_zones: int, target_samples: int = 20,
) -> list[int]:
    """Build a list of target zone counts (distinct zone types per sample).

    Distribution:
      1-2 zones:     ~10% (edge cases)
      3-10 zones:    ~30% (partial maps)
      50-90% zones:  ~40% (dense partial maps)
      ALL zones:     ~20% (full maps, but with random polygon thinning)

    Uses -1 to signal "all zones" (with per-zone polygon thinning).
    Returns a list of target zone counts.
    """
    if n_zones <= 0:
        return []

    counts = []

    # 10%: 1-2 zones
    n = max(1, round(target_samples * 0.10))
    for _ in range(n):
        counts.append(random.randint(1, min(2, n_zones)))

    # 30%: 3-10 zones (partial maps)
    n = max(1, round(target_samples * 0.30))
    valid = list(range(3, min(11, n_zones + 1)))
    if not valid:
        valid = [n_zones]
    for _ in range(n):
        counts.append(random.choice(valid))

    # 40%: 50-90% of zones (dense partial)
    n = max(1, round(target_samples * 0.40))
    for _ in range(n):
        frac = random.uniform(0.5, 0.9)
        counts.append(max(1, round(n_zones * frac)))

    # 20%: ALL zones (with polygon thinning per zone)
    n = max(1, round(target_samples * 0.20))
    for _ in range(n):
        counts.append(-1)

    random.shuffle(counts)
    if len(counts) > target_samples:
        counts = counts[:target_samples]
    elif len(counts) < target_samples:
        while len(counts) < target_samples:
            counts.append(-1)

    return counts


def sample_by_zone_count(
    gdf: gpd.GeoDataFrame, zone_field: str | None, target_zones: int,
) -> gpd.GeoDataFrame:
    """Select a connected cluster of polygons covering `target_zones` zone types.

    Strategy:
    1. Pick a random seed polygon.
    2. Grow outward adding touching neighbors (like sample_connected_subset).
    3. Stop when we have polygons covering `target_zones` distinct zone types.
    4. Randomly include 50-100% of each zone type's polygons for variety.
    """
    if zone_field and zone_field in gdf.columns:
        unique_zones = gdf[zone_field].dropna().unique().tolist()
    else:
        unique_zones = list(range(len(gdf)))

    target_zones = min(target_zones, len(unique_zones))
    if target_zones <= 0:
        return gdf.iloc[:0].copy()

    sindex = gdf.sindex
    all_indices = gdf.index.tolist()

    best_selected = None

    for _ in range(5):  # retry with different seeds
        seed_idx = random.choice(all_indices)
        selected = {seed_idx}
        frontier = {seed_idx}

        # Grow until we cover target_zones distinct types
        def count_zones(idxs):
            if zone_field and zone_field in gdf.columns:
                return gdf.loc[list(idxs), zone_field].nunique()
            return len(idxs)

        while count_zones(selected) < target_zones and frontier:
            current = random.choice(list(frontier))
            frontier.discard(current)

            geom = gdf.loc[current, "geometry"]
            candidate_idxs = list(sindex.query(geom, predicate="intersects"))
            candidate_labels = gdf.index[candidate_idxs]
            neighbors = [i for i in candidate_labels if i not in selected]

            random.shuffle(neighbors)
            for nb in neighbors:
                if gdf.loc[nb, "geometry"].intersects(geom):
                    selected.add(nb)
                    frontier.add(nb)
                if count_zones(selected) >= target_zones:
                    break

        if count_zones(selected) >= target_zones:
            # Randomly thin: keep 50-100% of polygons per zone for variety
            subset = gdf.loc[list(selected)].copy()
            if zone_field and zone_field in gdf.columns and len(subset) > target_zones:
                keep_frac = random.uniform(0.5, 1.0)
                kept = []
                for zone_type in subset[zone_field].unique():
                    zone_polys = subset[subset[zone_field] == zone_type]
                    if len(zone_polys) == 0:
                        continue
                    n_keep = max(1, int(len(zone_polys) * keep_frac))
                    kept.append(zone_polys.sample(n=n_keep))
                return gpd.GeoDataFrame(pd.concat(kept))
            return subset

        if best_selected is None or count_zones(selected) > count_zones(best_selected):
            best_selected = selected

    return gdf.loc[list(best_selected)].copy()
