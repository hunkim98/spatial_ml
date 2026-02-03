"""
City Matcher - Match zoneomics CSVs with municode ordinance folders.

Handles naming variations between the two data sources:
- zoneomics: "bay-minette.csv" (kebab-case)
- municode: "bay_minette/" (snake_case)
"""

import os
import re
from pathlib import Path
from dataclasses import dataclass
from typing import Optional


@dataclass
class CityMatch:
    """A matched city between zoneomics and municode data."""
    state: str  # State name (zoneomics format, e.g., "alabama")
    state_abbrev: str  # State abbreviation (e.g., "al")
    city_name: str  # Normalized city name
    zoneomics_path: Path  # Path to zoneomics CSV
    municode_path: Path  # Path to municode folder


# State name to abbreviation mapping
STATE_ABBREV = {
    "alabama": "al", "alaska": "ak", "arizona": "az", "arkansas": "ar",
    "california": "ca", "colorado": "co", "connecticut": "ct", "delaware": "de",
    "florida": "fl", "georgia": "ga", "hawaii": "hi", "idaho": "id",
    "illinois": "il", "indiana": "in", "iowa": "ia", "kansas": "ks",
    "kentucky": "ky", "louisiana": "la", "maine": "me", "maryland": "md",
    "massachusetts": "ma", "michigan": "mi", "minnesota": "mn", "mississippi": "ms",
    "missouri": "mo", "montana": "mt", "nebraska": "ne", "nevada": "nv",
    "new-hampshire": "nh", "new-jersey": "nj", "new-mexico": "nm", "new-york": "ny",
    "north-carolina": "nc", "north-dakota": "nd", "ohio": "oh", "oklahoma": "ok",
    "oregon": "or", "pennsylvania": "pa", "rhode-island": "ri", "south-carolina": "sc",
    "south-dakota": "sd", "tennessee": "tn", "texas": "tx", "utah": "ut",
    "vermont": "vt", "virginia": "va", "washington": "wa", "west-virginia": "wv",
    "wisconsin": "wi", "wyoming": "wy"
}


def normalize_city_name(name: str) -> str:
    """
    Normalize city name for matching.
    
    Handles:
    - Hyphens vs underscores: "bay-minette" -> "bayminette"
    - Dots and special chars: "mt._vernon" -> "mtvernon"
    - Case: "Birmingham" -> "birmingham"
    """
    name = name.lower()
    # Remove file extension if present
    name = re.sub(r'\.csv$', '', name)
    # Remove all non-alphanumeric characters
    name = re.sub(r'[^a-z0-9]', '', name)
    return name


class CityMatcher:
    """Match cities between zoneomics and municode datasets."""
    
    def __init__(
        self,
        zoneomics_dir: str | Path,
        municode_dir: str | Path
    ):
        """
        Initialize the city matcher.
        
        Args:
            zoneomics_dir: Path to zoneomics data (e.g., data/zoneomics/)
            municode_dir: Path to municode data (e.g., collector/tmp/zoning_ordinance/)
        """
        self.zoneomics_dir = Path(zoneomics_dir)
        self.municode_dir = Path(municode_dir)
        
        # Build indices
        self._zoneomics_index: dict[str, dict[str, Path]] = {}  # state -> {normalized_city -> path}
        self._municode_index: dict[str, dict[str, Path]] = {}  # state_abbrev -> {normalized_city -> path}
        
        self._build_indices()
    
    def _build_indices(self):
        """Build lookup indices for both data sources."""
        # Index zoneomics data (organized by state name)
        for state_dir in self.zoneomics_dir.iterdir():
            if not state_dir.is_dir():
                continue
            state_name = state_dir.name  # e.g., "alabama"
            self._zoneomics_index[state_name] = {}
            
            for csv_file in state_dir.glob("*.csv"):
                city_name = csv_file.stem  # e.g., "birmingham"
                normalized = normalize_city_name(city_name)
                self._zoneomics_index[state_name][normalized] = csv_file
        
        # Index municode data (organized by state abbreviation)
        for state_dir in self.municode_dir.iterdir():
            if not state_dir.is_dir():
                continue
            state_abbrev = state_dir.name  # e.g., "al"
            self._municode_index[state_abbrev] = {}
            
            for city_dir in state_dir.iterdir():
                if not city_dir.is_dir():
                    continue
                city_name = city_dir.name  # e.g., "birmingham"
                normalized = normalize_city_name(city_name)
                self._municode_index[state_abbrev][normalized] = city_dir
    
    def find_matches(self) -> list[CityMatch]:
        """
        Find all cities that exist in both zoneomics and municode data.
        
        Returns:
            List of CityMatch objects for cities with data in both sources.
        """
        matches = []
        
        for state_name, zoneomics_cities in self._zoneomics_index.items():
            # Get corresponding state abbreviation
            state_abbrev = STATE_ABBREV.get(state_name)
            if not state_abbrev:
                continue
            
            # Get municode cities for this state
            municode_cities = self._municode_index.get(state_abbrev, {})
            
            # Find intersection
            for normalized_city, zoneomics_path in zoneomics_cities.items():
                if normalized_city in municode_cities:
                    municode_path = municode_cities[normalized_city]
                    
                    # Use original city name from zoneomics (more readable)
                    city_name = zoneomics_path.stem
                    
                    matches.append(CityMatch(
                        state=state_name,
                        state_abbrev=state_abbrev,
                        city_name=city_name,
                        zoneomics_path=zoneomics_path,
                        municode_path=municode_path
                    ))
        
        return matches
    
    def get_match(self, state: str, city: str) -> Optional[CityMatch]:
        """
        Get a specific city match.
        
        Args:
            state: State name or abbreviation
            city: City name (any format)
            
        Returns:
            CityMatch if found, None otherwise.
        """
        # Normalize inputs
        state_lower = state.lower()
        normalized_city = normalize_city_name(city)
        
        # Determine state name and abbreviation
        if state_lower in STATE_ABBREV:
            state_name = state_lower
            state_abbrev = STATE_ABBREV[state_lower]
        elif state_lower in STATE_ABBREV.values():
            state_abbrev = state_lower
            state_name = next(k for k, v in STATE_ABBREV.items() if v == state_abbrev)
        else:
            return None
        
        # Look up in both indices
        zoneomics_cities = self._zoneomics_index.get(state_name, {})
        municode_cities = self._municode_index.get(state_abbrev, {})
        
        if normalized_city in zoneomics_cities and normalized_city in municode_cities:
            return CityMatch(
                state=state_name,
                state_abbrev=state_abbrev,
                city_name=zoneomics_cities[normalized_city].stem,
                zoneomics_path=zoneomics_cities[normalized_city],
                municode_path=municode_cities[normalized_city]
            )
        
        return None
    
    def get_stats(self) -> dict:
        """Get statistics about the data and matches."""
        zoneomics_total = sum(len(cities) for cities in self._zoneomics_index.values())
        municode_total = sum(len(cities) for cities in self._municode_index.values())
        matches = self.find_matches()
        
        return {
            "zoneomics_states": len(self._zoneomics_index),
            "zoneomics_cities": zoneomics_total,
            "municode_states": len(self._municode_index),
            "municode_cities": municode_total,
            "matched_cities": len(matches),
            "match_rate_zoneomics": len(matches) / zoneomics_total if zoneomics_total > 0 else 0,
            "match_rate_municode": len(matches) / municode_total if municode_total > 0 else 0,
        }


if __name__ == "__main__":
    # Example usage
    import sys
    
    # Default paths (relative to project root)
    zoneomics_dir = "data/zoneomics"
    municode_dir = "collector/tmp/zoning_ordinance"
    
    matcher = CityMatcher(zoneomics_dir, municode_dir)
    
    # Print statistics
    stats = matcher.get_stats()
    print("=" * 60)
    print("City Matching Statistics")
    print("=" * 60)
    print(f"Zoneomics: {stats['zoneomics_cities']} cities in {stats['zoneomics_states']} states")
    print(f"Municode:  {stats['municode_cities']} cities in {stats['municode_states']} states")
    print(f"Matched:   {stats['matched_cities']} cities")
    print(f"Match rate (of zoneomics): {stats['match_rate_zoneomics']:.1%}")
    print(f"Match rate (of municode):  {stats['match_rate_municode']:.1%}")
    print("=" * 60)
    
    # Print first 10 matches
    matches = matcher.find_matches()
    print(f"\nFirst 10 matches:")
    for match in matches[:10]:
        print(f"  {match.state_abbrev.upper()}/{match.city_name}")
