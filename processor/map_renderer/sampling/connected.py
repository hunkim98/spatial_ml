"""Connected sampler — grow a spatially connected cluster from a seed.

Focuses purely on spatial selection. Does not thin polygons.
"""

import random

import geopandas as gpd

from .base import BaseSampler


class ConnectedSampler(BaseSampler):
    """Sample a spatially connected cluster of polygons.

    Picks a random seed and grows outward until target_zones
    distinct zone types are covered. All polygons in the cluster
    are kept — no thinning.

    Args:
        target_zones: Number of distinct zone types to include.
                      None to randomize.
    """

    def __init__(self, target_zones: int | None = None):
        self.target_zones = target_zones

    def sample(self, gdf: gpd.GeoDataFrame, zone_column: str) -> gpd.GeoDataFrame:
        n_zones = gdf[zone_column].nunique()
        target = self.target_zones or random.randint(1, n_zones)
        target = min(target, n_zones)

        if target <= 0:
            return gdf.iloc[:0].copy()

        sindex = gdf.sindex
        all_indices = gdf.index.tolist()
        best_selected = None

        for _ in range(5):
            seed_idx = random.choice(all_indices)
            selected = {seed_idx}
            frontier = {seed_idx}

            while self._count_zones(gdf, selected, zone_column) < target and frontier:
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
                    if self._count_zones(gdf, selected, zone_column) >= target:
                        break

            if self._count_zones(gdf, selected, zone_column) >= target:
                return gdf.loc[list(selected)].copy()

            if best_selected is None or len(selected) > len(best_selected):
                best_selected = selected

        return gdf.loc[list(best_selected)].copy()

    def _count_zones(self, gdf, indices, zone_column):
        return gdf.loc[list(indices), zone_column].nunique()
