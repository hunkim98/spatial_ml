"""
Post-processing rules for compound zone codes.

Fixes tokenization fragmentation issues identified in performance analysis:
- Compound codes with multiple hyphens (b-1-a, b-1-b, pgh-40)
- Suffix codes (-s, -p, -t, -d, -m)
- Slash-separated codes (BP/LI, R/A)
- Decimal formats (RM2.5, R31.5)
"""

import re
from typing import List, Set
from dataclasses import dataclass


@dataclass
class CompletedCode:
    """Result of post-processing completion."""
    original: str
    completed: str
    confidence: float
    rule: str


class ZoneCodePostProcessor:
    """
    Post-processing engine for completing fragmented zone codes.

    Applies pattern-based rules to fix tokenization issues that cause
    the extractor to predict partial codes.
    """

    # Common compound patterns from the 163-city dataset
    COMPOUND_PATTERNS = [
        # b-X-Y patterns (Birmingham, AL and others)
        r'\b(b-[1-6](?:-[a-z])?)\b',

        # pgh-XX patterns (Pittsburgh-style codes)
        r'\b(pgh-\d{1,2})\b',

        # r-XX-suffix patterns (common suffix codes)
        r'\b(r-\d{1,2}(?:-[sptdm])?)\b',

        # Slash-separated codes
        r'\b([A-Z]{2,4}/[A-Z]{2,4})\b',

        # Decimal formats
        r'\b([A-Z]{1,3}\d+\.\d+)\b',

        # Prefix digit patterns
        r'\b(\d{1,2}[A-Z]\d+)\b',
    ]

    def __init__(self):
        """Initialize the post-processor."""
        self.patterns = [re.compile(p, re.IGNORECASE) for p in self.COMPOUND_PATTERNS]

    def post_process_extracted_codes(
        self,
        raw_codes: List[str],
        original_text: str
    ) -> List[CompletedCode]:
        """
        Apply pattern-based completion rules to extracted codes.

        Args:
            raw_codes: List of codes extracted by the model
            original_text: Original ordinance text

        Returns:
            List of CompletedCode objects with original and completed versions
        """
        completed_codes = []

        for code in raw_codes:
            # Try to complete the code
            completed = self._complete_code(code, original_text)
            completed_codes.append(completed)

        # Apply longest-match preference to remove partial duplicates
        deduplicated = self._deduplicate_by_longest_match(completed_codes)

        return deduplicated

    def _complete_code(self, code: str, text: str) -> CompletedCode:
        """
        Try to complete a potentially partial code.

        Args:
            code: Extracted code (may be partial)
            text: Original text to search in

        Returns:
            CompletedCode with completion result
        """
        code_lower = code.lower()
        text_lower = text.lower()

        # Rule 1: b-1 → b-1-a or b-1-b
        if code_lower == 'b-1':
            if 'b-1-a' in text_lower:
                return CompletedCode(code, 'b-1-a', 0.95, 'b-1-suffix-completion')
            elif 'b-1-b' in text_lower:
                return CompletedCode(code, 'b-1-b', 0.95, 'b-1-suffix-completion')

        # Rule 2: b-X without suffix → check for b-X-Y
        match = re.match(r'^b-([2-6])$', code_lower)
        if match:
            digit = match.group(1)
            # Check for b-X-a or b-X-b
            for suffix in ['a', 'b', 'c']:
                candidate = f'b-{digit}-{suffix}'
                if candidate in text_lower:
                    return CompletedCode(code, candidate, 0.90, 'b-X-suffix-completion')

        # Rule 3: pgh without number → pgh-XX
        if code_lower == 'pgh' or code_lower.startswith('pgh-') and len(code) < 6:
            matches = re.findall(r'pgh-(\d{1,2})', text_lower)
            if matches:
                # Use the most common number in context
                most_common = max(set(matches), key=matches.count)
                completed_code = f'pgh-{most_common}'
                return CompletedCode(code, completed_code, 0.85, 'pgh-number-completion')

        # Rule 4: r-XX without suffix → check for r-XX-S
        match = re.match(r'^r-(\d{1,2})$', code_lower)
        if match:
            number = match.group(1)
            # Check for common suffixes
            for suffix in ['s', 'p', 't', 'd', 'm']:
                candidate = f'r-{number}-{suffix}'
                if candidate in text_lower:
                    return CompletedCode(code, candidate, 0.90, 'r-suffix-completion')

        # Rule 5: Partial slash codes (e.g., "BP" when "BP/LI" exists)
        if len(code) >= 2 and '/' not in code:
            # Check if this is part of a slash code
            for pattern in [r'(\b' + re.escape(code_lower) + r'/[A-Z]{2,4})\b',
                           r'(\b[A-Z]{2,4}/' + re.escape(code_lower) + r')\b']:
                match = re.search(pattern, text_lower, re.IGNORECASE)
                if match:
                    return CompletedCode(code, match.group(1).upper(), 0.85, 'slash-completion')

        # Rule 6: Check for decimal extensions (e.g., "RM2" → "RM2.5")
        if re.match(r'^[A-Z]{1,3}\d+$', code.upper()):
            pattern = re.escape(code_lower) + r'\.\d+'
            match = re.search(pattern, text_lower)
            if match:
                return CompletedCode(code, match.group(0).upper(), 0.85, 'decimal-completion')

        # Rule 7: Prefix digit patterns (e.g., "20" → "20R1" if context has it)
        if re.match(r'^\d{1,2}$', code):
            pattern = re.escape(code) + r'[A-Z]\d+'
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return CompletedCode(code, match.group(0).upper(), 0.80, 'prefix-digit-completion')

        # No completion found - return original
        return CompletedCode(code, code.upper(), 1.0, 'no-completion')

    def _deduplicate_by_longest_match(
        self,
        codes: List[CompletedCode]
    ) -> List[CompletedCode]:
        """
        Remove partial codes when full version exists.

        For example, if both "b-1" and "b-1-a" are present, keep only "b-1-a".

        Args:
            codes: List of completed codes

        Returns:
            Deduplicated list
        """
        if not codes:
            return []

        # Sort by length (longest first) to prefer complete codes
        sorted_codes = sorted(codes, key=lambda x: len(x.completed), reverse=True)

        kept = []
        seen_prefixes = set()

        for code in sorted_codes:
            completed_lower = code.completed.lower()

            # Check if this is a prefix of any already-kept code
            is_prefix = False
            for kept_code in kept:
                kept_lower = kept_code.completed.lower()
                if completed_lower in kept_lower or kept_lower in completed_lower:
                    # One is a substring of the other
                    if len(completed_lower) < len(kept_lower):
                        # Current code is shorter (prefix), skip it
                        is_prefix = True
                        break
                    else:
                        # Current code is longer, remove the shorter one
                        kept.remove(kept_code)
                        break

            if not is_prefix:
                kept.append(code)

        return kept

    def extract_all_complete_codes(self, text: str) -> Set[str]:
        """
        Extract all complete zone codes from text using patterns.

        This can be used as a fallback or validation check.

        Args:
            text: Original ordinance text

        Returns:
            Set of zone codes found by pattern matching
        """
        codes = set()

        for pattern in self.patterns:
            matches = pattern.findall(text)
            codes.update(match.upper() for match in matches)

        return codes

    def validate_completion(
        self,
        original: str,
        completed: str,
        text: str
    ) -> bool:
        """
        Validate that a completion is reasonable.

        Args:
            original: Original extracted code
            completed: Completed code
            text: Original text

        Returns:
            True if completion is valid
        """
        # Completed code should contain or extend original
        if original.lower() not in completed.lower():
            return False

        # Completed code should exist in text
        if completed.lower() not in text.lower():
            return False

        # Length check - completion shouldn't be too much longer
        if len(completed) > len(original) * 3:
            return False

        return True


def apply_post_processing(
    extracted_codes: List[str],
    original_text: str
) -> List[str]:
    """
    Convenience function to apply post-processing.

    Args:
        extracted_codes: Raw codes from extractor
        original_text: Original ordinance text

    Returns:
        List of completed zone codes
    """
    processor = ZoneCodePostProcessor()
    completed = processor.post_process_extracted_codes(extracted_codes, original_text)

    # Return only the completed codes
    return [c.completed for c in completed]
