"""
Simplified FeatureServerDownloader (GeoPandas integrated)
---------------------------------------------------------
Downloads all layers from an ArcGIS FeatureServer,
handles pagination or objectId chunking via POST,
and writes a valid GeoJSON file using GeoPandas.
"""

import requests
import logging
import time
from pathlib import Path
from typing import Dict, Any, Optional
import geopandas as gpd


class FeatureServerDownloader:
    def __init__(self, logger: Optional[logging.Logger] = None, epsg_code: int = 4326, sleep: float = 0.2):
        self.logger = logger or logging.getLogger(__name__)
        self.epsg_code = epsg_code
        self.sleep = sleep

    def download_as_single_geojson(
        self,
        base_url: str,
        output_dir: str,
        merged_filename: str = "merged_layers.geojson",
        layer_name: str = "Merged Layers"
    ) -> Dict[str, Any]:
        Path(output_dir).mkdir(parents=True, exist_ok=True)
        service_info = requests.get(f"{base_url}?f=json")
        service_info.raise_for_status()
        layers = service_info.json().get("layers", [])
        if not layers:
            raise Exception("No layers found in FeatureServer")

        all_features = []

        for layer in layers:
            lid, lname = layer["id"], layer["name"]
            query_url = f"{base_url}/{lid}/query"
            info = requests.get(f"{base_url}/{lid}?f=json").json()

            supports_pagination = info.get("supportsPagination", False)
            max_count = info.get("maxRecordCount", 1000)

            self.logger.info(f"Downloading layer {lname} (supportsPagination={supports_pagination})")

            try:
                if supports_pagination:
                    # --- Pagination mode ---
                    offset = 0
                    while True:
                        params = {
                            "where": "1=1",
                            "outFields": "*",
                            "returnGeometry": "true",
                            "f": "pjson",
                            "outSR": self.epsg_code,
                            "resultOffset": offset,
                            "resultRecordCount": max_count
                        }
                        r = requests.get(query_url, params=params)
                        if not r.ok or not r.text.strip():
                            self.logger.warning(f"Empty response for offset {offset} in {lname}")
                            break
                        data = r.json()
                        feats = data.get("features", [])
                        if not feats:
                            break
                        all_features.extend(self._arcgis_to_geojson(feats, lname))
                        offset += len(feats)
                        time.sleep(self.sleep)
                        if len(feats) < max_count:
                            break
                else:
                    # --- ObjectID chunking mode using POST ---
                    ids_resp = requests.get(f"{query_url}?where=1=1&returnIdsOnly=true&f=pjson")
                    ids_resp.raise_for_status()
                    ids_data = ids_resp.json()
                    ids = ids_data.get("objectIds", [])
                    if not ids:
                        self.logger.warning(f"No object IDs found for {lname}")
                        continue

                    self.logger.info(f"Found {len(ids)} object IDs in {lname}")

                    for i in range(0, len(ids), max_count):
                        subset = ids[i:i + max_count]
                        params = {
                            "objectIds": ",".join(map(str, subset)),
                            "outFields": "*",
                            "returnGeometry": "true",
                            "f": "pjson",
                            "outSR": self.epsg_code
                        }
                        r = requests.post(query_url, data=params)
                        if not r.ok or not r.text.strip():
                            self.logger.warning(f"Empty response chunk {i}-{i+max_count} in {lname}")
                            continue
                        data = r.json()
                        feats = data.get("features", [])
                        if feats:
                            all_features.extend(self._arcgis_to_geojson(feats, lname))
                        time.sleep(self.sleep)
            except Exception as e:
                self.logger.error(f"Error downloading layer {lname}: {e}")
                continue

        # --- Build GeoDataFrame and save ---
        gdf = gpd.GeoDataFrame.from_features(all_features, crs=f"EPSG:{self.epsg_code}")

        # Fix invalid geometries using buffer(0) - repairs topology issues like self-intersections
        # This is a standard GIS technique that doesn't change the data, just fixes the topology
        invalid_count = (~gdf.geometry.is_valid).sum()
        if invalid_count > 0:
            self.logger.warning(f"Found {invalid_count} invalid geometries, fixing with buffer(0)")
            gdf['geometry'] = gdf.geometry.buffer(0)
            still_invalid = (~gdf.geometry.is_valid).sum()
            if still_invalid > 0:
                self.logger.error(f"❌ Still have {still_invalid} invalid geometries after buffer(0) fix")
            else:
                self.logger.info(f"✅ Fixed all {invalid_count} invalid geometries")

        out_path = Path(output_dir) / merged_filename
        gdf.to_file(out_path, driver="GeoJSON")

        count = len(gdf)
        self.logger.info(f"✅ Merged {len(layers)} layers ({count} valid geometries) → {out_path}")

        return {
            "layer_name": layer_name,
            "filename": merged_filename,
            "filepath": str(out_path),
            "feature_count": count,
            "url": base_url
        }

    # ------------------------------------------------------------------
    # Geometry converter (ESRI JSON → GeoJSON)
    # ------------------------------------------------------------------
    def _arcgis_to_geojson(self, features: list, layer_name: str) -> list:
        """Convert ArcGIS PJSON features into GeoJSON-compatible features."""
        geojson_features = []
        for f in features:
            geom = f.get("geometry")
            attrs = f.get("attributes", {})
            if not geom:
                continue

            # Convert ArcGIS geometry to GeoJSON format
            if "rings" in geom:
                geometry = {"type": "Polygon", "coordinates": geom["rings"]}
            elif "paths" in geom:
                geometry = {"type": "LineString", "coordinates": geom["paths"][0]}
            elif "x" in geom and "y" in geom:
                geometry = {"type": "Point", "coordinates": [geom["x"], geom["y"]]}
            else:
                continue

            geojson_features.append({
                "type": "Feature",
                "geometry": geometry,
                "properties": {**attrs, "_source_layer": layer_name}
            })
        return geojson_features