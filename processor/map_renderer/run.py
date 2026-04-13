"""Render sample zoning maps from real geojson data.

Usage:
    python -m processor.map_renderer.run                              # debug: 3 samples from first geojson
    python -m processor.map_renderer.run --no-debug                   # full: 5 random geojsons
    python -m processor.map_renderer.run --no-debug --count 20
    python -m processor.map_renderer.run --source data/maps/CA        # from California only
    python -m processor.map_renderer.run --dpi 300 --output my_output
"""

import argparse
import json
import logging
import random
import sys
import time
from pathlib import Path

import geopandas as gpd

# Ensure project root is on path
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from processor.map_renderer.canvas import Canvas
from processor.map_renderer.config import MapConfig
from processor.map_renderer.layers.background import BackgroundLayer
from processor.map_renderer.layers.zone import ZoneLayer
from processor.map_renderer.layers.label import LabelLayer
from processor.map_renderer.layers.grid import GridLayer
from processor.map_renderer.mask import generate_masks
from processor.map_renderer.pattern import extract_patterns
from processor.map_renderer.renderer import MapRenderer
from processor.map_renderer.postprocess.pipeline import PostProcessPipeline
from processor.map_renderer.sampling import RandomSampler
from processor.map_renderer.colors import build_zone_color_map
from processor.map_renderer.geo_utils import detect_zone_field

logger = logging.getLogger(__name__)


# ------------------------------------------------------------------
# Shared helpers (used by run.py and generate.py)
# ------------------------------------------------------------------

def find_all_geojsons(source: Path) -> list[Path]:
    """Return all geojson files under source, sorted."""
    files = sorted(source.rglob("*.geojson"))
    if not files:
        logger.error(f"No geojson files found in {source}")
        sys.exit(1)
    return files


def load_gdf(geojson_path: Path) -> tuple[gpd.GeoDataFrame, str] | None:
    """Load geojson and detect zone column. Returns (gdf, zone_col) or None."""
    gdf = gpd.read_file(geojson_path)

    zone_col = detect_zone_field(gdf)
    if zone_col is None:
        logger.warning(f"No zone column found in {geojson_path.name}")
        return None

    gdf = gdf[gdf[zone_col].notna()].copy()
    if gdf.empty:
        logger.warning(f"No valid zone data in {geojson_path.name}")
        return None

    gdf[zone_col] = gdf[zone_col].astype(str)
    return gdf, zone_col


BASEMAP_PROVIDERS = [
    None,  # no basemap (solid color background)
    "CartoDB.Positron",
    "CartoDB.Voyager",
]


def _resolve_basemap(name: str | None):
    """Resolve basemap name to contextily provider dict, or None."""
    if name is None:
        return None
    import contextily as cx
    provider = cx.providers
    for part in name.split("."):
        provider = provider[part]
    return provider


def _random_hatch_zones(zone_names: list[str]) -> dict[str, str]:
    """Randomly assign hatch patterns to some zones.

    40% of samples: no hatching
    30% of samples: 1-3 zones hatched
    30% of samples: most zones hatched
    """
    from processor.map_renderer.styles import HATCH_PATTERNS

    roll = random.random()
    if roll < 0.4:
        return {}

    pattern_names = list(HATCH_PATTERNS.keys())

    if roll < 0.7:
        n = random.randint(1, min(3, len(zone_names)))
        selected = random.sample(zone_names, n)
    else:
        n = random.randint(len(zone_names) // 2, len(zone_names))
        selected = random.sample(zone_names, n)

    return {z: random.choice(pattern_names) for z in selected}


def _build_layers(config: MapConfig, no_grid: bool = False) -> tuple[list, bool]:
    """Build randomized layer stack. Returns (layers, has_basemap)."""
    basemap_name = random.choice(BASEMAP_PROVIDERS)
    basemap = _resolve_basemap(basemap_name)
    has_basemap = basemap is not None

    layers = [BackgroundLayer(background=basemap)] if has_basemap else [BackgroundLayer()]

    zone_names = list(config.color_map.keys())
    hatch_zones = _random_hatch_zones(zone_names)
    layers.append(ZoneLayer(hatch_zones=hatch_zones))
    layers.append(LabelLayer())

    if not no_grid and random.random() < 0.2:
        layers.append(GridLayer())

    return layers, has_basemap


# ------------------------------------------------------------------
# Core: render a single sample (reusable by generate.py)
# ------------------------------------------------------------------

def render_sample(
    gdf: gpd.GeoDataFrame,
    zone_col: str,
    sample_name: str,
    output: Path,
    geojson_path: Path,
    dpi: int = 200,
    no_grid: bool = False,
    no_postprocess: bool = False,
    no_mask: bool = False,
) -> dict | None:
    """Render one sample: image + geojson + masks + patterns + annotation.

    Args:
        gdf: Full GeoDataFrame for the city (pre-loaded).
        zone_col: Zone column name.
        sample_name: e.g. "00042" — used for all output filenames.
        output: Root output directory (contains images/, masks/, etc.).
        geojson_path: Original source file path (for annotation).
        dpi: Image resolution.
        no_grid / no_postprocess / no_mask: Feature toggles.

    Returns:
        Annotation dict on success, None on failure.
    """
    img_dir = output / "images"
    ann_dir = output / "annotations"
    mask_root = output / "masks"
    geo_dir = output / "geojsons"

    # Sample a random subset of zones/polygons
    sampled = RandomSampler().sample(gdf, zone_col)
    if sampled.empty:
        logger.warning(f"  {sample_name}: sampling returned empty, skipping")
        return None

    # Build config + layers + renderer
    color_map = build_zone_color_map(sampled[zone_col].tolist())
    config = MapConfig(gdf=sampled, zone_column=zone_col, color_map=color_map)
    layers, has_basemap = _build_layers(config, no_grid=no_grid)
    postprocess = None if no_postprocess else PostProcessPipeline.random()
    renderer = MapRenderer(
        canvas=Canvas(dpi=dpi, has_basemap=has_basemap),
        layers=layers,
        postprocess=postprocess,
    )

    # Render
    result = renderer.render(config, img_dir / f"{sample_name}.png")

    # Save sampled GDF
    sampled.to_file(geo_dir / f"{sample_name}.geojson", driver="GeoJSON")

    # Mask + pattern extraction
    mask_info = None
    if not no_mask:
        mask_dir = mask_root / sample_name
        mask_info = generate_masks(
            gdf=result.gdf,
            extent=result.extent,
            final_size=(result.width, result.height),
            color_map=result.color_map,
            zone_column=result.zone_column,
            output_dir=mask_dir,
            post_rotation=result.post_rotation,
            raw_size=(result.raw_width, result.raw_height),
            original_extent=renderer.canvas.original_extent,
        )
        extract_patterns(
            nolabel_image=result.nolabel_image,
            mask_info=mask_info,
            mask_dir=mask_dir,
            gdf=result.gdf,
            extent=result.extent,
            zone_column=result.zone_column,
            hatch_zones=result.annotations.get("hatch_zones"),
            post_rotation=result.post_rotation,
        )
        for info in mask_info:
            info["zone_dir"] = f"masks/{sample_name}/{info['zone_dir']}"
            info["mask"] = f"{info['zone_dir']}/mask.png"
            info["pattern"] = f"{info['zone_dir']}/pattern.png"

    # Build annotation
    annotation = {
        "sample_id": sample_name,
        "image": f"images/{sample_name}.png",
        "image_width": result.width,
        "image_height": result.height,
        "crs": "EPSG:4326",
        "geojson": f"geojsons/{sample_name}.geojson",
        "n_zones": len(config.color_map),
        "zone_column": zone_col,
        "source_file": str(geojson_path),
        "renderer": "map_renderer",
        **result.annotations,
    }
    if mask_info is not None:
        annotation["zones"] = mask_info

    with open(ann_dir / f"{sample_name}.json", "w") as f:
        json.dump(annotation, f, indent=2)

    logger.info(f"  -> {sample_name}.png ({result.width}x{result.height})")
    return annotation


# ------------------------------------------------------------------
# CLI entry point (sequential, for debugging)
# ------------------------------------------------------------------

def parse_args():
    parser = argparse.ArgumentParser(description="Render sample zoning maps")
    parser.add_argument("--source", default="data/maps", help="GeoJSON source dir")
    parser.add_argument("--output", default="processor/map_renderer/test_output", help="Output dir")
    parser.add_argument("--count", type=int, default=5, help="Number of geojson files to use")
    parser.add_argument("--samples-per-file", type=int, default=1, help="Samples per geojson")
    parser.add_argument("--dpi", type=int, default=200, help="Image resolution")
    parser.add_argument("--seed", type=int, default=None, help="Random seed")
    parser.add_argument("--no-debug", action="store_true", help="Full run (default is debug mode)")
    parser.add_argument("--no-grid", action="store_true", help="Disable grid")
    parser.add_argument("--no-postprocess", action="store_true", help="Disable postprocessing effects")
    parser.add_argument("--no-mask", action="store_true", help="Skip mask and pattern generation")
    return parser.parse_args()


def main():
    args = parse_args()
    debug = not args.no_debug

    if debug:
        logger.info("DEBUG MODE: 3 samples from first geojson")
        args.count = 1
        args.samples_per_file = 3

    if args.seed is not None:
        random.seed(args.seed)

    source = Path(args.source)
    output = Path(args.output)
    for d in ["images", "annotations", "masks", "geojsons"]:
        (output / d).mkdir(parents=True, exist_ok=True)

    all_files = find_all_geojsons(source)
    logger.info(f"Found {len(all_files)} geojson files")
    files = random.sample(all_files, min(args.count, len(all_files)))

    start = time.time()
    sample_idx = 0

    for i, path in enumerate(files):
        logger.info(f"[{i+1}/{len(files)}] {path}")

        loaded = load_gdf(path)
        if loaded is None:
            continue
        gdf, zone_col = loaded

        for _ in range(args.samples_per_file):
            sample_name = f"{sample_idx:05d}"
            result = render_sample(
                gdf=gdf,
                zone_col=zone_col,
                sample_name=sample_name,
                output=output,
                geojson_path=path,
                dpi=args.dpi,
                no_grid=args.no_grid,
                no_postprocess=args.no_postprocess,
                no_mask=args.no_mask,
            )
            if result is not None:
                sample_idx += 1

    elapsed = time.time() - start
    logger.info(f"Done: {sample_idx} samples in {elapsed:.1f}s")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s")
    main()
