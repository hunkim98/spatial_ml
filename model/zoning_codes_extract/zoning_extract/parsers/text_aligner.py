"""
Text Aligner - Match zoneomics descriptions to their source in ordinance text.

Uses fuzzy string matching to locate where each zoning district is defined
in the ordinance documents, enabling creation of training data.
"""

import csv
import re
from pathlib import Path
from dataclasses import dataclass
from typing import Optional

from rapidfuzz import fuzz, process

from ..utils import normalize_zone_code, find_all_zone_codes_in_text


@dataclass
class ZoningDistrict:
    """A zoning district from zoneomics data."""
    zone_code: str
    zone_subtype: str
    area_acres: float
    description: str


@dataclass
class AlignedDistrict:
    """A zoning district aligned with its source text."""
    zone_code: str
    zone_subtype: str
    description: str  # From zoneomics
    source_text: str  # Extracted from ordinance
    source_context: str  # Surrounding context from ordinance
    match_score: float  # Fuzzy match score (0-100)
    source_file: str  # Which document it was found in


def load_zoneomics_csv(csv_path: Path) -> list[ZoningDistrict]:
    """
    Load zoning districts from a zoneomics CSV file.
    
    Expected columns: zone_code, zone_subtype, area_acres, description
    """
    districts = []
    
    with open(csv_path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            # Handle NA values
            area = row.get('area_acres', '0')
            try:
                area_float = float(area) if area and area != 'NA' else 0.0
            except ValueError:
                area_float = 0.0
            
            description = row.get('description', '')
            if description == 'NA':
                description = ''
            
            districts.append(ZoningDistrict(
                zone_code=row['zone_code'],
                zone_subtype=row.get('zone_subtype', ''),
                area_acres=area_float,
                description=description
            ))
    
    return districts


def extract_purpose_statement(text: str) -> str:
    """
    Extract the "purpose" statement from text, which typically defines a district.
    
    Looks for patterns like:
    - "The purpose of the R-1 district is..."
    - "...is designed to allow for..."
    - "...is provided for..."
    """
    # Common purpose statement patterns
    patterns = [
        r'(?:The\s+)?purpose\s+(?:of\s+)?(?:the\s+)?[\w\-]+\s+(?:district\s+)?is\s+(?:to\s+)?(?:provide|designed|intended).*?(?:\.|$)',
        r'(?:is\s+)?designed\s+to\s+allow\s+for.*?(?:\.|$)',
        r'(?:is\s+)?provided\s+(?:for|to).*?(?:\.|$)',
    ]
    
    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE | re.DOTALL)
        if match:
            return match.group(0).strip()
    
    return text


def normalize_for_matching(text: str) -> str:
    """Normalize text for fuzzy matching."""
    # Lowercase
    text = text.lower()
    # Remove extra whitespace
    text = ' '.join(text.split())
    # Remove common variations
    text = text.replace('single-family', 'single family')
    text = text.replace('multi-family', 'multi family')
    return text


# normalize_zone_code and find_all_zone_codes_in_text are now imported from utils


class TextAligner:
    """Align zoneomics descriptions with ordinance text."""
    
    # Minimum match score to consider a valid alignment
    MIN_MATCH_SCORE = 70
    
    # Context window size (characters before and after match)
    CONTEXT_WINDOW = 500
    
    def __init__(self, ordinance_text: str, source_file: str = ""):
        """
        Initialize aligner with ordinance text.
        
        Args:
            ordinance_text: Full text of zoning ordinance
            source_file: Name of source file for reference
        """
        self.ordinance_text = ordinance_text
        self.source_file = source_file
        self.normalized_text = normalize_for_matching(ordinance_text)
        
        # Pre-compute chunks for faster searching
        self._chunks = self._create_chunks()
    
    def _create_chunks(self, chunk_size: int = 1000, overlap: int = 200) -> list[tuple[int, str]]:
        """
        Create overlapping chunks of text for efficient searching.
        
        Returns:
            List of (start_position, chunk_text) tuples
        """
        chunks = []
        text = self.ordinance_text
        
        pos = 0
        while pos < len(text):
            end = min(pos + chunk_size, len(text))
            chunk = text[pos:end]
            chunks.append((pos, chunk))
            pos += chunk_size - overlap
        
        return chunks
    
    def find_district_in_text(
        self,
        district: ZoningDistrict,
        search_by_code: bool = True
    ) -> Optional[AlignedDistrict]:
        """
        Find where a district is defined in the ordinance text.
        
        Strategy:
        1. First try to find by zone code (e.g., "R-1")
        2. Then fuzzy match the description to confirm
        3. Extract surrounding context
        
        Args:
            district: ZoningDistrict to find
            search_by_code: Whether to also search by zone code
            
        Returns:
            AlignedDistrict if found with sufficient confidence, None otherwise
        """
        if not district.description or district.description == 'NA':
            return None
        
        best_match = None
        best_score = 0
        
        # Strategy 1: Search by zone code first
        if search_by_code:
            code_matches = self._find_by_code(district.zone_code)
            for start_pos, end_pos in code_matches:
                # Extract surrounding text
                context_start = max(0, start_pos - self.CONTEXT_WINDOW)
                context_end = min(len(self.ordinance_text), end_pos + self.CONTEXT_WINDOW)
                context = self.ordinance_text[context_start:context_end]
                
                # Fuzzy match the description in this context
                score = fuzz.partial_ratio(
                    normalize_for_matching(district.description[:200]),
                    normalize_for_matching(context)
                )
                
                if score > best_score:
                    best_score = score
                    best_match = context
        
        # Strategy 2: Fuzzy match description across all chunks
        if best_score < self.MIN_MATCH_SCORE:
            desc_normalized = normalize_for_matching(district.description[:300])
            
            for start_pos, chunk in self._chunks:
                chunk_normalized = normalize_for_matching(chunk)
                score = fuzz.partial_ratio(desc_normalized, chunk_normalized)
                
                if score > best_score:
                    best_score = score
                    # Get more context
                    context_start = max(0, start_pos - 200)
                    context_end = min(len(self.ordinance_text), start_pos + len(chunk) + 200)
                    best_match = self.ordinance_text[context_start:context_end]
        
        if best_score < self.MIN_MATCH_SCORE or best_match is None:
            return None
        
        # Extract the actual matching portion
        source_text = extract_purpose_statement(best_match)
        if len(source_text) < 50:
            source_text = best_match[:500]
        
        return AlignedDistrict(
            zone_code=district.zone_code,
            zone_subtype=district.zone_subtype,
            description=district.description,
            source_text=source_text,
            source_context=best_match,
            match_score=best_score,
            source_file=self.source_file
        )
    
    def _find_by_code(self, zone_code: str) -> list[tuple[int, int]]:
        """
        Find all occurrences of a zone code in the text.
        
        Handles variations:
        - R-1, R1, R 1
        - Case insensitive
        
        Returns:
            List of (start, end) positions
        """
        # Create pattern that handles code variations
        # E.g., "R-1" -> r"R[\s\-]?1"
        parts = re.split(r'([\-\s])', zone_code)
        pattern_parts = []
        for part in parts:
            if part in ['-', ' ']:
                pattern_parts.append(r'[\s\-]?')
            else:
                pattern_parts.append(re.escape(part))
        
        pattern = ''.join(pattern_parts)
        
        # Add word boundaries
        pattern = r'\b' + pattern + r'\b'
        
        matches = []
        for match in re.finditer(pattern, self.ordinance_text, re.IGNORECASE):
            matches.append((match.start(), match.end()))
        
        return matches
    
    def align_all(self, districts: list[ZoningDistrict]) -> list[AlignedDistrict]:
        """
        Align all districts with the ordinance text.
        
        Args:
            districts: List of ZoningDistrict from zoneomics
            
        Returns:
            List of successfully aligned districts
        """
        aligned = []
        for district in districts:
            result = self.find_district_in_text(district)
            if result:
                aligned.append(result)
        
        return aligned


def align_city(
    zoneomics_path: Path,
    ordinance_text: str,
    source_file: str = ""
) -> tuple[list[AlignedDistrict], list[ZoningDistrict]]:
    """
    Align zoneomics data with ordinance text for a city.
    
    Args:
        zoneomics_path: Path to zoneomics CSV
        ordinance_text: Combined ordinance text
        source_file: Source file name for reference
        
    Returns:
        Tuple of (aligned_districts, unaligned_districts)
    """
    districts = load_zoneomics_csv(zoneomics_path)
    aligner = TextAligner(ordinance_text, source_file)
    
    aligned = []
    unaligned = []
    
    for district in districts:
        result = aligner.find_district_in_text(district)
        if result:
            aligned.append(result)
        else:
            unaligned.append(district)
    
    return aligned, unaligned


if __name__ == "__main__":
    import sys
    from ordinance_parser import OrdinanceParser
    
    # Test with Birmingham
    zoneomics_path = Path("data/zoneomics/alabama/birmingham.csv")
    municode_path = Path("collector/tmp/zoning_ordinance/al/birmingham")
    
    if not zoneomics_path.exists() or not municode_path.exists():
        print("Test paths not found. Run from project root.")
        sys.exit(1)
    
    print("Loading zoneomics data...")
    districts = load_zoneomics_csv(zoneomics_path)
    print(f"Loaded {len(districts)} districts")
    
    print("\nParsing ordinance text...")
    parser = OrdinanceParser(municode_path)
    ordinance_text = parser.get_combined_zoning_text()
    print(f"Ordinance text length: {len(ordinance_text)} chars")
    
    print("\nAligning districts...")
    aligned, unaligned = align_city(zoneomics_path, ordinance_text, "birmingham_zoning")
    
    print(f"\nResults:")
    print(f"  Aligned: {len(aligned)} ({len(aligned)/len(districts)*100:.1f}%)")
    print(f"  Unaligned: {len(unaligned)} ({len(unaligned)/len(districts)*100:.1f}%)")
    
    print("\nSample aligned districts:")
    for ad in aligned[:3]:
        print(f"\n  Code: {ad.zone_code}")
        print(f"  Subtype: {ad.zone_subtype}")
        print(f"  Match score: {ad.match_score:.1f}")
        print(f"  Source text preview: {ad.source_text[:150]}...")
    
    if unaligned:
        print("\nSample unaligned districts:")
        for d in unaligned[:3]:
            print(f"  - {d.zone_code}: {d.zone_subtype}")
