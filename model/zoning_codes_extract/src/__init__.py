"""Core library components for zoning codes extraction."""

from .extractor import ZoneExtractor, ExtractedSpan
from .validator import ZoneValidator, CandidateZone, ValidationResult
from .categorizer import ZoneCategorizer, CategorizedZone, ZoneCategory
from .pipeline import ZoningCodePipeline, ExtractedZoneCode
from .text_aligner import (
    TextAligner,
    AlignedDistrict,
    ZoningDistrict,
    load_zoneomics_csv,
    align_city,
    find_all_zone_codes_in_text,
    normalize_zone_code,
)
from .city_matcher import CityMatcher, CityMatch
from .ordinance_parser import OrdinanceParser, OrdinanceDocument, Section

__all__ = [
    # Extraction
    "ZoneExtractor",
    "ExtractedSpan",
    # Validation
    "ZoneValidator",
    "CandidateZone",
    "ValidationResult",
    # Categorization
    "ZoneCategorizer",
    "CategorizedZone",
    "ZoneCategory",
    # Pipeline
    "ZoningCodePipeline",
    "ExtractedZoneCode",
    # Text alignment
    "TextAligner",
    "AlignedDistrict",
    "ZoningDistrict",
    "load_zoneomics_csv",
    "align_city",
    "find_all_zone_codes_in_text",
    "normalize_zone_code",
    # City matching
    "CityMatcher",
    "CityMatch",
    # Ordinance parsing
    "OrdinanceParser",
    "OrdinanceDocument",
    "Section",
]
