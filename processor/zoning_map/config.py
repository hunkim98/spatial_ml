"""Configuration dataclasses for zoning map rendering.

All variation parameters live here. No rendering logic — pure data.
"""

from dataclasses import dataclass, field
from pathlib import Path

import geopandas as gpd

from .legend import LegendConfig


@dataclass
class NoiseConfig:
    """Post-processing noise to simulate scanned/old maps."""

    type: str = "none"  # "none", "gaussian", "salt_pepper", "scan_lines"
    strength: float = 0.05  # 0.0–1.0


@dataclass
class ColorJitterConfig:
    """Random color perturbation applied to the rendered image."""

    brightness: float = 0.0  # -0.3 to 0.3
    contrast: float = 0.0  # -0.3 to 0.3
    saturation: float = 0.0  # -0.3 to 0.3


@dataclass
class MapConfig:
    """Full configuration for one training sample.

    Captures WHAT the map should look like — not HOW to render it.
    """

    # Polygon data
    gdf: gpd.GeoDataFrame = field(repr=False)
    zone_field: str | None = None
    color_map: dict[str, list[int]] = field(default_factory=dict, repr=False)

    # Basemap
    basemap: str | None = "Light Gray Canvas"

    # Zone layer appearance
    opacity: float = 0.9  # 0.0 (transparent) to 1.0 (opaque)
    show_labels: bool = False  # show zone code labels on polygons

    # Geometry transform
    rotation: float = 0.0  # degrees

    # Legend layout
    legend: LegendConfig | None = None

    # Page dimensions (inches)
    page_width: float = 11.0
    page_height: float = 8.5

    # Post-processing
    noise: NoiseConfig = field(default_factory=NoiseConfig)
    color_jitter: ColorJitterConfig = field(default_factory=ColorJitterConfig)
    old_map_intensity: float = 0.0  # 0.0 = modern, 0.3-0.7 = aged, 1.0 = very old

    # Hatching: {zone_name: style_name} for zones with hatch patterns
    # style_name: "diagonal", "horizontal", "vertical", "cross-diagonal"
    # Empty dict = all solid fills
    hatch_zones: dict[str, str] = field(default_factory=dict)

    # Map extent padding (1.0 = tight crop, 1.4 = zoomed out)
    extent_padding: float = 1.15

    # Rendering
    dpi: int = 200


@dataclass
class RenderResult:
    """Output of MapRenderer.render() — everything downstream needs."""

    image_path: Path
    width: int
    height: int
    extent: tuple[float, float, float, float]  # xmin, ymin, xmax, ymax
    color_map: dict[str, list[int]]
    zone_field: str | None
    gdf: gpd.GeoDataFrame = field(repr=False)
