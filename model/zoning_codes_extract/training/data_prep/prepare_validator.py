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
sys.path.append(str(Path(__file__).parent.parent.parent.parent))

from zoning_extract import (
    CityMatcher,
    OrdinanceParser,
    load_zoneomics_csv,
    normalize_zone_code
)

from .city_splits import get_or_create_splits, get_city_key

# Import extractor for negative generation
from zoning_extract.core.extractor import ZoneExtractor

# Import pattern creation from extractor data prep
from .prepare_extractor import _create_zone_code_pattern


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
        extractor_device: str = "auto",
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
            extractor_device: Device for extractor inference ('auto', 'cuda', 'cpu')
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
            resolved_device = None if extractor_device == "auto" else extractor_device
            print(f"Loading extractor from {extractor_model_path}")
            self.extractor = ZoneExtractor(
                model_path=extractor_model_path,
                min_score=0.3,  # Lower threshold to catch more potential FPs
                device=resolved_device
            )
            print(f"Extractor inference device: {self.extractor.device}")
        else:
            print("WARNING: No extractor model provided. Will skip negative generation.")

        print(f"Initialized validator data preparator")

    def prepare_all(
        self,
        output_dir: str = "model/zoning_codes_extract/training/data",
        train_ratio: float = 0.85,
        test_ratio: float = 0.15,
        states: Optional[List[str]] = None,
        use_extractor_for_negatives: bool = True,
        force_new_splits: bool = False
    ) -> Dict[str, int]:
        """
        Prepare validator training data from all matched cities using 2-way splitting (train/test).

        Args:
            output_dir: Where to save train/test files
            train_ratio: Proportion for training (default: 0.85)
            test_ratio: Proportion for testing (default: 0.15)
            states: Specific states to process (None for all)
            n_cities: Exact number of cities to use (None for all available)
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

        # NOTE: For validator, we use existing city_splits.json from extractor
        # to ensure both models use the exact same cities

        # Generate city keys for splitting
        city_keys = [get_city_key(m.state, m.city_name) for m in matches]

        # Validate extractor availability for negative generation
        if use_extractor_for_negatives and self.extractor is None:
            raise RuntimeError(
                "ERROR: Extractor model required for negative generation.\n"
                "Please train the extractor first, then re-run validator data prep."
            )

        # Get or create shared city splits (same as extractor uses)
        city_splits = get_or_create_splits(
            cities=city_keys,
            output_dir=output_dir,
            train_ratio=train_ratio,
            test_ratio=test_ratio,
            force_regenerate=force_new_splits
        )

        # Generate negatives for ALL cities (train and test)
        # This ensures we have negative examples even if test set is filtered
        negative_generation_cities = set(
            city_splits.get('train', []) + city_splits.get('test', [])
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
            output_file = output_path / f"{split_name}_validator.jsonl"
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
            'train_validator_cities': city_splits.get('train_validator', []),
            'val_validator_cities': city_splits.get('val_validator', []),
            'test_cities': city_splits.get('test', []),
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

        # Balance negatives to match ratio
        if negative_examples:
            target_negatives = int(len(positive_examples) * self.negative_positive_ratio)

            if len(negative_examples) > target_negatives:
                negative_examples = random.sample(negative_examples, target_negatives)
                print(f"  Balanced to {len(negative_examples)} negatives (ratio={self.negative_positive_ratio})")

        return positive_examples + negative_examples

    def _find_positive_candidates(
        self,
        full_text: str,
        ground_truth_codes: Set[str]
    ) -> Dict[str, List[str]]:
        """
        Find confirmed CSV zone codes in ordinance text.

        Returns passages where each confirmed code appears.
        Uses improved passage extraction prioritizing complete sentences
        with zone-related keywords.

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

                # Extract high-quality passages
                passages = self._extract_better_passages(
                    full_text,
                    zone_code,
                    start_char,
                    end_char
                )

                # Normalize and store
                normalized_code = normalize_zone_code(zone_code)
                candidate_passages[normalized_code].extend(passages)

        # Deduplicate and limit passages per code
        return {
            code: list(set(passages))[:self.max_passages_per_code]
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

    def _get_extractor_test_cities(self) -> set:
        """
        Get the set of cities that have extractor test examples.
        This ensures validator test set only includes cities with extractor data.
        """
        extractor_test_file = Path(__file__).parent / "data" / "test_extractor.jsonl"

        if not extractor_test_file.exists():
            print(f"  Warning: Extractor test file not found at {extractor_test_file}")
            return set()

        cities = set()
        with open(extractor_test_file) as f:
            for line in f:
                ex = json.loads(line)
                city = ex.get('city', '')
                state = ex.get('state', '')
                if city and state:
                    # Use same city key format as city_splits
                    city_key = f"{city}_{state}".replace(' ', '-').replace(',', '')
                    cities.add(city_key)

        print(f"  Found {len(cities)} cities in extractor test set")
        return cities

    def _split_by_city_splits(
        self,
        city_example_map: Dict[str, List[ValidatorExample]],
        city_splits: Dict[str, List[str]]
    ) -> Dict[str, List[ValidatorExample]]:
        """
        Split examples using pre-defined city splits (train/test only).

        Args:
            city_example_map: Map of city_key -> list of examples
            city_splits: Pre-defined splits with city lists

        Returns:
            Dict with 'train' and 'test' keys containing examples
        """
        splits = {
            'train': [],
            'test': []
        }

        print(f"\nSplitting examples:")

        # Split examples by city using the city_splits
        train_cities_with_data = 0
        for city_key in city_splits.get('train', []):
            if city_key in city_example_map:
                splits['train'].extend(city_example_map[city_key])
                train_cities_with_data += 1

        test_cities_with_data = 0
        for city_key in city_splits.get('test', []):
            if city_key in city_example_map:
                splits['test'].extend(city_example_map[city_key])
                test_cities_with_data += 1

        print(f"  Train: {train_cities_with_data}/{len(city_splits.get('train', []))} cities with data, {len(splits['train'])} examples")
        print(f"  Test: {test_cities_with_data}/{len(city_splits.get('test', []))} cities with data, {len(splits['test'])} examples")

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

    def _extract_better_passages(
        self,
        text: str,
        code: str,
        start_char: int,
        end_char: int,
        num_passages: int = 3
    ) -> List[str]:
        """
        Extract high-quality context passages for validation.

        Prioritizes:
        1. Full sentences containing zone district keywords
        2. Complete paragraphs with the code
        3. Traditional context window as fallback

        Args:
            text: Full ordinance text
            code: Zone code to find
            start_char: Start position of code mention
            end_char: End position of code mention
            num_passages: Number of passages to return

        Returns:
            List of high-quality passage strings
        """
        passages = []

        # Zone-related keywords for priority ranking
        zone_keywords = [
            'zone', 'district', 'zoning', 'designated', 'classified',
            'purpose', 'establish', 'permitted', 'allowed', 'use'
        ]

        # Strategy 1: Find complete sentences containing the code
        # Split text into sentences (simple approach)
        sentence_endings = ['.', '!', '?', '\n\n']
        sentences = []

        # Find sentence boundaries around the code
        sentence_start = start_char
        sentence_end = end_char

        # Expand backwards to sentence start
        for i in range(start_char - 1, max(0, start_char - 1000), -1):
            if text[i] in sentence_endings:
                sentence_start = i + 1
                break

        # Expand forwards to sentence end
        for i in range(end_char, min(len(text), end_char + 1000)):
            if text[i] in sentence_endings:
                sentence_end = i
                break

        # Extract the sentence
        sentence = text[sentence_start:sentence_end].strip()

        # Check if sentence has zone keywords
        has_zone_keywords = any(kw in sentence.lower() for kw in zone_keywords)

        if has_zone_keywords and len(sentence) > 50:
            passages.append(sentence)

        # Strategy 2: Find complete paragraphs containing the code
        # Look for paragraph boundaries (double newlines)
        para_start = start_char
        para_end = end_char

        # Expand to paragraph boundaries
        for i in range(start_char - 1, max(0, start_char - 2000), -1):
            if i > 0 and text[i-1:i+1] == '\n\n':
                para_start = i + 1
                break

        for i in range(end_char, min(len(text), end_char + 2000)):
            if text[i:i+2] == '\n\n':
                para_end = i
                break

        paragraph = text[para_start:para_end].strip()

        # Add if paragraph is substantial and different from sentence
        if len(paragraph) > 100 and paragraph not in passages:
            passages.append(paragraph)

        # Strategy 3: Traditional context window as fallback
        passage_start = max(0, start_char - self.context_window)
        passage_end = min(len(text), end_char + self.context_window)
        context_passage = text[passage_start:passage_end].strip()

        if context_passage not in passages:
            passages.append(context_passage)

        # Return top passages (prioritize those with zone keywords)
        def has_keywords(p):
            return sum(1 for kw in zone_keywords if kw in p.lower())

        passages.sort(key=lambda p: (has_keywords(p), len(p)), reverse=True)

        return passages[:num_passages]


def main():
    """Main entry point."""
    import argparse
    from dotenv import load_dotenv

    # Compute paths relative to this script
    script_dir = Path(__file__).parent
    project_root = script_dir.parent.parent.parent.parent

    parser = argparse.ArgumentParser(description="Prepare validator training data")
    parser.add_argument("--output-dir",
                        default=str(script_dir.parent / "data"),
                        help="Output directory for training data")
    parser.add_argument("--states", nargs="+", default=None,
                        help="States to process (default: all states)")
    parser.add_argument("--neg-pos-ratio", type=float, default=1.0,
                        help="Ratio of negative to positive examples")
    parser.add_argument("--zoneomics-dir",
                        default=str(project_root / "data" / "zoneomics"),
                        help="Directory with zoneomics CSVs (ignored if --use-gcs is set)")
    parser.add_argument("--municode-dir",
                        default=str(project_root / "collector" / "tmp" / "zoning_ordinance_md"),
                        help="Directory with municode ordinances (ignored if --use-gcs is set)")
    parser.add_argument("--extractor-model",
                        default=str(script_dir.parent.parent / "artifacts" / "models" / "extractor"),
                        help="Path to trained extractor model for negative generation")
    parser.add_argument("--extractor-device", type=str, default="auto",
                        choices=["auto", "cuda", "cpu"],
                        help="Device for extractor inference when generating negatives (default: auto)")
    parser.add_argument("--no-extractor-negatives", action="store_true",
                        help="Skip extractor-based negative generation (positives only)")

    # GCS data fetching arguments
    parser.add_argument("--use-gcs", action="store_true",
                        help="Fetch data from GCS bucket instead of using local paths")
    parser.add_argument("--gcs-cache-dir", type=str, default=None,
                        help="Local directory to cache GCS data (default: temporary directory)")
    parser.add_argument("--gcs-force-download", action="store_true",
                        help="Force re-download from GCS even if cache exists")

    # Split ratio arguments
    parser.add_argument("--train-ratio", type=float, default=0.85,
                        help="Train ratio (default: 0.85)")
    parser.add_argument("--test-ratio", type=float, default=0.15,
                        help="Test ratio (default: 0.15)")
    parser.add_argument("--force-new-splits", action="store_true",
                        help="Force regeneration of city splits even if file exists")

    args = parser.parse_args()

    # Load environment variables for GCS if needed
    if args.use_gcs:
        env_file = project_root / "secrets" / "teamspatially-project.env"
        if env_file.exists():
            load_dotenv(env_file)

        # Import and fetch data from GCS
        sys.path.append(str(script_dir.parent / "utils"))
        from gcs_data_fetcher import fetch_training_data_from_gcs

        print("\n" + "=" * 60)
        print("FETCHING DATA FROM GCS")
        print("=" * 60 + "\n")

        zoneomics_dir, municode_dir = fetch_training_data_from_gcs(
            cache_dir=Path(args.gcs_cache_dir) if args.gcs_cache_dir else None,
            force_download=args.gcs_force_download,
            states=args.states  # Pass states filter to GCS fetcher
        )

        # Override the directory arguments
        args.zoneomics_dir = str(zoneomics_dir)
        args.municode_dir = str(municode_dir)

    # Check if extractor model exists, download from GCS if not
    if not args.no_extractor_negatives:
        extractor_path = Path(args.extractor_model)

        # Try to find latest local extractor model
        models_dir = script_dir.parent.parent / "artifacts" / "models"
        if not extractor_path.exists():
            print(f"\n{'=' * 60}")
            print(f"Extractor model not found locally: {extractor_path}")
            print(f"Searching for latest extractor in artifacts/models/...")

            # Look for any extractor_* directory
            if models_dir.exists():
                extractor_dirs = sorted(
                    [d for d in models_dir.glob("extractor_*") if d.is_dir()],
                    key=lambda x: x.name,
                    reverse=True  # Latest first
                )
                if extractor_dirs:
                    extractor_path = extractor_dirs[0]
                    print(f"Found local extractor: {extractor_path.name}")
                    args.extractor_model = str(extractor_path)

        # If still not found, download from GCS
        if not extractor_path.exists():
            print(f"No local extractor found. Downloading latest from GCS...")

            # Import GCS model manager
            sys.path.append(str(script_dir.parent / "utils"))
            from gcs_model_manager import GCSModelManager

            try:
                model_manager = GCSModelManager()
                extractor_path = model_manager.download_model(
                    model_type="extractor",
                    timestamp=None,  # Latest
                    cache_dir=models_dir
                )
                args.extractor_model = str(extractor_path)
                print(f"✓ Downloaded extractor to: {extractor_path}")
            except Exception as e:
                print(f"ERROR: Failed to download extractor from GCS: {e}")
                print(f"Please train the extractor first or use --no-extractor-negatives")
                sys.exit(1)

            print(f"{'=' * 60}\n")

    preparator = ValidatorDataPreparator(
        zoneomics_dir=args.zoneomics_dir,
        municode_dir=args.municode_dir,
        extractor_model_path=args.extractor_model,
        extractor_device=args.extractor_device,
        negative_positive_ratio=args.neg_pos_ratio
    )

    counts = preparator.prepare_all(
        output_dir=args.output_dir,
        train_ratio=args.train_ratio,
        test_ratio=args.test_ratio,
        states=args.states,
        use_extractor_for_negatives=not args.no_extractor_negatives,
        force_new_splits=args.force_new_splits
    )

    print("\n=== Validator Training Data Preparation Complete ===")
    print(f"Train: {counts.get('train', 0)} examples")
    print(f"Test: {counts.get('test', 0)} examples")


if __name__ == "__main__":
    main()
