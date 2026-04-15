"""Parallel training data generation — uses all CPU cores.

Thin wrapper around run.py's render_sample(). Each worker process
handles one (geojson, sample_index) pair independently.

Usage:
    python -m processor.map_renderer.generate                            # all cities, 20 samples each
    python -m processor.map_renderer.generate --samples-per-file 10
    python -m processor.map_renderer.generate --workers 4                # limit cores
    python -m processor.map_renderer.generate --source data/maps/CA      # subset
    python -m processor.map_renderer.generate --resume                   # skip existing
"""

"""
uv run python -m processor.map_renderer.generate --output data/training/zoning_segmentation_v2
"""

import argparse
import json
import logging
import multiprocessing as mp
import random
import sys
import time
from pathlib import Path

from tqdm import tqdm

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(processName)s] %(message)s",
)
logger = logging.getLogger(__name__)


def parse_args():
    p = argparse.ArgumentParser(description="Parallel training data generation")
    p.add_argument("--source", default="data/maps", help="GeoJSON source dir")
    p.add_argument(
        "--output", default="data/training/zoning_segmentation", help="Output root dir"
    )
    p.add_argument(
        "--samples-per-file", type=int, default=20, help="Samples per GeoJSON file"
    )
    p.add_argument("--dpi", type=int, default=200, help="Image resolution")
    p.add_argument(
        "--workers",
        type=int,
        default=None,
        help="Number of workers (default: all CPUs)",
    )
    p.add_argument("--seed", type=int, default=42, help="Base random seed")
    p.add_argument(
        "--resume",
        action="store_true",
        help="Skip samples whose annotation already exists",
    )
    return p.parse_args()


def _worker(args):
    """Worker: render one sample. Runs in a subprocess."""
    geojson_path, sample_idx, seed, output, dpi, resume = args
    sample_name = f"{sample_idx:05d}"

    # Resume check
    ann_path = Path(output) / "annotations" / f"{sample_name}.json"
    if resume and ann_path.exists():
        return sample_name, True, "skipped"

    # Seed this worker's random state
    random.seed(seed)

    # Import render logic from run.py
    from processor.map_renderer.run import load_gdf, render_sample

    try:
        loaded = load_gdf(Path(geojson_path))
        if loaded is None:
            return sample_name, False, "no zone column"

        gdf, zone_col = loaded
        result = render_sample(
            gdf=gdf,
            zone_col=zone_col,
            sample_name=sample_name,
            output=Path(output),
            geojson_path=Path(geojson_path),
            dpi=dpi,
        )
        if result is None:
            return sample_name, False, "empty sample"

        return sample_name, True, f"{result['image_width']}x{result['image_height']}"

    except Exception as e:
        return sample_name, False, str(e)


def main():
    args = parse_args()

    source = Path(args.source)
    output = Path(args.output)

    # Create output dirs
    for d in ["images", "annotations", "masks", "geojsons"]:
        (output / d).mkdir(parents=True, exist_ok=True)

    # Discover all geojson files
    from processor.map_renderer.run import find_all_geojsons, load_gdf

    files = find_all_geojsons(source)
    logger.info(f"Found {len(files)} GeoJSON files")

    # Pre-filter: only keep files that have a valid zone column
    valid_files = []
    for path in tqdm(files, desc="Validating GeoJSONs", unit="file"):
        loaded = load_gdf(path)
        if loaded is not None:
            valid_files.append(path)
    logger.info(
        f"Valid files: {len(valid_files)}/{len(files)} "
        f"({len(files) - len(valid_files)} skipped — no zone column)"
    )

    # Build work items: (geojson_path, sample_index, seed)
    work = []
    idx = 0
    for path in valid_files:
        for _ in range(args.samples_per_file):
            work.append(
                (
                    str(path),
                    idx,
                    args.seed + idx,  # unique seed per sample
                    str(output),
                    args.dpi,
                    args.resume,
                )
            )
            idx += 1

    total = len(work)
    logger.info(
        f"Total: {total} samples "
        f"({len(valid_files)} valid files x {args.samples_per_file} each)"
    )

    n_workers = min(args.workers or mp.cpu_count(), total)
    logger.info(f"Workers: {n_workers} (CPUs: {mp.cpu_count()})")

    generated = 0
    failed = 0
    skipped = 0

    pbar = tqdm(
        total=total,
        desc="Generating",
        unit="sample",
        bar_format="{l_bar}{bar}| {n_fmt}/{total_fmt} [{elapsed}<{remaining}, {rate_fmt}] {postfix}",
    )

    with mp.Pool(n_workers) as pool:
        for name, ok, msg in pool.imap_unordered(_worker, work):
            pbar.update(1)
            if msg == "skipped":
                skipped += 1
            elif not ok:
                failed += 1
                tqdm.write(f"FAIL {name}: {msg}")
            else:
                generated += 1

            pbar.set_postfix(ok=generated, fail=failed, skip=skipped, refresh=False)

    pbar.close()

    elapsed = pbar.format_dict["elapsed"]
    logger.info(
        f"Done: {generated} generated, {skipped} skipped, {failed} failed "
        f"in {elapsed/60:.1f} min"
    )

    # Save metadata
    meta = {
        "total_samples": total,
        "generated": generated,
        "failed": failed,
        "skipped": skipped,
        "source": str(source),
        "dpi": args.dpi,
        "samples_per_file": args.samples_per_file,
        "seed": args.seed,
        "n_geojsons": len(files),
        "n_valid_geojsons": len(valid_files),
    }
    with open(output / "metadata.json", "w") as f:
        json.dump(meta, f, indent=2)


if __name__ == "__main__":
    main()
