"""Background layer — solid color or basemap tiles.

The background adds visual variety but never interferes with zone polygons.
Zones are always fully opaque on top.
"""

import random

import matplotlib.pyplot as plt

from ..config import MapConfig
from ..styles import BACKGROUNDS, BACKGROUND_COLORS
from .base import BaseLayer


class BackgroundLayer(BaseLayer):
    """Draws the map background.

    Args:
        background: A background name ("white", "parchment", ...),
                    a basemap provider dict, or None to randomize.
    """

    def __init__(self, background: str | dict | None = None):
        self.background = background

    def draw(self, ax: plt.Axes, config: MapConfig) -> dict:
        bg = self.background or random.choice(BACKGROUNDS)
        fig = ax.get_figure()

        if isinstance(bg, dict):
            # Basemap tiles — rendered at zorder=0 so polygons paint over them
            import contextily as cx
            cx.add_basemap(ax, source=bg, zoom="auto", zorder=0)
            bg_name = bg.get("name", "basemap")
        elif bg in BACKGROUND_COLORS:
            color = BACKGROUND_COLORS[bg]()
            ax.set_facecolor(color)
            fig.patch.set_facecolor(color)
            bg_name = bg
        else:
            ax.set_facecolor("white")
            fig.patch.set_facecolor("white")
            bg_name = "white"

        return {"background": bg_name}
