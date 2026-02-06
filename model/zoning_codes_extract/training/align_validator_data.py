"""
Align validator data with extractor data.

This script ensures the validator test/train data uses the exact same zone codes
that appear in the extractor's BIO-tagged data, rather than independently
finding candidates via pattern matching.
"""

import json
import re
import random
from pathlib import Path
from dataclasses import dataclass, asdict
from typing import List, Dict, Set, Optional
from collections import defaultdict

import sys
sys.path.append(str(Path(__file__).parent.parent.parent))

from zoning_codes_extract import OrdinanceParser, CityMatcher, normalize_zone_code
from city_splits import get_city_key


@dataclass
class ValidatorExample:
    """A training example for the validator."""
    code: str
    passages: List[str]
    label: int  # 1 = valid zone code, 0 = false positive
    city: str
    state: str


def extract_zones_from_bio(tokens: List[str], tags: List[str]) -> List[str]:
    """Extract zone codes from BIO-tagged tokens."""
    zones = []
    current = []

    # BERT special tokens to skip
    SKIP_TOKENS = {'[CLS]', '[SEP]', '[PAD]', '[UNK]', '[MASK]'}

    for token, tag in zip(tokens, tags):
        if tag == 'B-ZONE':
            if current:
                # Join and clean up BERT tokenization artifacts
                code = ''.join(current).replace('##', '')
                if code not in SKIP_TOKENS and not code.startswith('['):
                    zones.append(code)
            current = [token]
        elif tag == 'I-ZONE' and current:
            current.append(token)
        else:
            if current:
                code = ''.join(current).replace('##', '')
                if code not in SKIP_TOKENS and not code.startswith('['):
                    zones.append(code)
            current = []

    if current:
        code = ''.join(current).replace('##', '')
        if code not in SKIP_TOKENS and not code.startswith('['):
            zones.append(code)

    return zones


def load_extractor_zones(data_dir: Path, split: str) -> Dict[str, Dict]:
    """
    Load zone codes from extractor data by city.

    Returns:
        Dict mapping city_key -> {'zones': set of zone codes, 'city': original city name, 'state': state}
    """
    zones_by_city = {}
    filepath = data_dir / f"{split}.jsonl"

    if not filepath.exists():
        print(f"  Warning: {filepath} not found")
        return zones_by_city

    with open(filepath) as f:
        for line in f:
            ex = json.loads(line)
            city_key = get_city_key(ex['state'], ex['city'])

            if city_key not in zones_by_city:
                zones_by_city[city_key] = {
                    'zones': set(),
                    'city': ex['city'],  # Keep original city name
                    'state': ex['state']
                }

            zones = extract_zones_from_bio(ex['tokens'], ex['tags'])
            for z in zones:
                # Normalize the zone code
                normalized = normalize_zone_code(z)
                zones_by_city[city_key]['zones'].add(normalized)

    return zones_by_city


class AlignedValidatorDataPreparator:
    """
    Prepares validator data aligned with extractor data.

    Uses zone codes from extractor's BIO tags as ground truth for positive examples.
    """

    # Zone code patterns for finding candidates (comprehensive)
    ZONE_PATTERNS = [
        r'\b([A-Z]{1,3}-?\d{1,2}[A-Z]?)\b',      # R-1, C-2A, I-1
        r'\b([A-Z]{2,4})\b',                      # AG, MU, RMU
        r'\b([A-Z]-[A-Z]{1,2})\b',               # R-SF, C-GC
        r'\b([A-Z]{1,2}-[A-Z]{2,4})\b',          # R-MH, C-OFC
        r'\b(PD-?\d{1,2})\b',                    # PD-1, PD20
        r'\b(SP-?\d{1,2})\b',                    # SP-1, SP3
        r'\b([A-Z]{2}-[A-Z]{1,2}\d?)\b',         # AP-AR, AP-E1, NP-G, NP-W
        r'\b([A-Z]{1,2}-[A-Z])\b',               # O-I, M-X, P-O
        r'\b([A-Z]\d[A-Z]?)\b',                  # A1, B4, R4A, M1, M2
        r'\b(MX-[A-Z])\b',                       # MX-N
        r'\b(PO-[A-Z])\b',                       # PO-I
    ]

    def __init__(
        self,
        zoneomics_dir: str = "data/zoneomics",
        municode_dir: str = "tmp/zoning_ordinance",
        context_window: int = 500,
        max_passages_per_code: int = 10
    ):
        self.zoneomics_dir = Path(zoneomics_dir)
        self.municode_dir = Path(municode_dir)
        self.context_window = context_window
        self.max_passages_per_code = max_passages_per_code

        self.city_matcher = CityMatcher(
            str(self.zoneomics_dir),
            str(self.municode_dir)
        )

        self.pattern_re = re.compile('|'.join(f'({p})' for p in self.ZONE_PATTERNS))

    def align_data(
        self,
        data_dir: str,
        negative_positive_ratio: float = 1.0
    ) -> Dict[str, int]:
        """
        Create aligned validator data from extractor data.

        Args:
            data_dir: Directory containing extractor train.jsonl, test.jsonl
            negative_positive_ratio: Ratio of negative to positive examples

        Returns:
            Dictionary with counts per split
        """
        data_path = Path(data_dir)

        counts = {}

        for split in ['train', 'val', 'test']:
            print(f"\n=== Processing {split} split ===")

            # Load zone codes from extractor data
            extractor_zones = load_extractor_zones(data_path, split)

            if not extractor_zones:
                print(f"  No extractor data for {split}")
                # Write empty file
                with open(data_path / f"validator_{split}.jsonl", 'w') as f:
                    pass
                counts[split] = 0
                continue

            print(f"  Found {sum(len(z) for z in extractor_zones.values())} zone codes across {len(extractor_zones)} cities")

            # Generate validator examples for each city
            all_examples = []

            for city_key, city_data in extractor_zones.items():
                # Use original city/state names from extractor data
                city = city_data['city']
                state = city_data['state']
                positive_codes = city_data['zones']

                examples = self._prepare_city_aligned(
                    state, city, positive_codes, negative_positive_ratio
                )

                if examples:
                    pos = sum(1 for e in examples if e.label == 1)
                    neg = sum(1 for e in examples if e.label == 0)
                    print(f"  {city}, {state}: {pos} positive, {neg} negative")
                    all_examples.extend(examples)

            # Save examples
            output_file = data_path / f"validator_{split}.jsonl"
            with open(output_file, 'w') as f:
                for ex in all_examples:
                    f.write(json.dumps(asdict(ex)) + '\n')

            counts[split] = len(all_examples)
            print(f"  Saved {len(all_examples)} examples to {output_file}")

        # Save stats
        stats = {
            'aligned': True,
            'counts': counts,
        }
        with open(data_path / "validator_stats.json", 'w') as f:
            json.dump(stats, f, indent=2)

        return counts

    def _prepare_city_aligned(
        self,
        state: str,
        city: str,
        positive_codes: Set[str],
        negative_positive_ratio: float
    ) -> List[ValidatorExample]:
        """
        Prepare validator examples for a city using extractor's zone codes as ground truth.
        """
        # Find ordinance path
        match = self.city_matcher.get_match(state, city)
        if not match:
            return []

        ordinance_path = Path(match.municode_path)
        if not ordinance_path.exists():
            return []

        # Parse ordinances
        parser = OrdinanceParser(ordinance_path)
        documents = parser.parse_all(zoning_only=True)
        if not documents:
            return []

        # Combine all text
        full_text = self._combine_documents(documents)
        if not full_text:
            return []

        positive_examples = []
        negative_examples = []

        # Normalize positive codes for comparison
        positive_codes_normalized = {normalize_zone_code(c) for c in positive_codes}

        # STEP 1: Find passages for each positive code by direct search
        for code in positive_codes:
            normalized_code = normalize_zone_code(code)
            passages = self._find_passages_for_code(full_text, code)

            if passages:
                passages = passages[:self.max_passages_per_code]
                example = ValidatorExample(
                    code=normalized_code,
                    passages=passages,
                    label=1,
                    city=city,
                    state=state
                )
                positive_examples.append(example)

        # STEP 2: Find negative candidates via pattern matching
        candidate_passages = self._find_all_candidates(full_text)

        for code, passages in candidate_passages.items():
            normalized_code = normalize_zone_code(code)

            # Skip if it's a positive code
            if normalized_code in positive_codes_normalized:
                continue

            # Skip very short codes
            if len(normalized_code) < 2:
                continue

            passages = passages[:self.max_passages_per_code]
            if not passages:
                continue

            example = ValidatorExample(
                code=normalized_code,
                passages=passages,
                label=0,
                city=city,
                state=state
            )
            negative_examples.append(example)

        # Balance negative examples
        target_neg_count = int(len(positive_examples) * negative_positive_ratio)
        if len(negative_examples) > target_neg_count:
            negative_examples = random.sample(negative_examples, target_neg_count)

        return positive_examples + negative_examples

    def _find_passages_for_code(self, text: str, code: str) -> List[str]:
        """
        Find passages containing a specific zone code using direct search.
        Handles variations like R-1, R1, R 1, etc.
        """
        passages = []

        # Create variations of the code to search for
        variations = self._get_code_variations(code)

        for variant in variations:
            # Case-insensitive search
            pattern = re.compile(re.escape(variant), re.IGNORECASE)

            for match in pattern.finditer(text):
                start = max(0, match.start() - self.context_window)
                end = min(len(text), match.end() + self.context_window)
                passage = text[start:end].strip()

                # Avoid duplicate passages
                if passage not in passages:
                    passages.append(passage)

                if len(passages) >= self.max_passages_per_code:
                    break

            if len(passages) >= self.max_passages_per_code:
                break

        return passages

    def _get_code_variations(self, code: str) -> List[str]:
        """
        Generate variations of a zone code to search for.
        E.g., 'R-1' -> ['R-1', 'R1', 'R 1']
        """
        variations = [code]

        # Add version without hyphen
        if '-' in code:
            variations.append(code.replace('-', ''))
            variations.append(code.replace('-', ' '))

        # Add version with hyphen if none
        if '-' not in code:
            # Try to insert hyphen between letters and numbers
            import re
            with_hyphen = re.sub(r'([A-Za-z])(\d)', r'\1-\2', code)
            if with_hyphen != code:
                variations.append(with_hyphen)

        return variations

    def _find_all_candidates(self, text: str) -> Dict[str, List[str]]:
        """Find all candidate zone codes in text with their passages."""
        candidate_passages = defaultdict(list)

        for match in self.pattern_re.finditer(text):
            code = match.group(0)

            # Skip common words
            if code.upper() in ['THE', 'AND', 'FOR', 'ARE', 'NOT', 'BUT', 'CAN', 'MAY', 'ALL', 'USE', 'OF', 'OR']:
                continue

            # Extract context
            start = max(0, match.start() - self.context_window)
            end = min(len(text), match.end() + self.context_window)
            passage = text[start:end].strip()

            candidate_passages[code].append(passage)

        return candidate_passages

    def _combine_documents(self, documents) -> str:
        """Combine multiple documents into single text."""
        parts = []
        for doc in documents:
            for section in doc.sections:
                if section.content:
                    parts.append(section.content)
        return "\n\n".join(parts)


def main():
    import argparse

    parser = argparse.ArgumentParser(description="Align validator data with extractor data")
    parser.add_argument("--data-dir", default="model/zoning_codes_extract/training/data_test",
                        help="Directory with extractor data")
    parser.add_argument("--neg-pos-ratio", type=float, default=1.0,
                        help="Ratio of negative to positive examples")
    parser.add_argument("--zoneomics-dir", default="data/zoneomics",
                        help="Directory with zoneomics CSVs")
    parser.add_argument("--municode-dir", default="collector/tmp/zoning_ordinance",
                        help="Directory with municode ordinances")

    args = parser.parse_args()

    preparator = AlignedValidatorDataPreparator(
        zoneomics_dir=args.zoneomics_dir,
        municode_dir=args.municode_dir
    )

    counts = preparator.align_data(
        data_dir=args.data_dir,
        negative_positive_ratio=args.neg_pos_ratio
    )

    print("\n=== Alignment Complete ===")
    for split, count in counts.items():
        print(f"  {split}: {count} examples")


if __name__ == "__main__":
    main()
