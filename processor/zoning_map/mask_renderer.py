"""Rasterize GeoJSON polygons into per-zone binary masks + pattern thumbnails.

Each unique zone color produces:
  - mask.png: binary mask (255=zone, 0=not) at map frame resolution
  - pattern.png: small crop from the rendered map showing the zone's visual pattern

Output structure per sample:
    masks/{sample_id}/zone_00/mask.png
    masks/{sample_id}/zone_00/pattern.png
    masks/{sample_id}/zone_01/mask.png
    ...
"""

import json
import logging
from pathlib import Path

import geopandas as gpd
import numpy as np
from PIL import Image

logger = logging.getLogger(__name__)

PATTERN_SIZE = 32  # thumbnail size — enough to capture hatch/dot patterns


def _extract_pattern(
    map_image: Image.Image,
    mask: np.ndarray,
    zone_color: tuple[int, int, int],
    size: int = PATTERN_SIZE,
) -> Image.Image:
    """Crop a clean pattern thumbnail entirely inside the zone.

    Uses a distance transform to find the point deepest inside the zone,
    then crops a size×size patch centered there. If the zone is too small
    to fit a full crop, uses the largest square that fits. Falls back to
    a solid color swatch only if the zone has no interior area at all.
    """
    from scipy.ndimage import distance_transform_edt

    h, w = mask.shape
    if not np.any(mask > 0):
        return Image.new("RGB", (size, size), zone_color)

    dist = distance_transform_edt(mask > 0)
    max_dist = dist.max()

    if max_dist < 1:
        # Zone is a single pixel line — use solid swatch as last resort
        return Image.new("RGB", (size, size), zone_color)

    # Find the deepest interior point
    cy, cx = np.unravel_index(np.argmax(dist), dist.shape)

    # Crop at whatever fits inside the zone, then resize to target
    # Even a 4x4 crop will be upscaled — blurry but correct color/pattern
    usable = int(min(size, max_dist * 2))
    usable = max(usable, 4)  # minimum 4x4 crop

    half = usable // 2
    top = max(0, cy - half)
    left = max(0, cx - half)
    bottom = min(h, top + usable)
    right = min(w, left + usable)

    crop = map_image.crop((left, top, right, bottom))

    # Resize to target size if the crop was smaller
    if crop.size[0] != size or crop.size[1] != size:
        crop = crop.resize((size, size), Image.LANCZOS)

    return crop


def render_masks(
    gdf: gpd.GeoDataFrame,
    extent: tuple[float, float, float, float],
    width: int,
    height: int,
    color_map: dict[str, list[int]],
    zone_field: str | None,
    output_dir: Path,
    map_image: Image.Image | None = None,
    hatch_zones: dict[str, str] | None = None,
):
    """Render per-zone binary masks and pattern thumbnails.

    Args:
        gdf: GeoDataFrame with zone polygons.
        extent: (xmin, ymin, xmax, ymax) geographic extent of the map frame.
        width: output mask width in pixels.
        height: output mask height in pixels.
        color_map: {zone_name: [r, g, b]} mapping.
        zone_field: column name containing zone labels.
        output_dir: directory to write zone_XX/ subdirectories.
        map_image: rendered map image (PIL) for extracting pattern thumbnails.
            If None, pattern thumbnails are skipped.

    Returns:
        List of dicts with mask metadata.
    """
    from rasterio.features import rasterize
    from rasterio.transform import from_bounds

    output_dir.mkdir(parents=True, exist_ok=True)

    xmin, ymin, xmax, ymax = extent
    transform = from_bounds(xmin, ymin, xmax, ymax, width, height)

    # Group polygons by zone color
    color_to_zones = {}
    for zone_name, rgb in color_map.items():
        key = tuple(rgb)
        if key not in color_to_zones:
            color_to_zones[key] = []
        color_to_zones[key].append(zone_name)

    mask_info = []

    for zone_idx, ((r, g, b), zone_names) in enumerate(color_to_zones.items()):
        # Select polygons belonging to this color
        if zone_field and zone_field in gdf.columns:
            zone_gdf = gdf[gdf[zone_field].isin(zone_names)]
        else:
            target = json.dumps([r, g, b])
            zone_gdf = gdf[gdf["zone_color"] == target]

        if zone_gdf.empty:
            continue

        shapes = [(geom, 1) for geom in zone_gdf.geometry if geom is not None]
        if not shapes:
            continue

        # Rasterize
        mask = rasterize(
            shapes,
            out_shape=(height, width),
            transform=transform,
            fill=0,
            dtype=np.uint8,
        )
        mask = mask * 255

        # Create zone directory
        zone_dir_name = f"zone_{zone_idx:02d}"
        zone_dir = output_dir / zone_dir_name
        zone_dir.mkdir(parents=True, exist_ok=True)

        # Save mask
        mask_img = Image.fromarray(mask, mode="L")
        mask_img.save(zone_dir / "mask.png")

        # Extract and save pattern thumbnail
        if map_image is not None:
            pattern = _extract_pattern(map_image, mask, (r, g, b))
            pattern.save(zone_dir / "pattern.png")

        # Determine pattern type for this zone
        pattern_type = "solid"
        if hatch_zones:
            for name in zone_names:
                if name in hatch_zones:
                    pattern_type = hatch_zones[name]
                    break

        mask_info.append({
            "zone_dir": zone_dir_name,
            "color": [r, g, b],
            "names": zone_names,
            "pixel_count": int(np.sum(mask > 0)),
            "pattern_type": pattern_type,
        })

    logger.info(f"Rendered {len(mask_info)} masks to {output_dir}")
    return mask_info
