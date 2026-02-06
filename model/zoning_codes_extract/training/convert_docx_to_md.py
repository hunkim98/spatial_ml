#!/usr/bin/env python3
"""
Convert all docx files in zoning ordinance directory to markdown using pandoc.

This preprocessing step improves text extraction quality and parsing performance.
Markdown files are stored in a separate output directory, preserving the
state/city folder structure.

Usage:
    python convert_docx_to_md.py \
        --input collector/tmp/zoning_ordinance \
        --output collector/tmp/zoning_ordinance_md \
        --workers 8
"""

import subprocess
import argparse
import shutil
from pathlib import Path
from concurrent.futures import ProcessPoolExecutor, as_completed
from typing import Tuple, Optional


def check_pandoc_installed() -> bool:
    """Check if pandoc is available on the system."""
    return shutil.which('pandoc') is not None


def convert_single(args: Tuple[Path, Path]) -> Tuple[Path, bool, str]:
    """
    Convert a single docx file to markdown.

    Args:
        args: Tuple of (docx_path, output_md_path)

    Returns:
        Tuple of (md_path, success, message)
    """
    docx_path, md_path = args

    # Create output directory if needed
    md_path.parent.mkdir(parents=True, exist_ok=True)

    # Skip if already converted and up to date
    if md_path.exists() and md_path.stat().st_mtime > docx_path.stat().st_mtime:
        return (md_path, True, "skipped (up to date)")

    try:
        result = subprocess.run(
            [
                'pandoc', str(docx_path),
                '-f', 'docx',
                '-t', 'markdown',
                '-o', str(md_path),
                '--wrap=none'
            ],
            capture_output=True,
            text=True,
            timeout=60
        )

        if result.returncode == 0:
            return (md_path, True, "converted")
        else:
            return (md_path, False, result.stderr.strip()[:200])
    except subprocess.TimeoutExpired:
        return (md_path, False, "timeout")
    except Exception as e:
        return (md_path, False, str(e)[:200])


def convert_all(
    input_dir: Path,
    output_dir: Path,
    workers: int = 4,
    verbose: bool = False
) -> dict:
    """
    Convert all docx files in directory tree to markdown.

    Args:
        input_dir: Root directory to search for docx files
        output_dir: Root directory to output markdown files
        workers: Number of parallel workers
        verbose: Print detailed progress

    Returns:
        Dictionary with conversion statistics
    """
    docx_files = list(input_dir.rglob("*.docx"))
    print(f"Found {len(docx_files)} docx files in {input_dir}")

    if not docx_files:
        return {'total': 0, 'converted': 0, 'skipped': 0, 'failed': 0}

    # Build list of (input, output) paths
    conversion_tasks = []
    for docx_path in docx_files:
        # Compute relative path and create output path
        rel_path = docx_path.relative_to(input_dir)
        md_path = output_dir / rel_path.with_suffix('.md')
        conversion_tasks.append((docx_path, md_path))

    stats = {
        'total': len(docx_files),
        'converted': 0,
        'skipped': 0,
        'failed': 0,
        'errors': []
    }

    with ProcessPoolExecutor(max_workers=workers) as executor:
        futures = {executor.submit(convert_single, task): task[0] for task in conversion_tasks}

        for i, future in enumerate(as_completed(futures), 1):
            docx_path = futures[future]
            try:
                md_path, success, message = future.result()

                if success:
                    if "skipped" in message:
                        stats['skipped'] += 1
                    else:
                        stats['converted'] += 1
                    if verbose:
                        print(f"[{i}/{len(docx_files)}] {message}: {docx_path.name}")
                else:
                    stats['failed'] += 1
                    stats['errors'].append((str(docx_path), message))
                    if verbose:
                        print(f"[{i}/{len(docx_files)}] FAILED: {docx_path.name} - {message}")
            except Exception as e:
                stats['failed'] += 1
                stats['errors'].append((str(docx_path), str(e)))
                if verbose:
                    print(f"[{i}/{len(docx_files)}] ERROR: {docx_path.name} - {e}")

            # Progress indicator every 100 files
            if not verbose and i % 100 == 0:
                print(f"  Progress: {i}/{len(docx_files)} files processed")

    return stats


def convert_city(
    input_city_path: Path,
    output_city_path: Path,
    verbose: bool = False
) -> dict:
    """
    Convert all docx files for a single city.

    Args:
        input_city_path: Path to city's input municode folder
        output_city_path: Path to city's output folder
        verbose: Print detailed progress

    Returns:
        Dictionary with conversion statistics
    """
    docx_files = list(input_city_path.glob("*.docx"))

    # Create output directory
    output_city_path.mkdir(parents=True, exist_ok=True)

    stats = {
        'total': len(docx_files),
        'converted': 0,
        'skipped': 0,
        'failed': 0,
        'errors': []
    }

    for docx_path in docx_files:
        md_path = output_city_path / docx_path.with_suffix('.md').name
        _, success, message = convert_single((docx_path, md_path))

        if success:
            if "skipped" in message:
                stats['skipped'] += 1
            else:
                stats['converted'] += 1
        else:
            stats['failed'] += 1
            stats['errors'].append((str(docx_path), message))

        if verbose:
            status = "OK" if success else "FAILED"
            print(f"  [{status}] {docx_path.name}: {message}")

    return stats


def main():
    parser = argparse.ArgumentParser(
        description="Convert docx files to markdown using pandoc"
    )
    parser.add_argument(
        "--input", "-i",
        type=Path,
        default=Path("collector/tmp/zoning_ordinance"),
        help="Input directory with docx files"
    )
    parser.add_argument(
        "--output", "-o",
        type=Path,
        default=Path("collector/tmp/zoning_ordinance_md"),
        help="Output directory for markdown files"
    )
    parser.add_argument(
        "--workers", "-w",
        type=int,
        default=4,
        help="Number of parallel workers"
    )
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Print detailed progress"
    )
    parser.add_argument(
        "--city",
        type=str,
        help="Convert only a specific city (format: state/city, e.g., al/huntsville)"
    )

    args = parser.parse_args()

    # Check pandoc is installed
    if not check_pandoc_installed():
        print("ERROR: pandoc is not installed or not in PATH")
        print("Install with: brew install pandoc (macOS) or apt install pandoc (Ubuntu)")
        return 1

    # Convert
    if args.city:
        input_city = args.input / args.city
        output_city = args.output / args.city
        if not input_city.exists():
            print(f"ERROR: City path not found: {input_city}")
            return 1
        print(f"Converting city: {args.city}")
        stats = convert_city(input_city, output_city, verbose=args.verbose)
    else:
        if not args.input.exists():
            print(f"ERROR: Input directory not found: {args.input}")
            return 1
        args.output.mkdir(parents=True, exist_ok=True)
        print(f"Converting: {args.input} -> {args.output}")
        stats = convert_all(args.input, args.output, workers=args.workers, verbose=args.verbose)

    # Print summary
    print("\n=== Conversion Complete ===")
    print(f"Total files:  {stats['total']}")
    print(f"Converted:    {stats['converted']}")
    print(f"Skipped:      {stats['skipped']}")
    print(f"Failed:       {stats['failed']}")

    if stats['errors']:
        print(f"\nErrors ({len(stats['errors'])}):")
        for path, error in stats['errors'][:10]:
            print(f"  {Path(path).name}: {error}")
        if len(stats['errors']) > 10:
            print(f"  ... and {len(stats['errors']) - 10} more")

    return 0 if stats['failed'] == 0 else 1


if __name__ == "__main__":
    exit(main())
