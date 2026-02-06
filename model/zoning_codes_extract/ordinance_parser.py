"""
Ordinance Parser - Extract text from municode markdown files.

Parses the hierarchical markdown files (converted from docx using pandoc)
downloaded from municode and extracts text content, preserving section structure.

Prerequisites:
    Run the conversion script first to convert docx files to markdown:
    python model/zoning_codes_extract/training/convert_docx_to_md.py --dir collector/tmp/zoning_ordinance
"""

import re
from pathlib import Path
from dataclasses import dataclass, field
from typing import Iterator


@dataclass
class Section:
    """A section of ordinance text."""
    title: str
    content: str
    level: int = 0  # Nesting level (0 = top level)


@dataclass
class OrdinanceDocument:
    """A parsed ordinance document."""
    city: str
    state: str
    filename: str
    filepath: Path
    sections: list[Section] = field(default_factory=list)
    raw_text: str = ""

    @property
    def is_zoning_related(self) -> bool:
        """Check if this document is likely about zoning districts."""
        zoning_keywords = [
            'zoning', 'district', 'land use', 'residential', 'commercial',
            'industrial', 'agricultural', 'mixed use', 'overlay'
        ]
        text_lower = (self.filename + " " + self.raw_text[:2000]).lower()
        return any(kw in text_lower for kw in zoning_keywords)


class OrdinanceParser:
    """Parse ordinance documents from municode markdown files."""

    # Municode uses this separator in filenames for hierarchy
    HIERARCHY_SEPARATOR = "⫸"

    # HIGH CONFIDENCE: Files that definitely contain zoning districts
    # Note: patterns use lowercase since filenames are lowercased before matching
    HIGH_CONFIDENCE_PATTERNS = [
        # Zone code patterns in filename (R-1, C-2, M-1, CN, CG, etc.)
        r'[rcimb]-\d{1,2}[a-z]?(?:\s|$|\))',  # R-1, C-2, M-1, R-1A, R-5
        r'[rcim]-[a-z]{1,3}(?:\s|$|\))',       # R-SF, C-GC, I-BP, CN, CG
        r'rm-[\d\.]+',                          # RM-2.5, RM-1.5
        r'\b[rcimb]\d[a-z]?\b',                 # R1, C2, M1 (no hyphen)

        # Explicit zoning ordinance containers
        r'(?:title|appendix).*zoning',
        r'chapter\s*\d+.*zoning',
        r'article\s*\d+.*zoning',
        r'zoning\s+district',
        r'zoning\s+regulation',
        r'zoning\s+code',
        r'zoning\s+ordinance',

        # District definitions by type
        r'residential.*district',
        r'commercial.*district',
        r'industrial.*district',
        r'manufacturing.*district',
        r'agricultural.*district',
        r'office.*district',
        r'business.*district',
        r'mixed.?use.*district',
        r'overlay.*district',
        r'single.?family.*district',
        r'multi.?family.*district',

        # Zone patterns
        r'residential.*zone',
        r'commercial.*zone',
        r'industrial.*zone',

        # District regulation files
        r'district\s+regulations',
        r'district\s+requirements',
        r'establishment\s+of\s+districts',
        r'designation\s+of\s+districts',
        r'zones?\s+and\s+zoning\s+map',
        r'use\s+regulations?',
    ]

    # LAND USE AND DEVELOPMENT appendices (common in AL)
    LAND_USE_PATTERNS = [
        r'land.?use.*development',
    ]

    # Exclude false positives
    EXCLUDE_PATTERNS = [
        r'supervisorial\s+district',
        r'water\s+district',
        r'sanitary\s+district',
        r'fire\s+district',
        r'school\s+district',
        r'services?\s+district',
        r'improvement\s+district',
        r'district\s+attorney',
        r'community\s+facilities\s+district\s+no',  # CFD tax districts
    ]

    def __init__(self, municode_path: Path):
        """
        Initialize parser for a city's ordinance documents.

        Args:
            municode_path: Path to city's municode folder (e.g., collector/tmp/zoning_ordinance/al/birmingham/)
        """
        self.municode_path = Path(municode_path)
        self.city = self.municode_path.name
        self.state = self.municode_path.parent.name

    def list_documents(self) -> list[Path]:
        """
        List all markdown document files.

        Returns:
            List of markdown document paths
        """
        return sorted(self.municode_path.glob("*.md"))

    def list_zoning_documents(self) -> list[Path]:
        """
        List markdown files that are likely zoning-related based on filename.

        Uses evidence-based patterns derived from analysis of ordinances
        across multiple states (AL, CA, MA, etc.).
        """
        docs = []
        for doc_path in self.list_documents():
            filename_lower = doc_path.stem.lower()

            # Skip if matches exclusion pattern
            if any(re.search(p, filename_lower) for p in self.EXCLUDE_PATTERNS):
                continue

            # Include if matches any high confidence pattern
            if any(re.search(p, filename_lower) for p in self.HIGH_CONFIDENCE_PATTERNS):
                docs.append(doc_path)
                continue

            # Include land use/development files
            if any(re.search(p, filename_lower) for p in self.LAND_USE_PATTERNS):
                docs.append(doc_path)

        return docs

    def parse_document(self, md_path: Path) -> OrdinanceDocument:
        """
        Parse a markdown file into an OrdinanceDocument.

        Args:
            md_path: Path to the markdown file

        Returns:
            OrdinanceDocument with extracted text and sections
        """
        try:
            text = md_path.read_text(encoding='utf-8')
        except Exception:
            return OrdinanceDocument(
                city=self.city,
                state=self.state,
                filename=md_path.name,
                filepath=md_path,
                sections=[],
                raw_text=""
            )

        # Extract hierarchy from filename
        hierarchy = self._parse_filename_hierarchy(md_path.stem)

        # Split into sections based on headers
        sections = []
        current_title = hierarchy[-1] if hierarchy else md_path.stem
        current_content = []
        current_level = len(hierarchy)

        for line in text.split('\n'):
            # Check for markdown headers
            if line.startswith('#'):
                if current_content:
                    sections.append(Section(
                        title=current_title,
                        content='\n'.join(current_content),
                        level=current_level
                    ))
                # Count header level (# = 1, ## = 2, etc.)
                header_match = re.match(r'^(#+)\s*(.*)$', line)
                if header_match:
                    current_level = len(header_match.group(1))
                    current_title = header_match.group(2).strip()
                else:
                    current_title = line.lstrip('#').strip()
                current_content = []
            # Check for section patterns in text (e.g., "Sec. 17.24.010")
            elif self._is_section_header(line):
                if current_content:
                    sections.append(Section(
                        title=current_title,
                        content='\n'.join(current_content),
                        level=current_level
                    ))
                current_title = line.strip()
                current_content = []
            else:
                current_content.append(line)

        # Add final section
        if current_content:
            sections.append(Section(
                title=current_title,
                content='\n'.join(current_content),
                level=current_level
            ))

        return OrdinanceDocument(
            city=self.city,
            state=self.state,
            filename=md_path.name,
            filepath=md_path,
            sections=sections,
            raw_text=text
        )

    def _is_section_header(self, line: str) -> bool:
        """
        Detect section headers in markdown/text content.

        Args:
            line: A single line of text

        Returns:
            True if this line appears to be a section header
        """
        line = line.strip()
        if not line:
            return False

        # Numbered sections common in ordinances
        section_patterns = [
            r'^Sec\.\s*[\d\-\.]+',
            r'^Section\s*[\d\-\.]+',
            r'^Article\s+[IVX\d]+',
            r'^\d+[\.-]\d+[\.-]?\d*\s*[-—]',  # 17.24.010 -
        ]
        return any(re.match(p, line, re.IGNORECASE) for p in section_patterns)

    def _parse_filename_hierarchy(self, filename: str) -> list[str]:
        """
        Parse the hierarchy from a municode filename.

        Example:
            "Title 7 - BUILDING⫸CHAPTER 3. - PLANNING" -> ["Title 7 - BUILDING", "CHAPTER 3. - PLANNING"]
        """
        return filename.split(self.HIERARCHY_SEPARATOR)

    def parse_all(self, zoning_only: bool = True) -> Iterator[OrdinanceDocument]:
        """
        Parse all documents in the municode folder.

        Args:
            zoning_only: If True, only parse documents with zoning-related filenames

        Yields:
            OrdinanceDocument for each parsed file
        """
        if zoning_only:
            doc_paths = self.list_zoning_documents()
        else:
            doc_paths = self.list_documents()

        for doc_path in doc_paths:
            yield self.parse_document(doc_path)

    def get_combined_zoning_text(self) -> str:
        """
        Get all zoning-related text combined into a single string.

        Useful for text search across the entire zoning ordinance.
        """
        texts = []
        for doc in self.parse_all(zoning_only=True):
            if doc.raw_text:
                texts.append(f"=== {doc.filename} ===\n{doc.raw_text}")

        # If no zoning-specific documents found, try all documents
        if not texts:
            for doc in self.parse_all(zoning_only=False):
                if doc.is_zoning_related and doc.raw_text:
                    texts.append(f"=== {doc.filename} ===\n{doc.raw_text}")

        return "\n\n".join(texts)


def find_district_sections(doc: OrdinanceDocument) -> list[Section]:
    """
    Find sections that define zoning districts.

    Looks for sections with titles like:
    - "R-1 Single Family District"
    - "Sec. 5.1. - R-1 district"
    - "ARTICLE III. - RESIDENTIAL DISTRICTS"
    """
    district_pattern = re.compile(
        r'(?:^|[\s\-\.])([A-Z]{1,3}[\-\s]?\d{1,2}[A-Z]?)(?:[\s\-\.]|$)',
        re.IGNORECASE
    )

    district_sections = []
    for section in doc.sections:
        # Check title for district code patterns
        if district_pattern.search(section.title):
            district_sections.append(section)
        # Also check content for "purpose" statements
        elif 'purpose of' in section.content.lower() and 'district' in section.content.lower():
            district_sections.append(section)

    return district_sections


if __name__ == "__main__":
    import sys

    # Example usage
    if len(sys.argv) > 1:
        municode_path = Path(sys.argv[1])
    else:
        # Default test path
        municode_path = Path("collector/tmp/zoning_ordinance/al/birmingham")

    if not municode_path.exists():
        print(f"Path not found: {municode_path}")
        sys.exit(1)

    parser = OrdinanceParser(municode_path)

    print(f"Parsing ordinances for {parser.city}, {parser.state.upper()}")
    print("=" * 60)

    # List all documents
    all_docs = parser.list_documents()
    zoning_docs = parser.list_zoning_documents()

    print(f"Total documents: {len(all_docs)}")
    print(f"Zoning-related: {len(zoning_docs)}")
    print()

    # Parse zoning documents
    print("Zoning documents:")
    for doc in parser.parse_all(zoning_only=True):
        print(f"  - {doc.filename}")
        print(f"    Sections: {len(doc.sections)}")
        print(f"    Text length: {len(doc.raw_text)} chars")

        # Find district sections
        district_sections = find_district_sections(doc)
        if district_sections:
            print(f"    District sections: {len(district_sections)}")
            for section in district_sections[:3]:
                print(f"      * {section.title[:60]}...")
