"""Pattern extraction — crop a zone sample from the postprocessed nolabel image.

Finds a square deep inside each zone polygon that avoids boundaries
and neighboring zones. Uses polylabel (pole of inaccessibility) for
non-rotated renders, or raster distance transform as fallback.

Input: the postprocessed, label-free nolabel_image from RenderResult.
"""

import logging
import random
from pathlib import Path

import numpy as np
from PIL import Image

logger = logging.getLogger(__name__)

PATTERN_SIZE = 32


def _find_safe_center_vector(zone_gdf, extent, img_w, img_h):
    """Find deepest interior point via polylabel. Returns (cx, cy, radius) in pixels."""
    from shapely.ops import polylabel

    xmin, ymin, xmax, ymax = extent
    geo_w, geo_h = xmax - xmin, ymax - ymin
    if geo_w == 0 or geo_h == 0:
        return None

    valid_geoms = [g for g in zone_gdf.geometry if g is not None and not g.is_empty]
    if not valid_geoms:
        return None
    largest = max(valid_geoms, key=lambda g: g.area)
    if largest.is_empty:
        return None
    if largest.geom_type == "MultiPolygon":
        largest = max(largest.geoms, key=lambda g: g.area)

    try:
        pole = polylabel(largest, tolerance=0.001)
    except Exception:
        pole = largest.centroid

    radius_geo = pole.distance(largest.boundary)
    safe_radius = radius_geo * 0.7  # 30% safety margin

    px_x = img_w / geo_w
    px_y = img_h / geo_h
    cx = int((pole.x - xmin) * px_x)
    cy = int((ymax - pole.y) * px_y)
    safe_r = int(safe_radius * min(px_x, px_y))

    return (cx, cy, safe_r) if safe_r >= 4 else None


def _find_safe_center_raster(mask):
    """Fallback: deepest interior point via distance transform on binary mask."""
    from scipy.ndimage import binary_erosion, distance_transform_edt

    for px in [8, 5, 3]:
        eroded = binary_erosion(mask > 0, iterations=px).astype(np.uint8) * 255
        if np.any(eroded > 0):
            break
    else:
        eroded = mask

    dist = distance_transform_edt(eroded > 0)
    if dist.max() < 2:
        return None

    cy, cx = np.unravel_index(np.argmax(dist), dist.shape)
    return (int(cx), int(cy), int(dist.max() * 0.7))


def extract_patterns(
    nolabel_image: Image.Image,
    mask_info: list[dict],
    mask_dir: Path,
    gdf=None,
    extent=None,
    zone_column: str | None = None,
    hatch_zones: dict[str, str] | None = None,
    post_rotation: float = 0.0,
):
    """Extract pattern thumbnails for all zones from the postprocessed nolabel image.

    Updates mask_info dicts in-place with 'pattern_type' field.

    Args:
        nolabel_image: Postprocessed image WITHOUT text labels.
        mask_info: List of mask metadata dicts from generate_masks().
        mask_dir: Directory containing zone_XX/mask.png files.
        gdf: Render GDF (for vector-based polylabel; ignored if post_rotation).
        extent: Canvas extent (for geo-to-pixel mapping; ignored if post_rotation).
        zone_column: Zone column name in GDF.
        hatch_zones: {zone_name: pattern_name}.
        post_rotation: If nonzero, forces raster-only method (geo mapping invalid).
    """
    img_w, img_h = nolabel_image.size

    for info in mask_info:
        zone_dir = mask_dir / info["zone_dir"]
        mask = np.array(Image.open(zone_dir / "mask.png").convert("L"))
        r, g, b = info["color"]

        # Determine hatch type
        pattern_type = "solid"
        if hatch_zones:
            for name in info["names"]:
                if name in hatch_zones:
                    pattern_type = hatch_zones[name]
                    break
        info["pattern_type"] = pattern_type

        # Resize mask to match image if needed
        if mask.shape != (img_h, img_w):
            mask = np.array(Image.fromarray(mask).resize((img_w, img_h), Image.NEAREST))

        if not np.any(mask > 0):
            Image.new("RGB", (PATTERN_SIZE, PATTERN_SIZE), (r, g, b)).save(
                zone_dir / "pattern.png")
            continue

        # Find safe center — vector method only valid without post_rotation
        center = None
        if post_rotation == 0 and gdf is not None and extent is not None and zone_column:
            zone_gdf = gdf[gdf[zone_column].isin(info["names"])]
            if len(zone_gdf) > 0:
                center = _find_safe_center_vector(zone_gdf, extent, img_w, img_h)

        if center is None:
            center = _find_safe_center_raster(mask)

        if center is None:
            Image.new("RGB", (PATTERN_SIZE, PATTERN_SIZE), (r, g, b)).save(
                zone_dir / "pattern.png")
            continue

        # Crop a square from deep inside the zone — guaranteed no other zones
        cx, cy, safe_r = center
        max_half = PATTERN_SIZE * 3  # cap so hatch lines survive downscaling
        lo = min(PATTERN_SIZE, safe_r) if pattern_type != "solid" else min(16, safe_r)
        hi = min(safe_r, max_half)
        if lo > hi:
            lo = hi
        if hi < 2:
            Image.new("RGB", (PATTERN_SIZE, PATTERN_SIZE), (r, g, b)).save(
                zone_dir / "pattern.png")
            continue

        half = random.randint(lo, hi)
        left = max(0, cx - half)
        top = max(0, cy - half)
        right = min(img_w, left + half * 2)
        bottom = min(img_h, top + half * 2)

        if right <= left or bottom <= top:
            Image.new("RGB", (PATTERN_SIZE, PATTERN_SIZE), (r, g, b)).save(
                zone_dir / "pattern.png")
            continue

        crop = nolabel_image.crop((left, top, right, bottom))
        if crop.size != (PATTERN_SIZE, PATTERN_SIZE):
            crop = crop.resize((PATTERN_SIZE, PATTERN_SIZE), Image.LANCZOS)
        crop.save(zone_dir / "pattern.png")

    logger.info(f"Extracted {len(mask_info)} patterns")
