"""
Zoning Codes Extraction - 3-stage token classification pipeline.

This module provides tools for:
1. Matching cities between zoneomics (district codes) and municode (ordinances)
2. Parsing ordinance documents from docx files
3. Aligning district descriptions with their source text
4. Extracting zone codes using token classification (Stage 1: Extractor)
5. Validating candidates using rule-based validation (Stage 2: Validator)
6. Categorizing zones using keyword matching (Stage 3: Categorizer)
7. End-to-end pipeline orchestration

Usage:
    # Extract zone codes from ordinances
    from model.zoning_codes_extract import ZoningCodePipeline

    pipeline = ZoningCodePipeline(extractor_model_path="path/to/model")
    results = pipeline.extract_from_ordinances("tmp/zoning_ordinance/al/birmingham")
    pipeline.save_to_csv(results, "output/birmingham.csv")

    # Or use individual components
    from model.zoning_codes_extract import (
        ZoneExtractor,
        ZoneValidator,
        ZoneCategorizer
    )
"""

from .city_matcher import CityMatcher, CityMatch
from .ordinance_parser import OrdinanceParser, OrdinanceDocument, Section
from .text_aligner import (
    TextAligner,
    AlignedDistrict,
    ZoningDistrict,
    load_zoneomics_csv,
    align_city,
    find_all_zone_codes_in_text,
    normalize_zone_code,
)
from .extractor import ZoneExtractor, ExtractedSpan
from .validator import ZoneValidator, CandidateZone, ValidationResult
from .categorizer import ZoneCategorizer, CategorizedZone, ZoneCategory
from .pipeline import ZoningCodePipeline, ExtractedZoneCode

__all__ = [
    # City matching
    "CityMatcher",
    "CityMatch",

    # Ordinance parsing
    "OrdinanceParser",
    "OrdinanceDocument",
    "Section",

    # Text alignment
    "TextAligner",
    "AlignedDistrict",
    "ZoningDistrict",
    "load_zoneomics_csv",
    "align_city",
    "find_all_zone_codes_in_text",
    "normalize_zone_code",

    # Stage 1: Extraction
    "ZoneExtractor",
    "ExtractedSpan",

    # Stage 2: Validation
    "ZoneValidator",
    "CandidateZone",
    "ValidationResult",

    # Stage 3: Categorization
    "ZoneCategorizer",
    "CategorizedZone",
    "ZoneCategory",

    # Pipeline
    "ZoningCodePipeline",
    "ExtractedZoneCode",
]
