"""Dataset writer — filesystem I/O only.

Writes the standard segmentation dataset directory structure:
    images/, masks/{id}/, geojsons/, annotations/
"""

import json
import logging
import shutil
from pathlib import Path

import geopandas as gpd
from PIL import Image

from .config import RenderResult

logger = logging.getLogger(__name__)


class DatasetWriter:
    """Writes rendered outputs to the dataset directory structure."""

    def __init__(self, output_dir: str | Path):
        self._root = Path(output_dir).resolve()
        self._images_dir = self._root / "images"
        self._masks_dir = self._root / "masks"
        self._geojsons_dir = self._root / "geojsons"
        self._annotations_dir = self._root / "annotations"

        for d in [self._images_dir, self._masks_dir,
                  self._geojsons_dir, self._annotations_dir]:
            d.mkdir(parents=True, exist_ok=True)

    def write_sample(
        self,
        sample_id: str,
        image: Image.Image,
        mask_info: list[dict],
        mask_dir: Path,
        gdf: gpd.GeoDataFrame,
        render_result: RenderResult,
        extra_annotation: dict | None = None,
    ):
        """Write one complete training sample.

        Args:
            sample_id: zero-padded ID (e.g., "0000").
            image: PIL Image of the map frame (possibly augmented).
            mask_info: list of mask metadata dicts from MaskRenderer.
            mask_dir: temporary directory containing rrr_ggg_bbb.png masks.
            gdf: GeoDataFrame for the ground truth GeoJSON.
            render_result: RenderResult with extent, color_map, etc.
            extra_annotation: additional fields to merge into annotation JSON.
        """
        # Save image
        image_path = self._images_dir / f"{sample_id}.png"
        image.save(str(image_path))

        # Move masks to final location
        final_mask_dir = self._masks_dir / sample_id
        if final_mask_dir.exists():
            shutil.rmtree(final_mask_dir)
        shutil.copytree(mask_dir, final_mask_dir)

        # Save GeoJSON
        geojson_path = self._geojsons_dir / f"{sample_id}.geojson"
        gdf.to_file(geojson_path, driver="GeoJSON")

        # Build and save annotation
        n_zones = len(mask_info)
        total_zone_pixels = sum(info["pixel_count"] for info in mask_info)
        total_pixels = image.width * image.height

        annotation = {
            "sample_id": sample_id,
            "image": f"images/{sample_id}.png",
            "image_width": image.width,
            "image_height": image.height,
            "extent": list(render_result.extent),
            "crs": "EPSG:4326",
            "geojson": f"geojsons/{sample_id}.geojson",
            # Sample-level metadata
            "n_zones": n_zones,
            "zone_coverage": round(total_zone_pixels / max(1, total_pixels), 3),
            "zones": [
                {
                    "zone_dir": f"masks/{sample_id}/{info['zone_dir']}",
                    "mask": f"masks/{sample_id}/{info['zone_dir']}/mask.png",
                    "pattern": f"masks/{sample_id}/{info['zone_dir']}/pattern.png",
                    "names": info["names"],
                    "pixel_count": info["pixel_count"],
                    "pixel_fraction": round(info["pixel_count"] / max(1, total_pixels), 4),
                    "pattern_type": info.get("pattern_type", "solid"),
                }
                for info in mask_info
            ],
        }
        if extra_annotation:
            annotation.update(extra_annotation)

        with open(self._annotations_dir / f"{sample_id}.json", "w") as f:
            json.dump(annotation, f, indent=2)

        logger.info(
            f"Wrote sample {sample_id}: {image.width}x{image.height}, "
            f"{len(mask_info)} masks"
        )

    def write_metadata(self, total_samples: int, **extra):
        """Write dataset-level metadata.json."""
        metadata = {
            "total_samples": total_samples,
            "structure": {
                "images/{id}.png": "Rendered map image (model input)",
                "masks/{id}/zone_XX/mask.png": "Binary mask per zone (model target)",
                "masks/{id}/zone_XX/pattern.png": "64x64 pattern thumbnail (model query input)",
                "geojsons/{id}.geojson": "Ground truth vector polygons (for evaluation)",
                "annotations/{id}.json": "Per-sample metadata (zones, colors, extent)",
            },
            **extra,
        }
        with open(self._root / "metadata.json", "w") as f:
            json.dump(metadata, f, indent=2)
