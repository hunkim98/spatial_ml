"""
Prepare training data for token classification (BIO tagging).

This script:
1. Loads zoneomics CSVs (ground truth zone codes)
2. Parses municode ordinances
3. Uses TextAligner to find zone codes in text
4. Creates BIO tags for each token
5. Splits by city into train/val/test
6. Exports in HuggingFace datasets format
"""

import json
import random
from pathlib import Path
from dataclasses import dataclass, asdict
from typing import List, Dict, Tuple, Optional, Set
from collections import defaultdict

from transformers import AutoTokenizer

# Import from parent module
import sys
sys.path.append(str(Path(__file__).parent.parent.parent))

from zoning_codes_extract import (
    CityMatcher,
    OrdinanceParser,
    TextAligner,
    load_zoneomics_csv,
    normalize_zone_code
)

from city_splits import get_or_create_splits, get_city_key


@dataclass
class TokenClassificationExample:
    """A single training example with BIO tags."""
    tokens: List[str]
    tags: List[str]
    city: str
    state: str


class TrainingDataPreparator:
    """
    Prepares BIO-tagged training data for token classification.

    Uses ground truth zone codes from zoneomics CSVs and finds their
    mentions in the municode ordinances to create labeled training data.
    """

    BIO_TAGS = ['O', 'B-ZONE', 'I-ZONE']

    def __init__(
        self,
        zoneomics_dir: str = "data/zoneomics",
        municode_dir: str = "tmp/zoning_ordinance",
        tokenizer_name: str = "bert-base-uncased",
        max_seq_length: int = 512,
        context_window: int = 500
    ):
        """
        Initialize preparator.

        Args:
            zoneomics_dir: Directory with ground truth CSVs
            municode_dir: Directory with scraped ordinances
            tokenizer_name: Tokenizer to use for tokenization
            max_seq_length: Maximum sequence length
            context_window: Characters of context around each zone code
        """
        self.zoneomics_dir = Path(zoneomics_dir)
        self.municode_dir = Path(municode_dir)
        self.max_seq_length = max_seq_length
        self.context_window = context_window

        # Initialize components
        self.city_matcher = CityMatcher(
            str(self.zoneomics_dir),
            str(self.municode_dir)
        )
        self.tokenizer = AutoTokenizer.from_pretrained(tokenizer_name)

        print(f"Initialized with tokenizer: {tokenizer_name}")

    def prepare_all(
        self,
        output_dir: str = "model/zoning_codes_extract/training/data",
        train_ratio: float = 0.8,
        val_ratio: float = 0.1,
        test_ratio: float = 0.1,
        states: Optional[List[str]] = None,
        max_cities: Optional[int] = None,
        force_new_splits: bool = False
    ) -> Dict[str, int]:
        """
        Prepare training data from all matched cities.

        Args:
            output_dir: Where to save train/val/test files
            train_ratio: Proportion for training
            val_ratio: Proportion for validation
            test_ratio: Proportion for testing
            states: Specific states to process (None for all)
            max_cities: Maximum cities to process (None for all)
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

        # Get or create shared city splits
        city_splits = get_or_create_splits(
            cities=city_keys,
            output_dir=output_dir,
            train_ratio=train_ratio,
            val_ratio=val_ratio,
            test_ratio=test_ratio,
            force_regenerate=force_new_splits
        )

        # Create lookup from city key to match
        key_to_match = {get_city_key(m.state, m.city_name): m for m in matches}

        # Process each city
        all_examples = []
        city_example_map = {}  # Map city_key -> list of examples

        for i, match in enumerate(matches):
            city_key = get_city_key(match.state, match.city_name)
            print(f"\nProcessing {i+1}/{len(matches)}: {match.city_name}, {match.state}")

            try:
                examples = self.prepare_city(match.state, match.city_name)
                if examples:
                    all_examples.extend(examples)
                    city_example_map[city_key] = examples
                    print(f"  Generated {len(examples)} examples")
                else:
                    print(f"  No examples generated")
            except Exception as e:
                print(f"  Error: {e}")
                continue

        print(f"\nTotal examples: {len(all_examples)}")

        # Split examples using the shared city splits
        splits = self._split_by_city_splits(city_example_map, city_splits)

        # Save splits
        counts = {}
        for split_name, examples in splits.items():
            output_file = output_path / f"{split_name}.jsonl"
            self._save_examples(examples, str(output_file))
            counts[split_name] = len(examples)
            print(f"Saved {len(examples)} examples to {output_file}")

        # Save statistics
        stats = {
            'total_examples': len(all_examples),
            'splits': counts,
            'num_cities': len(matches),
            'train_cities': city_splits['train'],
            'val_cities': city_splits['val'],
            'test_cities': city_splits['test'],
        }
        stats_file = output_path / "stats.json"
        with open(stats_file, 'w') as f:
            json.dump(stats, f, indent=2)

        return counts

    def prepare_city(
        self,
        state: str,
        city: str
    ) -> List[TokenClassificationExample]:
        """
        Prepare training data for a single city.

        Args:
            state: State name or abbreviation
            city: City name

        Returns:
            List of training examples
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

        # Create text aligner
        aligner = TextAligner(full_text)

        # Align each district to find it in text
        aligned_districts = aligner.align_all(districts)

        # Get all ground truth zone codes for this city
        # Filter out zone codes that are too short (< 2 chars) to avoid false positives
        # Single-letter codes like 'A', 'O', 'R' match too many things in text
        all_zone_codes_raw = [normalize_zone_code(d.zone_code) for d in districts]
        all_zone_codes = [zc for zc in all_zone_codes_raw if len(zc) >= 2]

        skipped_codes = set(all_zone_codes_raw) - set(all_zone_codes)
        if skipped_codes:
            print(f"  Skipped {len(skipped_codes)} short codes: {sorted(skipped_codes)}")

        # Create examples from aligned districts
        # Pass ALL zone codes so we can tag multiple codes in each context window
        examples = []
        seen_contexts = set()  # Avoid duplicate examples
        found_codes = set()  # Track which codes were found in text

        for aligned in aligned_districts:
            normalized_code = normalize_zone_code(aligned.zone_code)
            # Skip short codes
            if len(normalized_code) < 2:
                continue
            if aligned.source_text:  # If we found the zone code in text
                found_codes.add(normalized_code)
                # Create examples from the context around this zone code
                # Pass all zone codes so ALL codes in the context are tagged
                district_examples = self._create_examples_for_zone(
                    zone_code=aligned.zone_code,
                    all_zone_codes=all_zone_codes,
                    full_text=full_text,
                    city=city,
                    state=state,
                    seen_contexts=seen_contexts
                )
                examples.extend(district_examples)

        # Print coverage report
        total_valid_codes = len(all_zone_codes)
        found_count = len(found_codes)
        coverage_pct = 100 * found_count / total_valid_codes if total_valid_codes > 0 else 0
        print(f"  Coverage: {found_count}/{total_valid_codes} codes ({coverage_pct:.1f}%)")

        missing_codes = set(all_zone_codes) - found_codes
        if missing_codes and len(missing_codes) <= 20:
            print(f"  Missing: {sorted(missing_codes)}")
        elif missing_codes:
            print(f"  Missing: {len(missing_codes)} codes (showing first 20): {sorted(missing_codes)[:20]}")

        return examples

    def _create_examples_for_zone(
        self,
        zone_code: str,
        all_zone_codes: List[str],
        full_text: str,
        city: str,
        state: str,
        seen_contexts: set
    ) -> List[TokenClassificationExample]:
        """
        Create BIO-tagged examples for a specific zone code.

        Finds all mentions of the zone code in text and creates training
        examples with context around each mention. Tags ALL zone codes
        from all_zone_codes that appear in the context window.
        """
        import re
        examples = []

        # Normalize zone code for matching
        normalized_code = normalize_zone_code(zone_code)

        # Create flexible pattern (handles variations like "R-1", "R 1", "R1")
        # Use word boundaries to avoid matching parts of other words (e.g., "a 150" matching "A-1")
        code_pattern = re.escape(normalized_code)
        code_pattern = code_pattern.replace(r'\-', r'[-\s]?')  # Allow hyphen or space
        code_pattern = r'\b' + code_pattern + r'\b'  # Word boundaries

        for match in re.finditer(code_pattern, full_text, re.IGNORECASE):
            start_char = match.start()
            end_char = match.end()

            # Extract context window
            context_start = max(0, start_char - self.context_window)
            context_end = min(len(full_text), end_char + self.context_window)
            context_text = full_text[context_start:context_end]
            
            # Skip if we've already processed this context (avoid duplicates)
            context_key = (context_start, context_end)
            if context_key in seen_contexts:
                continue
            seen_contexts.add(context_key)

            # Find ALL zone code occurrences in this context window
            zone_spans = []  # List of (start, end) tuples for all zone codes

            for zc in all_zone_codes:
                # Skip zone codes that are too short (already filtered in prepare_city,
                # but double-check here for safety)
                if len(zc) < 2:
                    continue

                zc_pattern = re.escape(zc)
                zc_pattern = zc_pattern.replace(r'\-', r'[-\s]?')
                zc_pattern = r'\b' + zc_pattern + r'\b'  # Word boundaries

                for zc_match in re.finditer(zc_pattern, context_text, re.IGNORECASE):
                    zone_spans.append((zc_match.start(), zc_match.end()))
            
            # Merge overlapping spans
            zone_spans = self._merge_spans(zone_spans)

            # Tokenize context
            encoding = self.tokenizer(
                context_text,
                truncation=True,
                max_length=self.max_seq_length,
                return_offsets_mapping=True
            )

            tokens = self.tokenizer.convert_ids_to_tokens(encoding['input_ids'])
            offsets = encoding['offset_mapping']

            # Create BIO tags - tag ALL zone codes in the context
            tags = []
            for i, (token_start, token_end) in enumerate(offsets):
                if token_start is None or token_end is None:
                    # Special token
                    tags.append('O')
                else:
                    # Check if this token overlaps with any zone code span
                    tag = 'O'
                    for span_start, span_end in zone_spans:
                        if token_start >= span_start and token_end <= span_end:
                            # Token is inside a zone code span
                            if token_start == span_start:
                                tag = 'B-ZONE'
                            else:
                                tag = 'I-ZONE'
                            break
                    tags.append(tag)

            # Filter out examples with no zone tags (can happen with truncation)
            if 'B-ZONE' not in tags:
                continue

            # Create example
            example = TokenClassificationExample(
                tokens=tokens,
                tags=tags,
                city=city,
                state=state
            )
            examples.append(example)

        return examples
    
    def _merge_spans(self, spans: List[Tuple[int, int]]) -> List[Tuple[int, int]]:
        """Merge overlapping spans."""
        if not spans:
            return []
        
        # Sort by start position
        spans = sorted(spans, key=lambda x: x[0])
        
        merged = [spans[0]]
        for start, end in spans[1:]:
            last_start, last_end = merged[-1]
            if start <= last_end:
                # Overlapping, merge
                merged[-1] = (last_start, max(last_end, end))
            else:
                merged.append((start, end))
        
        return merged

    def _split_by_city(
        self,
        examples: List[TokenClassificationExample],
        train_ratio: float,
        val_ratio: float,
        test_ratio: float
    ) -> Dict[str, List[TokenClassificationExample]]:
        """
        Split examples by city to prevent data leakage.

        Args:
            examples: All examples
            train_ratio: Train proportion
            val_ratio: Validation proportion
            test_ratio: Test proportion

        Returns:
            Dict with 'train', 'val', 'test' keys
        """
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
        city_example_map: Dict[str, List[TokenClassificationExample]],
        city_splits: Dict[str, List[str]]
    ) -> Dict[str, List[TokenClassificationExample]]:
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

    def _save_examples(self, examples: List[TokenClassificationExample], output_file: str):
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

    parser = argparse.ArgumentParser(description="Prepare training data for zone code extraction")
    parser.add_argument("--output-dir", default="model/zoning_codes_extract/training/data",
                        help="Output directory for training data")
    parser.add_argument("--states", nargs="+", default=["alabama"],
                        help="States to process")
    parser.add_argument("--max-cities", type=int, default=None,
                        help="Maximum number of cities to process")
    parser.add_argument("--tokenizer", default="bert-base-uncased",
                        help="Tokenizer to use")
    parser.add_argument("--zoneomics-dir", default="data/zoneomics",
                        help="Directory with zoneomics CSVs")
    parser.add_argument("--municode-dir", default="tmp/zoning_ordinance",
                        help="Directory with municode ordinances")

    args = parser.parse_args()

    preparator = TrainingDataPreparator(
        zoneomics_dir=args.zoneomics_dir,
        municode_dir=args.municode_dir,
        tokenizer_name=args.tokenizer
    )

    counts = preparator.prepare_all(
        output_dir=args.output_dir,
        states=args.states,
        max_cities=args.max_cities
    )

    print("\n=== Training Data Preparation Complete ===")
    print(f"Train: {counts['train']} examples")
    print(f"Val: {counts['val']} examples")
    print(f"Test: {counts['test']} examples")


if __name__ == "__main__":
    main()
