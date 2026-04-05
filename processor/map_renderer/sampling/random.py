"""Random sampler — picks a sampling strategy for maximum variety."""

import random

import geopandas as gpd

from .base import BaseSampler
from .connected import ConnectedSampler
from .full import FullSampler


class RandomSampler(BaseSampler):
    """Randomly pick and apply a sampling strategy.

    ConnectedSampler is dominant — it always produces spatially
    contiguous clusters that look like real maps.

    Distribution:
        60%: ConnectedSampler (spatially realistic clusters)
        20%: FullSampler (all zones, thin per class)
        20%: No sampling (pass through)
    """

    def sample(self, gdf: gpd.GeoDataFrame, zone_column: str) -> gpd.GeoDataFrame:
        roll = random.random()

        if roll < 0.60:
            return ConnectedSampler().sample(gdf, zone_column)
        elif roll < 0.80:
            return FullSampler().sample(gdf, zone_column)
        else:
            return gdf
