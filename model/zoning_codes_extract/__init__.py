"""
Zoning Codes Extraction - Training data pipeline and model trainer.

This module provides tools for:
1. Matching cities between zoneomics (district codes) and municode (ordinances)
2. Parsing ordinance documents from docx files
3. Aligning district descriptions with their source text
4. Generating training data for LLM fine-tuning
5. Training/fine-tuning models for zoning code extraction

Usage:
    # Generate training data
    python -m model.zoning_codes_extract.training_data_generator
    
    # Or use the classes directly
    from model.zoning_codes_extract import (
        CityMatcher,
        OrdinanceParser,
        TextAligner,
        TrainingDataGenerator,
        ZoningCodesExtractTrainer
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
from .training_data_generator import TrainingDataGenerator, TrainingExample
from .trainer import ZoningCodesExtractTrainer

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
    
    # Training data generation
    "TrainingDataGenerator",
    "TrainingExample",
    
    # Training
    "ZoningCodesExtractTrainer",
]
