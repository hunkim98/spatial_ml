"""Zoning map training dataset generator.

Pipeline: MapConfig → MapRenderer → Augmentations → MaskRenderer → DatasetWriter

Usage:
    from processor.zoning_map.dataset import generate_dataset
    generate_dataset(source_dir="data/maps", output_dir="data/training/zoning_segmentation")
"""

from .config import ColorJitterConfig, MapConfig, NoiseConfig, RenderResult
from .legend import LegendConfig
from .writer import DatasetWriter

# Lazy imports for arcpy-dependent modules (MapRenderer, dataset functions)
# Import them explicitly when needed:
#   from processor.zoning_map.dataset import generate_dataset
#   from processor.zoning_map.renderer import MapRenderer

__all__ = [
    "MapConfig",
    "NoiseConfig",
    "ColorJitterConfig",
    "RenderResult",
    "LegendConfig",
    "DatasetWriter",
]
