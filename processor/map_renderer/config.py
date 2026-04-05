"""Config for randomized zoning map rendering.

MapConfig = the data (what to render).
RenderResult = the output.
Style lives in individual layer classes, not here.
"""

from dataclasses import dataclass, field
from pathlib import Path

import geopandas as gpd


# ------------------------------------------------------------------
# Data — what to render
# ------------------------------------------------------------------

@dataclass
class MapConfig:
    """The map data. No visual opinions. Validates on creation."""

    gdf: gpd.GeoDataFrame
    zone_column: str = ""
    color_map: dict[str, list[int]] = field(default_factory=dict)  # zone -> [R,G,B]

    def __post_init__(self):
        if self.gdf.empty:
            raise ValueError("gdf is empty")
        if not self.zone_column:
            raise ValueError("zone_column is required")
        if self.zone_column not in self.gdf.columns:
            raise ValueError(f"zone_column '{self.zone_column}' not found in gdf. Columns: {list(self.gdf.columns)}")
        if not self.color_map:
            raise ValueError("color_map is required")

        zones_in_data = set(self.gdf[self.zone_column].unique())
        zones_in_map = set(self.color_map.keys())
        missing = zones_in_data - zones_in_map
        if missing:
            raise ValueError(f"Zones missing from color_map: {missing}")


# ------------------------------------------------------------------
# Result
# ------------------------------------------------------------------

@dataclass
class RenderResult:
    """What render() returns."""

    image_path: Path
    width: int
    height: int
    extent: tuple[float, float, float, float]  # xmin, ymin, xmax, ymax
    color_map: dict[str, list[int]] = field(default_factory=dict)
    zone_column: str | None = None
    gdf: gpd.GeoDataFrame | None = field(repr=False, default=None)
    annotations: dict = field(default_factory=dict)
    raw_width: int | None = None   # pre-rotation image width
    raw_height: int | None = None  # pre-rotation image height
    post_rotation: float = 0.0     # rotation applied to raster (basemap case)
    nolabel_image: object = field(repr=False, default=None)  # PIL Image: postprocessed but no labels
