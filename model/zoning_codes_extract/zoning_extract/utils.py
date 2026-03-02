"""
Shared utilities for zoning code extraction.

This module provides canonical implementations of common functions
to avoid code duplication across the codebase.
"""

import re
from typing import List, Pattern


def normalize_zone_code(code: str) -> str:
    """
    Normalize a zone code to canonical form.

    This is the single source of truth for zone code normalization.
    Replaces 4 different implementations across the codebase.

    Examples:
        "R 1" -> "R-1"
        "r-1" -> "R-1"
        "B1" -> "B-1"
        " C 2 " -> "C-2"

    Args:
        code: Raw zone code string

    Returns:
        Normalized zone code (uppercase, with hyphens)
    """
    # Uppercase and strip whitespace
    code = code.strip().upper()

    # Replace spaces with hyphens
    code = re.sub(r'\s+', '-', code)

    # Add hyphen between letter and number if missing (e.g., B1 -> B-1)
    code = re.sub(r'([A-Z]+)(\d)', r'\1-\2', code)

    return code


def normalize_zone_code_for_comparison(code: str) -> str:
    """
    Normalize zone code for fuzzy comparison (removes hyphens/spaces).

    Used for comparing zone codes where "R-1", "R1", and "R 1" should match.

    Examples:
        "R-1" -> "R1"
        "R 1" -> "R1"
        "C-2A" -> "C2A"

    Args:
        code: Zone code string

    Returns:
        Normalized code with hyphens and spaces removed
    """
    return code.replace('-', '').replace(' ', '').upper()


def extract_zones_from_bio(tokens: List[str], labels: List[str]) -> List[str]:
    """
    Extract zone code strings from BIO-tagged token sequence.

    This is the single source of truth for BIO extraction.
    Replaces 2 duplicate implementations in the codebase.

    BIO tagging format:
        - B-ZONE: Beginning of zone code
        - I-ZONE: Inside (continuation) of zone code
        - O: Outside (not a zone code)

    Examples:
        tokens: ["The", "R", "-", "1", "zone"]
        labels: ["O", "B-ZONE", "I-ZONE", "I-ZONE", "O"]
        returns: ["R-1"]

    Args:
        tokens: List of tokens (strings)
        labels: Corresponding BIO labels

    Returns:
        List of extracted zone code strings
    """
    zones = []
    current_zone = []

    for token, label in zip(tokens, labels):
        if label == 'B-ZONE':
            # Start of new zone - save previous if exists
            if current_zone:
                zone_str = ''.join(current_zone).replace('##', '').strip()
                if zone_str:
                    zones.append(zone_str)
            current_zone = [token]

        elif label == 'I-ZONE' and current_zone:
            # Continuation of current zone
            current_zone.append(token)

        else:
            # End of zone or non-zone token
            if current_zone:
                zone_str = ''.join(current_zone).replace('##', '').strip()
                if zone_str:
                    zones.append(zone_str)
                current_zone = []

    # Handle final zone if exists
    if current_zone:
        zone_str = ''.join(current_zone).replace('##', '').strip()
        if zone_str:
            zones.append(zone_str)

    # Filter out special tokens
    zones = [z for z in zones if z not in ['[CLS]', '[SEP]', '[PAD]', '']]

    return zones


def create_zone_code_pattern() -> Pattern:
    """
    Create regex pattern for matching zone codes in text.

    This is the single source of truth for zone code pattern matching.
    Replaces 4+ different pattern definitions across the codebase.

    Matches common zone code formats:
        - Simple hyphenated: R-1, C-2, AG-1
        - With suffix: R-1-A, B-2-S
        - Letter-only: AG, MU, PRD
        - Slash-separated: BP/LI, R/A
        - Decimal: RM-2.5, C-3.5
        - Prefix digits: 20R1, 4R1

    Returns:
        Compiled regex pattern
    """
    # Combine all common zone code patterns
    pattern_str = r'\b(?:' + r'|'.join([
        # Compound codes with multiple parts (b-1-a, pgh-40-x)
        r'[A-Za-z]{1,4}-\d{1,3}(?:-[A-Za-z0-9]{1,3})+',

        # Simple hyphenated codes (R-1, C-2, AG-1)
        r'[A-Za-z]{1,4}-\d{1,3}(?:-[A-Za-z]{1,2})?',

        # Slash-separated codes (BP/LI, R/A)
        r'[A-Za-z]{2,4}/[A-Za-z]{2,4}',

        # Decimal formats (RM2.5, R31.5, C-3.5)
        r'[A-Za-z]{1,4}-?\d+\.\d+',

        # Prefix digit patterns (20R1, 4R1)
        r'\d{1,2}[A-Za-z]\d+',

        # Letter-only codes (AG, MU, PRD, MUD)
        r'[A-Z]{2,4}',
    ]) + r')\b'

    return re.compile(pattern_str, re.IGNORECASE)


def find_all_zone_codes_in_text(text: str) -> List[str]:
    """
    Find all zone code patterns in text.

    Returns normalized, deduplicated zone codes found in the text.

    Args:
        text: Text to search

    Returns:
        Sorted list of unique zone codes found
    """
    pattern = create_zone_code_pattern()
    matches = pattern.findall(text)

    # Normalize and deduplicate
    normalized = {normalize_zone_code(m) for m in matches}

    return sorted(normalized)


def check_zone_code_format(code: str) -> bool:
    """
    Check if a string matches common zone code format patterns.

    Used for validation and filtering.

    Args:
        code: String to check

    Returns:
        True if matches zone code format, False otherwise
    """
    common_patterns = [
        r'^[A-Z]{1,3}-?\d{1,2}$',           # R-1, C-2, I-1
        r'^[A-Z]{2,4}$',                     # AG, MU, RMU
        r'^[A-Z]-[A-Z]{1,2}$',              # R-SF, C-GC
        r'^[A-Z]{1,2}/[A-Z]{1,2}$',         # M/H, R/O
        r'^[A-Z]{1,2}-[A-Z]{2,4}$',         # R-MH, C-OFC
        r'^[A-Z]{1,4}-\d{1,3}-[A-Za-z0-9]{1,3}$',  # B-1-A, PGH-40-X
    ]

    code_clean = code.strip().upper()
    return any(re.match(p, code_clean) for p in common_patterns)
