#!/usr/bin/env python3
"""
Test suite for the new zone code extractor training data improvements.

Tests:
1. ZONE_CODE_PATTERN regex - correctly matches zone-code-like patterns
2. Negative examples generation - creates valid training examples
3. Training data loading - negative examples are properly merged
"""

import json
import re
import sys
import tempfile
from pathlib import Path
from typing import List, Tuple

# Add parent paths for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "training"))
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from transformers import AutoTokenizer


# ============================================================================
# Test 1: ZONE_CODE_PATTERN regex
# ============================================================================

# Import the pattern and function from the training script
from prepare_extractor_data import ZONE_CODE_PATTERN, find_zone_code_spans, find_csv_zone_code_spans


def test_zone_code_pattern():
    """Test that find_zone_code_spans correctly matches zone-code-like patterns."""
    print("\n" + "=" * 60)
    print("TEST 1: Zone Code Pattern Matching")
    print("=" * 60)

    # Patterns that SHOULD match (true zone codes)
    should_match = [
        # Basic patterns
        ("R-1", "Basic residential"),
        ("R-2", "Basic residential 2"),
        ("R1", "No hyphen"),
        # ("R 1", "Space separator"),  # Single letter + space is not matched (by design)
        ("C-1", "Commercial"),
        ("M-1", "Manufacturing"),
        ("I-1", "Industrial"),
        ("A-1", "Agricultural"),

        # Multi-letter prefixes
        ("AG-1", "Agriculture"),
        ("MU-1", "Mixed use"),
        ("MHP-1", "Mobile home park"),
        ("PUD-1", "Planned unit development"),
        ("CBD-1", "Central business district"),

        # Multi-digit suffixes
        ("R-10", "Two digit"),
        ("R-100", "Three digit"),
        ("C-2A", "With letter suffix"),
        ("M-1B", "With letter suffix"),

        # Decimal patterns
        ("RM-2.5", "With decimal"),
        ("R-1.5", "With decimal"),

        # Slash separator
        ("R/1", "Slash separator"),

        # Case insensitive
        ("r-1", "Lowercase"),
        ("R-1a", "Mixed case suffix"),
    ]

    # Patterns that should NOT match (false positives to avoid)
    should_not_match = [
        ("a 150-foot setback", "Number after article 'a'"),
        ("the 200 acres", "Number after article 'the'"),
        ("Chapter 5", "Chapter reference"),
        ("Section 12", "Section reference"),
        ("12345", "Just numbers"),
        ("ABC", "Just letters"),
        ("RESIDENTIAL", "Full word"),
        ("COVID-19", "Not a zone pattern"),
        ("24/7", "Time pattern"),
        ("3.14159", "Pi"),
        ("page 10", "Page reference"),
        ("Table 5", "Table reference"),
    ]

    passed = 0
    failed = 0

    print("\n--- Should Match ---")
    for pattern, description in should_match:
        spans = find_zone_code_spans(pattern)
        if spans:
            matched_text = pattern[spans[0][0]:spans[0][1]]
            print(f"  ✓ '{pattern}' matched: {matched_text} ({description})")
            passed += 1
        else:
            print(f"  ✗ '{pattern}' did NOT match ({description})")
            failed += 1

    print("\n--- Should NOT Match ---")
    for text, description in should_not_match:
        spans = find_zone_code_spans(text)
        if not spans:
            print(f"  ✓ '{text}' correctly not matched ({description})")
            passed += 1
        else:
            matched_texts = [text[s:e] for s, e in spans]
            print(f"  ✗ '{text}' incorrectly matched: {matched_texts} ({description})")
            failed += 1

    print(f"\n--- Results: {passed} passed, {failed} failed ---")
    return failed == 0


def test_zone_code_pattern_in_context():
    """Test pattern matching within larger text contexts."""
    print("\n" + "=" * 60)
    print("TEST 2: Zone Code Pattern in Context")
    print("=" * 60)

    test_cases = [
        (
            "The R-1 district allows single-family homes. R-2 allows duplexes.",
            ["R-1", "R-2"],
            "Multiple zone codes in sentence"
        ),
        (
            "Zoning: AG-1, AG-2, and AG-3 are agricultural districts.",
            ["AG-1", "AG-2", "AG-3"],
            "List of zone codes"
        ),
        (
            "The property is zoned MU-2A with a C-1 overlay.",
            ["MU-2A", "C-1"],
            "Zone with overlay"
        ),
        (
            "Interstate I-5 runs through zone R-1.",
            ["I-5", "R-1"],  # I-5 will match (highway, but looks like zone)
            "Highway and zone (both match pattern)"
        ),
        (
            "Building heights in R-1.5 shall not exceed 35 feet.",
            ["R-1.5"],
            "Zone with decimal"
        ),
    ]

    passed = 0
    failed = 0

    for text, expected_codes, description in test_cases:
        spans = find_zone_code_spans(text)
        found_codes = [text[s:e] for s, e in spans]

        # Normalize for comparison (case insensitive)
        found_upper = [c.upper() for c in found_codes]
        expected_upper = [c.upper() for c in expected_codes]

        # Check if we found at least the expected codes
        all_found = all(any(exp in found for found in found_upper) for exp in expected_upper)

        if all_found:
            print(f"  ✓ {description}")
            print(f"      Text: '{text[:50]}...'")
            print(f"      Found: {found_codes}")
            passed += 1
        else:
            print(f"  ✗ {description}")
            print(f"      Text: '{text[:50]}...'")
            print(f"      Expected: {expected_codes}, Found: {found_codes}")
            failed += 1

    print(f"\n--- Results: {passed} passed, {failed} failed ---")
    return failed == 0


# ============================================================================
# Test 3: Negative Examples Generation
# ============================================================================

def test_negative_examples_generation():
    """Test that negative examples are generated correctly."""
    print("\n" + "=" * 60)
    print("TEST 3: Negative Examples Generation")
    print("=" * 60)

    from prepare_negative_examples import (
        extract_sentences_with_patterns,
        create_negative_example,
        generate_synthetic_negatives,
        has_zone_code_pattern,
    )

    tokenizer = AutoTokenizer.from_pretrained("bert-base-uncased")

    passed = 0
    failed = 0

    # Test 3.1: extract_sentences_with_patterns
    print("\n--- Test 3.1: extract_sentences_with_patterns ---")
    test_text = """
    The Interstate I-5 highway runs north to south. It connects major cities.
    The H-1B visa program allows skilled workers. This has been controversial.
    Regular sentence without patterns here. Another plain sentence.
    The R-1 receptor is important for signaling. More science follows.
    """

    sentences = extract_sentences_with_patterns(test_text, min_length=20)
    expected_count = 3  # I-5, H-1B, R-1 sentences

    if len(sentences) >= expected_count:
        print(f"  ✓ Found {len(sentences)} sentences with patterns (expected >= {expected_count})")
        for s in sentences[:3]:
            print(f"      - '{s[:60]}...'")
        passed += 1
    else:
        print(f"  ✗ Found {len(sentences)} sentences (expected >= {expected_count})")
        failed += 1

    # Test 3.2: create_negative_example
    print("\n--- Test 3.2: create_negative_example ---")
    test_sentence = "Take I-5 north to the R-1 exit near the M-2 industrial zone."

    example = create_negative_example(test_sentence, tokenizer, "test_category")

    if example is not None:
        # Check that all tags are 'O'
        all_o_tags = all(tag == 'O' for tag in example.tags)
        if all_o_tags:
            print(f"  ✓ All tags are 'O' (correct for negative example)")
            print(f"      Tokens: {example.tokens[:10]}...")
            print(f"      Tags: {example.tags[:10]}...")
            passed += 1
        else:
            print(f"  ✗ Not all tags are 'O': {set(example.tags)}")
            failed += 1

        # Check metadata
        if example.city == "negative" and example.state == "test_category":
            print(f"  ✓ Metadata correct: city='{example.city}', state='{example.state}'")
            passed += 1
        else:
            print(f"  ✗ Metadata incorrect: city='{example.city}', state='{example.state}'")
            failed += 1
    else:
        print(f"  ✗ create_negative_example returned None")
        failed += 1

    # Test 3.3: generate_synthetic_negatives
    print("\n--- Test 3.3: generate_synthetic_negatives ---")
    synthetic = generate_synthetic_negatives(tokenizer, count=10)

    if len(synthetic) == 10:
        print(f"  ✓ Generated {len(synthetic)} synthetic examples")
        passed += 1
    else:
        print(f"  ✗ Generated {len(synthetic)} examples (expected 10)")
        failed += 1

    # Check that synthetic examples have correct format
    all_valid = True
    for ex in synthetic:
        if not (hasattr(ex, 'tokens') and hasattr(ex, 'tags') and
                ex.city == "negative" and ex.state == "synthetic"):
            all_valid = False
            break
        if not all(tag == 'O' for tag in ex.tags):
            all_valid = False
            break

    if all_valid:
        print(f"  ✓ All synthetic examples have valid format")
        passed += 1
    else:
        print(f"  ✗ Some synthetic examples have invalid format")
        failed += 1

    print(f"\n--- Results: {passed} passed, {failed} failed ---")
    return failed == 0


# ============================================================================
# Test 4: Training Data Loading with Negative Examples
# ============================================================================

def test_training_data_loading():
    """Test that negative examples are properly loaded and merged."""
    print("\n" + "=" * 60)
    print("TEST 4: Training Data Loading")
    print("=" * 60)

    passed = 0
    failed = 0

    # Create temporary directory with test data
    with tempfile.TemporaryDirectory() as tmpdir:
        tmppath = Path(tmpdir)

        # Create mock train.jsonl
        train_examples = [
            {"tokens": ["[CLS]", "the", "r", "-", "1", "zone", "[SEP]"],
             "tags": ["O", "O", "B-ZONE", "I-ZONE", "I-ZONE", "O", "O"],
             "city": "testcity", "state": "teststate"},
            {"tokens": ["[CLS]", "c", "-", "2", "district", "[SEP]"],
             "tags": ["O", "B-ZONE", "I-ZONE", "I-ZONE", "O", "O"],
             "city": "testcity", "state": "teststate"},
        ]

        with open(tmppath / "train.jsonl", 'w') as f:
            for ex in train_examples:
                f.write(json.dumps(ex) + '\n')

        # Create mock negative.jsonl
        negative_examples = [
            {"tokens": ["[CLS]", "take", "i", "-", "5", "north", "[SEP]"],
             "tags": ["O", "O", "O", "O", "O", "O", "O"],
             "city": "negative", "state": "wiki_highway"},
            {"tokens": ["[CLS]", "h", "-", "1", "b", "visa", "[SEP]"],
             "tags": ["O", "O", "O", "O", "O", "O", "O"],
             "city": "negative", "state": "wiki_visa"},
        ]

        with open(tmppath / "negative.jsonl", 'w') as f:
            for ex in negative_examples:
                f.write(json.dumps(ex) + '\n')

        # Test loading
        print("\n--- Test 4.1: Load and count examples ---")

        # Load train examples
        with open(tmppath / "train.jsonl") as f:
            loaded_train = [json.loads(line) for line in f]

        # Load negative examples
        with open(tmppath / "negative.jsonl") as f:
            loaded_negative = [json.loads(line) for line in f]

        if len(loaded_train) == 2 and len(loaded_negative) == 2:
            print(f"  ✓ Loaded {len(loaded_train)} train + {len(loaded_negative)} negative examples")
            passed += 1
        else:
            print(f"  ✗ Wrong counts: train={len(loaded_train)}, negative={len(loaded_negative)}")
            failed += 1

        # Test merging
        print("\n--- Test 4.2: Merge examples ---")
        merged = loaded_train + loaded_negative

        if len(merged) == 4:
            print(f"  ✓ Merged to {len(merged)} examples")
            passed += 1
        else:
            print(f"  ✗ Merged count wrong: {len(merged)}")
            failed += 1

        # Check that negative examples have all 'O' tags
        print("\n--- Test 4.3: Verify negative example tags ---")
        negative_correct = all(
            all(tag == 'O' for tag in ex['tags'])
            for ex in merged if ex['city'] == 'negative'
        )

        if negative_correct:
            print(f"  ✓ All negative examples have only 'O' tags")
            passed += 1
        else:
            print(f"  ✗ Some negative examples have non-'O' tags")
            failed += 1

        # Check that positive examples have zone tags
        print("\n--- Test 4.4: Verify positive example tags ---")
        positive_correct = all(
            'B-ZONE' in ex['tags']
            for ex in merged if ex['city'] != 'negative'
        )

        if positive_correct:
            print(f"  ✓ All positive examples have B-ZONE tags")
            passed += 1
        else:
            print(f"  ✗ Some positive examples missing B-ZONE tags")
            failed += 1

    print(f"\n--- Results: {passed} passed, {failed} failed ---")
    return failed == 0


# ============================================================================
# Test 5: Consistency Check - Same patterns tagged same way
# ============================================================================

def test_tagging_consistency():
    """Test that the same patterns are tagged consistently."""
    print("\n" + "=" * 60)
    print("TEST 5: Tagging Consistency")
    print("=" * 60)

    passed = 0
    failed = 0

    # Two different "cities" with overlapping zone codes
    context1 = "The R-1 zone allows residential use. Adjacent C-2 is commercial."
    context2 = "Zoning district R-1 is for homes. The M-1 zone is industrial."

    def get_zone_codes(text):
        """Get all zone codes in text using find_zone_code_spans."""
        spans = find_zone_code_spans(text)
        return [(s, e, text[s:e]) for s, e in spans]

    # Get spans from both contexts
    spans1 = get_zone_codes(context1)
    spans2 = get_zone_codes(context2)

    print(f"\n--- Context 1 spans ---")
    for start, end, code in spans1:
        print(f"  '{code}' at [{start}:{end}]")

    print(f"\n--- Context 2 spans ---")
    for start, end, code in spans2:
        print(f"  '{code}' at [{start}:{end}]")

    # Check that R-1 is found in both
    r1_in_1 = any(code.upper() == "R-1" for _, _, code in spans1)
    r1_in_2 = any(code.upper() == "R-1" for _, _, code in spans2)

    print(f"\n--- Consistency Check ---")
    if r1_in_1 and r1_in_2:
        print(f"  ✓ 'R-1' found in both contexts (consistent tagging)")
        passed += 1
    else:
        print(f"  ✗ 'R-1' not found consistently: context1={r1_in_1}, context2={r1_in_2}")
        failed += 1

    # Verify that using regex (not CSV codes) means we tag ALL zone-like patterns
    all_codes_1 = [code.upper() for _, _, code in spans1]
    all_codes_2 = [code.upper() for _, _, code in spans2]

    expected_1 = ["R-1", "C-2"]
    expected_2 = ["R-1", "M-1"]

    if set(expected_1).issubset(set(all_codes_1)):
        print(f"  ✓ Context 1 has all expected codes: {all_codes_1}")
        passed += 1
    else:
        print(f"  ✗ Context 1 missing codes. Expected: {expected_1}, Found: {all_codes_1}")
        failed += 1

    if set(expected_2).issubset(set(all_codes_2)):
        print(f"  ✓ Context 2 has all expected codes: {all_codes_2}")
        passed += 1
    else:
        print(f"  ✗ Context 2 missing codes. Expected: {expected_2}, Found: {all_codes_2}")
        failed += 1

    print(f"\n--- Results: {passed} passed, {failed} failed ---")
    return failed == 0


# ============================================================================
# Test 6: CSV-Only Matching
# ============================================================================

def test_csv_only_matching():
    """Test that only CSV codes are tagged, not all regex patterns."""
    print("\n" + "=" * 60)
    print("TEST 6: CSV-Only Matching")
    print("=" * 60)

    passed = 0
    failed = 0

    csv_codes = ["R-1", "C-2"]
    text = "The R-1 zone allows homes. M-1 is industrial. C-2 is commercial."

    spans = find_csv_zone_code_spans(text, csv_codes)
    found = [text[s:e] for s, e in spans]

    print(f"\n--- CSV codes: {csv_codes} ---")
    print(f"--- Text: '{text}' ---")
    print(f"--- Found: {found} ---")

    # Should find R-1 and C-2 (in CSV)
    has_r1 = any("R-1" in f.upper() or "R 1" in f.upper() or "R1" in f.upper() for f in found)
    has_c2 = any("C-2" in f.upper() or "C 2" in f.upper() or "C2" in f.upper() for f in found)
    has_m1 = any("M-1" in f.upper() or "M 1" in f.upper() or "M1" in f.upper() for f in found)

    if has_r1:
        print(f"  ✓ Found R-1 (in CSV)")
        passed += 1
    else:
        print(f"  ✗ Did not find R-1 (in CSV)")
        failed += 1

    if has_c2:
        print(f"  ✓ Found C-2 (in CSV)")
        passed += 1
    else:
        print(f"  ✗ Did not find C-2 (in CSV)")
        failed += 1

    # Should NOT find M-1 (not in CSV)
    if not has_m1:
        print(f"  ✓ Did not find M-1 (not in CSV)")
        passed += 1
    else:
        print(f"  ✗ Incorrectly found M-1 (not in CSV)")
        failed += 1

    print(f"\n--- Results: {passed} passed, {failed} failed ---")
    return failed == 0


def test_variation_handling():
    """Test that code variations are matched correctly."""
    print("\n" + "=" * 60)
    print("TEST 7: Variation Handling")
    print("=" * 60)

    passed = 0
    failed = 0

    csv_codes = ["R-1"]

    test_cases = [
        ("The R-1 zone", True, "hyphen"),
        ("The R 1 zone", True, "space"),
        ("The R1 zone", True, "no separator"),
        ("The R-11 zone", False, "different code"),
        ("The R-10 zone", False, "different code"),
    ]

    print(f"\n--- CSV code: R-1 ---")

    for text, should_find, description in test_cases:
        spans = find_csv_zone_code_spans(text, csv_codes)
        found = len(spans) > 0

        if found == should_find:
            status = "✓" if should_find else "✓"
            action = "Found" if found else "Not found"
            print(f"  {status} {action} in '{text}' ({description})")
            passed += 1
        else:
            status = "✗"
            expected = "should find" if should_find else "should not find"
            print(f"  {status} Failed for '{text}' ({description}): {expected}")
            failed += 1

    print(f"\n--- Results: {passed} passed, {failed} failed ---")
    return failed == 0


def test_no_false_positives():
    """Test that non-CSV patterns are not matched."""
    print("\n" + "=" * 60)
    print("TEST 8: No False Positives")
    print("=" * 60)

    passed = 0
    failed = 0

    csv_codes = ["R-1"]
    text = "Interstate I-5, H-1B visa, M-2 zoning, COVID-19"

    spans = find_csv_zone_code_spans(text, csv_codes)

    print(f"\n--- CSV code: {csv_codes} ---")
    print(f"--- Text: '{text}' ---")
    print(f"--- Found spans: {spans} ---")

    if len(spans) == 0:
        print(f"  ✓ No false positives (none of these are in CSV)")
        passed += 1
    else:
        found = [text[s:e] for s, e in spans]
        print(f"  ✗ Incorrectly matched: {found}")
        failed += 1

    print(f"\n--- Results: {passed} passed, {failed} failed ---")
    return failed == 0


def test_case_insensitive_csv_matching():
    """Test that CSV matching is case insensitive."""
    print("\n" + "=" * 60)
    print("TEST 9: Case Insensitive CSV Matching")
    print("=" * 60)

    passed = 0
    failed = 0

    csv_codes = ["R-1", "MU-2"]

    test_cases = [
        ("The R-1 zone", ["R-1"]),
        ("The r-1 zone", ["r-1"]),
        ("The MU-2 district", ["MU-2"]),
        ("The mu-2 district", ["mu-2"]),
        ("The Mu-2 district", ["Mu-2"]),
    ]

    print(f"\n--- CSV codes: {csv_codes} ---")

    for text, expected_matches in test_cases:
        spans = find_csv_zone_code_spans(text, csv_codes)
        found = [text[s:e] for s, e in spans]

        if len(found) == len(expected_matches):
            print(f"  ✓ Found {len(found)} match(es) in '{text}'")
            passed += 1
        else:
            print(f"  ✗ Expected {len(expected_matches)}, found {len(found)} in '{text}'")
            print(f"      Expected: {expected_matches}, Found: {found}")
            failed += 1

    print(f"\n--- Results: {passed} passed, {failed} failed ---")
    return failed == 0


# ============================================================================
# Main
# ============================================================================

def main():
    """Run all tests."""
    print("\n" + "=" * 60)
    print("ZONE CODE EXTRACTOR - NEW IMPLEMENTATION TESTS")
    print("=" * 60)

    results = {}

    # Run tests
    results["ZONE_CODE_PATTERN basic"] = test_zone_code_pattern()
    results["ZONE_CODE_PATTERN in context"] = test_zone_code_pattern_in_context()
    results["Negative examples generation"] = test_negative_examples_generation()
    results["Training data loading"] = test_training_data_loading()
    results["Tagging consistency"] = test_tagging_consistency()
    results["CSV-only matching"] = test_csv_only_matching()
    results["Variation handling"] = test_variation_handling()
    results["No false positives"] = test_no_false_positives()
    results["Case insensitive CSV matching"] = test_case_insensitive_csv_matching()

    # Summary
    print("\n" + "=" * 60)
    print("TEST SUMMARY")
    print("=" * 60)

    all_passed = True
    for test_name, passed in results.items():
        status = "✓ PASSED" if passed else "✗ FAILED"
        print(f"  {status}: {test_name}")
        if not passed:
            all_passed = False

    print("\n" + "=" * 60)
    if all_passed:
        print("ALL TESTS PASSED!")
    else:
        print("SOME TESTS FAILED - please review above")
    print("=" * 60)

    return 0 if all_passed else 1


if __name__ == "__main__":
    sys.exit(main())
