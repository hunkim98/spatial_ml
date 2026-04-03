"""Dataset generator — orchestrates the full pipeline.

    MapConfig → MapRenderer → Augmentations → MaskRenderer → DatasetWriter

Each component is independent and testable on its own.
"""

import logging
import random
import shutil
import tempfile
from pathlib import Path

import geopandas as gpd
import pandas as pd
from PIL import Image

from .augmentations import augment
from .config import ColorJitterConfig, MapConfig, NoiseConfig
from .geo_utils import (
    annotate_colors,
    detect_zone_field,
    load_geojson,
    rotate_gdf,
)
from .legend import LegendConfig
from .mask_renderer import render_masks
from .renderer import MapRenderer
from .writer import DatasetWriter

logger = logging.getLogger(__name__)

# Basemaps available for randomization
BASEMAP_OPTIONS = [
    None,
    "Light Gray Canvas",
    "Topographic",
    # "Streets",
    # "Terrain with Labels",
]


def generate_sample(
    config: MapConfig,
    sample_id: str,
    renderer: MapRenderer,
    writer: DatasetWriter,
):
    """Generate one training sample through the full pipeline.

    Pipeline:
        1. MapRenderer.render(config) → RenderResult (image + extent)
        2. Augmentations (noise, color jitter) → augmented image
        3. MaskRenderer.render_masks() → per-color binary masks
        4. DatasetWriter.write_sample() → save everything
    """
    with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmp:
        work_dir = Path(tmp)
        mask_dir = work_dir / "masks"
        mask_dir.mkdir()

        # 1. Render map image (arcpy)
        result = renderer.render(config, work_dir)

        # 2. Augment the rendered image (PIL/numpy)
        img = Image.open(result.image_path)
        img = augment(img, config.noise, config.color_jitter, config.old_map_intensity)

        # 3. Render per-zone binary masks + pattern thumbnails (rasterio)
        mask_info = render_masks(
            result.gdf,
            result.extent,
            result.width,
            result.height,
            result.color_map,
            result.zone_field,
            mask_dir,
            map_image=img,
            hatch_zones=config.hatch_zones or None,
        )

        # 4. Write to dataset structure
        extra = {
            "rotation": round(config.rotation, 1),
            "basemap": config.basemap or "none",
            "has_labels": config.show_labels,
            "has_hatching": bool(config.hatch_zones),
            "old_map_intensity": round(config.old_map_intensity, 2),
            "opacity": round(config.opacity, 2),
            "extent_padding": round(config.extent_padding, 2),
            "page_size": f"{config.page_width}x{config.page_height}",
        }
        if config.noise.type != "none":
            extra["noise"] = {"type": config.noise.type, "strength": round(config.noise.strength, 3)}
        if config.hatch_zones:
            extra["hatch_zones"] = config.hatch_zones

        writer.write_sample(
            sample_id=sample_id,
            image=img,
            mask_info=mask_info,
            mask_dir=mask_dir,
            gdf=result.gdf,
            render_result=result,
            extra_annotation=extra,
        )


def random_config(
    gdf,
    zone_field,
    color_map,
    *,
    basemap: str | None = ...,
    opacity: float | None = None,
    extent_padding: float | None = None,
    page_size: tuple[float, float] | None = None,
    hatch_probability: float | None = None,
    show_labels: bool | None = None,
    noise_type: str | None = None,
    noise_strength: float | None = None,
    brightness: float | None = None,
    contrast: float | None = None,
    saturation: float | None = None,
    old_map_intensity: float | None = None,
    legend: LegendConfig | None = ...,
    dpi: int = 200,
) -> MapConfig:
    """Create a MapConfig. Randomizes any parameter left as None.

    Use explicit values for controlled testing, or leave as None for
    full randomization during dataset generation.

    Args:
        basemap: Basemap name. ... = random, None = no basemap.
        opacity: Zone layer opacity (0-1). None = random 0.75-1.0.
        extent_padding: Zoom level (1.0=tight, 1.4=zoomed out). None = random.
        noise_type: "none", "gaussian", "salt_pepper", "scan_lines". None = random.
        noise_strength: 0.0-1.0. None = random.
        brightness/contrast/saturation: Color jitter. None = random.
        old_map_intensity: 0.0 = modern, 0.3-0.7 = aged, 1.0 = very old. None = random.
        legend: LegendConfig. ... = random, None = no legend.
        dpi: Rendering resolution.
    """
    # Basemap: ... means random, None means no basemap
    if basemap is ...:
        basemap = random.choice(BASEMAP_OPTIONS)

    # Legend: ... means random, None means no legend
    if legend is ...:
        legend = LegendConfig()

    # Opacity
    if opacity is None:
        opacity = random.uniform(0.75, 1.0)

    # Extent padding
    if extent_padding is None:
        extent_padding = random.uniform(1.05, 1.40)

    # Page size (inches)
    _PAGE_SIZES = [
        (11, 8.5),    # letter landscape
        (8.5, 11),    # letter portrait
        (14, 8.5),    # legal landscape
        (8.5, 14),    # legal portrait
        (17, 11),     # tabloid landscape
        (11, 17),     # tabloid portrait
        (10, 10),     # square
        (12, 12),     # large square
    ]
    if page_size is None:
        page_size = random.choice(_PAGE_SIZES)

    # Old map style (mutually exclusive with noise/jitter)
    if old_map_intensity is None:
        # 30% chance of old-map style
        if random.random() < 0.3:
            old_map_intensity = random.uniform(0.2, 0.8)
        else:
            old_map_intensity = 0.0

    # Noise (ignored if old_map_intensity > 0, but set anyway for annotation)
    if noise_type is None:
        noise_type = random.choices(
            ["none", "gaussian", "salt_pepper", "scan_lines"],
            weights=[50, 25, 15, 10],
        )[0]
    if noise_strength is None:
        noise_strength = random.uniform(0.01, 0.08) if noise_type != "none" else 0
    noise = NoiseConfig(type=noise_type, strength=noise_strength)

    # Color jitter
    jitter = ColorJitterConfig(
        brightness=brightness if brightness is not None else random.uniform(-0.15, 0.15),
        contrast=contrast if contrast is not None else random.uniform(-0.15, 0.15),
        saturation=saturation if saturation is not None else random.uniform(-0.2, 0.2),
    )

    # Hatching: randomly assign some zones to have hatch patterns
    from .renderer import HATCH_STYLES
    if hatch_probability is None:
        hatch_probability = 0.25  # 25% of samples get hatching
    hatch_zones_map = {}
    if random.random() < hatch_probability:
        zone_names = list(color_map.keys())
        n_hatched = random.randint(1, max(1, len(zone_names) // 3))
        hatched = random.sample(zone_names, min(n_hatched, len(zone_names)))
        for z in hatched:
            hatch_zones_map[z] = random.choice(HATCH_STYLES)["name"]

    # Labels: 50% of samples show zone labels
    if show_labels is None:
        show_labels = random.random() < 0.5

    return MapConfig(
        gdf=gdf,
        zone_field=zone_field,
        color_map=color_map,
        basemap=basemap,
        opacity=opacity,
        show_labels=show_labels,
        hatch_zones=hatch_zones_map,
        extent_padding=extent_padding,
        page_width=page_size[0],
        page_height=page_size[1],
        legend=legend,
        noise=noise,
        color_jitter=jitter,
        old_map_intensity=old_map_intensity,
        dpi=dpi,
    )


def _build_zone_plan(
    n_zones: int, target_samples: int = 20,
) -> list[int]:
    """Build a list of target zone counts (distinct zone types per sample).

    Distribution:
      1-2 zones:     ~10% (edge cases)
      3-10 zones:    ~30% (partial maps)
      50-90% zones:  ~40% (dense partial maps)
      ALL zones:     ~20% (full maps, but with random polygon thinning)

    Uses -1 to signal "all zones" (with per-zone polygon thinning).
    Returns a list of target zone counts.
    """
    if n_zones <= 0:
        return []

    counts = []

    # 10%: 1-2 zones
    n = max(1, round(target_samples * 0.10))
    for _ in range(n):
        counts.append(random.randint(1, min(2, n_zones)))

    # 30%: 3-10 zones (partial maps)
    n = max(1, round(target_samples * 0.30))
    valid = list(range(3, min(11, n_zones + 1)))
    if not valid:
        valid = [n_zones]
    for _ in range(n):
        counts.append(random.choice(valid))

    # 40%: 50-90% of zones (dense partial)
    n = max(1, round(target_samples * 0.40))
    for _ in range(n):
        frac = random.uniform(0.5, 0.9)
        counts.append(max(1, round(n_zones * frac)))

    # 20%: ALL zones (with polygon thinning per zone)
    n = max(1, round(target_samples * 0.20))
    for _ in range(n):
        counts.append(-1)

    random.shuffle(counts)
    if len(counts) > target_samples:
        counts = counts[:target_samples]
    elif len(counts) < target_samples:
        while len(counts) < target_samples:
            counts.append(-1)

    return counts


def _sample_by_zone_count(
    gdf: gpd.GeoDataFrame, zone_field: str | None, target_zones: int,
) -> gpd.GeoDataFrame:
    """Select a connected cluster of polygons covering `target_zones` zone types.

    Strategy:
    1. Pick a random seed polygon.
    2. Grow outward adding touching neighbors (like sample_connected_subset).
    3. Stop when we have polygons covering `target_zones` distinct zone types.
    4. Randomly include 50-100% of each zone type's polygons for variety.
    """
    if zone_field and zone_field in gdf.columns:
        unique_zones = gdf[zone_field].dropna().unique().tolist()
    else:
        unique_zones = list(range(len(gdf)))

    target_zones = min(target_zones, len(unique_zones))
    if target_zones <= 0:
        return gdf.iloc[:0].copy()

    sindex = gdf.sindex
    all_indices = gdf.index.tolist()

    best_selected = None

    for _ in range(5):  # retry with different seeds
        seed_idx = random.choice(all_indices)
        selected = {seed_idx}
        frontier = {seed_idx}

        # Grow until we cover target_zones distinct types
        def count_zones(idxs):
            if zone_field and zone_field in gdf.columns:
                return gdf.loc[list(idxs), zone_field].nunique()
            return len(idxs)

        while count_zones(selected) < target_zones and frontier:
            current = random.choice(list(frontier))
            frontier.discard(current)

            geom = gdf.loc[current, "geometry"]
            candidate_idxs = list(sindex.query(geom, predicate="intersects"))
            candidate_labels = gdf.index[candidate_idxs]
            neighbors = [i for i in candidate_labels if i not in selected]

            random.shuffle(neighbors)
            for nb in neighbors:
                if gdf.loc[nb, "geometry"].intersects(geom):
                    selected.add(nb)
                    frontier.add(nb)
                if count_zones(selected) >= target_zones:
                    break

        if count_zones(selected) >= target_zones:
            # Randomly thin: keep 50-100% of polygons per zone for variety
            subset = gdf.loc[list(selected)].copy()
            if zone_field and zone_field in gdf.columns and len(subset) > target_zones:
                keep_frac = random.uniform(0.5, 1.0)
                kept = []
                for zone_type in subset[zone_field].unique():
                    zone_polys = subset[subset[zone_field] == zone_type]
                    n_keep = max(1, int(len(zone_polys) * keep_frac))
                    kept.append(zone_polys.sample(n=n_keep))
                return gpd.GeoDataFrame(pd.concat(kept))
            return subset

        if best_selected is None or count_zones(selected) > count_zones(best_selected):
            best_selected = selected

    return gdf.loc[list(best_selected)].copy()


def generate_dataset(
    source_dir: str = "data/maps",
    output_dir: str = "data/training/zoning_segmentation",
    samples_per_geojson: int = 20,
    dpi: int = 200,
    seed: int | None = None,
):
    """Generate a full segmentation dataset from all GeoJSON files.

    Each GeoJSON produces ~samples_per_geojson samples with varied zone
    counts. Samples include ALL polygons of the selected zone types,
    not a fixed polygon count.

    219 GeoJSONs × 20 samples = ~4,380 total samples.
    """
    if seed is not None:
        random.seed(seed)

    source_path = Path(source_dir)
    renderer = MapRenderer()
    writer = DatasetWriter(output_dir)

    geojson_files = sorted(source_path.rglob("*.geojson"))
    logger.info(f"Found {len(geojson_files)} GeoJSON files")

    sample_counter = 0

    for geojson_path in geojson_files:
        try:
            gdf = load_geojson(geojson_path)
            if len(gdf) < 1:
                continue
            zone_field = detect_zone_field(gdf)

            # Count distinct zone types
            if zone_field and zone_field in gdf.columns:
                n_zones = gdf[zone_field].nunique()
            else:
                n_zones = len(gdf)

            plan = _build_zone_plan(n_zones, samples_per_geojson)
            logger.info(
                f"{geojson_path.stem}: {len(gdf)} polygons, {n_zones} zones, "
                f"{len(plan)} samples planned"
            )

            for target_zones in plan:
                if target_zones == -1:
                    # All zones, but randomly thin polygons per zone
                    # Each zone keeps 30-100% of its polygons
                    if zone_field and zone_field in gdf.columns:
                        keep_frac = random.uniform(0.3, 1.0)
                        kept = []
                        for zone_type in gdf[zone_field].unique():
                            zone_polys = gdf[gdf[zone_field] == zone_type]
                            n_keep = max(1, int(len(zone_polys) * keep_frac))
                            kept.append(zone_polys.sample(n=n_keep))
                        subset = gpd.GeoDataFrame(pd.concat(kept))
                    else:
                        subset = gdf.copy()
                else:
                    subset = _sample_by_zone_count(gdf, zone_field, target_zones)
                if len(subset) == 0:
                    continue

                # Geometry rotation: 50% north-up, 50% random continuous angle
                if random.random() < 0.5:
                    angle = 0
                else:
                    angle = random.uniform(0, 360)
                rotated = rotate_gdf(subset, angle) if angle else subset

                annotated, color_map = annotate_colors(rotated, zone_field)
                if not color_map:
                    continue

                config = random_config(annotated, zone_field, color_map)
                config.rotation = angle
                config.dpi = dpi

                sample_id = f"{sample_counter:05d}"
                try:
                    generate_sample(config, sample_id, renderer, writer)
                    sample_counter += 1
                except Exception:
                    logger.exception(f"Failed sample {sample_id}")

                if sample_counter % 100 == 0:
                    logger.info(f"Progress: {sample_counter} samples generated")

        except Exception:
            logger.exception(f"Failed to process {geojson_path}")

    writer.write_metadata(
        total_samples=sample_counter, dpi=dpi,
        source_dir=str(source_dir),
        samples_per_geojson=samples_per_geojson,
    )
    logger.info(f"Dataset complete: {sample_counter} samples")
