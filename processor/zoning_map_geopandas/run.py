"""Generate zoning map segmentation dataset.

Usage:
    python -m processor.zoning_map_geopandas.run                    # debug: 5 samples
    python -m processor.zoning_map_geopandas.run --no-debug         # full: all GeoJSONs
    python -m processor.zoning_map_geopandas.run --source data/maps/CA/adelanto/geojson
    python -m processor.zoning_map_geopandas.run --no-debug --workers 4
"""

import argparse
import logging
import os
import random
import sys
import time
from concurrent.futures import ProcessPoolExecutor, as_completed
from multiprocessing import Manager

import geopandas as gpd
import pandas as pd

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s")
logger = logging.getLogger(__name__)


def _process_geojson(args_tuple):
    """Process one GeoJSON file — generate all samples for it.

    Runs in a worker process. Returns list of sample IDs generated.
    """
    (geojson_path, sample_ids, samples_per_geojson,
     dpi, seed, output_dir) = args_tuple

    # Each worker gets its own seed derived from the file seed
    import random as _rng
    _rng.seed(seed)

    import matplotlib
    matplotlib.use("Agg")

    from pathlib import Path
    from processor.zoning_map.geo_utils import (
        load_geojson, detect_zone_field, annotate_colors, rotate_gdf,
    )
    from processor.zoning_map.writer import DatasetWriter
    from processor.zoning_map.sampling import build_zone_plan, sample_by_zone_count
    from processor.zoning_map_geopandas.dataset import generate_sample, random_config

    writer = DatasetWriter(output_dir)
    generated = []

    try:
        gdf = load_geojson(Path(geojson_path))
        if len(gdf) < 1:
            return generated
        zone_field = detect_zone_field(gdf)
        if not zone_field:
            return generated

        n_zones = gdf[zone_field].nunique()
        plan = build_zone_plan(n_zones, samples_per_geojson)

        sid_idx = 0
        for tz in plan:
            if sid_idx >= len(sample_ids):
                break

            if tz == -1:
                keep = _rng.uniform(0.3, 1.0)
                kept = []
                for zt in gdf[zone_field].unique():
                    zp = gdf[gdf[zone_field] == zt]
                    if len(zp) == 0:
                        continue
                    n = max(1, int(len(zp) * keep))
                    kept.append(zp.sample(n=n))
                if not kept:
                    continue
                subset = gpd.GeoDataFrame(pd.concat(kept))
            else:
                subset = sample_by_zone_count(gdf, zone_field, tz)

            if len(subset) == 0:
                continue

            if _rng.random() < 0.5:
                subset = rotate_gdf(subset, _rng.uniform(0, 360))

            annotated, color_map = annotate_colors(subset, zone_field)
            if not color_map:
                continue

            config, rk = random_config(annotated, zone_field, color_map)
            config.dpi = dpi

            sid = sample_ids[sid_idx]
            try:
                generate_sample(config, rk, sid, writer,
                                source_file=str(geojson_path))
                generated.append(sid)
                sid_idx += 1
            except Exception as e:
                logging.warning(f"Sample {sid} failed: {e}")

    except Exception as e:
        logging.warning(f"Failed {geojson_path}: {e}")

    return generated


def main():
    parser = argparse.ArgumentParser(description="Generate segmentation dataset")
    parser.add_argument("--source", default="data/maps", help="GeoJSON source dir")
    parser.add_argument("--output", default="data/training/zoning_segmentation", help="Output dir")
    parser.add_argument("--samples-per-geojson", type=int, default=20)
    parser.add_argument("--dpi", type=int, default=150)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--workers", type=int, default=1, help="Number of parallel workers")
    parser.add_argument("--no-debug", action="store_true", help="Full generation (not debug)")
    args = parser.parse_args()

    debug = not args.no_debug
    if debug:
        logger.info("DEBUG MODE: generating 5 samples from first GeoJSON")

    os.chdir(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
    sys.path.insert(0, ".")

    from pathlib import Path
    from processor.zoning_map.writer import DatasetWriter

    source = Path(args.source)
    geojson_files = sorted(source.rglob("*.geojson"))
    logger.info(f"Found {len(geojson_files)} GeoJSON files")

    if debug:
        geojson_files = geojson_files[:1]
        args.samples_per_geojson = 5

    # Pre-assign sample IDs so filenames don't collide across workers
    random.seed(args.seed)
    tasks = []
    sample_counter = 0
    for gi, gj in enumerate(geojson_files):
        ids = [f"{sample_counter + i:05d}" for i in range(args.samples_per_geojson)]
        # Each file gets a deterministic seed
        file_seed = random.randint(0, 2**31)
        tasks.append((str(gj), ids, args.samples_per_geojson,
                       args.dpi, file_seed, args.output))
        sample_counter += args.samples_per_geojson

    # Ensure output dirs exist
    writer = DatasetWriter(args.output)

    start = time.time()

    if args.workers <= 1:
        # Sequential — same as before
        total_generated = 0
        for ti, task in enumerate(tasks):
            result = _process_geojson(task)
            total_generated += len(result)
            elapsed = time.time() - start
            done = ti + 1
            total = len(tasks)
            eta = (elapsed / done) * (total - done) if done > 0 else 0
            logger.info(
                f"{done}/{total} files, {total_generated} samples, "
                f"{elapsed:.0f}s elapsed, ETA {eta/60:.0f}min"
            )
    else:
        # Parallel
        logger.info(f"Using {args.workers} workers")
        total_generated = 0
        done = 0
        with ProcessPoolExecutor(max_workers=args.workers) as executor:
            futures = {executor.submit(_process_geojson, t): t for t in tasks}
            for future in as_completed(futures):
                try:
                    result = future.result()
                    total_generated += len(result)
                except Exception as e:
                    logger.warning(f"Worker failed: {e}")
                done += 1
                if done % 5 == 0 or done == len(tasks):
                    elapsed = time.time() - start
                    eta = (elapsed / done) * (len(tasks) - done) if done > 0 else 0
                    logger.info(
                        f"{done}/{len(tasks)} files, {total_generated} samples, "
                        f"{elapsed:.0f}s elapsed, ETA {eta/60:.0f}min"
                    )

    writer.write_metadata(total_samples=total_generated, dpi=args.dpi,
                          source_dir=args.source, renderer="geopandas")
    logger.info(f"Done: {total_generated} samples in {(time.time()-start)/60:.1f}min")


if __name__ == "__main__":
    main()
