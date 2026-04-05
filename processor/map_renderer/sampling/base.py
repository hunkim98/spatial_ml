"""Base class for polygon sampling strategies."""

from abc import ABC, abstractmethod

import geopandas as gpd


class BaseSampler(ABC):
    """Takes a GeoDataFrame and returns a subset."""

    @abstractmethod
    def sample(self, gdf: gpd.GeoDataFrame, zone_column: str) -> gpd.GeoDataFrame:
        """Return a subset of the GeoDataFrame."""
