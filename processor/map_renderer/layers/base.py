"""Base class for all renderable layers."""

from abc import ABC, abstractmethod

import matplotlib.pyplot as plt

from ..config import MapConfig


class BaseLayer(ABC):
    """A single visual layer of the map.

    Each layer owns its randomization logic.
    Pass concrete values to pin; leave None to randomize.
    """

    @abstractmethod
    def draw(self, ax: plt.Axes, config: MapConfig) -> dict | None:
        """Draw this layer onto the axes. Returns annotation dict or None."""
