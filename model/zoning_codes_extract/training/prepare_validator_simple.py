#!/usr/bin/env python3
"""
Simplified validator data preparation.

Creates training data for the validator model (binary classification):
- Positive examples: Zone codes from zoneomics CSVs found in ordinances
- Negative examples: Pattern matches that look like zone codes but aren't in ground truth
"""

import json
import re
import random
from pathlib import Path
from dataclasses import dataclass, asdict
from typing import List, Dict, Set, Optional
from collections import defaultdict

import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from ordinance_parser import OrdinanceParser
from text_aligner import load_zoneomics_csv, normalize_zone_code


@dataclass
class ValidatorExample:
    """A training example for the validator."""
    code: str
    passages: List[str]
    label: int  # 1 = valid zone code, 0 = false positive
    city: str
    state: str


# State name mapping
STATE_NAMES = {
    'al': 'alabama',
    'ca': 'california',
    'ma': 'massachusetts',
}


# Zone code patterns for finding candidates
ZONE_PATTERNS = [
    r'\b([A-Z]{1,3}-\d{1,2}[A-Z]?)\b',   # R-1, C-2, I-1, R-1A
    r'\b([A-Z]\d[A-Z]?)\b',               # R1, C2, M1, R1A (no hyphen)
    r'\b([A-Z]{2,4})\b',                   # AG, MU, PD, RMU
    r'\b([A-Z]-[A-Z]{1,3})\b',             # R-SF, C-GC, I-BP
    r'\b([A-Z]{1,2}-[A-Z]{2,4})\b',        # R-MH, C-OFC
]


# Common words that match patterns but aren't zone codes
SKIP_WORDS = {
    'THE', 'AND', 'FOR', 'ARE', 'NOT', 'BUT', 'CAN', 'MAY', 'ALL',
    'ANY', 'USE', 'SET', 'PER', 'LOT', 'FEE', 'ACT', 'TAX', 'MAP',
    'SEC', 'ART', 'DIV', 'SUB', 'ADD', 'NEW', 'OLD', 'MAX', 'MIN',
    'AVE', 'WAY', 'RD', 'ST', 'DR', 'LN', 'CT', 'PL', 'HWY',
    'NO', 'OF', 'TO', 'IN', 'ON', 'AT', 'BY', 'OR', 'IF', 'AS',
    'AN', 'BE', 'IS', 'IT', 'SO', 'UP', 'US', 'WE', 'HE', 'ME',
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


def find_all_candidates(text: str, context_window: int = 300) -> Dict[str, List[str]]:
    """
    Find all candidate zone codes in text with their passages.

    Returns:
        Dictionary mapping code -> list of passages
    """
    pattern_re = re.compile('|'.join(ZONE_PATTERNS), re.IGNORECASE)
    candidate_passages = defaultdict(list)

    for match in pattern_re.finditer(text):
        code = match.group(0).upper()

        # Skip common words
        if code in SKIP_WORDS:
            continue

        # Skip very short codes (likely false positives)
        if len(code) < 2:
            continue

        # Extract context
        start = max(0, match.start() - context_window)
        end = min(len(text), match.end() + context_window)
        passage = text[start:end].strip()

        # Clean up passage (remove excessive whitespace)
        passage = ' '.join(passage.split())

        candidate_passages[code].append(passage)

    return candidate_passages


def prepare_city_validator_data(
    city: str,
    state: str,
    municode_dir: Path,
    zoneomics_dir: Path,
    max_passages_per_code: int = 5,
    min_passages_per_code: int = 1,
    negative_positive_ratio: float = 1.5
) -> List[ValidatorExample]:
    """
    Prepare validator training data for a single city.
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

    # Normalize ground truth codes
    ground_truth_codes = {normalize_zone_code(d.zone_code) for d in districts}
    # Also keep original forms for matching
    original_codes = {d.zone_code.upper().replace('-', '').replace(' ', '') for d in districts}
    all_truth_codes = ground_truth_codes | original_codes

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

    # Find all candidate codes
    candidate_passages = find_all_candidates(full_text)

    # Separate into positive and negative examples
    positive_examples = []
    negative_examples = []

    for code, passages in candidate_passages.items():
        normalized = normalize_zone_code(code)

        # Skip if too few passages
        if len(passages) < min_passages_per_code:
            continue

        # Limit and deduplicate passages
        unique_passages = list(dict.fromkeys(passages))[:max_passages_per_code]

        # Check if this is a real zone code
        if normalized in all_truth_codes or code in all_truth_codes:
            positive_examples.append(ValidatorExample(
                code=code,
                passages=unique_passages,
                label=1,
                city=city,
                state=state
            ))
        else:
            negative_examples.append(ValidatorExample(
                code=code,
                passages=unique_passages,
                label=0,
                city=city,
                state=state
            ))

    # Balance negative examples
    target_neg_count = int(len(positive_examples) * negative_positive_ratio)
    if len(negative_examples) > target_neg_count and target_neg_count > 0:
        negative_examples = random.sample(negative_examples, target_neg_count)

    all_examples = positive_examples + negative_examples
    random.shuffle(all_examples)

    pos_count = len(positive_examples)
    neg_count = len(negative_examples)
    print(f"  {city}: {len(all_examples)} examples ({pos_count} pos, {neg_count} neg)")

    return all_examples


def main():
    import argparse

    parser = argparse.ArgumentParser(description="Prepare validator training data")
    parser.add_argument("--output-dir", default="model/zoning_codes_extract/training/data")
    parser.add_argument("--municode-dir", default="collector/tmp/zoning_ordinance_md")
    parser.add_argument("--zoneomics-dir", default="data/zoneomics")
    parser.add_argument("--neg-pos-ratio", type=float, default=1.5,
                        help="Ratio of negative to positive examples")
    args = parser.parse_args()

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    # Load city splits (same as extractor uses)
    splits_path = output_dir / "city_splits.json"
    if not splits_path.exists():
        print(f"Error: {splits_path} not found. Run extractor data prep first.")
        return

    with open(splits_path) as f:
        splits = json.load(f)

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

            examples = prepare_city_validator_data(
                city=city,
                state=state,
                municode_dir=municode_dir,
                zoneomics_dir=zoneomics_dir,
                negative_positive_ratio=args.neg_pos_ratio
            )
            all_examples.extend(examples)

        # Save
        output_file = output_dir / f"validator_{split_name}.jsonl"
        with open(output_file, 'w') as f:
            for ex in all_examples:
                f.write(json.dumps(asdict(ex)) + '\n')

        pos = sum(1 for ex in all_examples if ex.label == 1)
        neg = sum(1 for ex in all_examples if ex.label == 0)
        print(f"Saved {len(all_examples)} examples ({pos} pos, {neg} neg) to {output_file}")

    print("\n=== Validator Data Preparation Complete ===")


if __name__ == "__main__":
    main()
