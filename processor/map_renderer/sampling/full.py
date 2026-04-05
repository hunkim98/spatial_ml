"""Full sampler — keep all zone types, thin per zone class independently."""

import random

import geopandas as gpd
import pandas as pd

from .base import BaseSampler


class FullSampler(BaseSampler):
    """Keep all zone types, but independently thin each zone class.

    Each zone type gets its own random keep fraction,
    creating natural variety in polygon density per zone.

    Args:
        min_keep: Minimum fraction per zone. Default 0.3.
        max_keep: Maximum fraction per zone. Default 1.0.
    """

    def __init__(self, min_keep: float = 0.3, max_keep: float = 1.0):
        self.min_keep = min_keep
        self.max_keep = max_keep

    def sample(self, gdf: gpd.GeoDataFrame, zone_column: str) -> gpd.GeoDataFrame:
        kept = []
        for _, zone_gdf in gdf.groupby(zone_column):
            frac = random.uniform(self.min_keep, self.max_keep)
            n = max(1, int(len(zone_gdf) * frac))
            kept.append(zone_gdf.sample(n=n))
        return gpd.GeoDataFrame(pd.concat(kept))
