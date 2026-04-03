"""Zoning map training dataset generator.

Pipeline: MapConfig → MapRenderer → Augmentations → MaskRenderer → DatasetWriter

Usage:
    from processor.zoning_map.dataset import generate_dataset
    generate_dataset(source_dir="data/maps", output_dir="data/training/zoning_segmentation")
"""

from .config import ColorJitterConfig, MapConfig, NoiseConfig, RenderResult
from .dataset import generate_dataset, generate_sample, random_config
from .legend import LegendConfig
from .renderer import MapRenderer
from .writer import DatasetWriter

__all__ = [
    "MapConfig",
    "NoiseConfig",
    "ColorJitterConfig",
    "RenderResult",
    "LegendConfig",
    "MapRenderer",
    "DatasetWriter",
    "generate_dataset",
    "generate_sample",
    "random_config",
]
