"""Canvas — figure setup from data geometry.

Computes extent, zoom, resolution, and applies rotation.
When a basemap is used, rotation is deferred to post-render
(rotate the entire raster so basemap and zones stay aligned).
"""

import math
import random

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import geopandas as gpd
from shapely.affinity import rotate as shapely_rotate


class Canvas:
    """Creates a matplotlib figure sized to the data.

    Args:
        zoom: How much of the data to show. 1.0=exact fit, <1=zoomed out,
              >1=zoomed in (clips edges). None to randomize.
        width: Output image width in pixels. None to auto-compute from
               data complexity.
        rotation: Rotation angle in degrees. None to randomize
                  (50% chance of 0, 50% random 0-360).
        dpi: Dots per inch for the figure.
        has_basemap: If True, rotation is deferred to post-render.
    """

    def __init__(
        self,
        zoom: float | None = None,
        width: int | None = None,
        rotation: float | None = None,
        dpi: int = 200,
        has_basemap: bool = False,
    ):
        self.zoom = zoom
        self.width = width
        self.rotation = rotation
        self.dpi = dpi
        self.has_basemap = has_basemap
        self.extent = None
        self.original_extent = None  # pre-expansion extent (for correct crop)
        self.post_rotation = 0.0  # rotation to apply after render

    def create(self, gdf: gpd.GeoDataFrame) -> tuple[plt.Figure, plt.Axes, gpd.GeoDataFrame]:
        """Create figure, axes, and (possibly rotated) GDF.

        Returns:
            (fig, ax, gdf_for_rendering)
        """
        angle = self._resolve_rotation()
        self.rotation = angle  # store resolved value for annotations

        if self.has_basemap:
            # Reproject to EPSG:3857 for basemap tile alignment
            render_gdf = gdf.to_crs(epsg=3857)
            render_gdf["geometry"] = render_gdf["geometry"].make_valid()
            # Don't rotate GDF — defer to post-render image rotation
            self.post_rotation = angle
        else:
            render_gdf = gdf.copy()
            render_gdf["geometry"] = render_gdf["geometry"].make_valid()
            if angle != 0:
                render_gdf = self._rotate_gdf(render_gdf, angle)
            self.post_rotation = 0.0

        zoom = self.zoom or random.uniform(0.7, 1.5)
        self.resolved_zoom = zoom  # store for annotations
        width = self.width or self._auto_width(render_gdf)
        extent = self._compute_extent(render_gdf, zoom)

        self.original_extent = extent

        # When post-rotation is needed, render larger to cover corners
        if self.post_rotation != 0:
            extent = self._expand_for_rotation(extent, self.post_rotation)

        xmin, ymin, xmax, ymax = extent
        aspect = (ymax - ymin) / (xmax - xmin) if (xmax - xmin) > 0 else 0.75
        height = int(width * aspect)

        fig_w = width / self.dpi
        fig_h = height / self.dpi
        fig, ax = plt.subplots(figsize=(fig_w, fig_h), dpi=self.dpi)

        ax.set_xlim(xmin, xmax)
        ax.set_ylim(ymin, ymax)
        ax.set_axis_off()
        ax.set_aspect("equal")
        ax.set_position([0, 0, 1, 1])

        self.extent = extent
        return fig, ax, render_gdf

    def _resolve_rotation(self) -> float:
        if self.rotation is not None:
            return self.rotation
        if random.random() < 0.5:
            return 0.0
        return random.uniform(0, 360)

    def _rotate_gdf(self, gdf: gpd.GeoDataFrame, angle: float) -> gpd.GeoDataFrame:
        """Rotate all geometries around the collection centroid."""
        rotated = gdf.copy()
        centroid = rotated.union_all().centroid
        rotated["geometry"] = rotated["geometry"].apply(
            lambda geom: shapely_rotate(geom, angle, origin=centroid) if geom is not None else None
        )
        return rotated

    def _expand_for_rotation(self, extent, angle):
        """Expand extent so rotated image can be cropped without blank corners."""
        xmin, ymin, xmax, ymax = extent
        cx = (xmin + xmax) / 2
        cy = (ymin + ymax) / 2
        half_w = (xmax - xmin) / 2
        half_h = (ymax - ymin) / 2

        # Diagonal of the original extent = minimum covering circle radius
        diag = math.sqrt(half_w ** 2 + half_h ** 2)
        # Expand to square that covers the diagonal
        return (cx - diag, cy - diag, cx + diag, cy + diag)

    def _compute_extent(
        self, gdf: gpd.GeoDataFrame, zoom: float
    ) -> tuple[float, float, float, float]:
        """Data bounds adjusted by zoom, centered on data centroid."""
        xmin, ymin, xmax, ymax = gdf.total_bounds
        cx = (xmin + xmax) / 2
        cy = (ymin + ymax) / 2
        half_w = (xmax - xmin) / 2 / zoom
        half_h = (ymax - ymin) / 2 / zoom
        return (cx - half_w, cy - half_h, cx + half_w, cy + half_h)

    def _auto_width(self, gdf: gpd.GeoDataFrame) -> int:
        """Pick image width based on data complexity."""
        areas = gdf.geometry.area
        total_area = areas.sum()

        if total_area <= 0:
            return 1024

        smallest_ratio = areas.min() / total_area
        width = int(800 + (1 - smallest_ratio) * 1248)
        return max(800, min(width, 2048))
