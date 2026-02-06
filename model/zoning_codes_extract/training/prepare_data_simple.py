#!/usr/bin/env python3
"""
Simplified data preparation for zone code extraction training.

Prepares BIO-tagged data from selected cities without relying on CityMatcher.
"""

import json
import re
from pathlib import Path
from dataclasses import dataclass, asdict
from typing import List, Dict, Tuple, Optional, Set
from collections import defaultdict

from transformers import AutoTokenizer

import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from ordinance_parser import OrdinanceParser
from text_aligner import load_zoneomics_csv, normalize_zone_code


@dataclass
class TokenClassificationExample:
    """A single training example with BIO tags."""
    tokens: List[str]
    tags: List[str]
    city: str
    state: str


# State name mapping
STATE_NAMES = {
    'al': 'alabama',
    'ca': 'california',
    'ma': 'massachusetts',
}


def find_zoneomics_csv(state_abbr: str, city: str, zoneomics_dir: Path) -> Optional[Path]:
    """Find the zoneomics CSV for a city."""
    state_name = STATE_NAMES.get(state_abbr.lower(), state_abbr.lower())
    state_dir = zoneomics_dir / state_name

    if not state_dir.exists():
        return None

    # Try exact match first
    csv_path = state_dir / f"{city}.csv"
    if csv_path.exists():
        return csv_path

    # Try with hyphens instead of underscores
    csv_path = state_dir / f"{city.replace('_', '-')}.csv"
    if csv_path.exists():
        return csv_path

    return None


def prepare_city_data(
    city: str,
    state: str,
    municode_dir: Path,
    zoneomics_dir: Path,
    tokenizer,
    max_seq_length: int = 512,
    context_window: int = 500
) -> List[TokenClassificationExample]:
    """
    Prepare training data for a single city.

    Returns list of BIO-tagged examples.
    """
    # Find zoneomics CSV
    csv_path = find_zoneomics_csv(state, city, zoneomics_dir)
    if not csv_path:
        print(f"  No zoneomics CSV found for {city}, {state}")
        return []

    # Load ground truth zone codes
    districts = load_zoneomics_csv(str(csv_path))
    if not districts:
        print(f"  No districts in CSV for {city}")
        return []

    # Get all zone codes (filter short ones)
    all_zone_codes = [normalize_zone_code(d.zone_code) for d in districts]
    all_zone_codes = [zc for zc in all_zone_codes if len(zc) >= 2]

    if not all_zone_codes:
        print(f"  No valid zone codes for {city}")
        return []

    # Parse ordinances
    ordinance_path = municode_dir / state / city
    if not ordinance_path.exists():
        print(f"  No ordinance dir for {city}")
        return []

    parser = OrdinanceParser(ordinance_path)
    zoning_docs = list(parser.parse_all(zoning_only=True))

    if not zoning_docs:
        print(f"  No zoning documents for {city}")
        return []

    # Combine all text
    full_text = "\n\n".join(
        section.content
        for doc in zoning_docs
        for section in doc.sections
        if section.content
    )

    if not full_text:
        print(f"  No text content for {city}")
        return []

    # Find all zone code mentions and create examples
    examples = []
    seen_contexts = set()
    found_codes = set()

    for zone_code in all_zone_codes:
        # Create pattern for this zone code
        pattern = re.escape(zone_code)
        pattern = pattern.replace(r'\-', r'[-\s]?')
        pattern = r'\b' + pattern + r'\b'

        for match in re.finditer(pattern, full_text, re.IGNORECASE):
            found_codes.add(zone_code)

            # Extract context window
            start = max(0, match.start() - context_window)
            end = min(len(full_text), match.end() + context_window)

            # Skip duplicates
            context_key = (start, end)
            if context_key in seen_contexts:
                continue
            seen_contexts.add(context_key)

            context_text = full_text[start:end]

            # Find ALL zone codes in this context
            zone_spans = []
            for zc in all_zone_codes:
                zc_pattern = re.escape(zc).replace(r'\-', r'[-\s]?')
                zc_pattern = r'\b' + zc_pattern + r'\b'
                for zc_match in re.finditer(zc_pattern, context_text, re.IGNORECASE):
                    zone_spans.append((zc_match.start(), zc_match.end()))

            # Merge overlapping spans
            zone_spans = merge_spans(zone_spans)

            # Tokenize
            encoding = tokenizer(
                context_text,
                truncation=True,
                max_length=max_seq_length,
                return_offsets_mapping=True
            )

            tokens = tokenizer.convert_ids_to_tokens(encoding['input_ids'])
            offsets = encoding['offset_mapping']

            # Create BIO tags
            tags = []
            for token_start, token_end in offsets:
                if token_start is None or token_end is None:
                    tags.append('O')
                else:
                    tag = 'O'
                    for span_start, span_end in zone_spans:
                        if token_start >= span_start and token_end <= span_end:
                            tag = 'B-ZONE' if token_start == span_start else 'I-ZONE'
                            break
                    tags.append(tag)

            # Only keep examples with zone tags
            if 'B-ZONE' in tags:
                examples.append(TokenClassificationExample(
                    tokens=tokens,
                    tags=tags,
                    city=city,
                    state=state
                ))

    # Report coverage
    coverage = 100 * len(found_codes) / len(all_zone_codes) if all_zone_codes else 0
    print(f"  {city}: {len(examples)} examples, {len(found_codes)}/{len(all_zone_codes)} codes ({coverage:.0f}%)")

    return examples


def merge_spans(spans: List[Tuple[int, int]]) -> List[Tuple[int, int]]:
    """Merge overlapping spans."""
    if not spans:
        return []
    spans = sorted(spans)
    merged = [spans[0]]
    for start, end in spans[1:]:
        if start <= merged[-1][1]:
            merged[-1] = (merged[-1][0], max(merged[-1][1], end))
        else:
            merged.append((start, end))
    return merged


def main():
    import argparse

    parser = argparse.ArgumentParser(description="Prepare training data")
    parser.add_argument("--output-dir", default="model/zoning_codes_extract/training/data")
    parser.add_argument("--municode-dir", default="collector/tmp/zoning_ordinance_md")
    parser.add_argument("--zoneomics-dir", default="data/zoneomics")
    parser.add_argument("--tokenizer", default="bert-base-uncased")
    args = parser.parse_args()

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    # Load city splits
    splits_path = output_dir / "city_splits.json"
    if not splits_path.exists():
        print(f"Error: {splits_path} not found. Run city selection first.")
        return

    with open(splits_path) as f:
        splits = json.load(f)

    # Initialize tokenizer
    tokenizer = AutoTokenizer.from_pretrained(args.tokenizer)

    municode_dir = Path(args.municode_dir)
    zoneomics_dir = Path(args.zoneomics_dir)

    # Process each split
    for split_name in ['train', 'test']:
        city_keys = splits.get(split_name, [])
        if not city_keys:
            continue

        print(f"\n=== Processing {split_name} ({len(city_keys)} cities) ===")

        all_examples = []
        for city_key in city_keys:
            # Parse city_key: "city_state"
            parts = city_key.rsplit('_', 1)
            if len(parts) != 2:
                print(f"  Skipping invalid key: {city_key}")
                continue
            city, state = parts

            examples = prepare_city_data(
                city=city,
                state=state,
                municode_dir=municode_dir,
                zoneomics_dir=zoneomics_dir,
                tokenizer=tokenizer
            )
            all_examples.extend(examples)

        # Save
        output_file = output_dir / f"{split_name}.jsonl"
        with open(output_file, 'w') as f:
            for ex in all_examples:
                f.write(json.dumps(asdict(ex)) + '\n')

        print(f"Saved {len(all_examples)} examples to {output_file}")

    print("\n=== Data Preparation Complete ===")


if __name__ == "__main__":
    main()
