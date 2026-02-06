"""
Prepare training data for the validator model (binary classification).

This script:
1. Loads ground truth zone codes from zoneomics CSVs
2. Parses municode ordinances
3. Finds all candidate zone codes in text (pattern matching)
4. Labels candidates as positive (real zone code) or negative (false positive)
5. Exports training data for binary classification
"""

import json
import re
import random
from pathlib import Path
from dataclasses import dataclass, asdict
from typing import List, Dict, Set, Tuple, Optional
from collections import defaultdict

from transformers import AutoTokenizer

# Import from parent module
import sys
sys.path.append(str(Path(__file__).parent.parent.parent))

from zoning_codes_extract import (
    CityMatcher,
    OrdinanceParser,
    load_zoneomics_csv,
    normalize_zone_code
)

from city_splits import get_or_create_splits, get_city_key


@dataclass
class ValidatorExample:
    """A training example for the validator."""
    code: str
    passages: List[str]
    label: int  # 1 = valid zone code, 0 = false positive
    city: str
    state: str


class ValidatorDataPreparator:
    """
    Prepares training data for the validator binary classification model.

    Strategy:
    - Positive examples: Zone codes from zoneomics CSVs found in ordinances
    - Negative examples: Pattern matches in text that are NOT in ground truth
    """

    # Zone code patterns for finding candidates
    ZONE_PATTERNS = [
        r'\b([A-Z]{1,3}-?\d{1,2})\b',           # R-1, C-2, I-1
        r'\b([A-Z]{2,4})\b',                     # AG, MU, RMU
        r'\b([A-Z]-[A-Z]{1,2})\b',              # R-SF, C-GC
        r'\b([A-Z]{1,2}/[A-Z]{1,2})\b',         # M/H, R/O
        r'\b([A-Z]{1,2}-[A-Z]{2,4})\b',         # R-MH, C-OFC
    ]

    def __init__(
        self,
        zoneomics_dir: str = "data/zoneomics",
        municode_dir: str = "tmp/zoning_ordinance",
        context_window: int = 500,
        max_passages_per_code: int = 10,
        min_passages_per_code: int = 2
    ):
        """
        Initialize preparator.

        Args:
            zoneomics_dir: Directory with ground truth CSVs
            municode_dir: Directory with scraped ordinances
            context_window: Characters of context around each code mention
            max_passages_per_code: Maximum passages to collect per code
            min_passages_per_code: Minimum passages required to include a code
        """
        self.zoneomics_dir = Path(zoneomics_dir)
        self.municode_dir = Path(municode_dir)
        self.context_window = context_window
        self.max_passages_per_code = max_passages_per_code
        self.min_passages_per_code = min_passages_per_code

        # Initialize components
        self.city_matcher = CityMatcher(
            str(self.zoneomics_dir),
            str(self.municode_dir)
        )

        # Compile patterns
        self.pattern_re = re.compile('|'.join(f'({p})' for p in self.ZONE_PATTERNS))

        print(f"Initialized validator data preparator")

    def prepare_all(
        self,
        output_dir: str = "model/zoning_codes_extract/training/data",
        train_ratio: float = 0.8,
        val_ratio: float = 0.1,
        test_ratio: float = 0.1,
        states: Optional[List[str]] = None,
        max_cities: Optional[int] = None,
        negative_positive_ratio: float = 1.0,
        force_new_splits: bool = False
    ) -> Dict[str, int]:
        """
        Prepare validator training data from all matched cities.

        Args:
            output_dir: Where to save train/val/test files
            train_ratio: Proportion for training
            val_ratio: Proportion for validation
            test_ratio: Proportion for testing
            states: Specific states to process (None for all)
            max_cities: Maximum cities to process (None for all)
            negative_positive_ratio: Ratio of negative to positive examples
            force_new_splits: If True, regenerate city splits even if file exists

        Returns:
            Dictionary with counts per split
        """
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)

        # Get matched cities
        matches = self.city_matcher.find_matches()
        print(f"Found {len(matches)} matched cities")

        # Filter by state if specified
        if states:
            states_lower = [s.lower() for s in states]
            matches = [m for m in matches if m.state.lower() in states_lower]
            print(f"Filtered to {len(matches)} cities in states: {states}")

        # Limit number of cities if specified
        if max_cities and len(matches) > max_cities:
            matches = matches[:max_cities]
            print(f"Limited to {max_cities} cities")

        # Generate city keys for splitting
        city_keys = [get_city_key(m.state, m.city_name) for m in matches]

        # Get or create shared city splits (same as extractor uses)
        city_splits = get_or_create_splits(
            cities=city_keys,
            output_dir=output_dir,
            train_ratio=train_ratio,
            val_ratio=val_ratio,
            test_ratio=test_ratio,
            force_regenerate=force_new_splits
        )

        # Process each city
        all_examples = []
        city_example_map = {}  # Map city_key -> list of examples
        pos_count = 0
        neg_count = 0

        for i, match in enumerate(matches):
            city_key = get_city_key(match.state, match.city_name)
            print(f"\nProcessing {i+1}/{len(matches)}: {match.city_name}, {match.state}")

            try:
                examples = self.prepare_city(match.state, match.city_name, negative_positive_ratio)
                if examples:
                    pos = sum(1 for e in examples if e.label == 1)
                    neg = sum(1 for e in examples if e.label == 0)
                    all_examples.extend(examples)
                    city_example_map[city_key] = examples
                    pos_count += pos
                    neg_count += neg
                    print(f"  Generated {len(examples)} examples ({pos} positive, {neg} negative)")
                else:
                    print(f"  No examples generated")
            except Exception as e:
                print(f"  Error: {e}")
                continue

        print(f"\nTotal examples: {len(all_examples)} ({pos_count} positive, {neg_count} negative)")

        # Split examples using the shared city splits
        splits = self._split_by_city_splits(city_example_map, city_splits)

        # Save splits
        counts = {}
        for split_name, examples in splits.items():
            output_file = output_path / f"validator_{split_name}.jsonl"
            self._save_examples(examples, str(output_file))
            counts[split_name] = len(examples)
            print(f"Saved {len(examples)} examples to {output_file}")

        # Save statistics
        stats = {
            'total_examples': len(all_examples),
            'positive_examples': pos_count,
            'negative_examples': neg_count,
            'splits': counts,
            'num_cities': len(matches),
            'train_cities': city_splits['train'],
            'val_cities': city_splits['val'],
            'test_cities': city_splits['test'],
        }
        stats_file = output_path / "validator_stats.json"
        with open(stats_file, 'w') as f:
            json.dump(stats, f, indent=2)

        return counts

    def prepare_city(
        self,
        state: str,
        city: str,
        negative_positive_ratio: float = 1.0
    ) -> List[ValidatorExample]:
        """
        Prepare validator training data for a single city.

        Args:
            state: State name or abbreviation
            city: City name
            negative_positive_ratio: Ratio of negative to positive examples

        Returns:
            List of validator training examples
        """
        # Load ground truth zone codes
        csv_path = self._find_csv_path(state, city)
        if not csv_path or not csv_path.exists():
            print(f"  CSV not found: {csv_path}")
            return []

        districts = load_zoneomics_csv(str(csv_path))
        if not districts:
            print(f"  No districts in CSV")
            return []

        # Normalize ground truth codes
        ground_truth_codes = {normalize_zone_code(d.zone_code) for d in districts}

        # Parse ordinances
        ordinance_path = self._find_ordinance_path(state, city)
        if not ordinance_path or not ordinance_path.exists():
            print(f"  Ordinance dir not found: {ordinance_path}")
            return []

        parser = OrdinanceParser(ordinance_path)
        documents = parser.parse_all(zoning_only=True)
        if not documents:
            print(f"  No ordinance documents found")
            return []

        # Combine all text
        full_text = self._combine_documents(documents)
        if not full_text:
            print(f"  No text extracted from ordinances")
            return []

        # Find all candidate codes in text
        candidate_passages = self._find_all_candidates(full_text)

        # Separate into positive and negative examples
        positive_examples = []
        negative_examples = []

        for code, passages in candidate_passages.items():
            normalized_code = normalize_zone_code(code)

            # Skip if too few passages
            if len(passages) < self.min_passages_per_code:
                continue

            # Limit passages
            passages = passages[:self.max_passages_per_code]

            # Check if this is a real zone code
            if normalized_code in ground_truth_codes:
                # Positive example
                example = ValidatorExample(
                    code=normalized_code,
                    passages=passages,
                    label=1,
                    city=city,
                    state=state
                )
                positive_examples.append(example)
            else:
                # Negative example
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

    def _find_all_candidates(self, text: str) -> Dict[str, List[str]]:
        """
        Find all candidate zone codes in text with their passages.

        Args:
            text: Full ordinance text

        Returns:
            Dictionary mapping code -> list of passages
        """
        candidate_passages = defaultdict(list)

        # Find all matches
        for match in self.pattern_re.finditer(text):
            code = match.group(0)

            # Skip very common words that match patterns
            if code.upper() in ['THE', 'AND', 'FOR', 'ARE', 'NOT', 'BUT', 'CAN', 'MAY', 'ALL']:
                continue

            # Extract context
            start = max(0, match.start() - self.context_window)
            end = min(len(text), match.end() + self.context_window)
            passage = text[start:end].strip()

            candidate_passages[code].append(passage)

        return candidate_passages

    def _split_by_city(
        self,
        examples: List[ValidatorExample],
        train_ratio: float,
        val_ratio: float,
        test_ratio: float
    ) -> Dict[str, List[ValidatorExample]]:
        """Split examples by city to prevent data leakage."""
        # Group by city
        city_examples = defaultdict(list)
        for ex in examples:
            key = f"{ex.state}_{ex.city}"
            city_examples[key].append(ex)

        # Shuffle cities
        cities = list(city_examples.keys())
        random.shuffle(cities)

        # Split cities
        n_cities = len(cities)
        n_train = int(n_cities * train_ratio)
        n_val = int(n_cities * val_ratio)

        train_cities = cities[:n_train]
        val_cities = cities[n_train:n_train + n_val]
        test_cities = cities[n_train + n_val:]

        # Collect examples
        splits = {
            'train': [],
            'val': [],
            'test': []
        }

        for city in train_cities:
            splits['train'].extend(city_examples[city])
        for city in val_cities:
            splits['val'].extend(city_examples[city])
        for city in test_cities:
            splits['test'].extend(city_examples[city])

        print(f"\nSplit cities:")
        print(f"  Train: {len(train_cities)} cities, {len(splits['train'])} examples")
        print(f"  Val: {len(val_cities)} cities, {len(splits['val'])} examples")
        print(f"  Test: {len(test_cities)} cities, {len(splits['test'])} examples")

        return splits

    def _split_by_city_splits(
        self,
        city_example_map: Dict[str, List[ValidatorExample]],
        city_splits: Dict[str, List[str]]
    ) -> Dict[str, List[ValidatorExample]]:
        """
        Split examples using pre-defined city splits.

        Args:
            city_example_map: Map of city_key -> list of examples
            city_splits: Pre-defined splits with 'train', 'val', 'test' city lists

        Returns:
            Dict with 'train', 'val', 'test' keys containing examples
        """
        splits = {
            'train': [],
            'val': [],
            'test': []
        }

        for city_key in city_splits.get('train', []):
            if city_key in city_example_map:
                splits['train'].extend(city_example_map[city_key])

        for city_key in city_splits.get('val', []):
            if city_key in city_example_map:
                splits['val'].extend(city_example_map[city_key])

        for city_key in city_splits.get('test', []):
            if city_key in city_example_map:
                splits['test'].extend(city_example_map[city_key])

        print(f"\nSplit using shared city_splits.json:")
        print(f"  Train: {len(city_splits.get('train', []))} cities, {len(splits['train'])} examples")
        print(f"  Val: {len(city_splits.get('val', []))} cities, {len(splits['val'])} examples")
        print(f"  Test: {len(city_splits.get('test', []))} cities, {len(splits['test'])} examples")

        return splits

    def _save_examples(self, examples: List[ValidatorExample], output_file: str):
        """Save examples to JSONL file."""
        with open(output_file, 'w') as f:
            for ex in examples:
                f.write(json.dumps(asdict(ex)) + '\n')

    def _find_csv_path(self, state: str, city: str) -> Optional[Path]:
        """Find CSV path for a city."""
        match = self.city_matcher.get_match(state, city)
        if match:
            return Path(match.zoneomics_path)
        return None

    def _find_ordinance_path(self, state: str, city: str) -> Optional[Path]:
        """Find ordinance directory for a city."""
        match = self.city_matcher.get_match(state, city)
        if match:
            return Path(match.municode_path)
        return None

    def _combine_documents(self, documents) -> str:
        """Combine multiple documents into single text."""
        parts = []
        for doc in documents:
            for section in doc.sections:
                if section.content:
                    parts.append(section.content)
        return "\n\n".join(parts)


def main():
    """Main entry point."""
    import argparse

    parser = argparse.ArgumentParser(description="Prepare validator training data")
    parser.add_argument("--output-dir", default="model/zoning_codes_extract/training/data",
                        help="Output directory for training data")
    parser.add_argument("--states", nargs="+", default=["alabama"],
                        help="States to process")
    parser.add_argument("--max-cities", type=int, default=None,
                        help="Maximum number of cities to process")
    parser.add_argument("--neg-pos-ratio", type=float, default=1.0,
                        help="Ratio of negative to positive examples")
    parser.add_argument("--zoneomics-dir", default="data/zoneomics",
                        help="Directory with zoneomics CSVs")
    parser.add_argument("--municode-dir", default="tmp/zoning_ordinance",
                        help="Directory with municode ordinances")

    args = parser.parse_args()

    preparator = ValidatorDataPreparator(
        zoneomics_dir=args.zoneomics_dir,
        municode_dir=args.municode_dir
    )

    counts = preparator.prepare_all(
        output_dir=args.output_dir,
        states=args.states,
        max_cities=args.max_cities,
        negative_positive_ratio=args.neg_pos_ratio
    )

    print("\n=== Validator Training Data Preparation Complete ===")
    print(f"Train: {counts['train']} examples")
    print(f"Val: {counts['val']} examples")
    print(f"Test: {counts['test']} examples")


if __name__ == "__main__":
    main()
