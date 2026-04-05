"""Grid layer — coordinate grid overlay.

Draws evenly spaced grid lines snapped to round coordinate values,
like real map grids (e.g. every 0.01 degrees, every 100m).
Always subtler than zone boundaries.

Draw order is controlled by placement in the layer list:
- Before ZoneLayer = grid below zones
- After ZoneLayer = grid on top of zones
"""

import math
import random

import matplotlib.pyplot as plt
import numpy as np

from ..config import MapConfig
from ..utils import line_weight_to_linewidth
from .base import BaseLayer


class GridLayer(BaseLayer):
    """Draws a coordinate grid snapped to clean intervals.

    Args:
        color: Grid line color. None to randomize.
        line_weight: Relative line thickness 0.0-1.0. None to randomize.
        alpha: Grid transparency 0.0-1.0. None to randomize.
        show_tick_labels: Show coordinate values at edges. None to randomize.
    """

    def __init__(
        self,
        color: str | None = None,
        line_weight: float | None = None,
        alpha: float | None = None,
        show_tick_labels: bool | None = None,
    ):
        self.color = color
        self.line_weight = line_weight
        self.alpha = alpha
        self.show_tick_labels = show_tick_labels

    def draw(self, ax: plt.Axes, config: MapConfig) -> dict:
        color = self.color or random.choice([
            "#999999", "#aaaaaa", "#777777",
            "#6688aa",  # subtle blue, common on topo maps
        ])
        line_weight = self.line_weight if self.line_weight is not None else random.uniform(0.05, 0.25)
        alpha = self.alpha if self.alpha is not None else random.uniform(0.2, 0.5)
        show_ticks = self.show_tick_labels if self.show_tick_labels is not None else random.random() < 0.3

        linewidth = line_weight_to_linewidth(line_weight, ax, scale=0.05)

        xlim = ax.get_xlim()
        ylim = ax.get_ylim()
        interval = self._pick_interval(xlim[1] - xlim[0], ylim[1] - ylim[0])

        x_ticks = np.arange(
            math.ceil(xlim[0] / interval) * interval, xlim[1], interval
        )
        y_ticks = np.arange(
            math.ceil(ylim[0] / interval) * interval, ylim[1], interval
        )

        for x in x_ticks:
            ax.axvline(x, color=color, linewidth=linewidth, alpha=alpha)
        for y in y_ticks:
            ax.axhline(y, color=color, linewidth=linewidth, alpha=alpha)

        if show_ticks and len(x_ticks) > 0 and len(y_ticks) > 0:
            ax.set_xticks(x_ticks)
            ax.set_yticks(y_ticks)
            ax.tick_params(labelsize=4, colors=color, length=2)
        else:
            ax.set_xticks([])
            ax.set_yticks([])

        return {"has_grid": True}

    def _pick_interval(self, data_width: float, data_height: float) -> float:
        """Pick a clean grid interval that gives roughly 4-8 lines."""
        extent = min(data_width, data_height)
        if extent <= 0:
            return 1.0

        raw = extent / random.randint(4, 8)

        exponent = math.floor(math.log10(raw))
        base = 10 ** exponent
        for nice in [1, 2, 5, 10]:
            if base * nice >= raw:
                return base * nice

        return base * 10
