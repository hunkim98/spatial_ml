"""
Stage 2: Validator
Validates candidate zone codes using a binary classification model.
Distinguishes real zone codes from false positives (acronyms, section references, etc.).
"""

import re
from dataclasses import dataclass
from typing import List, Optional
import torch
from transformers import (
    AutoTokenizer,
    AutoModelForSequenceClassification,
    pipeline
)


@dataclass
class CandidateZone:
    """A candidate zone code with supporting passages."""
    code: str
    passages: List[str]
    locations: List[tuple[int, int]]  # (start, end) positions in document


@dataclass
class ValidationResult:
    """Result of zone code validation."""
    code: str
    is_valid: bool
    confidence: float
    reasons: List[str]


class ZoneValidator:
    """
    Validates candidate zone codes using a binary classification model.

    The model takes a candidate code + all passages where it appears,
    and predicts whether it's a real zone code or a false positive.

    Examples:
    - Valid: "R-1" in "The purpose of the R-1 Zone is to provide..."
    - Invalid: "R-1" in "See Appendix R-1 for details"
    """

    def __init__(
        self,
        model_path: Optional[str] = None,
        tokenizer_name: str = "bert-base-uncased",
        min_confidence: float = 0.5,
        max_length: int = 512,
        device: Optional[str] = None
    ):
        """
        Initialize validator with model.

        Args:
            model_path: Path to trained validator model (if None, uses rule-based fallback)
            tokenizer_name: Name of tokenizer to use
            min_confidence: Minimum confidence threshold for validation
            max_length: Maximum sequence length
            device: Device to run model on ('cuda', 'cpu', or None for auto)
        """
        self.min_confidence = min_confidence
        self.max_length = max_length

        # Set device
        if device is None:
            self.device = 'cuda' if torch.cuda.is_available() else 'cpu'
        else:
            self.device = device

        # Load tokenizer
        self.tokenizer = AutoTokenizer.from_pretrained(tokenizer_name)

        # Load model if path provided
        self.model = None
        self.classifier = None
        if model_path:
            self.load_model(model_path)

    def load_model(self, model_path: str):
        """Load a trained validator model."""
        self.model = AutoModelForSequenceClassification.from_pretrained(model_path)
        self.model.to(self.device)
        self.model.eval()

        # Create classification pipeline
        self.classifier = pipeline(
            "text-classification",
            model=self.model,
            tokenizer=self.tokenizer,
            device=0 if self.device == 'cuda' else -1,
            return_all_scores=True
        )

    def validate(self, candidate: CandidateZone) -> ValidationResult:
        """
        Validate a candidate zone code.

        Args:
            candidate: Candidate zone with code and supporting passages

        Returns:
            ValidationResult with decision and confidence score
        """
        if self.classifier is None:
            # Fallback to simple rule-based validation
            return self._validate_rule_based(candidate)

        # Prepare input for model
        input_text = self._prepare_input(candidate)

        # Run classifier
        try:
            predictions = self.classifier(input_text)[0]

            # Extract scores (assuming label 1 = valid, 0 = invalid)
            # predictions is a list like [{'label': 'LABEL_0', 'score': 0.2}, {'label': 'LABEL_1', 'score': 0.8}]
            valid_score = next(p['score'] for p in predictions if p['label'] == 'LABEL_1')

            is_valid = valid_score >= self.min_confidence

            reasons = []
            if is_valid:
                reasons.append(f"Model confidence: {valid_score:.3f}")
            else:
                reasons.append(f"Model confidence too low: {valid_score:.3f} < {self.min_confidence}")

            return ValidationResult(
                code=candidate.code,
                is_valid=is_valid,
                confidence=valid_score,
                reasons=reasons
            )

        except Exception as e:
            # Fallback on error
            return ValidationResult(
                code=candidate.code,
                is_valid=False,
                confidence=0.0,
                reasons=[f"Validation error: {str(e)}"]
            )

    def validate_batch(self, candidates: List[CandidateZone]) -> List[ValidationResult]:
        """Validate multiple candidates."""
        if self.classifier is None:
            return [self._validate_rule_based(c) for c in candidates]

        # Prepare batch inputs
        inputs = [self._prepare_input(c) for c in candidates]

        # Run batch prediction
        try:
            batch_predictions = self.classifier(inputs)

            results = []
            for candidate, predictions in zip(candidates, batch_predictions):
                valid_score = next(p['score'] for p in predictions if p['label'] == 'LABEL_1')
                is_valid = valid_score >= self.min_confidence

                results.append(ValidationResult(
                    code=candidate.code,
                    is_valid=is_valid,
                    confidence=valid_score,
                    reasons=[f"Model confidence: {valid_score:.3f}"]
                ))

            return results

        except Exception as e:
            # Fallback to individual validation on error
            return [self.validate(c) for c in candidates]

    def _prepare_input(self, candidate: CandidateZone) -> str:
        """
        Prepare input text for the classifier.

        Format: "[CODE] {zone_code} [SEP] {passage1} [SEP] {passage2} ..."
        """
        # Join all passages (limit to avoid exceeding max_length)
        combined_passages = " [SEP] ".join(candidate.passages[:5])  # Max 5 passages

        # Create input text with special format
        input_text = f"[CODE] {candidate.code} [SEP] {combined_passages}"

        # Truncate if too long
        tokens = self.tokenizer.tokenize(input_text)
        if len(tokens) > self.max_length - 2:  # Account for [CLS] and [SEP]
            tokens = tokens[:self.max_length - 2]
            input_text = self.tokenizer.convert_tokens_to_string(tokens)

        return input_text

    def _validate_rule_based(self, candidate: CandidateZone) -> ValidationResult:
        """
        Simple rule-based fallback validation when no model is loaded.

        Checks:
        1. Code format matches common patterns
        2. Appears in multiple passages
        3. Contains zoning-related keywords
        """
        reasons = []
        confidence = 0.0

        # 1. Format check
        if self._check_format(candidate.code):
            confidence += 0.4
            reasons.append("Matches zone code pattern")
        else:
            return ValidationResult(
                code=candidate.code,
                is_valid=False,
                confidence=0.0,
                reasons=["Does not match zone code pattern"]
            )

        # 2. Frequency check
        if len(candidate.passages) >= 2:
            confidence += 0.3
            reasons.append(f"Appears {len(candidate.passages)} times")

        # 3. Context check
        has_zone_keywords = any(
            any(kw in p.lower() for kw in ['zone', 'district', 'zoning'])
            for p in candidate.passages
        )
        if has_zone_keywords:
            confidence += 0.3
            reasons.append("Contains zoning keywords")

        is_valid = confidence >= self.min_confidence

        return ValidationResult(
            code=candidate.code,
            is_valid=is_valid,
            confidence=confidence,
            reasons=reasons
        )

    def _check_format(self, code: str) -> bool:
        """Check if code matches common zone code patterns."""
        patterns = [
            r'^[A-Z]{1,3}-?\d{1,2}$',           # R-1, C-2, I-1
            r'^[A-Z]{2,4}$',                     # AG, MU, RMU
            r'^[A-Z]-[A-Z]{1,2}$',              # R-SF, C-GC
            r'^[A-Z]{1,2}/[A-Z]{1,2}$',         # M/H, R/O
            r'^[A-Z]{1,2}-[A-Z]{2,4}$',         # R-MH, C-OFC
        ]
        code_clean = code.strip().upper()
        return any(re.match(p, code_clean) for p in patterns)

    def normalize_zone_code(self, code: str) -> str:
        """
        Normalize zone code to canonical form.
        E.g., "R 1" -> "R-1", "r-1" -> "R-1"
        """
        code = code.strip().upper()
        # Add hyphen between letter and number if missing
        code = re.sub(r'([A-Z]+)\s+(\d+)', r'\1-\2', code)
        return code
