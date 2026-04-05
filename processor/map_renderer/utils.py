"""Color, geometry, and scaling utilities."""

import matplotlib.pyplot as plt


def rgb_to_hex(rgb: list[int]) -> str:
    """[R, G, B] (0-255) -> '#rrggbb'."""
    return f"#{rgb[0]:02x}{rgb[1]:02x}{rgb[2]:02x}"


def darken(rgb: list[int], amount: float = 0.25) -> list[int]:
    """Darken an RGB color."""
    return [max(0, int(c - 255 * amount)) for c in rgb]


def lighten(rgb: list[int], amount: float = 0.25) -> list[int]:
    """Lighten an RGB color."""
    return [min(255, int(c + 255 * amount)) for c in rgb]


def line_weight_to_linewidth(weight: float, ax: plt.Axes, scale: float = 0.1) -> float:
    """Convert relative line weight (0-1) to matplotlib linewidth.

    Scales proportionally to figure width so lines look consistent
    at any zoom level.

    Args:
        weight: Relative weight 0.0-1.0.
        ax: The axes (used to get figure size).
        scale: Max linewidth as fraction of figure width. Default 0.1.
            Use smaller values (e.g. 0.05) for subtle elements like grids.
    """
    fig = ax.get_figure()
    max_lw = fig.get_figwidth() * scale
    return weight * max_lw
