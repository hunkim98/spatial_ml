"""
End-to-end pipeline for extracting zoning codes from ordinance documents.
Orchestrates the 3-stage extraction process: Extractor -> Validator -> Categorizer
"""

import csv
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import List, Optional, Dict
from collections import defaultdict

from .core.extractor import ZoneExtractor, ExtractedSpan
from .core.validator import ZoneValidator, CandidateZone, ValidationResult
from .core.categorizer import ZoneCategorizer, CategorizedZone
from .parsers.ordinance_parser import OrdinanceParser, OrdinanceDocument


@dataclass
class ExtractedZoneCode:
    """Final extracted zone code with all metadata."""
    zone_code: str
    zone_subtype: str
    area_acres: Optional[float]
    description: str
    confidence: float
    num_mentions: int
    sample_passages: List[str]


class ZoningCodePipeline:
    """
    End-to-end pipeline for extracting zoning codes from municipal ordinances.

    Pipeline stages:
    1. Extractor: Identifies zone code mentions in text (token classification model)
    2. Validator: Filters false positives using binary classification model
    3. Categorizer: Assigns category and subtype labels

    Usage:
        pipeline = ZoningCodePipeline(
            extractor_model_path="path/to/extractor",
            validator_model_path="path/to/validator"
        )
        results = pipeline.extract_from_ordinances("tmp/zoning_ordinance/al/birmingham")
        pipeline.save_to_csv(results, "output/birmingham.csv")
    """

    def __init__(
        self,
        extractor_model_path: Optional[str] = None,
        validator_model_path: Optional[str] = None,
        min_validation_confidence: float = 0.5,
        min_extraction_score: float = 0.5,
        max_sample_passages: int = 3
    ):
        """
        Initialize the pipeline.

        Args:
            extractor_model_path: Path to trained extractor model
            validator_model_path: Path to trained validator model (if None, uses rule-based fallback)
            min_validation_confidence: Minimum confidence for validator
            min_extraction_score: Minimum score for extractor predictions
            max_sample_passages: Max number of sample passages to keep per zone
        """
        self.max_sample_passages = max_sample_passages

        # Initialize components
        self.extractor = ZoneExtractor(
            model_path=extractor_model_path,
            min_score=min_extraction_score
        )
        self.validator = ZoneValidator(
            model_path=validator_model_path,
            min_confidence=min_validation_confidence
        )
        self.categorizer = ZoneCategorizer()
        self.parser = OrdinanceParser()

    def extract_from_text(self, text: str) -> List[ExtractedZoneCode]:
        """
        Extract zone codes from a single text string.

        Args:
            text: Ordinance text

        Returns:
            List of extracted zone codes
        """
        # Stage 1: Extract candidate mentions
        spans = self.extractor.extract(text)

        if not spans:
            return []

        # Group spans by normalized code
        code_to_spans = defaultdict(list)
        for span in spans:
            normalized = self.extractor.normalize_extracted_code(span.text)
            code_to_spans[normalized].append(span)

        # Stage 2: Validate candidates
        candidates = []
        for code, code_spans in code_to_spans.items():
            # Extract passages around each mention
            passages = self._extract_passages(text, code_spans)

            candidate = CandidateZone(
                code=code,
                passages=passages,
                locations=[(s.start, s.end) for s in code_spans]
            )
            candidates.append(candidate)

        validation_results = self.validator.validate_batch(candidates)

        # Filter to valid codes
        valid_codes = []
        for candidate, result in zip(candidates, validation_results):
            if result.is_valid:
                valid_codes.append((candidate, result))

        if not valid_codes:
            return []

        # Stage 3: Categorize valid codes
        zone_descriptions = self._extract_descriptions(text, valid_codes)

        categorized = []
        for (candidate, validation), description in zip(valid_codes, zone_descriptions):
            cat_result = self.categorizer.categorize(
                zone_code=candidate.code,
                description=description
            )

            # Create final result
            zone = ExtractedZoneCode(
                zone_code=candidate.code,
                zone_subtype=cat_result.subtype or "Unknown",
                area_acres=None,  # Not available from text
                description=description,
                confidence=validation.confidence * cat_result.confidence,
                num_mentions=len(candidate.passages),
                sample_passages=candidate.passages[:self.max_sample_passages]
            )
            categorized.append(zone)

        return categorized

    def extract_from_ordinances(
        self,
        ordinance_dir: str,
        zoning_only: bool = True
    ) -> List[ExtractedZoneCode]:
        """
        Extract zone codes from a directory of ordinance documents.

        Args:
            ordinance_dir: Path to directory with DOCX files
            zoning_only: Only process zoning-related documents

        Returns:
            List of extracted zone codes
        """
        # Parse ordinance documents
        documents = self.parser.parse_all(ordinance_dir, zoning_only=zoning_only)

        if not documents:
            return []

        # Combine all text
        full_text = self._combine_documents(documents)

        # Extract from combined text
        return self.extract_from_text(full_text)

    def save_to_csv(
        self,
        zones: List[ExtractedZoneCode],
        output_path: str,
        include_metadata: bool = False
    ):
        """
        Save extracted zones to CSV in zoneomics format.

        Args:
            zones: List of extracted zone codes
            output_path: Path to output CSV file
            include_metadata: Whether to include extra columns (confidence, etc.)
        """
        output_file = Path(output_path)
        output_file.parent.mkdir(parents=True, exist_ok=True)

        with open(output_file, 'w', newline='', encoding='utf-8') as f:
            if include_metadata:
                fieldnames = [
                    'zone_code', 'zone_subtype', 'area_acres', 'description',
                    'confidence', 'num_mentions'
                ]
            else:
                fieldnames = ['zone_code', 'zone_subtype', 'area_acres', 'description']

            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()

            for zone in zones:
                row = {
                    'zone_code': zone.zone_code,
                    'zone_subtype': zone.zone_subtype,
                    'area_acres': zone.area_acres or '',
                    'description': zone.description
                }
                if include_metadata:
                    row['confidence'] = f"{zone.confidence:.3f}"
                    row['num_mentions'] = zone.num_mentions

                writer.writerow(row)

    def _extract_passages(
        self,
        text: str,
        spans: List[ExtractedSpan],
        context_window: Optional[int] = None
    ) -> List[str]:
        """
        Extract text passages around each span.

        Args:
            text: Source text
            spans: List of extracted spans
            context_window: Size of context window (defaults to half of CONTEXT_WINDOW from config)

        Returns:
            List of passage strings
        """
        # Default to 250 (half of typical 500 context window)
        # This can be overridden by passing context_window explicitly
        if context_window is None:
            context_window = 250

        passages = []
        for span in spans:
            start = max(0, span.start - context_window)
            end = min(len(text), span.end + context_window)
            passage = text[start:end].strip()
            passages.append(passage)
        return passages

    def _extract_descriptions(
        self,
        text: str,
        valid_codes: List[tuple[CandidateZone, ValidationResult]]
    ) -> List[str]:
        """
        Extract description for each valid zone code.

        Looks for definitional passages or uses the longest passage.
        """
        descriptions = []
        for candidate, _ in valid_codes:
            # Find the best passage (longest one, or one with "purpose")
            best_passage = ""
            for passage in candidate.passages:
                if "purpose" in passage.lower() or "establish" in passage.lower():
                    best_passage = passage
                    break
                if len(passage) > len(best_passage):
                    best_passage = passage

            descriptions.append(best_passage)

        return descriptions

    def _combine_documents(self, documents: List[OrdinanceDocument]) -> str:
        """Combine multiple documents into single text."""
        parts = []
        for doc in documents:
            for section in doc.sections:
                if section.content:
                    parts.append(section.content)

        return "\n\n".join(parts)
