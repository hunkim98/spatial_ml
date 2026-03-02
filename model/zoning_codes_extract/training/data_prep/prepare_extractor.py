"""
Prepare training data for token classification (BIO tagging).

This script:
1. Loads zoneomics CSVs (ground truth zone codes)
2. Parses municode ordinances
3. Uses TextAligner to find zone codes in text
4. Creates BIO tags for each token using CSV-based detection
5. Splits by city into train/val/test
6. Exports in HuggingFace datasets format

IMPORTANT: Uses CSV zone codes to tag patterns in context windows.
Only zone codes from the zoneomics CSV are tagged, ensuring we only label
confirmed zone codes for each city.
"""

import json
import random
import re
from pathlib import Path
from dataclasses import dataclass, asdict
from typing import List, Dict, Tuple, Optional, Set
from collections import defaultdict

from transformers import AutoTokenizer

# Import from parent module
import sys
sys.path.append(str(Path(__file__).parent.parent.parent.parent))

from zoning_extract import (
    CityMatcher,
    OrdinanceParser,
    TextAligner,
    load_zoneomics_csv,
    normalize_zone_code
)

from .city_splits import get_or_create_splits, get_city_key

# Import custom tokenization
try:
    from ..utils.custom_tokenization import create_zone_aware_tokenizer
    CUSTOM_TOKENIZATION_AVAILABLE = True
except ImportError:
    CUSTOM_TOKENIZATION_AVAILABLE = False
    print("WARNING: Custom tokenization module not available")


# Common English words that should NOT be matched as zone code prefixes
# These are words that might appear before numbers but aren't zone codes
EXCLUDED_WORDS = frozenset([
    'the', 'and', 'for', 'are', 'but', 'not', 'you', 'all', 'can', 'had',
    'her', 'was', 'one', 'our', 'out', 'has', 'his', 'how', 'its', 'may',
    'new', 'now', 'old', 'see', 'way', 'who', 'did', 'get', 'let', 'put',
    'say', 'she', 'too', 'use', 'per', 'any', 'each', 'from', 'have', 'been',
    'call', 'come', 'could', 'than', 'them', 'then', 'into', 'only', 'over',
    'such', 'take', 'than', 'that', 'their', 'them', 'this', 'will', 'with',
    'about', 'after', 'being', 'could', 'every', 'first', 'found', 'great',
    'under', 'where', 'which', 'while', 'would', 'these', 'there', 'other',
    # Common words that appear before numbers in text
    'page', 'pages', 'section', 'chapter', 'part', 'item', 'number', 'no',
    'table', 'figure', 'fig', 'exhibit', 'appendix', 'article', 'title',
    'year', 'years', 'day', 'days', 'week', 'weeks', 'month', 'months',
    'to', 'of', 'in', 'on', 'at', 'by', 'up', 'or', 'as', 'if', 'so',
    'an', 'be', 'we', 'us', 'it', 'is', 'am', 'no', 'do', 'go', 'he', 'me',
])

# Regex pattern to detect zone-code-like patterns in text
# This ensures consistent tagging across all cities
#
# Pattern requirements:
# - 1-4 letters followed by 1-4 digits
# - Optional separator: hyphen, slash, or space (but space only if 2+ letters)
# - Optional decimal suffix (e.g., RM-2.5)
# - Optional letter suffix (e.g., R-1A)
#
# To avoid false positives like "a 150" or "the 200":
# - Single letter + space + number is NOT matched
# - Single letter requires hyphen/slash/nothing as separator
# - Common English words are filtered out after matching
ZONE_CODE_PATTERN = re.compile(
    r'\b'
    r'(?:'
    # Option 1: Single letter + hyphen/slash (NO space) + digits
    r'([A-Z])[-/](\d{1,4})'
    r'|'
    # Option 2: Single letter + digits (no separator)
    r'([A-Z])(\d{1,4})'
    r'|'
    # Option 3: 2-4 letters + optional separator (hyphen/slash/space) + digits
    r'([A-Z]{2,4})[-/\s]?(\d{1,4})'
    r')'
    r'(\.\d+)?'               # optional decimal (RM2.5)
    r'([A-Z]{1,2})?'          # optional suffix (R-1A)
    r'\b',
    re.IGNORECASE
)


def find_zone_code_spans(text: str) -> List[Tuple[int, int]]:
    """
    Find all zone-code-like patterns in text, excluding common English words.

    NOTE: This function is kept for reference but is no longer used in the
    main data preparation pipeline. We now use find_csv_zone_code_spans()
    which only tags confirmed zone codes from the CSV.

    Returns:
        List of (start, end) tuples for each zone code span
    """
    spans = []
    for match in ZONE_CODE_PATTERN.finditer(text):
        # Extract the letter prefix from the match
        # The prefix is in one of the capture groups (1, 3, or 5)
        matched_text = match.group(0)

        # Extract the letter prefix (before any digits)
        prefix_match = re.match(r'^([A-Za-z]+)', matched_text)
        if prefix_match:
            prefix = prefix_match.group(1).lower()
            # Skip if the prefix is a common English word
            if prefix in EXCLUDED_WORDS:
                continue

        spans.append((match.start(), match.end()))

    return spans


def _create_zone_code_pattern(zone_code: str) -> str:
    """
    Create regex pattern for a zone code that handles variations.

    E.g., "R-1" -> pattern matching "R-1", "R 1", "R1"

    Reuses logic from TextAligner._find_by_code() in text_aligner.py

    Args:
        zone_code: Normalized zone code (e.g., "R-1")

    Returns:
        Regex pattern string with word boundaries
    """
    # Split on separators
    parts = re.split(r'([\-\s])', zone_code)
    pattern_parts = []

    for part in parts:
        if part in ['-', ' ', '']:
            pattern_parts.append(r'[\s\-]?')
        else:
            pattern_parts.append(re.escape(part))

    pattern = ''.join(pattern_parts)
    pattern = r'\b' + pattern + r'\b'

    return pattern


def find_csv_zone_code_spans(
    text: str,
    csv_zone_codes: List[str]
) -> List[Tuple[int, int]]:
    """
    Find all occurrences of CSV zone codes in text.

    Handles variations:
    - "R-1" in CSV matches "R-1", "R 1", "R1" in text
    - Case insensitive
    - Word boundaries prevent partial matches

    Args:
        text: Text to search in
        csv_zone_codes: List of normalized zone codes from CSV

    Returns:
        Sorted list of (start, end) tuples
    """
    all_spans = []

    for zone_code in csv_zone_codes:
        # Generate flexible pattern (reuse TextAligner pattern logic)
        pattern = _create_zone_code_pattern(zone_code)

        # Find all matches
        for match in re.finditer(pattern, text, re.IGNORECASE):
            all_spans.append((match.start(), match.end()))

    # Sort and merge overlapping spans
    if not all_spans:
        return []

    all_spans = sorted(all_spans, key=lambda x: x[0])

    # Use existing _merge_spans logic (will be available via self in class methods)
    # For now, inline merge logic
    merged_spans = []
    if all_spans:
        merged_spans = [all_spans[0]]
        for start, end in all_spans[1:]:
            last_start, last_end = merged_spans[-1]
            if start <= last_end:
                # Overlapping, merge
                merged_spans[-1] = (last_start, max(last_end, end))
            else:
                merged_spans.append((start, end))

    return merged_spans


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

    # Standard BIO tags
    BIO_TAGS = ['O', 'B-ZONE', 'I-ZONE']

    # Enhanced BIO tags with token type information
    ENHANCED_BIO_TAGS = [
        'O',
        'B-ZONE',
        'I-ZONE-LETTER',   # Letter token inside zone
        'I-ZONE-DIGIT',    # Digit token inside zone
        'I-ZONE-HYPHEN',   # Hyphen token inside zone
        'I-ZONE-SUFFIX',   # Suffix letter after hyphen+digit
        'I-ZONE-DOT',      # Dot in decimal zones
        'I-ZONE-SLASH',    # Slash in compound zones
    ]

    def __init__(
        self,
        zoneomics_dir: str = "data/zoneomics",
        municode_dir: str = "tmp/zoning_ordinance",
        tokenizer_name: str = "bert-base-uncased",
        max_seq_length: int = 512,
        context_window: int = 500,
        use_custom_tokenization: bool = True,
        use_enhanced_tags: bool = False
    ):
        """
        Initialize preparator.

        Args:
            zoneomics_dir: Directory with ground truth CSVs
            municode_dir: Directory with scraped ordinances
            tokenizer_name: Tokenizer to use for tokenization
            max_seq_length: Maximum sequence length
            context_window: Characters of context around each zone code
            use_custom_tokenization: Whether to use custom zone-aware tokenization
            use_enhanced_tags: Whether to use enhanced BIO tags with token types
        """
        self.zoneomics_dir = Path(zoneomics_dir)
        self.municode_dir = Path(municode_dir)
        self.max_seq_length = max_seq_length
        self.context_window = context_window
        self.use_custom_tokenization = use_custom_tokenization and CUSTOM_TOKENIZATION_AVAILABLE
        self.use_enhanced_tags = use_enhanced_tags

        # Set tag set based on mode
        self.tag_set = self.ENHANCED_BIO_TAGS if use_enhanced_tags else self.BIO_TAGS

        # Initialize components
        self.city_matcher = CityMatcher(
            str(self.zoneomics_dir),
            str(self.municode_dir)
        )

        # Initialize tokenizer (with or without custom protection)
        if self.use_custom_tokenization:
            self.tokenizer = create_zone_aware_tokenizer(
                tokenizer_name=tokenizer_name,
                use_protection=True
            )
            print(f"Initialized with zone-protected tokenizer: {tokenizer_name}")
        else:
            self.tokenizer = AutoTokenizer.from_pretrained(tokenizer_name)
            print(f"Initialized with standard tokenizer: {tokenizer_name}")

        if self.use_enhanced_tags:
            print(f"Enhanced BIO tagging enabled ({len(self.tag_set)} tags)")

    def prepare_all(
        self,
        output_dir: str = "model/zoning_codes_extract/training/data",
        train_ratio: float = 0.85,
        test_ratio: float = 0.15,
        states: Optional[List[str]] = None,
        force_new_splits: bool = False
    ) -> Dict[str, int]:
        """
        Prepare training data from all matched cities using 2-way splitting (train/test).

        Args:
            output_dir: Where to save train/test files
            train_ratio: Proportion for training (default: 0.85)
            test_ratio: Proportion for testing (default: 0.15)
            states: Specific states to process (None for all)
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

        # Process all cities
        all_examples = []
        city_example_map = {}  # Map city_key -> list of examples
        cities_with_data = []  # Track cities that produced examples

        print(f"\nProcessing all {len(matches)} cities...")

        for i, match in enumerate(matches):
            city_key = get_city_key(match.state, match.city_name)
            print(f"\nProcessing {i+1}/{len(matches)}: {match.city_name}, {match.state}")

            try:
                examples = self.prepare_city(match.state, match.city_name)
                if examples:
                    all_examples.extend(examples)
                    city_example_map[city_key] = examples
                    cities_with_data.append(city_key)
                    print(f"  ✓ Generated {len(examples)} examples")
                else:
                    print(f"  ✗ No examples generated (skipping)")
            except Exception as e:
                print(f"  ✗ Error: {e} (skipping)")
                continue

        print(f"\n✓ Successfully processed {len(cities_with_data)} cities with valid training data")

        print(f"\nTotal examples: {len(all_examples)} from {len(cities_with_data)} cities")

        # Generate city splits from cities that have data
        city_splits = get_or_create_splits(
            cities=cities_with_data,
            output_dir=output_dir,
            train_ratio=train_ratio,
            test_ratio=test_ratio,
            force_regenerate=force_new_splits
        )

        # Split examples using the shared city splits
        splits = self._split_by_city_splits(city_example_map, city_splits)

        # Save splits
        counts = {}
        for split_name, examples in splits.items():
            output_file = output_path / f"{split_name}_extractor.jsonl"
            self._save_examples(examples, str(output_file))
            counts[split_name] = len(examples)
            print(f"Saved {len(examples)} examples to {output_file}")

        # Save statistics
        stats = {
            'total_examples': len(all_examples),
            'splits': counts,
            'num_cities': len(cities_with_data),
            'cities_processed': i + 1,  # Total cities checked
            'train_extractor_cities': city_splits.get('train_extractor', []),
            'val_extractor_cities': city_splits.get('val_extractor', []),
            'train_validator_cities': city_splits.get('train_validator', []),
            'val_validator_cities': city_splits.get('val_validator', []),
            'test_cities': city_splits.get('test', []),
        }

        stats_file = output_path / "extractor_stats.json"
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
        examples with context around each mention. Uses CSV codes to tag ONLY
        confirmed zone codes from the zoneomics CSV, not all zone-code-like patterns.

        This ensures zero false positives: only zone codes present in the CSV
        for this city are tagged as zone codes.
        """
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

            # Find ONLY zone codes from the CSV in this context
            # Handles variations like "R-1", "R 1", "R1"
            zone_spans = find_csv_zone_code_spans(context_text, all_zone_codes)

            # Spans are already merged in find_csv_zone_code_spans

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
            if self.use_enhanced_tags:
                tags = self._create_enhanced_tags(
                    tokens, offsets, context_text, zone_spans
                )
            else:
                tags = self._create_standard_tags(
                    tokens, offsets, zone_spans
                )


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

    def _create_standard_tags(
        self,
        tokens: List[str],
        offsets: List[Tuple[int, int]],
        zone_spans: List[Tuple[int, int]]
    ) -> List[str]:
        """
        Create standard BIO tags (O, B-ZONE, I-ZONE).

        Args:
            tokens: List of tokens
            offsets: Token offsets in text
            zone_spans: Spans of zone codes

        Returns:
            List of BIO tags
        """
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

        return tags

    def _create_enhanced_tags(
        self,
        tokens: List[str],
        offsets: List[Tuple[int, int]],
        text: str,
        zone_spans: List[Tuple[int, int]]
    ) -> List[str]:
        """
        Create enhanced BIO tags with token type information.

        Tags like I-ZONE-DIGIT, I-ZONE-HYPHEN help the model learn
        patterns specific to zone code structure.

        Args:
            tokens: List of tokens
            offsets: Token offsets in text
            text: Original text
            zone_spans: Spans of zone codes

        Returns:
            List of enhanced BIO tags
        """
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
                            # Determine token type for enhanced tag
                            token = tokens[i]
                            token_text = text[token_start:token_end]

                            # Remove BERT subword marker
                            clean_token = token.replace('##', '')

                            # Classify token type
                            if clean_token == '-':
                                tag = 'I-ZONE-HYPHEN'
                            elif clean_token == '/':
                                tag = 'I-ZONE-SLASH'
                            elif clean_token == '.':
                                tag = 'I-ZONE-DOT'
                            elif clean_token.isdigit():
                                tag = 'I-ZONE-DIGIT'
                            elif clean_token.isalpha():
                                # Check if suffix (letter after digit+hyphen)
                                # Look at previous tokens in zone
                                if i >= 2:
                                    prev_token = tokens[i-1].replace('##', '')
                                    prev_prev = tokens[i-2].replace('##', '') if i >= 2 else ''
                                    if prev_token == '-' and prev_prev.isdigit():
                                        tag = 'I-ZONE-SUFFIX'
                                    else:
                                        tag = 'I-ZONE-LETTER'
                                else:
                                    tag = 'I-ZONE-LETTER'
                            else:
                                # Default to generic I-ZONE
                                tag = 'I-ZONE-LETTER'

                        break
                tags.append(tag)

        return tags

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

        for city_key in city_splits.get('train', []):
            if city_key in city_example_map:
                splits['train'].extend(city_example_map[city_key])

        for city_key in city_splits.get('test', []):
            if city_key in city_example_map:
                splits['test'].extend(city_example_map[city_key])

        print(f"\nSplitting examples:")
        print(f"  Train: {len(city_splits.get('train', []))} cities, {len(splits['train'])} examples")
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
    from dotenv import load_dotenv

    # Compute paths relative to this script
    script_dir = Path(__file__).parent
    project_root = script_dir.parent.parent.parent.parent

    parser = argparse.ArgumentParser(description="Prepare training data for zone code extraction")
    parser.add_argument("--output-dir",
                        default=str(script_dir.parent / "data"),
                        help="Output directory for training data")
    parser.add_argument("--states", nargs="+", default=None,
                        help="States to process (default: all states)")
    parser.add_argument("--tokenizer", default="bert-base-uncased",
                        help="Tokenizer to use")
    parser.add_argument("--zoneomics-dir",
                        default=str(project_root / "data" / "zoneomics"),
                        help="Directory with zoneomics CSVs (ignored if --use-gcs is set)")
    parser.add_argument("--municode-dir",
                        default=str(project_root / "collector" / "tmp" / "zoning_ordinance_md"),
                        help="Directory with municode ordinances (ignored if --use-gcs is set)")
    parser.add_argument("--no-custom-tokenization", action="store_true",
                        help="Disable custom zone-aware tokenization")
    parser.add_argument("--enhanced-tags", action="store_true",
                        help="Use enhanced BIO tagging with token types")

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

    preparator = TrainingDataPreparator(
        zoneomics_dir=args.zoneomics_dir,
        municode_dir=args.municode_dir,
        tokenizer_name=args.tokenizer,
        use_custom_tokenization=not args.no_custom_tokenization,
        use_enhanced_tags=args.enhanced_tags
    )

    counts = preparator.prepare_all(
        output_dir=args.output_dir,
        train_ratio=args.train_ratio,
        test_ratio=args.test_ratio,
        states=args.states,
        force_new_splits=args.force_new_splits
    )

    print("\n=== Training Data Preparation Complete ===")
    print(f"Train: {counts.get('train', 0)} examples")
    print(f"Test: {counts.get('test', 0)} examples")


if __name__ == "__main__":
    main()
