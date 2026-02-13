"""
Prepare training data for the validator model (binary classification).

This script:
1. Loads ground truth zone codes from zoneomics CSVs
2. Parses municode ordinances
3. Generates POSITIVE examples: CSV-confirmed zone codes found in ordinance text
4. Generates NEGATIVE examples: False positives from trained extractor model
5. Exports balanced training data for binary classification

IMPORTANT: Uses CSV-based positives + extractor-based negatives for realistic validation task.
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

# Import extractor for negative generation
from zoning_codes_extract.src.extractor import ZoneExtractor

# Import pattern creation from extractor data prep
from prepare_extractor_data import _create_zone_code_pattern


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
    - Positive examples: CSV-confirmed zone codes found in ordinance text
    - Negative examples: False positives from trained extractor model
    """

    def __init__(
        self,
        zoneomics_dir: str = "data/zoneomics",
        municode_dir: str = "tmp/zoning_ordinance",
        extractor_model_path: Optional[str] = None,
        context_window: int = 500,
        max_passages_per_code: int = 10,
        min_passages_per_code: int = 2,
        negative_positive_ratio: float = 1.0
    ):
        """
        Initialize preparator.

        Args:
            zoneomics_dir: Directory with ground truth CSVs
            municode_dir: Directory with scraped ordinances
            extractor_model_path: Path to trained extractor model for negative generation
            context_window: Characters of context around each code mention
            max_passages_per_code: Maximum passages to collect per code
            min_passages_per_code: Minimum passages required to include a code
            negative_positive_ratio: Ratio of negative to positive examples
        """
        self.zoneomics_dir = Path(zoneomics_dir)
        self.municode_dir = Path(municode_dir)
        self.context_window = context_window
        self.max_passages_per_code = max_passages_per_code
        self.min_passages_per_code = min_passages_per_code
        self.negative_positive_ratio = negative_positive_ratio

        # Initialize components
        self.city_matcher = CityMatcher(
            str(self.zoneomics_dir),
            str(self.municode_dir)
        )

        # Initialize extractor for negative generation
        self.extractor = None
        if extractor_model_path and Path(extractor_model_path).exists():
            print(f"Loading extractor from {extractor_model_path}")
            self.extractor = ZoneExtractor(
                model_path=extractor_model_path,
                min_score=0.3,  # Lower threshold to catch more potential FPs
                device="cpu"
            )
        else:
            print("WARNING: No extractor model provided. Will skip negative generation.")

        print(f"Initialized validator data preparator")

    def prepare_all(
        self,
        output_dir: str = "model/zoning_codes_extract/training/data",
        train_ratio: float = 0.8,
        val_ratio: float = 0.1,
        test_ratio: float = 0.1,
        states: Optional[List[str]] = None,
        max_cities: Optional[int] = None,
        use_extractor_for_negatives: bool = True,
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
            use_extractor_for_negatives: If True, use extractor for negatives (default: True)
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

        # Determine which cities to use for negative generation
        # Use val/test cities (held-out from extractor training)
        negative_generation_cities = set(
            city_splits.get('val', []) + city_splits.get('test', [])
        )

        # Process each city
        all_examples = []
        city_example_map = {}  # Map city_key -> list of examples
        pos_count = 0
        neg_count = 0

        for i, match in enumerate(matches):
            city_key = get_city_key(match.state, match.city_name)
            print(f"\nProcessing {i+1}/{len(matches)}: {match.city_name}, {match.state}")

            # Only generate negatives for held-out cities
            generate_negatives = (
                use_extractor_for_negatives
                and city_key in negative_generation_cities
            )

            if generate_negatives:
                print(f"  Using extractor for negatives (held-out city)")
            else:
                print(f"  Positives only (training city)")

            try:
                examples = self.prepare_city(
                    match.state,
                    match.city_name,
                    generate_negatives=generate_negatives
                )
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
                import traceback
                traceback.print_exc()
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
        generate_negatives: bool = True
    ) -> List[ValidatorExample]:
        """
        Prepare validator training data for a single city.

        Args:
            state: State name or abbreviation
            city: City name
            generate_negatives: If True, use extractor to generate negatives (default: True)

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

        # Normalize ground truth codes (filter out single-letter codes)
        ground_truth_codes = {
            normalize_zone_code(d.zone_code)
            for d in districts
            if len(normalize_zone_code(d.zone_code)) >= 2
        }

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

        # STEP 1: Generate positive examples (CSV-based)
        positive_candidates = self._find_positive_candidates(full_text, ground_truth_codes)

        positive_examples = []
        for code, passages in positive_candidates.items():
            positive_examples.append(ValidatorExample(
                code=code,
                passages=passages,
                label=1,
                city=city,
                state=state
            ))

        print(f"  Generated {len(positive_examples)} positive examples")

        # STEP 2: Generate negative examples (Extractor-based)
        negative_examples = []

        if generate_negatives:
            negative_candidates = self._generate_negative_candidates(full_text, ground_truth_codes)

            for code, passages in negative_candidates.items():
                negative_examples.append(ValidatorExample(
                    code=code,
                    passages=passages,
                    label=0,
                    city=city,
                    state=state
                ))

            print(f"  Generated {len(negative_examples)} negative examples (extractor FPs)")
        else:
            print(f"  Skipped negative generation (generate_negatives=False)")

        # STEP 3: Balance negatives to match ratio
        if negative_examples:
            target_negatives = int(len(positive_examples) * self.negative_positive_ratio)

            if len(negative_examples) > target_negatives:
                negative_examples = random.sample(negative_examples, target_negatives)
                print(f"  Sampled down to {len(negative_examples)} negatives (ratio={self.negative_positive_ratio})")

        return positive_examples + negative_examples

    def _find_positive_candidates(
        self,
        full_text: str,
        ground_truth_codes: Set[str]
    ) -> Dict[str, List[str]]:
        """
        Find confirmed CSV zone codes in ordinance text.

        Returns passages where each confirmed code appears.
        Uses same strategy as extractor data preparation.

        Args:
            full_text: Complete ordinance text
            ground_truth_codes: Set of normalized CSV codes

        Returns:
            Dict mapping code -> list of passage strings
        """
        candidate_passages = defaultdict(list)

        for zone_code in ground_truth_codes:
            # Create flexible pattern (handles R-1, R 1, R1)
            pattern = _create_zone_code_pattern(zone_code)

            # Find all occurrences
            for match in re.finditer(pattern, full_text, re.IGNORECASE):
                start_char = match.start()
                end_char = match.end()

                # Extract context passage
                passage_start = max(0, start_char - self.context_window)
                passage_end = min(len(full_text), end_char + self.context_window)
                passage = full_text[passage_start:passage_end].strip()

                # Normalize and store
                normalized_code = normalize_zone_code(zone_code)
                candidate_passages[normalized_code].append(passage)

        # Filter codes with too few passages
        return {
            code: passages[:self.max_passages_per_code]
            for code, passages in candidate_passages.items()
            if len(passages) >= self.min_passages_per_code
        }

    def _generate_negative_candidates(
        self,
        full_text: str,
        ground_truth_codes: Set[str]
    ) -> Dict[str, List[str]]:
        """
        Generate negative examples using trained extractor.

        Runs extractor on text and collects false positives:
        - Codes predicted by extractor
        - BUT not present in ground truth CSV

        Args:
            full_text: Complete ordinance text
            ground_truth_codes: Set of normalized CSV codes

        Returns:
            Dict mapping false positive code -> list of passages
        """
        if self.extractor is None:
            print("  No extractor model available. Skipping negative generation.")
            return {}

        # Run extractor inference
        spans = self.extractor.extract(full_text)

        # Group spans by normalized code
        code_to_spans = defaultdict(list)
        for span in spans:
            normalized = self.extractor.normalize_extracted_code(span.text)
            code_to_spans[normalized].append(span)

        # Collect false positives (predicted but not in CSV)
        negative_passages = defaultdict(list)

        for code, code_spans in code_to_spans.items():
            # Check if this is a false positive
            if code not in ground_truth_codes:
                # Extract passages around each occurrence
                for span in code_spans[:self.max_passages_per_code]:
                    passage_start = max(0, span.start - self.context_window)
                    passage_end = min(len(full_text), span.end + self.context_window)
                    passage = full_text[passage_start:passage_end].strip()
                    negative_passages[code].append(passage)

        # Filter codes with too few passages
        return {
            code: passages[:self.max_passages_per_code]
            for code, passages in negative_passages.items()
            if len(passages) >= self.min_passages_per_code
        }

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
    parser.add_argument("--states", nargs="+", default=None,
                        help="States to process")
    parser.add_argument("--max-cities", type=int, default=None,
                        help="Maximum number of cities to process")
    parser.add_argument("--neg-pos-ratio", type=float, default=1.0,
                        help="Ratio of negative to positive examples")
    parser.add_argument("--zoneomics-dir", default="data/zoneomics",
                        help="Directory with zoneomics CSVs")
    parser.add_argument("--municode-dir", default="tmp/zoning_ordinance",
                        help="Directory with municode ordinances")
    parser.add_argument("--extractor-model",
                        default="model/zoning_codes_extract/artifacts/models/extractor",
                        help="Path to trained extractor model for negative generation")
    parser.add_argument("--no-extractor-negatives", action="store_true",
                        help="Skip extractor-based negative generation (positives only)")

    args = parser.parse_args()

    preparator = ValidatorDataPreparator(
        zoneomics_dir=args.zoneomics_dir,
        municode_dir=args.municode_dir,
        extractor_model_path=args.extractor_model,
        negative_positive_ratio=args.neg_pos_ratio
    )

    counts = preparator.prepare_all(
        output_dir=args.output_dir,
        states=args.states,
        max_cities=args.max_cities,
        use_extractor_for_negatives=not args.no_extractor_negatives
    )

    print("\n=== Validator Training Data Preparation Complete ===")
    print(f"Train: {counts['train']} examples")
    print(f"Val: {counts['val']} examples")
    print(f"Test: {counts['test']} examples")


if __name__ == "__main__":
    main()
