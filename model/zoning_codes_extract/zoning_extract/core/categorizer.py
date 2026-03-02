"""
Stage 3: Category Assignment
Assigns coarse categories to validated zone codes based on their descriptions.
Uses rule-based keyword matching for classification.
"""

import re
from dataclasses import dataclass
from enum import Enum
from typing import List, Optional


class ZoneCategory(Enum):
    """Coarse zoning categories."""
    RESIDENTIAL = "Residential"
    COMMERCIAL = "Commercial"
    INDUSTRIAL = "Industrial"
    AGRICULTURAL = "Agricultural"
    MIXED_USE = "Mixed Use"
    SPECIAL = "Special Purpose"
    UNKNOWN = "Unknown"


@dataclass
class CategorizedZone:
    """A zone code with assigned category and subtype."""
    code: str
    category: ZoneCategory
    subtype: Optional[str]
    confidence: float
    description: str


class ZoneCategorizer:
    """
    Assigns category labels to zone codes based on code pattern and description.

    Uses rule-based keyword matching to classify zones into coarse categories:
    - Residential (single-family, multi-family, etc.)
    - Commercial (retail, office, service)
    - Industrial (light, heavy, manufacturing)
    - Agricultural
    - Mixed Use
    - Special Purpose (parks, public, institutional)
    """

    # Category keywords (code patterns and description keywords)
    CATEGORY_RULES = {
        ZoneCategory.RESIDENTIAL: {
            'code_patterns': [r'^R-?\d*', r'^RS', r'^RM', r'^RH', r'^R/'],
            'keywords': [
                'residential', 'dwelling', 'housing', 'home', 'family',
                'single family', 'multi family', 'duplex', 'townhouse',
                'apartment', 'condominium', 'mobile home', 'manufactured home'
            ],
            'subtypes': {
                'single family': 'Single Family Residential',
                'duplex': 'Single And Duplex Residential',
                'multi family': 'Multi Family Residential',
                'multi-family': 'Multi Family Residential',
                'multifamily': 'Multi Family Residential',
                'apartment': 'Multi Family Residential',
                'manufactured home': 'Manufactured Home Residential',
                'mobile home': 'Manufactured Home Residential',
                'townhouse': 'Multi Family Residential',
                'high density': 'High Density Residential',
                'medium density': 'Medium Density Residential',
                'low density': 'Low Density Residential',
            }
        },
        ZoneCategory.COMMERCIAL: {
            'code_patterns': [r'^C-?\d*', r'^B-?\d*', r'^COM', r'^NC', r'^GC'],
            'keywords': [
                'commercial', 'business', 'retail', 'office', 'service',
                'shopping', 'store', 'sales', 'consumer', 'professional',
                'administrative', 'mercantile'
            ],
            'subtypes': {
                'office': 'Commercial Office',
                'professional': 'Commercial Office',
                'general business': 'General Business',
                'general commercial': 'General Commercial',
                'neighborhood': 'Neighborhood Commercial',
                'service': 'General Services',
                'retail': 'Retail Commercial',
            }
        },
        ZoneCategory.INDUSTRIAL: {
            'code_patterns': [r'^I-?\d*', r'^M-?\d*', r'^IND', r'^MFG'],
            'keywords': [
                'industrial', 'manufacturing', 'warehouse', 'distribution',
                'production', 'fabrication', 'assembly', 'processing',
                'heavy industrial', 'light industrial'
            ],
            'subtypes': {
                'light': 'Light Industrial',
                'light industrial': 'Light Industrial',
                'garden': 'Garden Industrial',
                'heavy': 'Heavy Industrial',
                'heavy industrial': 'Heavy Industrial',
                'general': 'General Industrial',
                'manufacturing': 'Manufacturing',
                'warehouse': 'Warehouse and Distribution',
            }
        },
        ZoneCategory.AGRICULTURAL: {
            'code_patterns': [r'^A-?\d*', r'^AG', r'^FARM', r'^RUR'],
            'keywords': [
                'agricultural', 'agriculture', 'farming', 'farm',
                'rural', 'crop', 'livestock', 'ranch'
            ],
            'subtypes': {
                'general': 'General Agricultural',
                'intensive': 'Intensive Agricultural',
            }
        },
        ZoneCategory.MIXED_USE: {
            'code_patterns': [r'^MU', r'^MX', r'^RMU', r'^PMU'],
            'keywords': [
                'mixed use', 'mixed-use', 'mixed development',
                'live-work', 'transit-oriented'
            ],
            'subtypes': {
                'regional': 'Regional Mixed Use',
                'urban': 'Urban Mixed Use',
                'neighborhood': 'Neighborhood Mixed Use',
            }
        },
        ZoneCategory.SPECIAL: {
            'code_patterns': [r'^P-?\d*', r'^OS', r'^PD', r'^PAD', r'^PUD'],
            'keywords': [
                'public', 'institutional', 'park', 'open space',
                'planned development', 'planned area', 'planned unit',
                'recreational', 'civic', 'government'
            ],
            'subtypes': {
                'planned': 'Planned Area Development',
                'public': 'Public/Institutional',
                'park': 'Parks and Recreation',
                'open space': 'Open Space',
            }
        },
    }

    def __init__(self, default_category: ZoneCategory = ZoneCategory.UNKNOWN):
        """
        Initialize categorizer.

        Args:
            default_category: Category to assign when no match found
        """
        self.default_category = default_category

        # Compile regex patterns for efficiency
        self.compiled_patterns = {}
        for category, rules in self.CATEGORY_RULES.items():
            patterns = [re.compile(p, re.IGNORECASE) for p in rules['code_patterns']]
            self.compiled_patterns[category] = patterns

    def categorize(
        self,
        zone_code: str,
        description: str
    ) -> CategorizedZone:
        """
        Categorize a zone code based on its code and description.

        Args:
            zone_code: The zone code (e.g., "R-1", "C-2")
            description: Full text description of the zone

        Returns:
            CategorizedZone with category, subtype, and confidence
        """
        description_lower = description.lower()
        code_upper = zone_code.upper()

        # Score each category
        scores = {}
        for category, rules in self.CATEGORY_RULES.items():
            score = 0.0

            # Check code pattern (strong signal)
            for pattern in self.compiled_patterns[category]:
                if pattern.match(code_upper):
                    score += 0.6
                    break

            # Check description keywords
            keyword_matches = sum(
                1 for keyword in rules['keywords']
                if keyword in description_lower
            )
            if keyword_matches > 0:
                score += min(0.4, keyword_matches * 0.1)

            scores[category] = score

        # Get best category
        if not scores or max(scores.values()) == 0:
            category = self.default_category
            confidence = 0.0
        else:
            category = max(scores, key=scores.get)
            confidence = scores[category]

        # Extract subtype
        subtype = self._extract_subtype(category, description_lower)

        return CategorizedZone(
            code=zone_code,
            category=category,
            subtype=subtype,
            confidence=confidence,
            description=description
        )

    def categorize_batch(
        self,
        zones: List[tuple[str, str]]
    ) -> List[CategorizedZone]:
        """
        Categorize multiple zones.

        Args:
            zones: List of (zone_code, description) tuples

        Returns:
            List of CategorizedZone objects
        """
        return [self.categorize(code, desc) for code, desc in zones]

    def _extract_subtype(
        self,
        category: ZoneCategory,
        description_lower: str
    ) -> Optional[str]:
        """
        Extract a more specific subtype based on keywords in description.

        Args:
            category: The assigned category
            description_lower: Lowercase description text

        Returns:
            Subtype string or None
        """
        if category not in self.CATEGORY_RULES:
            return None

        subtypes = self.CATEGORY_RULES[category].get('subtypes', {})

        # Find the best matching subtype
        for keyword, subtype_name in subtypes.items():
            if keyword in description_lower:
                return subtype_name

        # Return a default subtype based on category
        if category == ZoneCategory.RESIDENTIAL:
            return "Residential"
        elif category == ZoneCategory.COMMERCIAL:
            return "Commercial"
        elif category == ZoneCategory.INDUSTRIAL:
            return "Industrial"
        elif category == ZoneCategory.AGRICULTURAL:
            return "Agricultural"
        elif category == ZoneCategory.MIXED_USE:
            return "Mixed Use"
        elif category == ZoneCategory.SPECIAL:
            return "Special Purpose"

        return None
