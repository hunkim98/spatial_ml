"""Zone layer — fill, boundary, and hatch per zone in a single pass.

Zones are always fully opaque so colors can be used for mask extraction.
Each zone type gets its own randomized boundary style for variety.
"""

import random

import matplotlib.pyplot as plt

from ..config import MapConfig
from ..styles import BOUNDARY_PRESETS, HATCH_PATTERNS
from ..utils import rgb_to_hex, line_weight_to_linewidth
from .base import BaseLayer


class ZoneLayer(BaseLayer):
    """Draws zone polygons: fill + boundary + hatch, one zone type at a time.

    Each zone type gets its own randomized boundary style unless pinned.

    Args:
        boundary_color: Edge color for all zones. None to randomize per zone.
        boundary_line_weight: Relative thickness 0.0-1.0. None to randomize per zone.
        boundary_line_style: "-", "--", ":", "-.". None to randomize per zone.
        hatch_zones: {zone_name: pattern_name}. None for no hatching.
    """

    def __init__(
        self,
        boundary_color: str | None = None,
        boundary_line_weight: float | None = None,
        boundary_line_style: str | None = None,
        hatch_zones: dict[str, str] | None = None,
    ):
        self.boundary_color = boundary_color
        self.boundary_line_weight = boundary_line_weight
        self.boundary_line_style = boundary_line_style
        self.hatch_zones = hatch_zones or {}

    def draw(self, ax: plt.Axes, config: MapConfig) -> dict:
        gdf = config.gdf
        zone_col = config.zone_column

        zone_annotations = {}
        for zone_name, zone_gdf in gdf.groupby(zone_col):
            style = self._zone_boundary_style(ax)
            fill = rgb_to_hex(config.color_map[zone_name])
            hatch_name = self.hatch_zones.get(zone_name)
            hatch = HATCH_PATTERNS.get(hatch_name, None)

            zone_gdf.plot(
                ax=ax,
                color=fill,
                edgecolor=style["color"] if style["linewidth"] > 0 else "none",
                linewidth=style["linewidth"],
                linestyle=style["line_style"],
                hatch=hatch,
            )

            zone_annotations[zone_name] = {
                "color": fill,
                "hatch": hatch_name,
                "polygon_count": len(zone_gdf),
            }

        return {
            "zone_styles": zone_annotations,
            "has_hatching": bool(self.hatch_zones),
            "hatch_zones": self.hatch_zones,
        }

    def _zone_boundary_style(self, ax: plt.Axes) -> dict:
        """Generate boundary style for one zone. Pinned values override random."""
        preset = random.choice(BOUNDARY_PRESETS)

        color = self.boundary_color or preset["color"]
        weight = self.boundary_line_weight if self.boundary_line_weight is not None else preset["line_weight"]
        line_style = self.boundary_line_style or preset["line_style"]
        linewidth = line_weight_to_linewidth(weight, ax)

        return {
            "color": color,
            "linewidth": linewidth,
            "line_style": line_style,
        }
