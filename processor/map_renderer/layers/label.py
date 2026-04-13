"""Label layer — zone name text on polygons.

Mimics real map labeling:
- Connected polygons of the same zone are grouped; only the largest
  component per group gets a label (avoids redundant labels).
- Uses polylabel (pole of inaccessibility) for placement so labels
  sit deep inside the polygon, not outside concave shapes.
- Each zone type gets its own randomized style (font, weight, color).
- Not every zone gets labeled — randomized per zone type.
"""

import random

import matplotlib.pyplot as plt
from shapely.ops import unary_union, polylabel

from ..config import MapConfig
from ..styles import LABEL_FONTS
from .base import BaseLayer


class LabelLayer(BaseLayer):
    """Draws zone name labels with per-zone style variation.

    Args:
        font: Font family for all zones. None to randomize per zone.
        color: Text color for all zones. None to randomize per zone.
    """

    def __init__(
        self,
        font: str | None = None,
        color: str | None = None,
    ):
        self.font = font
        self.color = color

    def draw(self, ax: plt.Axes, config: MapConfig) -> dict:
        gdf = config.gdf
        zone_col = config.zone_column
        map_width = ax.get_xlim()[1] - ax.get_xlim()[0]

        label_count = 0
        labeled_zones = set()

        for zone_name, zone_gdf in gdf.groupby(zone_col):
            style = self._zone_style()
            if style["label_probability"] == 0.0:
                continue

            # Merge touching polygons into connected components
            components = self._connected_components(zone_gdf)

            for component in components:
                if random.random() > style["label_probability"]:
                    continue

                # Pick the largest polygon in this connected group
                largest = max(component, key=lambda g: g.area)
                bounds = largest.bounds  # (minx, miny, maxx, maxy)
                poly_width = bounds[2] - bounds[0]
                poly_height = bounds[3] - bounds[1]

                size = self._fit_font_size(poly_width, poly_height, len(zone_name), map_width)
                if size is None:
                    continue

                # polylabel finds the point deepest inside the polygon
                try:
                    pt = polylabel(largest, tolerance=0.01)
                except Exception:
                    pt = largest.centroid

                ax.text(
                    pt.x, pt.y, zone_name,
                    fontsize=size,
                    fontfamily=style["font"],
                    fontweight=style["weight"],
                    fontstyle=style["style"],
                    color=style["color"],
                    ha="center",
                    va="center",
                    rotation=style["rotation"],
                )

                label_count += 1
                labeled_zones.add(zone_name)

        return {
            "has_labels": label_count > 0,
            "label_count": label_count,
            "labeled_zones": sorted(labeled_zones),
        }

    def _connected_components(self, zone_gdf) -> list[list]:
        """Group touching/overlapping polygons into connected components.

        Returns a list of groups, where each group is a list of
        individual Polygon geometries that are connected.
        """
        geoms = [g for g in zone_gdf.geometry if g is not None and not g.is_empty]
        if not geoms:
            return []

        merged = unary_union(geoms)

        if merged.geom_type == "Polygon":
            return [[merged]]
        elif merged.geom_type == "MultiPolygon":
            return [[p] for p in merged.geoms]
        else:
            return []

    def _zone_style(self) -> dict:
        """Generate a random style for one zone type."""
        return {
            "font": self.font or random.choice(LABEL_FONTS),
            "weight": random.choice(["normal", "normal", "bold"]),
            "style": random.choice(["normal", "normal", "italic"]),
            "color": self.color or random.choice([
                "black", "#222222", "#333333", "#444444",
                "#1a1a2e", "#2d2d2d",
            ]),
            "rotation": random.choice([0, 0, 0, 0, random.uniform(-15, 15)]),
            # ~30% of zone types get no labels at all
            "label_probability": 0.0 if random.random() < 0.3 else random.uniform(0.3, 0.9),
        }

    def _fit_font_size(
        self,
        poly_width: float,
        poly_height: float,
        text_len: int,
        map_width: float,
    ) -> float | None:
        """Return a font size that fits inside the polygon, or None if too small.

        Estimates text extent relative to polygon dimensions and picks the
        largest size that keeps the label within bounds.
        """
        if map_width <= 0:
            return None

        width_ratio = poly_width / map_width

        if width_ratio < 0.03:
            return None

        # Size constrained by width: text of `text_len` chars must fit
        # Approximate char width ~ 0.6 * fontsize in data units
        char_width_factor = 0.6
        size_by_width = (poly_width / (text_len * char_width_factor)) * (72 / map_width) * 50

        # Size constrained by height: single line must fit vertically
        height_ratio = poly_height / map_width
        size_by_height = height_ratio * 80

        size = min(size_by_width, size_by_height)
        return max(4, min(size, 18))
