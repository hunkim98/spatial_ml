#!/usr/bin/env python3
"""
Prepare negative training examples for zone code extraction.

This script generates examples where zone-code-like patterns appear in
NON-zoning contexts (e.g., Wikipedia articles about highways, visa categories,
building codes). All patterns are tagged as 'O' (not zone codes).

This helps the model learn that not every "R-1" or "I-5" is a zone code.
"""

import json
import random
import re
import argparse
import urllib.request
import urllib.parse
from pathlib import Path
from dataclasses import dataclass, asdict
from typing import List, Dict, Tuple, Optional
from html import unescape

from transformers import AutoTokenizer

# Common English words that should NOT be matched as zone code prefixes
EXCLUDED_WORDS = frozenset([
    'the', 'and', 'for', 'are', 'but', 'not', 'you', 'all', 'can', 'had',
    'her', 'was', 'one', 'our', 'out', 'has', 'his', 'how', 'its', 'may',
    'new', 'now', 'old', 'see', 'way', 'who', 'did', 'get', 'let', 'put',
    'say', 'she', 'too', 'use', 'per', 'any', 'each', 'from', 'have', 'been',
    'call', 'come', 'could', 'than', 'them', 'then', 'into', 'only', 'over',
    'such', 'take', 'than', 'that', 'their', 'them', 'this', 'will', 'with',
    'about', 'after', 'being', 'could', 'every', 'first', 'found', 'great',
    'under', 'where', 'which', 'while', 'would', 'these', 'there', 'other',
    'page', 'pages', 'section', 'chapter', 'part', 'item', 'number', 'no',
    'table', 'figure', 'fig', 'exhibit', 'appendix', 'article', 'title',
    'year', 'years', 'day', 'days', 'week', 'weeks', 'month', 'months',
    'to', 'of', 'in', 'on', 'at', 'by', 'up', 'or', 'as', 'if', 'so',
    'an', 'be', 'we', 'us', 'it', 'is', 'am', 'no', 'do', 'go', 'he', 'me',
])

# Reuse the zone code pattern from the main training script
ZONE_CODE_PATTERN = re.compile(
    r'\b'
    r'(?:'
    r'([A-Z])[-/](\d{1,4})'
    r'|'
    r'([A-Z])(\d{1,4})'
    r'|'
    r'([A-Z]{2,4})[-/\s]?(\d{1,4})'
    r')'
    r'(\.\d+)?'
    r'([A-Z]{1,2})?'
    r'\b',
    re.IGNORECASE
)


def find_zone_code_spans(text: str) -> List[Tuple[int, int]]:
    """Find zone-code-like patterns, excluding common English words."""
    spans = []
    for match in ZONE_CODE_PATTERN.finditer(text):
        matched_text = match.group(0)
        prefix_match = re.match(r'^([A-Za-z]+)', matched_text)
        if prefix_match:
            prefix = prefix_match.group(1).lower()
            if prefix in EXCLUDED_WORDS:
                continue
        spans.append((match.start(), match.end()))
    return spans


def has_zone_code_pattern(text: str) -> bool:
    """Check if text contains zone-code-like patterns."""
    return len(find_zone_code_spans(text)) > 0


@dataclass
class NegativeExample:
    """A single negative training example with all 'O' tags."""
    tokens: List[str]
    tags: List[str]
    city: str  # "negative" for negative examples
    state: str  # source category (e.g., "wiki_highway", "wiki_visa")


# Wikipedia articles known to contain zone-code-like patterns in non-zoning contexts
WIKIPEDIA_ARTICLES = {
    # Highways (I-5, I-95, I-10, US-1, etc.)
    "wiki_highway": [
        "Interstate_5",
        "Interstate_95",
        "Interstate_10",
        "Interstate_80",
        "Interstate_40",
        "U.S._Route_1",
        "U.S._Route_66",
        "California_State_Route_1",
        "List_of_Interstate_Highways",
    ],
    # Visa categories (R-1, H-1B, E-2, L-1, etc.)
    "wiki_visa": [
        "R-1_visa",
        "H-1B_visa",
        "E-2_visa",
        "L-1_visa",
        "O-1_visa",
        "EB-1_visa",
        "EB-2_visa",
        "EB-5_visa",
    ],
    # Building/fire codes (R-1, R-2, R-3 occupancy types)
    "wiki_building": [
        "Building_code",
        "International_Building_Code",
        "Occupancy_classification",
        "Fire_code",
        "NFPA_1",
    ],
    # Scientific/medical (R-1 receptor, Type A-1, etc.)
    "wiki_science": [
        "Dopamine_receptor_D1",
        "Adrenergic_receptor",
        "Type_1_diabetes",
        "Vitamin_B1",
        "Vitamin_B12",
    ],
    # Military designations (B-1, F-22, A-10, etc.)
    "wiki_military": [
        "Rockwell_B-1_Lancer",
        "Fairchild_Republic_A-10_Thunderbolt_II",
        "McDonnell_Douglas_F-15_Eagle",
        "General_Dynamics_F-16_Fighting_Falcon",
        "Boeing_B-52_Stratofortress",
    ],
    # Other (general articles with alphanumeric codes)
    "wiki_other": [
        "Vitamin",
        "List_of_aircraft_by_manufacturer",
        "Immigration_to_the_United_States",
        "Transportation_in_the_United_States",
    ],
}


def fetch_wikipedia_text(article_title: str) -> Optional[str]:
    """
    Fetch plain text content from Wikipedia API.

    Args:
        article_title: Wikipedia article title (e.g., "Interstate_5")

    Returns:
        Plain text content of the article, or None if fetch fails
    """
    # Wikipedia API endpoint for plain text extract
    base_url = "https://en.wikipedia.org/w/api.php"
    params = {
        "action": "query",
        "titles": article_title,
        "prop": "extracts",
        "explaintext": "true",  # Get plain text, not HTML
        "exsectionformat": "plain",
        "format": "json",
    }

    url = f"{base_url}?{urllib.parse.urlencode(params)}"

    try:
        # Create request with User-Agent header (required by Wikipedia API)
        request = urllib.request.Request(
            url,
            headers={
                "User-Agent": "ZoningCodeExtractor/1.0 (training data generation; contact@example.com)"
            }
        )
        with urllib.request.urlopen(request, timeout=10) as response:
            data = json.loads(response.read().decode("utf-8"))

        pages = data.get("query", {}).get("pages", {})
        for page_id, page_data in pages.items():
            if page_id == "-1":
                return None  # Page not found
            return page_data.get("extract", "")
    except Exception as e:
        print(f"  Failed to fetch {article_title}: {e}")
        return None


def extract_sentences_with_patterns(text: str, min_length: int = 50) -> List[str]:
    """
    Extract sentences that contain zone-code-like patterns.

    Args:
        text: Full article text
        min_length: Minimum sentence length to include

    Returns:
        List of sentences containing zone-code-like patterns
    """
    # Split into sentences (simple approach)
    sentences = re.split(r'(?<=[.!?])\s+', text)

    matching_sentences = []
    for sentence in sentences:
        # Check if sentence contains zone-code-like pattern (excluding common words)
        if has_zone_code_pattern(sentence) and len(sentence) >= min_length:
            # Clean up whitespace
            sentence = ' '.join(sentence.split())
            matching_sentences.append(sentence)

    return matching_sentences


def create_negative_example(
    text: str,
    tokenizer,
    source_category: str,
    max_seq_length: int = 512
) -> Optional[NegativeExample]:
    """
    Create a negative training example from text.

    All zone-code-like patterns are tagged as 'O' (not zone codes).

    Args:
        text: Text containing zone-code-like patterns
        tokenizer: HuggingFace tokenizer
        source_category: Category for tracking (e.g., "wiki_highway")
        max_seq_length: Maximum sequence length

    Returns:
        NegativeExample or None if no patterns found
    """
    # Check if text has zone-code-like patterns (excluding common words)
    if not has_zone_code_pattern(text):
        return None

    # Tokenize
    encoding = tokenizer(
        text,
        truncation=True,
        max_length=max_seq_length,
        return_offsets_mapping=True
    )

    tokens = tokenizer.convert_ids_to_tokens(encoding['input_ids'])

    # All tags are 'O' for negative examples
    tags = ['O'] * len(tokens)

    return NegativeExample(
        tokens=tokens,
        tags=tags,
        city="negative",
        state=source_category
    )


def generate_negative_examples(
    output_path: str,
    tokenizer_name: str = "bert-base-uncased",
    target_count: int = 4000,
    max_seq_length: int = 512,
) -> Dict[str, int]:
    """
    Generate negative training examples from Wikipedia articles.

    Args:
        output_path: Path to output JSONL file
        tokenizer_name: Tokenizer to use
        target_count: Target number of examples to generate
        max_seq_length: Maximum sequence length

    Returns:
        Dictionary with counts per category
    """
    tokenizer = AutoTokenizer.from_pretrained(tokenizer_name)

    examples = []
    category_counts = {}

    print(f"Generating negative examples from Wikipedia...")
    print(f"Target: {target_count} examples")

    # Shuffle categories for balanced sampling
    all_articles = []
    for category, articles in WIKIPEDIA_ARTICLES.items():
        for article in articles:
            all_articles.append((category, article))
    random.shuffle(all_articles)

    for category, article_title in all_articles:
        if len(examples) >= target_count:
            break

        print(f"  Fetching {article_title}...")
        text = fetch_wikipedia_text(article_title)

        if not text:
            continue

        # Extract sentences with zone-code-like patterns
        sentences = extract_sentences_with_patterns(text)
        print(f"    Found {len(sentences)} matching sentences")

        for sentence in sentences:
            if len(examples) >= target_count:
                break

            example = create_negative_example(
                sentence, tokenizer, category, max_seq_length
            )

            if example:
                examples.append(example)
                category_counts[category] = category_counts.get(category, 0) + 1

    # If we don't have enough examples, generate synthetic ones
    if len(examples) < target_count:
        print(f"\nGenerating synthetic negative examples...")
        synthetic_examples = generate_synthetic_negatives(
            tokenizer,
            target_count - len(examples),
            max_seq_length
        )
        examples.extend(synthetic_examples)
        category_counts["synthetic"] = len(synthetic_examples)

    # Save to file
    output_file = Path(output_path)
    output_file.parent.mkdir(parents=True, exist_ok=True)

    with open(output_file, 'w') as f:
        for ex in examples:
            f.write(json.dumps(asdict(ex)) + '\n')

    print(f"\n=== Negative Examples Generation Complete ===")
    print(f"Total examples: {len(examples)}")
    print(f"Saved to: {output_file}")
    print(f"\nCategory breakdown:")
    for category, count in sorted(category_counts.items()):
        print(f"  {category}: {count}")

    return category_counts


def generate_synthetic_negatives(
    tokenizer,
    count: int,
    max_seq_length: int = 512
) -> List[NegativeExample]:
    """
    Generate synthetic negative examples with zone-code-like patterns.

    These are template-based sentences where patterns like "R-1" or "I-5"
    appear but are clearly not zoning codes.
    """
    templates = [
        # Highway references
        "Take {code} north for 5 miles, then exit onto Highway 101.",
        "The {code} freeway runs through downtown Los Angeles.",
        "Traffic on {code} was backed up for miles due to an accident.",
        "The {code} corridor connects major metropolitan areas.",

        # Visa references
        "She applied for an {code} visa to work in the United States.",
        "The {code} visa category requires employer sponsorship.",
        "Processing times for {code} applications have increased.",

        # Building code references
        "Section {code} of the building code specifies fire safety requirements.",
        "Occupancy type {code} buildings require sprinkler systems.",
        "The inspector cited violations of code section {code}.",

        # Military references
        "The {code} bomber entered service in the 1980s.",
        "The {code} fighter jet is known for its maneuverability.",

        # Scientific references
        "The {code} receptor is involved in neurotransmitter signaling.",
        "Vitamin {code} deficiency can cause various health issues.",

        # Generic alphanumeric references
        "Form {code} must be submitted before the deadline.",
        "Appendix {code} contains additional technical specifications.",
        "Model {code} was discontinued in 2020.",
        "The {code} variant showed improved performance.",
    ]

    # Zone-code-like patterns to insert
    patterns = [
        "R-1", "R-2", "R-3", "R-4", "R-5",
        "I-5", "I-10", "I-95", "I-80", "I-40",
        "A-1", "A-2", "A-3",
        "B-1", "B-2", "B-52",
        "C-1", "C-2", "C-3",
        "E-2", "E-3",
        "H-1B", "L-1", "O-1",
        "M-1", "M-2",
        "P-1", "P-2",
    ]

    examples = []

    for _ in range(count):
        template = random.choice(templates)
        pattern = random.choice(patterns)
        text = template.format(code=pattern)

        example = create_negative_example(
            text, tokenizer, "synthetic", max_seq_length
        )
        if example:
            examples.append(example)

    return examples


def main():
    parser = argparse.ArgumentParser(
        description="Generate negative examples for zone code extraction training"
    )
    parser.add_argument(
        "--output", "-o",
        default="model/zoning_codes_extract/training/data_full/negative.jsonl",
        help="Output JSONL file path"
    )
    parser.add_argument(
        "--count", "-n",
        type=int,
        default=4000,
        help="Target number of negative examples"
    )
    parser.add_argument(
        "--tokenizer",
        default="bert-base-uncased",
        help="Tokenizer to use"
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=42,
        help="Random seed"
    )

    args = parser.parse_args()

    random.seed(args.seed)

    generate_negative_examples(
        output_path=args.output,
        tokenizer_name=args.tokenizer,
        target_count=args.count
    )


if __name__ == "__main__":
    main()
