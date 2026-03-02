"""
Custom tokenization for zone codes.

Addresses tokenization fragmentation issues:
- Protects zone codes from being split across multiple tokens
- Preserves compound codes (b-1-a, pgh-40)
- Handles suffix codes (-s, -p, -t)
- Preserves slash-separated codes (BP/LI)
- Handles decimal formats (RM2.5)

Strategy: Pre-tokenization marking to protect zone codes.
"""

import re
from typing import List, Tuple, Optional
from transformers import PreTrainedTokenizer


class ZoneCodeProtectedTokenizer:
    """
    Tokenizer wrapper that protects zone codes from fragmentation.

    Uses pre-tokenization marking to replace hyphens with special characters
    that BERT won't split, then restores them after tokenization.
    """

    # Special character to replace hyphens (won't be split by WordPiece)
    HYPHEN_MARKER = '▁'  # Unicode underscore (U+2581)
    SLASH_MARKER = '▂'   # Unicode underscore (U+2582)
    DOT_MARKER = '▃'     # Unicode underscore (U+2583)

    # Zone code patterns to protect
    ZONE_CODE_PATTERNS = [
        # Compound codes with multiple hyphens (b-1-a, pgh-40-x)
        r'\b([A-Za-z]{1,4}-\d{1,3}(?:-[A-Za-z0-9]{1,3})+)\b',

        # Simple hyphenated codes (R-1, C-2, AG-1)
        r'\b([A-Za-z]{1,4}-\d{1,3}(?:-[A-Za-z]{1,2})?)\b',

        # Slash-separated codes (BP/LI, R/A, I/MR)
        r'\b([A-Za-z]{2,4}/[A-Za-z]{2,4})\b',

        # Decimal formats (RM2.5, R31.5, C-3.5)
        r'\b([A-Za-z]{1,4}-?\d+\.\d+)\b',

        # Prefix digit patterns (20R1, 4R1, 7R1)
        r'\b(\d{1,2}[A-Za-z]\d+)\b',
    ]

    def __init__(self, base_tokenizer: PreTrainedTokenizer):
        """
        Initialize protected tokenizer.

        Args:
            base_tokenizer: Base BERT tokenizer to wrap
        """
        self.base_tokenizer = base_tokenizer
        self.patterns = [re.compile(p, re.IGNORECASE) for p in self.ZONE_CODE_PATTERNS]

    def tokenize(self, text: str, **kwargs) -> List[str]:
        """
        Tokenize with zone code protection.

        Args:
            text: Input text
            **kwargs: Additional arguments for base tokenizer

        Returns:
            List of tokens
        """
        # Step 1: Mark zone codes
        marked_text, replacements = self._mark_zone_codes(text)

        # Step 2: Tokenize with base tokenizer
        tokens = self.base_tokenizer.tokenize(marked_text, **kwargs)

        # Step 3: Restore markers in tokens
        restored_tokens = self._restore_markers(tokens)

        return restored_tokens

    def __call__(self, text, **kwargs):
        """Allow using as callable like base tokenizer."""
        # Step 1: Mark zone codes
        marked_text, replacements = self._mark_zone_codes(text)

        # Step 2: Call base tokenizer
        result = self.base_tokenizer(marked_text, **kwargs)

        # Step 3: Restore markers in tokens if 'input_ids' in result
        if 'input_ids' in result:
            # Get tokens from input_ids
            tokens = self.base_tokenizer.convert_ids_to_tokens(result['input_ids'])
            # Restore markers
            restored_tokens = self._restore_markers(tokens)
            # Convert back to ids
            result['input_ids'] = self.base_tokenizer.convert_tokens_to_ids(restored_tokens)

        return result

    def _mark_zone_codes(self, text: str) -> Tuple[str, List[Tuple[int, int, str]]]:
        """
        Replace special characters in zone codes with markers.

        Args:
            text: Original text

        Returns:
            Tuple of (marked_text, list of replacements)
        """
        marked_text = text
        replacements = []

        # Find all zone code matches
        for pattern in self.patterns:
            for match in pattern.finditer(text):
                zone_code = match.group(1)
                start, end = match.span(1)

                # Create marked version
                marked_code = zone_code
                marked_code = marked_code.replace('-', self.HYPHEN_MARKER)
                marked_code = marked_code.replace('/', self.SLASH_MARKER)
                marked_code = marked_code.replace('.', self.DOT_MARKER)

                # Record replacement
                replacements.append((start, end, zone_code))

                # Replace in text
                marked_text = marked_text[:start] + marked_code + marked_text[end:]

        return marked_text, replacements

    def _restore_markers(self, tokens: List[str]) -> List[str]:
        """
        Restore original characters from markers.

        Args:
            tokens: Tokens with markers

        Returns:
            Tokens with restored characters
        """
        restored = []
        for token in tokens:
            restored_token = token
            restored_token = restored_token.replace(self.HYPHEN_MARKER, '-')
            restored_token = restored_token.replace(self.SLASH_MARKER, '/')
            restored_token = restored_token.replace(self.DOT_MARKER, '.')
            restored.append(restored_token)

        return restored

    def convert_ids_to_tokens(self, ids):
        """Delegate to base tokenizer."""
        return self.base_tokenizer.convert_ids_to_tokens(ids)

    def convert_tokens_to_ids(self, tokens):
        """Delegate to base tokenizer."""
        return self.base_tokenizer.convert_tokens_to_ids(tokens)

    def convert_tokens_to_string(self, tokens):
        """Delegate to base tokenizer."""
        return self.base_tokenizer.convert_tokens_to_string(tokens)

    @property
    def vocab_size(self):
        """Delegate to base tokenizer."""
        return self.base_tokenizer.vocab_size

    @property
    def pad_token(self):
        """Delegate to base tokenizer."""
        return self.base_tokenizer.pad_token

    @property
    def pad_token_id(self):
        """Delegate to base tokenizer."""
        return self.base_tokenizer.pad_token_id


def create_zone_aware_tokenizer(
    tokenizer_name: str = "bert-base-uncased",
    use_protection: bool = True
) -> PreTrainedTokenizer:
    """
    Create a tokenizer with optional zone code protection.

    Args:
        tokenizer_name: Name of base tokenizer
        use_protection: Whether to use zone code protection

    Returns:
        Tokenizer (wrapped if protection enabled)
    """
    from transformers import AutoTokenizer

    base_tokenizer = AutoTokenizer.from_pretrained(tokenizer_name)

    if use_protection:
        return ZoneCodeProtectedTokenizer(base_tokenizer)
    else:
        return base_tokenizer


def test_tokenization_protection():
    """
    Test that zone code protection works correctly.
    """
    from transformers import AutoTokenizer

    # Create tokenizers
    base_tokenizer = AutoTokenizer.from_pretrained("bert-base-uncased")
    protected_tokenizer = ZoneCodeProtectedTokenizer(base_tokenizer)

    # Test cases
    test_cases = [
        "The b-1-a district allows residential uses.",
        "Properties in pgh-40 zone must comply.",
        "R-75-s codes require larger lots.",
        "BP/LI districts support mixed use.",
        "RM2.5 zones have minimum lot size.",
    ]

    print("Testing tokenization protection:\n")

    for text in test_cases:
        base_tokens = base_tokenizer.tokenize(text)
        protected_tokens = protected_tokenizer.tokenize(text)

        print(f"Text: {text}")
        print(f"Base tokens:      {base_tokens}")
        print(f"Protected tokens: {protected_tokens}")
        print()


if __name__ == "__main__":
    test_tokenization_protection()
