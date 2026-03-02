"""Core library components for zoning codes extraction."""

# Core models
from .core.extractor import ZoneExtractor, ExtractedSpan
from .core.validator import ZoneValidator, CandidateZone, ValidationResult
from .core.categorizer import ZoneCategorizer, CategorizedZone, ZoneCategory

# Pipeline
from .pipeline import ZoningCodePipeline, ExtractedZoneCode

# Parsers
from .parsers.text_aligner import (
    TextAligner,
    AlignedDistrict,
    ZoningDistrict,
    load_zoneomics_csv,
    align_city,
)
from .parsers.ordinance_parser import OrdinanceParser, OrdinanceDocument

# Utilities
from .utils import (
    normalize_zone_code,
    find_all_zone_codes_in_text,
    extract_zones_from_bio,
)

# City matcher (stays in root for now)
from .city_matcher import CityMatcher, CityMatch

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
    # Utilities
    "normalize_zone_code",
    "find_all_zone_codes_in_text",
    "extract_zones_from_bio",
    # City matching
    "CityMatcher",
    "CityMatch",
    # Ordinance parsing
    "OrdinanceParser",
    "OrdinanceDocument",
]
