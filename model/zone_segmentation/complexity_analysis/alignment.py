"""Utilities for aligning GeoJSON data to rendered map images.

Uses annotation metadata (render_extent, render_crs, rotation, rotation_center)
to transform GeoJSON coordinates so they match the rendered image exactly.

Usage:
    from alignment import align_geojson_to_image, count_visible_features, geo_to_pixel

    ann = json.load(open("annotations/00000.json"))
    gdf = gpd.read_file("geojsons/00000.geojson")

    aligned_gdf, viewport = align_geojson_to_image(ann, gdf)
    stats = count_visible_features(aligned_gdf, viewport, ann["zone_column"])
    sx, sy, ox, oy = geo_to_pixel(viewport, ann["image_width"], ann["image_height"])
"""

import json
from pathlib import Path

import geopandas as gpd
from shapely.affinity import rotate as shapely_rotate
from shapely.geometry import Point, box


def align_geojson_to_image(
    ann: dict, gdf: gpd.GeoDataFrame
) -> tuple[gpd.GeoDataFrame, tuple[float, float, float, float]]:
    """Align a GeoJSON GeoDataFrame to the rendered image.

    Transforms the GDF to the render CRS and applies the same rotation
    used during rendering, so polygons match the image pixel-perfectly.

    Args:
        ann: Annotation dict (from annotations/{id}.json). Must contain
             render_extent, render_crs, rotation, rotation_center.
        gdf: GeoDataFrame loaded from the corresponding geojson file.

    Returns:
        (aligned_gdf, viewport) where:
        - aligned_gdf: GDF in render CRS with rotation applied
        - viewport: (xmin, ymin, xmax, ymax) in render CRS
    """
    render_extent = ann["render_extent"]
    render_crs = ann.get("render_crs", "EPSG:4326")
    rotation = ann.get("rotation", 0.0)
    rotation_center = ann.get("rotation_center")

    # Transform to render CRS
    if render_crs and render_crs != "EPSG:4326":
        aligned = gdf.to_crs(render_crs)
    else:
        aligned = gdf.copy()

    # Rotate around the exact center used during rendering
    if rotation != 0 and rotation_center:
        center_point = Point(rotation_center[0], rotation_center[1])
        aligned["geometry"] = aligned["geometry"].apply(
            lambda geom: shapely_rotate(geom, rotation, origin=center_point)
            if geom is not None
            else None
        )

    return aligned, tuple(render_extent)


def count_visible_features(
    gdf: gpd.GeoDataFrame,
    viewport: tuple[float, float, float, float],
    zone_col: str,
) -> dict:
    """Count polygons, lines, and zones visible within the viewport.

    Clips geometries to the viewport and counts features by type.

    Args:
        gdf: Aligned GeoDataFrame (output of align_geojson_to_image).
        viewport: (xmin, ymin, xmax, ymax) in render CRS.
        zone_col: Name of the zone column.

    Returns:
        Dict with keys: n_zones, n_polygons, n_lines, n_features.
    """
    xmin, ymin, xmax, ymax = viewport
    clip_box = box(xmin, ymin, xmax, ymax)

    clipped = gdf[gdf.geometry.notna()].copy()
    clipped["geometry"] = clipped["geometry"].intersection(clip_box)
    clipped = clipped[~clipped.geometry.is_empty]

    n_polygons = sum(1 for g in clipped.geometry if "Polygon" in g.geom_type)
    n_lines = sum(1 for g in clipped.geometry if "Line" in g.geom_type)
    n_zones = clipped[zone_col].nunique() if zone_col in clipped.columns else 0

    return {
        "n_zones": n_zones,
        "n_polygons": n_polygons,
        "n_lines": n_lines,
        "n_features": len(clipped),
    }


def geo_to_pixel(
    viewport: tuple[float, float, float, float],
    img_w: int,
    img_h: int,
) -> tuple[float, float, float, float]:
    """Compute affine parameters to convert geo coordinates to pixel coordinates.

    Args:
        viewport: (xmin, ymin, xmax, ymax) in render CRS.
        img_w: Image width in pixels.
        img_h: Image height in pixels.

    Returns:
        (scale_x, scale_y, offset_x, offset_y) where:
            pixel_x = (geo_x - offset_x) * scale_x
            pixel_y = (offset_y - geo_y) * scale_y
    """
    xmin, ymin, xmax, ymax = viewport
    scale_x = img_w / (xmax - xmin)
    scale_y = img_h / (ymax - ymin)
    return scale_x, scale_y, xmin, ymax


def load_sample(
    data_dir: str | Path,
    sample_id: str,
) -> tuple[dict, gpd.GeoDataFrame]:
    """Load annotation and GeoJSON for a sample.

    Args:
        data_dir: Root dataset directory (contains annotations/, geojsons/).
        sample_id: Sample ID string (e.g. "00000").

    Returns:
        (ann, gdf) tuple.
    """
    data_dir = Path(data_dir)
    with open(data_dir / "annotations" / f"{sample_id}.json") as f:
        ann = json.load(f)
    gdf = gpd.read_file(data_dir / "geojsons" / f"{sample_id}.geojson")
    return ann, gdf
