"""Color generation for zoning map training data.

Generates random RGB colors per sample while ensuring minimum perceptual
distance between colors in the same map. This trains the model to work
with ANY color, not just a fixed palette.
"""

import math
import random


def _rgb_to_lab(r: int, g: int, b: int) -> tuple[float, float, float]:
    """Convert sRGB (0-255) to approximate CIELAB."""
    r, g, b = r / 255.0, g / 255.0, b / 255.0
    r = r / 12.92 if r <= 0.04045 else ((r + 0.055) / 1.055) ** 2.4
    g = g / 12.92 if g <= 0.04045 else ((g + 0.055) / 1.055) ** 2.4
    b = b / 12.92 if b <= 0.04045 else ((b + 0.055) / 1.055) ** 2.4
    x = 0.4124 * r + 0.3576 * g + 0.1805 * b
    y = 0.2126 * r + 0.7152 * g + 0.0722 * b
    z = 0.0193 * r + 0.1192 * g + 0.9505 * b
    x, y, z = x / 0.95047, y / 1.0, z / 1.08883

    def f(t):
        return t ** (1 / 3) if t > 0.008856 else 7.787 * t + 16 / 116

    L = 116 * f(y) - 16
    a = 500 * (f(x) - f(y))
    bv = 200 * (f(y) - f(z))
    return L, a, bv


def _color_distance(c1: tuple[int, int, int], c2: tuple[int, int, int]) -> float:
    """CIE76 perceptual distance between two RGB colors."""
    lab1 = _rgb_to_lab(*c1)
    lab2 = _rgb_to_lab(*c2)
    return math.sqrt(sum((a - b) ** 2 for a, b in zip(lab1, lab2)))


def _random_rgb() -> tuple[int, int, int]:
    """Generate a random RGB color with good visibility.

    Uses HSV space to ensure colors are saturated and bright enough
    to be clearly visible on any basemap. Full hue range (0-360),
    moderate-to-high saturation, moderate-to-high value.
    """
    import colorsys
    while True:
        h = random.random()            # 0-1 full hue range
        s = random.uniform(0.3, 1.0)   # moderate to full saturation
        v = random.uniform(0.4, 1.0)   # moderate to full brightness
        r, g, b = colorsys.hsv_to_rgb(h, s, v)
        ri, gi, bi = int(r * 255), int(g * 255), int(b * 255)
        # Skip near-white (low saturation + high value)
        if ri > 230 and gi > 230 and bi > 230:
            continue
        return (ri, gi, bi)


def generate_distinct_colors(
    n: int, min_distance: float = 25.0, max_attempts: int = 100
) -> list[tuple[int, int, int]]:
    """Generate n random RGB colors with minimum perceptual distance.

    Each new color is checked against all previously selected colors.
    If a color is too close to any existing one, a new random color is tried.

    Args:
        n: number of colors to generate.
        min_distance: minimum CIE76 deltaE between any two colors.
        max_attempts: max tries per color before relaxing the constraint.

    Returns:
        List of n (r, g, b) tuples.
    """
    colors = []
    for _ in range(n):
        best_color = None
        best_min_dist = 0

        for attempt in range(max_attempts):
            candidate = _random_rgb()

            if not colors:
                best_color = candidate
                break

            # Check distance to all existing colors
            min_dist = min(_color_distance(candidate, c) for c in colors)

            if min_dist >= min_distance:
                best_color = candidate
                break

            # Track best candidate in case we can't meet the threshold
            if min_dist > best_min_dist:
                best_min_dist = min_dist
                best_color = candidate

        colors.append(best_color)

    return colors


def build_zone_color_map(zones: list[str]) -> dict[str, list[int]]:
    """Assign random distinct RGB colors to each unique zone type.

    Colors are generated fresh each call — every training sample gets
    different colors, ensuring the model learns to work with any RGB.
    """
    unique = sorted(set(zones))
    colors = generate_distinct_colors(len(unique))
    return {zone: list(color) for zone, color in zip(unique, colors)}
