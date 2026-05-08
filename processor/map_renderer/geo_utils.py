"""GeoJSON utility functions for zone field detection."""

import geopandas as gpd

# Known zoning column names across different city datasets
_ZONE_FIELD_CANDIDATES = [
    "ZONINGCODE", "Zoning", "ZONEDIST", "ZONE", "ZONE_CODE",
    "ZONING", "ZoneClass", "ZONE_TYPE", "CATEGORY",
    # Additional columns found across US city datasets
    "PROP_CLASS", "ZD", "zn_class", "LAYER", "ZCODE",
    "REGULATIONCLASSIFICATION", "CODE", "ZNG_CODE",
    "CITY_ZN_CO", "SCAG_ZN_CO", "CITY_GP_CO", "TYPE",
    "Legend", "Name",
]

# Columns that are geometry metadata, not zoning info
_SKIP_COLUMNS = {
    "geometry", "shape__area", "shape__length", "shape_area",
    "shape_leng", "shape_le_1", "shape_le_2", "shape.area", "shape.len",
    "shape.starea()", "shape.stlength()",
    "objectid", "objectid_1", "fid", "globalid",
    "created_user", "created_date", "last_edited_user", "last_edited_date",
    "distribution_policy", "data_security",
}


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
