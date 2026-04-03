"""GeoJSON loading, zone field detection, sampling, rotation, and color annotation."""

import json
import logging
import random
from pathlib import Path

import geopandas as gpd
from shapely.affinity import rotate as shapely_rotate

from .colors import build_zone_color_map

logger = logging.getLogger(__name__)

# Known zoning column names across different city datasets
_ZONE_FIELD_CANDIDATES = [
    "ZONINGCODE", "Zoning", "ZONEDIST", "ZONE", "ZONE_CODE",
    "ZONING", "ZoneClass", "ZONE_TYPE", "CATEGORY",
]

# Columns that are geometry metadata, not zoning info
_SKIP_COLUMNS = {
    "geometry", "shape__area", "shape__length", "shape_area",
    "shape_leng", "shape_le_1", "objectid", "objectid_1", "fid",
}


def load_geojson(path: Path) -> gpd.GeoDataFrame:
    """Load a GeoJSON file and reproject to WGS84 if needed."""
    gdf = gpd.read_file(path)
    if gdf.crs and gdf.crs.to_epsg() != 4326:
        gdf = gdf.to_crs(epsg=4326)
    return gdf


def detect_zone_field(gdf: gpd.GeoDataFrame) -> str | None:
    """Find the zoning code column regardless of naming convention."""
    for col in _ZONE_FIELD_CANDIDATES:
        if col in gdf.columns:
            return col
    # Case-insensitive search for columns containing "zon"
    for col in gdf.columns:
        if "zon" in col.lower():
            return col
    # Fallback: first string column that isn't geometry metadata
    for col in gdf.columns:
        if col.lower() not in _SKIP_COLUMNS and gdf[col].dtype == "object":
            return col
    return None


def sample_connected_subset(
    gdf: gpd.GeoDataFrame, target: int, max_retries: int = 5,
) -> gpd.GeoDataFrame:
    """Sample spatially connected polygons from a GeoDataFrame.

    Picks a random seed polygon and grows outward by adding touching/nearby
    neighbors until the target count is reached. If the connected cluster
    can't reach target, retries with a different seed. Returns the best
    attempt (closest to target) — never jumps to disconnected areas.

    Polygons stay at their real coordinates for basemap alignment.
    """
    target = min(target, len(gdf))
    if target <= 0:
        return gdf.iloc[:0].copy()
    if target >= len(gdf):
        return gdf.copy()

    sindex = gdf.sindex
    all_indices = gdf.index.tolist()
    best_selected = None

    for _ in range(max_retries):
        seed_idx = random.choice(all_indices)
        selected = {seed_idx}
        frontier = {seed_idx}

        while len(selected) < target and frontier:
            current = random.choice(list(frontier))
            frontier.discard(current)

            geom = gdf.loc[current, "geometry"]
            # Find nearby polygons (touching or intersecting)
            candidate_idxs = list(sindex.query(geom, predicate="intersects"))
            candidate_labels = gdf.index[candidate_idxs]
            neighbors = [i for i in candidate_labels if i not in selected]

            random.shuffle(neighbors)
            for nb in neighbors:
                if len(selected) >= target:
                    break
                if gdf.loc[nb, "geometry"].intersects(geom):
                    selected.add(nb)
                    frontier.add(nb)

        # If we reached target, use it immediately
        if len(selected) >= target:
            return gdf.loc[list(selected)].copy()

        # Track best attempt
        if best_selected is None or len(selected) > len(best_selected):
            best_selected = selected

    # Return the best connected cluster we found
    return gdf.loc[list(best_selected)].copy()


def rotate_gdf(gdf: gpd.GeoDataFrame, angle: float) -> gpd.GeoDataFrame:
    """Rotate all geometries around the centroid of the entire collection."""
    if angle == 0:
        return gdf
    rotated = gdf.copy()
    centroid = gdf.union_all().centroid
    rotated["geometry"] = rotated["geometry"].apply(
        lambda geom: shapely_rotate(geom, angle, origin=centroid)
    )
    return rotated


def annotate_colors(
    gdf: gpd.GeoDataFrame, zone_field: str | None
) -> tuple[gpd.GeoDataFrame, dict[str, list[int]]]:
    """Add `zone_color` RGB property to each feature based on its zone type."""
    gdf = gdf.copy()
    if zone_field and zone_field in gdf.columns:
        zones = gdf[zone_field].fillna("UNKNOWN").astype(str).tolist()
    else:
        zones = [f"ZONE_{i}" for i in range(len(gdf))]
        zone_field = "zone_label"
        gdf[zone_field] = zones

    color_map = build_zone_color_map(zones)
    gdf["zone_color"] = [json.dumps(color_map[z]) for z in zones]
    return gdf, color_map
