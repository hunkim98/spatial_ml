"""Dataset generator using geopandas renderer — no arcpy dependency.

Same output structure as the arcpy pipeline:
    images/{id}.png, masks/{id}/zone_XX/mask.png+pattern.png,
    geojsons/{id}.geojson, annotations/{id}.json
"""

import logging
import random
import tempfile
from pathlib import Path

import geopandas as gpd
import pandas as pd
from PIL import Image

from processor.zoning_map.augmentations import augment
from processor.zoning_map.colors import build_zone_color_map
from processor.zoning_map.config import ColorJitterConfig, MapConfig, NoiseConfig
from processor.zoning_map.geo_utils import (
    annotate_colors, detect_zone_field, load_geojson, rotate_gdf,
)
from processor.zoning_map.legend import LegendConfig
from processor.zoning_map.mask_renderer import render_masks
from processor.zoning_map.writer import DatasetWriter

from .renderer import (
    BACKGROUND_STYLES, HATCH_PATTERNS,
    render_map, render_pattern_swatch,
)

logger = logging.getLogger(__name__)

# Basemaps that work without API keys
BASEMAP_PROVIDERS = [
    None,  # no basemap (use background color)
    "OpenTopoMap",
    "CartoDB.Positron",
    "CartoDB.DarkMatter",
    "Esri.WorldTopoMap",
    "Esri.WorldTerrain",
]


def _get_basemap_provider(name: str | None):
    """Resolve a basemap name to a contextily provider."""
    if name is None:
        return None
    import contextily as cx
    parts = name.split(".")
    provider = cx.providers
    for p in parts:
        provider = provider[p]
    return provider


def random_config(
    gdf, zone_field, color_map,
    *,
    basemap: str | None = ...,
    background: str | None = None,
    opacity: float | None = None,
    extent_padding: float | None = None,
    page_size: tuple[float, float] | None = None,
    hatch_probability: float | None = None,
    show_labels: bool | None = None,
    old_map_intensity: float | None = None,
    noise_type: str | None = None,
    noise_strength: float | None = None,
    brightness: float | None = None,
    contrast: float | None = None,
    saturation: float | None = None,
    dpi: int = 200,
) -> tuple[MapConfig, dict]:
    """Create a MapConfig + rendering kwargs with randomized parameters.

    Returns (config, render_kwargs) tuple.
    """
    if basemap is ...:
        basemap = random.choice(BASEMAP_PROVIDERS)
    if background is None:
        background = random.choice(BACKGROUND_STYLES) if basemap is None else "white"
    if opacity is None:
        opacity = random.uniform(0.6, 0.95)
    if extent_padding is None:
        # Tighter crops: 50% chance of very tight (polygons may cut at edges)
        if random.random() < 0.5:
            extent_padding = random.uniform(0.85, 1.05)  # tight — polygons cut at edges
        else:
            extent_padding = random.uniform(1.05, 1.25)   # normal padding
    if show_labels is None:
        show_labels = random.random() < 0.5
    if old_map_intensity is None:
        old_map_intensity = random.uniform(0.2, 0.8) if random.random() < 0.3 else 0.0

    _PAGE_SIZES = [
        (11, 8.5), (8.5, 11), (14, 8.5), (8.5, 14),
        (17, 11), (11, 17), (10, 10), (12, 12),
        (16, 8), (8, 16),   # wide/tall
        (20, 10), (10, 20), # very wide/tall
    ]
    if page_size is None:
        page_size = random.choice(_PAGE_SIZES)

    # Hatching
    if hatch_probability is None:
        hatch_probability = 0.40
    hatch_zones = {}
    if random.random() < hatch_probability:
        zone_names = list(color_map.keys())
        n_hatched = random.randint(1, max(1, len(zone_names) // 2))
        hatched = random.sample(zone_names, min(n_hatched, len(zone_names)))
        for z in hatched:
            hatch_zones[z] = random.choice(HATCH_PATTERNS)["name"]

    # Noise / jitter
    if noise_type is None:
        noise_type = random.choices(
            ["none", "gaussian", "salt_pepper"], weights=[60, 25, 15]
        )[0]
    if noise_strength is None:
        noise_strength = random.uniform(0.01, 0.05) if noise_type != "none" else 0
    noise = NoiseConfig(type=noise_type, strength=noise_strength)

    jitter = ColorJitterConfig(
        brightness=brightness if brightness is not None else random.uniform(-0.15, 0.15),
        contrast=contrast if contrast is not None else random.uniform(-0.15, 0.15),
        saturation=saturation if saturation is not None else random.uniform(-0.2, 0.2),
    )

    config = MapConfig(
        gdf=gdf,
        zone_field=zone_field,
        color_map=color_map,
        basemap=basemap,
        opacity=opacity,
        show_labels=show_labels,
        hatch_zones=hatch_zones,
        extent_padding=extent_padding,
        page_width=page_size[0],
        page_height=page_size[1],
        noise=noise,
        color_jitter=jitter,
        old_map_intensity=old_map_intensity,
        dpi=dpi,
    )

    # Extra kwargs for the geopandas renderer
    render_kwargs = {
        "background": background,
        "grid_lines": random.random() < 0.15,
        "contour_lines": random.random() < 0.15,
    }

    return config, render_kwargs


def generate_sample(
    config: MapConfig,
    render_kwargs: dict,
    sample_id: str,
    writer: DatasetWriter,
):
    """Generate one training sample using geopandas renderer."""
    with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmp:
        work_dir = Path(tmp)
        mask_dir = work_dir / "masks"
        mask_dir.mkdir()

        basemap_provider = _get_basemap_provider(config.basemap) if config.basemap else None

        # LAYERED RENDERING:
        # Layer 1: Map (zones + basemap + hatching, NO labels)
        # Layer 2: Text labels on transparent background
        # Merge: training image = Layer 1 + Layer 2
        # Patterns: crop from Layer 1 (clean, no text)
        # Masks: from GeoJSON (same extent as Layer 1)

        from copy import copy

        # Layer 1: Map without labels, NO boundaries (clean for pattern extraction)
        config_map = copy(config)
        config_map.show_labels = False
        map_path = work_dir / "map_layer.png"
        result_map = render_map(
            config_map, map_path, dpi=config.dpi,
            basemap_provider=basemap_provider,
            boundary_style="none",
            contour_lines=render_kwargs.get("contour_lines", False),
            grid_lines=render_kwargs.get("grid_lines", False),
        )

        # Layer 2: Text labels on transparent background (same extent/size)
        if config.show_labels:
            config_text = copy(config)
            config_text.show_labels = True
            # Render with transparent bg — just the labels
            text_path = work_dir / "text_layer.png"
            result_text = render_map(
                config_text, text_path, dpi=config.dpi,
                basemap_provider=basemap_provider,
                **render_kwargs,
            )
            # The text layer IS the full render with labels — we'll use it as the training image
            result = result_text
        else:
            result = result_map

        # The map layer's extent and CRS — use this for EVERYTHING
        map_extent = result_map.extent

        # If basemap was used, GDF needs to be in 3857 to match the map
        if basemap_provider:
            gdf_for_masks = config.gdf.to_crs(epsg=3857)
        else:
            gdf_for_masks = config.gdf

        result.gdf = gdf_for_masks
        result_map.gdf = gdf_for_masks

        # Augment BOTH layers with the same transforms
        img_map = Image.open(result_map.image_path).convert("RGB")
        img_map = augment(img_map, config.noise, config.color_jitter, config.old_map_intensity)

        if config.show_labels:
            img = Image.open(result.image_path).convert("RGB")
            img = augment(img, config.noise, config.color_jitter, config.old_map_intensity)
        else:
            img = img_map

        # Everything uses map_extent (same CRS as map image)
        map_w, map_h = img_map.size
        mask_info = render_masks(
            gdf_for_masks, map_extent, map_w, map_h,
            config.color_map, config.zone_field, mask_dir,
            map_image=img_map,
            hatch_zones=config.hatch_zones or None,
        )

        # 5. Random edge crop (40% chance) — crop 5-15% from random edges
        #    so the model doesn't learn that edges are always empty
        edge_cropped = False
        if random.random() < 0.4:
            w, h = img.size
            crop_left = int(w * random.uniform(0, 0.12)) if random.random() < 0.5 else 0
            crop_top = int(h * random.uniform(0, 0.12)) if random.random() < 0.5 else 0
            crop_right = w - (int(w * random.uniform(0, 0.12)) if random.random() < 0.5 else 0)
            crop_bottom = h - (int(h * random.uniform(0, 0.12)) if random.random() < 0.5 else 0)

            if crop_right > crop_left + 100 and crop_bottom > crop_top + 100:
                img = img.crop((crop_left, crop_top, crop_right, crop_bottom))
                # Crop all masks the same way
                for info in mask_info:
                    zone_dir = mask_dir / info["zone_dir"]
                    mask_path = zone_dir / "mask.png"
                    if mask_path.exists():
                        m = Image.open(mask_path)
                        m = m.crop((crop_left, crop_top, crop_right, crop_bottom))
                        m.save(str(mask_path))
                edge_cropped = True

        # 6. Write
        extra = {
            "rotation": round(config.rotation, 1),
            "basemap": config.basemap or "none",
            "background": render_kwargs.get("background", "white"),
            "has_labels": config.show_labels,
            "has_hatching": bool(config.hatch_zones),
            "has_grid": render_kwargs.get("grid_lines", False),
            "has_contours": render_kwargs.get("contour_lines", False),
            "old_map_intensity": round(config.old_map_intensity, 2),
            "opacity": round(config.opacity, 2),
            "extent_padding": round(config.extent_padding, 2),
            "edge_cropped": edge_cropped,
            "page_size": f"{config.page_width}x{config.page_height}",
            "renderer": "geopandas",
        }
        if config.hatch_zones:
            extra["hatch_zones"] = config.hatch_zones

        writer.write_sample(
            sample_id=sample_id,
            image=img,
            mask_info=mask_info,
            mask_dir=mask_dir,
            gdf=config.gdf,
            render_result=result,
            extra_annotation=extra,
        )
