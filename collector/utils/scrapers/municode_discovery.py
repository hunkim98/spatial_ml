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
        Get the codes/ordinances URL for a specific municipality WITH the nodeId.

        This method navigates to the municipality's codes page, clicks on the first
        item in the left panel (the root code of ordinances), and returns the URL
        with the nodeId parameter appended.

        Args:
            state_abbrev: Two-letter state abbreviation
            municipality_slug: Municipality URL slug

        Returns:
            URL to the municipality's code of ordinances with nodeId, or None if not found
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

            codes_page_url = None
            for pattern in code_patterns:
                try:
                    link = self.selenium_util.driver.find_element(
                        By.CSS_SELECTOR, f"a[href*='{pattern}']"
                    )
                    href = link.get_attribute("href")
                    if href:
                        codes_page_url = href
                        break
                except Exception:
                    continue

            # If specific patterns not found, look for any codes link
            if not codes_page_url:
                try:
                    link = self.selenium_util.driver.find_element(
                        By.CSS_SELECTOR, f"a[href*='/{state_abbrev}/{municipality_slug}/codes/']"
                    )
                    codes_page_url = link.get_attribute("href")
                except Exception:
                    pass

            if not codes_page_url:
                print(f"No codes URL found for {municipality_slug}")
                return None

            print(f"Found codes page: {codes_page_url}")
            
            # Now navigate to the codes page and click the first item to get nodeId
            return self._get_url_with_node_id(codes_page_url)

        finally:
            self._quit_browser()

    def _get_url_with_node_id(self, codes_page_url: str) -> Optional[str]:
        """
        Get the nodeId for the first TOC item by opening the download panel.

        The Municode site stores nodeIds in the download panel's TOC tree.
        We open the panel, grab the first nodeId, then close it.

        Args:
            codes_page_url: URL to the codes page (without nodeId)

        Returns:
            URL with nodeId parameter, or None if not found
        """
        print(f"Getting nodeId for: {codes_page_url}")
        self.selenium_util.driver.get(codes_page_url)
        time.sleep(4)  # Wait for page to fully load

        try:
            # First, try clicking the first item in the left panel TOC
            # and check if URL changes (some pages do update the URL)
            node_id = self._try_get_nodeid_from_toc_click()
            if node_id:
                result_url = f"{codes_page_url}?nodeId={node_id}"
                print(f"Got nodeId from TOC click: {node_id}")
                return result_url

            # Method 2: Open the Download panel and get nodeId from there
            node_id = self._try_get_nodeid_from_download_panel()
            if node_id:
                result_url = f"{codes_page_url}?nodeId={node_id}"
                print(f"Got nodeId from download panel: {node_id}")
                return result_url

            # Method 3: Try extracting from Angular scope or page data
            node_id = self._try_get_nodeid_from_page_data()
            if node_id:
                result_url = f"{codes_page_url}?nodeId={node_id}"
                print(f"Got nodeId from page data: {node_id}")
                return result_url

            print("Could not extract nodeId, returning URL without nodeId")
            return codes_page_url

        except Exception as e:
            print(f"Error getting nodeId: {e}")
            import traceback
            traceback.print_exc()
            return codes_page_url

    def _try_get_nodeid_from_toc_click(self) -> Optional[str]:
        """Try to get nodeId by clicking the first TOC item."""
        try:
            # Find and click the first item in the left panel TOC
            # Look for the first expandable/clickable item
            selectors = [
                # Button with the code title
                "button.toc-item-btn",
                ".toc-item button",
                # Anchor links in TOC
                ".toc-nav a",
                "nav.toc a",
                # Generic TOC structure
                "[class*='toc'] a:first-of-type",
                "[class*='toc'] button:first-of-type",
            ]

            for selector in selectors:
                try:
                    element = self.selenium_util.driver.find_element(By.CSS_SELECTOR, selector)
                    if element and element.is_displayed():
                        self.selenium_util.driver.execute_script("arguments[0].click();", element)
                        time.sleep(2)
                        
                        # Check if URL now has nodeId
                        current_url = self.selenium_util.driver.current_url
                        if "nodeId=" in current_url:
                            match = current_url.split("nodeId=")[-1].split("&")[0]
                            return match
                        break
                except Exception:
                    continue

            return None
        except Exception:
            return None

    def _try_get_nodeid_from_download_panel(self) -> Optional[str]:
        """Try to get nodeId by opening the download panel."""
        try:
            # Dismiss any popups first
            popup_selectors = [".hopscotch-bubble-close", ".hopscotch-cta button"]
            for selector in popup_selectors:
                try:
                    btns = self.selenium_util.driver.find_elements(By.CSS_SELECTOR, selector)
                    for btn in btns:
                        if btn.is_displayed():
                            btn.click()
                            time.sleep(0.5)
                except Exception:
                    pass

            # Find and click the Download (Docx) button to open the panel
            download_selectors = [
                "//button[.//span[contains(text(), 'Download')]]",
                "//button[contains(., 'Download')]",
            ]

            panel_opened = False
            for selector in download_selectors:
                try:
                    btn = self.selenium_util.driver.find_element(By.XPATH, selector)
                    if btn and btn.is_displayed():
                        self.selenium_util.driver.execute_script("arguments[0].click();", btn)
                        time.sleep(2)
                        panel_opened = True
                        break
                except Exception:
                    continue

            if not panel_opened:
                return None

            # Wait for offcanvas panel
            try:
                self.selenium_util.find_element(By.CSS_SELECTOR, ".offcanvas-pane.active", timeout=5)
            except Exception:
                return None

            time.sleep(1)

            # Get the first nodeId from the panel
            node_id = self.selenium_util.driver.execute_script("""
                var items = document.querySelectorAll('.offcanvas-pane li[data-nodeid]');
                if (items.length > 0) {
                    return items[0].getAttribute('data-nodeid');
                }
                return null;
            """)

            # Close the panel
            try:
                close_btn = self.selenium_util.driver.find_element(
                    By.CSS_SELECTOR, ".offcanvas-pane button[data-close]"
                )
                close_btn.click()
            except Exception:
                pass

            return node_id

        except Exception as e:
            print(f"Download panel method error: {e}")
            return None

    def _try_get_nodeid_from_page_data(self) -> Optional[str]:
        """Try to get nodeId from Angular scope or embedded page data."""
        try:
            node_id = self.selenium_util.driver.execute_script("""
                // Helper function to validate nodeId - it should be a string code, not a number
                function isValidNodeId(id) {
                    if (!id) return false;
                    // Valid nodeIds are alphanumeric codes like COORALAL, CD_ORD_ALICEVILLE_ALABAMA
                    // Invalid ones are pure numbers like 10161, 14225 (these are product IDs)
                    if (/^\\d+$/.test(id)) return false;  // Reject pure numbers
                    if (id.length < 3) return false;
                    if (id === 'undefined') return false;
                    return true;
                }
                
                // Try Angular scope - look for toc with Children
                try {
                    var scope = angular.element(document.body).scope();
                    if (scope) {
                        // Navigate through possible scope properties
                        var toc = scope.toc || scope.codesToc || scope.$root.toc;
                        if (toc && toc.Children && toc.Children.length > 0) {
                            var childId = toc.Children[0].Id;
                            if (isValidNodeId(childId)) {
                                return childId;
                            }
                        }
                    }
                } catch(e) {}
                
                // Try window variables
                try {
                    if (window.tocData && window.tocData.Children && window.tocData.Children.length > 0) {
                        var childId = window.tocData.Children[0].Id;
                        if (isValidNodeId(childId)) {
                            return childId;
                        }
                    }
                } catch(e) {}
                
                // Look for data-nodeid anywhere on page - but validate it
                var items = document.querySelectorAll('[data-nodeid]');
                for (var i = 0; i < items.length; i++) {
                    var id = items[i].getAttribute('data-nodeid');
                    if (isValidNodeId(id)) {
                        return id;
                    }
                }
                
                return null;
            """)
            return node_id
        except Exception:
            return None

