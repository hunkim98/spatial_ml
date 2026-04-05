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


def _find_safe_crop_region(
    gdf_zone: gpd.GeoDataFrame,
    extent: tuple[float, float, float, float],
    img_w: int,
    img_h: int,
) -> tuple[int, int, int] | None:
    """Use vector geometry to find the largest safe crop square inside a zone.

    Uses polylabel to find the deepest interior point, then computes the
    inscribed radius from the ORIGINAL (not shrunk) polygon boundary.
    Applies a 30% safety margin to the radius to avoid any boundary
    rendering artifacts (anti-aliasing, stroke width, neighboring zone overlap).

    Returns (center_x_px, center_y_px, safe_radius_px) or None if too small.
    """
    from shapely.ops import polylabel

    xmin, ymin, xmax, ymax = extent
    geo_w = xmax - xmin
    geo_h = ymax - ymin
    if geo_w == 0 or geo_h == 0:
        return None

    # Find the largest polygon in this zone
    largest = max(gdf_zone.geometry, key=lambda g: g.area)
    if largest.is_empty:
        return None

    # Handle MultiPolygon — use the largest part
    if largest.geom_type == "MultiPolygon":
        largest = max(largest.geoms, key=lambda g: g.area)

    # Find pole of inaccessibility on the original polygon
    try:
        pole = polylabel(largest, tolerance=0.001)
    except Exception:
        pole = largest.centroid

    # Inscribed radius = distance from pole to nearest boundary edge
    radius_geo = pole.distance(largest.boundary)

    # Apply 30% safety margin — keeps crop well inside the zone,
    # avoids boundary strokes, anti-aliasing, and neighboring zone bleed
    safe_radius_geo = radius_geo * 0.7

    # Convert to pixel coordinates
    px_per_geo_x = img_w / geo_w
    px_per_geo_y = img_h / geo_h
    scale = min(px_per_geo_x, px_per_geo_y)

    cx_px = int((pole.x - xmin) * px_per_geo_x)
    cy_px = int((ymax - pole.y) * px_per_geo_y)
    safe_radius_px = int(safe_radius_geo * scale)

    if safe_radius_px < 4:
        return None

    return (cx_px, cy_px, safe_radius_px)


def _extract_pattern(
    map_image: Image.Image,
    zone_gdf: gpd.GeoDataFrame | None,
    extent: tuple[float, float, float, float] | None,
    mask: np.ndarray,
    zone_color: tuple[int, int, int],
    size: int = PATTERN_SIZE,
    is_hatched: bool = False,
    hatch_pattern: str | None = None,
) -> tuple[Image.Image, tuple | None]:
    """Crop a pattern from the zone layer (no text, consistent CRS).

    Uses polylabel to find the deepest interior, crops from the actual
    rendered zone layer, and masks out non-zone pixels with median fill.
    """
    import random as _rng

    img_w, img_h = map_image.size
    h, w = img_h, img_w

    if not np.any(mask > 0):
        return Image.new("RGB", (size, size), zone_color), None

    # Resize mask to match image if needed
    mask_h, mask_w = mask.shape
    if mask_w != img_w or mask_h != img_h:
        mask_r = np.array(Image.fromarray(mask).resize((img_w, img_h), Image.NEAREST))
    else:
        mask_r = mask

    # Vector method: find safe crop region
    crop_region = None
    if zone_gdf is not None and extent is not None and len(zone_gdf) > 0:
        crop_region = _find_safe_crop_region(zone_gdf, extent, w, h)

    if crop_region is not None:
        cx_px, cy_px, safe_r = crop_region
        # Cap crop size so patterns survive downscaling to `size x size`.
        # Hatching lines are ~2-3px; at >3x downscale they vanish.
        max_half = size * 3  # e.g. 96px for size=32 → 2x2 crop → lines stay ≥1px
        if is_hatched:
            min_half = min(size, safe_r)          # at least 1:1 with output
            half = _rng.randint(min_half, min(safe_r, max_half))
        else:
            min_half = min(16, safe_r)
            half = _rng.randint(min_half, min(safe_r, max_half))
    else:
        # Fallback: raster distance transform
        from scipy.ndimage import binary_erosion, distance_transform_edt
        for px in [8, 5, 3]:
            eroded = binary_erosion(mask_r > 0, iterations=px).astype(np.uint8) * 255
            if np.any(eroded > 0):
                break
        else:
            eroded = mask_r
        dist = distance_transform_edt(eroded > 0)
        max_dist = dist.max()
        if max_dist < 2:
            return Image.new("RGB", (size, size), zone_color), None
        cy_px, cx_px = np.unravel_index(np.argmax(dist), dist.shape)
        safe_r = int(max_dist * 0.7)
        max_half = size * 3
        half = max(4, _rng.randint(4, min(max(4, safe_r), max_half)))

    top = max(0, cy_px - half)
    left = max(0, cx_px - half)
    bottom = min(h, top + half * 2)
    right = min(w, left + half * 2)

    crop = map_image.crop((left, top, right, bottom))
    crop_arr = np.array(crop)

    # Mask out non-zone pixels (neighbor bleed from anti-aliasing)
    mask_region = mask_r[top:bottom, left:right]
    if mask_region.shape[0] == crop_arr.shape[0] and mask_region.shape[1] == crop_arr.shape[1]:
        outside = mask_region == 0
        if outside.any():
            zone_pixels = crop_arr[~outside]
            if len(zone_pixels) > 0:
                fill = np.median(zone_pixels, axis=0).astype(np.uint8)
                crop_arr[outside] = fill
                crop = Image.fromarray(crop_arr)

    if crop.size[0] != size or crop.size[1] != size:
        crop = crop.resize((size, size), Image.LANCZOS)

    return crop, (left, top, right, bottom)


def _generate_pattern_swatch(
    color: tuple[int, int, int],
    pattern_type: str = "solid",
    size: int = PATTERN_SIZE,
) -> Image.Image:
    """Generate a clean pattern swatch — just fill color + optional hatch lines.

    No text, no basemap, no boundary artifacts. This is what the model
    uses as a visual query to identify the target zone.
    """
    from PIL import ImageDraw

    img = Image.new("RGB", (size, size), color)

    if pattern_type == "solid":
        return img

    draw = ImageDraw.Draw(img)
    line_color = (
        max(0, color[0] - 60),
        max(0, color[1] - 60),
        max(0, color[2] - 60),
    )
    spacing = max(3, size // 8)
    width = max(1, size // 16)

    if pattern_type in ("diagonal", "cross-diagonal"):
        for i in range(-size, size * 2, spacing):
            draw.line([(i, 0), (i + size, size)], fill=line_color, width=width)
    if pattern_type in ("cross-diagonal",):
        for i in range(-size, size * 2, spacing):
            draw.line([(i + size, 0), (i, size)], fill=line_color, width=width)
    elif pattern_type == "horizontal":
        for y in range(0, size, spacing):
            draw.line([(0, y), (size, y)], fill=line_color, width=width)
    elif pattern_type == "vertical":
        for x in range(0, size, spacing):
            draw.line([(x, 0), (x, size)], fill=line_color, width=width)
    elif pattern_type == "crosshatch":
        for y in range(0, size, spacing):
            draw.line([(0, y), (size, y)], fill=line_color, width=width)
        for x in range(0, size, spacing):
            draw.line([(x, 0), (x, size)], fill=line_color, width=width)
    elif pattern_type == "striped":
        for i in range(-size, size * 2, spacing):
            draw.line([(i, 0), (i + size, size)], fill=line_color, width=width)
    elif pattern_type in ("dots_sparse", "dots_medium", "dots_dense"):
        dot_spacing = {"dots_sparse": 8, "dots_medium": 5, "dots_dense": 3}
        sp = dot_spacing.get(pattern_type, 5)
        dot_r = max(1, size // 20)
        for y in range(sp, size, sp):
            for x in range(sp, size, sp):
                draw.ellipse(
                    [x - dot_r, y - dot_r, x + dot_r, y + dot_r],
                    fill=line_color,
                )
    elif pattern_type == "stipple":
        import random as _rng
        n_dots = size * size // 20
        dot_r = max(1, size // 24)
        for _ in range(n_dots):
            x, y = _rng.randint(0, size - 1), _rng.randint(0, size - 1)
            draw.ellipse([x - dot_r, y - dot_r, x + dot_r, y + dot_r], fill=line_color)
    elif pattern_type == "diamond":
        for i in range(-size, size * 2, spacing):
            draw.line([(i, 0), (i + size, size)], fill=line_color, width=width)
            draw.line([(i + size, 0), (i, size)], fill=line_color, width=width)

    return img


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
    debug_visualizations: bool = False,
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

        # Determine pattern type for this zone
        pattern_type = "solid"
        if hatch_zones:
            for name in zone_names:
                if name in hatch_zones:
                    pattern_type = hatch_zones[name]
                    break

        # Extract pattern — render this zone ALONE to avoid neighbor bleed
        if map_image is not None:
            # Get the zone's GeoDataFrame subset for vector-based crop
            if zone_field and zone_field in gdf.columns:
                zone_gdf_for_crop = gdf[gdf[zone_field].isin(zone_names)]
            else:
                zone_gdf_for_crop = None

            pattern, crop_box = _extract_pattern(
                map_image, zone_gdf_for_crop, extent, mask, (r, g, b),
                is_hatched=(pattern_type != "solid"),
                hatch_pattern=pattern_type,
            )
            pattern.save(zone_dir / "pattern.png")

            # Generate mask_pattern.png — debug visualization only
            if debug_visualizations:
                img_w_actual, img_h_actual = map_image.size
                try:
                    from rasterio.features import rasterize as _rast
                    from rasterio.transform import from_bounds as _fb
                    _ext = extent
                    _tf = _fb(_ext[0], _ext[1], _ext[2], _ext[3], img_w_actual, img_h_actual)
                    _shapes = [(g, 1) for g in zone_gdf_for_crop.geometry if g is not None]
                    mask_vis = _rast(_shapes, out_shape=(img_h_actual, img_w_actual),
                                     transform=_tf, fill=0, dtype=np.uint8) * 255
                except Exception:
                    mask_vis = np.zeros((img_h_actual, img_w_actual), dtype=np.uint8)

                mp = np.zeros((img_h_actual, img_w_actual, 3), dtype=np.uint8)
                mp[mask_vis > 0] = [255, 255, 255]
                if crop_box:
                    cl, ct, cr, cb = crop_box
                    ct, cb = max(0, ct), min(img_h_actual, cb)
                    cl, cr = max(0, cl), min(img_w_actual, cr)
                    mp[ct:cb, cl:cr, 0] = np.minimum(
                        mp[ct:cb, cl:cr, 0].astype(int) + 200, 255).astype(np.uint8)
                    mp[ct:cb, cl:cr, 1] = (mp[ct:cb, cl:cr, 1] * 0.3).astype(np.uint8)
                    mp[ct:cb, cl:cr, 2] = (mp[ct:cb, cl:cr, 2] * 0.3).astype(np.uint8)
                Image.fromarray(mp).save(zone_dir / "mask_pattern.png")

        mask_info.append({
            "zone_dir": zone_dir_name,
            "color": [r, g, b],
            "names": zone_names,
            "pixel_count": int(np.sum(mask > 0)),
            "pattern_type": pattern_type,
        })

    logger.info(f"Rendered {len(mask_info)} masks to {output_dir}")
    return mask_info
