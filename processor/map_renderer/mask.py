"""Per-zone binary mask generation via rasterio.

Rasterizes zone polygons into binary masks (255=zone, 0=not) at
the rendered image resolution. Handles post-rotation alignment
for basemap renders.
"""

import logging
from pathlib import Path

import geopandas as gpd
import numpy as np
from PIL import Image

logger = logging.getLogger(__name__)


def _rotate_and_crop(
    img: Image.Image,
    angle: float,
    original_extent: tuple[float, float, float, float],
    expanded_extent: tuple[float, float, float, float],
) -> Image.Image:
    """Apply post-render rotation + crop back to original extent.

    Computes crop fractions from the ratio of original to expanded extent,
    matching the renderer's _apply_rotation exactly.
    """
    img = img.rotate(angle, resample=Image.BICUBIC, expand=False)
    w, h = img.size

    oxmin, oymin, oxmax, oymax = original_extent
    exmin, eymin, exmax, eymax = expanded_extent
    ew = exmax - exmin
    eh = eymax - eymin

    crop_left = (oxmin - exmin) / ew if ew > 0 else 0
    crop_top = (eymax - oymax) / eh if eh > 0 else 0
    crop_right = (exmax - oxmax) / ew if ew > 0 else 0
    crop_bottom = (oymin - eymin) / eh if eh > 0 else 0

    left = int(w * crop_left)
    top = int(h * crop_top)
    right = int(w * (1 - crop_right))
    bottom = int(h * (1 - crop_bottom))
    return img.crop((left, top, right, bottom))


def generate_masks(
    gdf: gpd.GeoDataFrame,
    extent: tuple[float, float, float, float],
    final_size: tuple[int, int],
    color_map: dict[str, list[int]],
    zone_column: str,
    output_dir: Path,
    post_rotation: float = 0.0,
    raw_size: tuple[int, int] | None = None,
    original_extent: tuple[float, float, float, float] | None = None,
) -> list[dict]:
    """Generate per-zone binary masks.

    Args:
        gdf: Render GeoDataFrame (in render CRS).
        extent: Canvas extent (xmin, ymin, xmax, ymax) — expanded if post_rotation.
        final_size: (width, height) of the final image.
        color_map: {zone_name: [R, G, B]}.
        zone_column: Column name for zone labels.
        output_dir: Directory to write zone_XX/ subdirs.
        post_rotation: Raster rotation applied after render (basemap case).
        raw_size: (w, h) of image before rotation/crop.
        original_extent: Pre-expansion extent (needed for correct crop).

    Returns:
        List of mask metadata dicts.
    """
    from rasterio.features import rasterize
    from rasterio.transform import from_bounds

    output_dir.mkdir(parents=True, exist_ok=True)
    final_w, final_h = final_size

    # Rasterize at pre-rotation size if rotation was applied
    rast_w, rast_h = raw_size if (post_rotation != 0 and raw_size) else final_size
    xmin, ymin, xmax, ymax = extent
    transform = from_bounds(xmin, ymin, xmax, ymax, rast_w, rast_h)

    # Group polygons by color
    color_to_zones: dict[tuple[int, ...], list[str]] = {}
    for zone_name, rgb in color_map.items():
        color_to_zones.setdefault(tuple(rgb), []).append(zone_name)

    mask_info = []
    total_pixels = final_w * final_h

    for zone_idx, ((r, g, b), zone_names) in enumerate(color_to_zones.items()):
        zone_gdf = gdf[gdf[zone_column].isin(zone_names)]
        shapes = [(geom, 1) for geom in zone_gdf.geometry if geom is not None]
        if not shapes:
            continue

        mask = rasterize(shapes, out_shape=(rast_h, rast_w), transform=transform,
                         fill=0, dtype=np.uint8) * 255

        # Align with final image if post-rotation was applied
        if post_rotation != 0 and original_extent is not None:
            mask_img = _rotate_and_crop(
                Image.fromarray(mask, "L"), post_rotation,
                original_extent, extent,
            )
            if mask_img.size != (final_w, final_h):
                mask_img = mask_img.resize((final_w, final_h), Image.NEAREST)
            mask = np.array(mask_img)

        # Save
        zone_dir = output_dir / f"zone_{zone_idx:02d}"
        zone_dir.mkdir(parents=True, exist_ok=True)
        Image.fromarray(mask, "L").save(zone_dir / "mask.png")

        pixel_count = int(np.sum(mask > 0))
        mask_info.append({
            "zone_idx": zone_idx,
            "zone_dir": f"zone_{zone_idx:02d}",
            "names": zone_names,
            "color": [r, g, b],
            "pixel_count": pixel_count,
            "pixel_fraction": round(pixel_count / max(1, total_pixels), 4),
        })

    logger.info(f"Generated {len(mask_info)} masks in {output_dir}")
    return mask_info
