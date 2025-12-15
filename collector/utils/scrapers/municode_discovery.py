"""
Municode Discovery - Discover states and municipalities from library.municode.com

This module provides functionality to:
1. List all available states
2. List all municipalities within a state
3. Get the zoning ordinance URL for a specific municipality
"""

from utils.selenium import SeleniumUtil
from selenium.webdriver.common.by import By
import time
from typing import Optional
import us


class MunicodeDiscovery:
    """Discover states and municipalities from Municode Library."""

    BASE_URL = "https://library.municode.com"

    def __init__(self, headless: bool = True):
        """
        Initialize the discovery tool.

        Args:
            headless: Whether to run browser in headless mode
        """
        self.headless = headless
        self.selenium_util = None

    def _init_browser(self):
        """Initialize browser if not already initialized."""
        if self.selenium_util is None:
            self.selenium_util = SeleniumUtil(headless=self.headless)

    def _quit_browser(self):
        """Quit browser if initialized."""
        if self.selenium_util:
            self.selenium_util.quit()
            self.selenium_util = None

    def list_states(self) -> list[dict]:
        """
        List all available US states.

        Returns:
            List of dicts with 'abbrev', 'name', and 'url' keys
        """
        states = []
        for state in us.states.STATES:
            abbrev = state.abbr.lower()
            states.append({
                "abbrev": abbrev,
                "name": state.name,
                "url": f"{self.BASE_URL}/{abbrev}"
            })
        # Add DC
        states.append({
            "abbrev": "dc",
            "name": "District of Columbia",
            "url": f"{self.BASE_URL}/dc"
        })
        return sorted(states, key=lambda x: x["name"])

    def get_state_name(self, state_abbrev: str) -> str:
        """Get full state name from abbreviation."""
        state = us.states.lookup(state_abbrev)
        if state:
            return state.name
        if state_abbrev.lower() == "dc":
            return "District of Columbia"
        return state_abbrev

    def list_municipalities(self, state_abbrev: str) -> list[dict]:
        """
        List all municipalities for a given state.

        Args:
            state_abbrev: Two-letter state abbreviation (e.g., 'al', 'ma')

        Returns:
            List of dicts with 'name', 'slug', 'state_abbrev', 'state_name', and 'url' keys
        """
        state_abbrev = state_abbrev.lower()
        state_name = self.get_state_name(state_abbrev)
        state_url = f"{self.BASE_URL}/{state_abbrev}"

        print(f"Fetching municipalities for {state_name} ({state_abbrev.upper()})...")

        try:
            self._init_browser()
            self.selenium_util.driver.get(state_url)
            time.sleep(3)  # Wait for dynamic content to load

            municipalities = []

            # Find all municipality links
            # The structure is typically: /state_abbrev/municipality_slug/codes/...
            links = self.selenium_util.driver.find_elements(
                By.CSS_SELECTOR, f"a[href*='/{state_abbrev}/']"
            )

            seen_slugs = set()
            for link in links:
                try:
                    href = link.get_attribute("href")
                    text = link.text.strip()

                    if not href or not text:
                        continue

                    # Parse the URL to extract municipality slug
                    # Format: https://library.municode.com/al/abbeville/codes/...
                    parts = href.replace(self.BASE_URL, "").strip("/").split("/")
                    if len(parts) >= 2 and parts[0] == state_abbrev:
                        municipality_slug = parts[1]

                        # Skip if we've already seen this municipality
                        if municipality_slug in seen_slugs:
                            continue
                        seen_slugs.add(municipality_slug)

                        # Skip non-municipality links (like 'codes', 'ordinances', etc.)
                        if municipality_slug in ['codes', 'ordinances', 'charter', 'land_development']:
                            continue

                        municipalities.append({
                            "name": text,
                            "slug": municipality_slug,
                            "state_abbrev": state_abbrev,
                            "state_name": state_name,
                            "url": f"{self.BASE_URL}/{state_abbrev}/{municipality_slug}"
                        })

                except Exception:
                    continue

            print(f"Found {len(municipalities)} municipalities in {state_name}")
            return sorted(municipalities, key=lambda x: x["name"])

        finally:
            self._quit_browser()

    def get_municipality_codes_url(self, state_abbrev: str, municipality_slug: str) -> Optional[str]:
        """
        Get the codes/ordinances URL for a specific municipality.

        Args:
            state_abbrev: Two-letter state abbreviation
            municipality_slug: Municipality URL slug

        Returns:
            URL to the municipality's code of ordinances, or None if not found
        """
        state_abbrev = state_abbrev.lower()
        municipality_url = f"{self.BASE_URL}/{state_abbrev}/{municipality_slug}"

        print(f"Finding codes URL for {municipality_slug}, {state_abbrev.upper()}...")

        try:
            self._init_browser()
            self.selenium_util.driver.get(municipality_url)
            time.sleep(3)

            # Look for links to codes/ordinances
            code_patterns = [
                "codes/code_of_ordinances",
                "codes/zoning",
                "codes/land_development",
                "codes/unified_development",
            ]

            for pattern in code_patterns:
                try:
                    link = self.selenium_util.driver.find_element(
                        By.CSS_SELECTOR, f"a[href*='{pattern}']"
                    )
                    href = link.get_attribute("href")
                    if href:
                        print(f"Found codes URL: {href}")
                        return href
                except Exception:
                    continue

            # If specific patterns not found, look for any codes link
            try:
                link = self.selenium_util.driver.find_element(
                    By.CSS_SELECTOR, f"a[href*='/{state_abbrev}/{municipality_slug}/codes/']"
                )
                href = link.get_attribute("href")
                if href:
                    print(f"Found codes URL: {href}")
                    return href
            except Exception:
                pass

            print(f"No codes URL found for {municipality_slug}")
            return None

        finally:
            self._quit_browser()

