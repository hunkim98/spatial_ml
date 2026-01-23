#!/usr/bin/env python3
"""Split a PDF file into single-page PDFs."""

import argparse
from pathlib import Path

from pypdf import PdfReader, PdfWriter


def split_pdf(input_path: str, output_dir: str | None = None) -> list[Path]:
    """Split a PDF into single-page PDFs.

    Args:
        input_path: Path to the input PDF file.
        output_dir: Directory for output files. Defaults to same directory as input.

    Returns:
        List of paths to the created PDF files.
    """
    input_path = Path(input_path)
    if not input_path.exists():
        raise FileNotFoundError(f"Input file not found: {input_path}")

    if output_dir is None:
        output_dir = input_path.parent
    else:
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)

    reader = PdfReader(input_path)
    stem = input_path.stem
    created_files = []

    for i, page in enumerate(reader.pages, start=1):
        writer = PdfWriter()
        writer.add_page(page)

        output_path = output_dir / f"{stem}_page_{i:03d}.pdf"
        with open(output_path, "wb") as f:
            writer.write(f)

        created_files.append(output_path)
        print(f"Created: {output_path}")

    print(f"\nSplit {len(created_files)} pages from {input_path.name}")
    return created_files


def main():
    parser = argparse.ArgumentParser(description="Split a PDF into single-page PDFs")
    parser.add_argument("input", help="Input PDF file")
    parser.add_argument(
        "-o", "--output-dir", help="Output directory (default: same as input)"
    )
    args = parser.parse_args()

    split_pdf(args.input, args.output_dir)


if __name__ == "__main__":
    main()
