from utils.playwright import PlaywrightUtil
from .base import ZoningCodesBaseCollector
import os
import time
import re
import pandas as pd
from concurrent.futures import ThreadPoolExecutor, as_completed
from threading import Lock


class ZoneomicsCollector(ZoningCodesBaseCollector):
    BASE_URL = "https://www.zoneomics.com"

    # US states with their URL slugs (the website doesn't list states dynamically)
    US_STATES = [
        ("Alabama", "alabama"),
        ("Alaska", "alaska"),
        ("Arizona", "arizona"),
        ("Arkansas", "arkansas"),
        ("California", "california"),
        ("Colorado", "colorado"),
        ("Connecticut", "connecticut"),
        ("Delaware", "delaware"),
        ("Florida", "florida"),
        ("Georgia", "georgia"),
        ("Hawaii", "hawaii"),
        ("Idaho", "idaho"),
        ("Illinois", "illinois"),
        ("Indiana", "indiana"),
        ("Iowa", "iowa"),
        ("Kansas", "kansas"),
        ("Kentucky", "kentucky"),
        ("Louisiana", "louisiana"),
        ("Maine", "maine"),
        ("Maryland", "maryland"),
        ("Massachusetts", "massachusetts"),
        ("Michigan", "michigan"),
        ("Minnesota", "minnesota"),
        ("Mississippi", "mississippi"),
        ("Missouri", "missouri"),
        ("Montana", "montana"),
        ("Nebraska", "nebraska"),
        ("Nevada", "nevada"),
        ("New Hampshire", "new-hampshire"),
        ("New Jersey", "new-jersey"),
        ("New Mexico", "new-mexico"),
        ("New York", "new-york"),
        ("North Carolina", "north-carolina"),
        ("North Dakota", "north-dakota"),
        ("Ohio", "ohio"),
        ("Oklahoma", "oklahoma"),
        ("Oregon", "oregon"),
        ("Pennsylvania", "pennsylvania"),
        ("Rhode Island", "rhode-island"),
        ("South Carolina", "south-carolina"),
        ("South Dakota", "south-dakota"),
        ("Tennessee", "tennessee"),
        ("Texas", "texas"),
        ("Utah", "utah"),
        ("Vermont", "vermont"),
        ("Virginia", "virginia"),
        ("Washington", "washington"),
        ("West Virginia", "west-virginia"),
        ("Wisconsin", "wisconsin"),
        ("Wyoming", "wyoming"),
    ]

    def __init__(self, max_workers: int = 4):
        super().__init__()
        # Use Playwright for better Next.js compatibility
        self.browser_util = PlaywrightUtil(headless=True, logger=self.logger)
        self.max_workers = max_workers
        self._save_lock = Lock()  # Thread-safe file saving

    def resource_url(self) -> str:
        """Return the resource URL for this collector."""
        return f"{self.BASE_URL}/all-cities/usa"

    def download_directory(self) -> str:
        """Return the download directory path for this collector."""
        return os.path.abspath("tmp/zoning_codes/zoneomics")

    def find_states(self) -> list[dict]:
        """
        Return all US state URLs.

        The Zoneomics website doesn't display state links directly on the page
        (it uses a search interface), so we use a predefined list of US states.

        Returns:
            list[dict]: List of dicts with 'name', 'slug', and 'url' keys for each state.
        """
        states = []
        for name, slug in self.US_STATES:
            states.append(
                {
                    "name": name,
                    "slug": slug,
                    "url": f"{self.BASE_URL}/all-cities/usa/{slug}",
                }
            )

        self.logger.info(f"Using {len(states)} predefined US states")
        return states

    def get_state_by_slug(self, state_slug: str) -> dict | None:
        """
        Get a specific state by its URL slug.

        Args:
            state_slug: The state's URL slug (e.g., "california", "new-york")

        Returns:
            dict with 'name', 'slug', and 'url' keys, or None if not found.
        """
        for name, slug in self.US_STATES:
            if slug == state_slug:
                return {
                    "name": name,
                    "slug": slug,
                    "url": f"{self.BASE_URL}/all-cities/usa/{slug}",
                }
        return None

    def find_cities(self, state_url: str) -> list[dict]:
        """
        Navigate to a state page and extract all city links for that state.

        Args:
            state_url: The full URL to the state's city listing page.

        Returns:
            list[dict]: List of dicts with 'name', 'slug', and 'url' keys for each city.
        """
        self.logger.info(f"Navigating to state page: {state_url}")
        self.browser_util.goto(state_url, wait_until="networkidle")

        # Extract state slug from URL to filter cities
        state_url_match = re.search(r"/all-cities/usa/([^/]+)/?$", state_url)
        target_state_slug = state_url_match.group(1) if state_url_match else None

        if not target_state_slug:
            self.logger.warning(f"Could not extract state slug from URL: {state_url}")
            return []

        # Find all city links - pattern: /zoning-maps/{state}/{city}
        city_links = self.browser_util.query_selector_all("a[href*='/zoning-maps/']")

        cities = []
        seen_urls = set()

        for link in city_links:
            href = link.get_attribute("href")
            text = link.text_content().strip() if link.text_content() else ""

            # Filter to valid city links
            # Pattern: /zoning-maps/{state}/{city}
            if href and "/zoning-maps/" in href and "undefined" not in href:
                path_match = re.search(r"/zoning-maps/([^/]+)/([^/]+)/?$", href)
                if path_match and href not in seen_urls:
                    state_slug = path_match.group(1)
                    city_slug = path_match.group(2)

                    # Only include cities from the target state
                    if state_slug != target_state_slug:
                        continue

                    city_name = text if text else city_slug.replace("-", " ").title()

                    # Ensure URL is absolute
                    full_url = (
                        href if href.startswith("http") else f"{self.BASE_URL}{href}"
                    )

                    cities.append(
                        {
                            "name": city_name,
                            "slug": city_slug,
                            "state_slug": state_slug,
                            "url": full_url,
                        }
                    )
                    seen_urls.add(href)
                    self.logger.debug(f"Found city: {city_name} -> {full_url}")

        self.logger.info(f"Found {len(cities)} cities in {target_state_slug}")
        return cities

    def _load_and_find_table(self, city_url: str):
        """
        Load page and attempt to find the zoning table.

        Returns:
            table element or None
        """
        self.browser_util.goto(city_url, wait_until="networkidle")

        # Check if page loaded successfully (not an error page)
        page_title = self.browser_util.title
        if "Application error" in page_title or "error" in page_title.lower():
            self.logger.warning(f"Page error detected: {page_title}")
            return None

        # Wait a bit for dynamic content
        time.sleep(2)

        # Scroll to trigger lazy loading
        self.browser_util.page.evaluate(
            "window.scrollTo(0, document.body.scrollHeight / 2)"
        )
        time.sleep(1)

        # Try to click expand button
        try:
            expand_button = self.browser_util.page.query_selector(
                "button[class*='address-explanation__content--expand']"
            )
            if expand_button:
                button_text = expand_button.text_content().strip().lower()
                if "expand" in button_text:
                    expand_button.scroll_into_view_if_needed()
                    expand_button.click()
                    self.logger.debug("Clicked 'Expand Table' button")
                    time.sleep(2)
        except Exception:
            pass

        # Find the zoning codes table specifically
        # The page has multiple tables - we need the one with zone codes (has <strong> tags)
        tables = self.browser_util.query_selector_all(
            "tbody[class*='RowTable_table-body-container']"
        )

        for table in tables:
            # Verify it's the zoning codes table by checking for <strong> tag (zone code)
            first_strong = table.query_selector("tr td strong")
            if first_strong:
                self.logger.debug(
                    f"Found zoning codes table with {len(table.query_selector_all('tr'))} rows"
                )
                return table

        return None

    def process_city_zoning(self, city_url: str, max_retries: int = 3) -> dict:
        """
        Navigate to a city's zoning map page and extract zone code data.

        Args:
            city_url: The full URL to the city's zoning map page.
            max_retries: Number of retry attempts if table not found.

        Returns:
            dict: Contains 'city_url' and 'zones' list with zone data.
        """
        self.logger.info(f"Processing city zoning: {city_url}")
        zones = []

        # Retry loop
        table = None
        for attempt in range(max_retries):
            table = self._load_and_find_table(city_url)
            if table:
                self.logger.debug(f"Found table on attempt {attempt + 1}")
                break
            else:
                self.logger.warning(
                    f"Attempt {attempt + 1}/{max_retries}: No table found, retrying..."
                )
                if attempt < max_retries - 1:
                    time.sleep(2 * (attempt + 1))
                    # Reinitialize browser with fresh session
                    self.browser_util.reinitialize()

        if not table:
            tables = self.browser_util.query_selector_all("table")
            page_title = self.browser_util.title
            page_content_len = len(self.browser_util.content)
            self.logger.warning(
                f"No zoning table found for {city_url} after {max_retries} attempts. "
                f"Found {len(tables)} tables on page. "
                f"Page title: '{page_title}', Content length: {page_content_len}"
            )
            return {"city_url": city_url, "zones": zones}

        # Parse table rows
        try:
            rows = table.query_selector_all("tr")

            for row in rows:
                try:
                    cells = row.query_selector_all("td")
                    if len(cells) >= 3:
                        zone_cell = cells[0]
                        zone_code = ""
                        zone_subtype = ""

                        # Try to get zone code from <strong> tag
                        strong = zone_cell.query_selector("strong")
                        if strong:
                            zone_code = strong.text_content().strip()

                        # Get zone subtype from the inner div that's NOT the strong tag
                        # Structure: <td><div class="h-full"><strong>B-1</strong><div>Neighborhood Commercial</div></div></td>
                        inner_divs = zone_cell.query_selector_all("div.h-full > div")
                        for div in inner_divs:
                            text = (
                                div.text_content().strip() if div.text_content() else ""
                            )
                            if text and text != zone_code:
                                zone_subtype = text
                                break

                        # Fallback: if no subtype found, try direct div children
                        if not zone_subtype:
                            divs = zone_cell.query_selector_all("div")
                            for div in divs:
                                # Skip the parent div, get text from child divs only
                                if div.query_selector("strong"):
                                    continue
                                text = (
                                    div.text_content().strip()
                                    if div.text_content()
                                    else ""
                                )
                                # Make sure it doesn't contain the zone code
                                if (
                                    text
                                    and zone_code
                                    and not text.startswith(zone_code)
                                ):
                                    zone_subtype = text
                                    break

                        area_acres = (
                            cells[1].text_content().strip()
                            if cells[1].text_content()
                            else ""
                        )
                        description = (
                            cells[2].text_content().strip()
                            if cells[2].text_content()
                            else ""
                        )

                        if zone_code:
                            zones.append(
                                {
                                    "zone_code": zone_code,
                                    "zone_subtype": zone_subtype,
                                    "area_acres": area_acres,
                                    "description": description,
                                }
                            )

                except Exception as e:
                    self.logger.debug(f"Error parsing row: {e}")

        except Exception as e:
            self.logger.error(f"Error processing city zoning: {e}")

        self.logger.info(f"Found {len(zones)} zones for {city_url}")
        return {"city_url": city_url, "zones": zones}

    def _process_city_worker(self, city: dict) -> dict:
        """
        Process a single city with its own browser instance.
        Used for concurrent processing.

        Args:
            city: Dict with city info including 'url', 'name', 'slug', 'state_slug', 'state_name'

        Returns:
            dict: Result with 'success', 'city_name', and optionally 'error'
        """
        browser_util = None
        try:
            # Create a new browser instance for this worker
            browser_util = PlaywrightUtil(headless=True, logger=self.logger)

            city_url = city["url"]
            city_name = city["name"]
            city_slug = city.get("slug", "")
            state_slug = city.get("state_slug", "")
            state_name = city.get("state_name", "")

            self.logger.info(f"[Worker] Processing: {city_name}, {state_name}")

            # Process the city using this worker's browser
            zoning_data = self._process_city_zoning_with_browser(browser_util, city_url)
            zoning_data["city_name"] = city_name
            zoning_data["city_slug"] = city_slug
            zoning_data["state_name"] = state_name
            zoning_data["state_slug"] = state_slug

            # Thread-safe save
            with self._save_lock:
                self.save_city_zoning(zoning_data)

            return {"success": True, "city_name": city_name}

        except Exception as e:
            self.logger.error(
                f"[Worker] Error processing {city.get('name', 'unknown')}: {e}"
            )
            return {
                "success": False,
                "city_name": city.get("name", "unknown"),
                "error": str(e),
            }
        finally:
            if browser_util:
                browser_util.quit()

    def _process_city_zoning_with_browser(
        self, browser_util: PlaywrightUtil, city_url: str, max_retries: int = 3
    ) -> dict:
        """
        Process city zoning using a specific browser instance.
        Similar to process_city_zoning but accepts browser as parameter.

        Args:
            browser_util: The PlaywrightUtil instance to use
            city_url: The full URL to the city's zoning map page.
            max_retries: Number of retry attempts if table not found.

        Returns:
            dict: Contains 'city_url' and 'zones' list with zone data.
        """
        zones = []

        # Retry loop
        table = None
        for attempt in range(max_retries):
            table = self._load_and_find_table_with_browser(browser_util, city_url)
            if table:
                break
            else:
                self.logger.warning(
                    f"Attempt {attempt + 1}/{max_retries}: No table found, retrying..."
                )
                if attempt < max_retries - 1:
                    time.sleep(2 * (attempt + 1))
                    browser_util.reinitialize()

        if not table:
            return {"city_url": city_url, "zones": zones}

        # Parse table rows (same logic as process_city_zoning)
        try:
            rows = table.query_selector_all("tr")

            for row in rows:
                try:
                    cells = row.query_selector_all("td")
                    if len(cells) >= 3:
                        zone_cell = cells[0]
                        zone_code = ""
                        zone_subtype = ""

                        strong = zone_cell.query_selector("strong")
                        if strong:
                            zone_code = strong.text_content().strip()

                        inner_divs = zone_cell.query_selector_all("div.h-full > div")
                        for div in inner_divs:
                            text = (
                                div.text_content().strip() if div.text_content() else ""
                            )
                            if text and text != zone_code:
                                zone_subtype = text
                                break

                        if not zone_subtype:
                            divs = zone_cell.query_selector_all("div")
                            for div in divs:
                                if div.query_selector("strong"):
                                    continue
                                text = (
                                    div.text_content().strip()
                                    if div.text_content()
                                    else ""
                                )
                                if (
                                    text
                                    and zone_code
                                    and not text.startswith(zone_code)
                                ):
                                    zone_subtype = text
                                    break

                        area_acres = (
                            cells[1].text_content().strip()
                            if cells[1].text_content()
                            else ""
                        )
                        description = (
                            cells[2].text_content().strip()
                            if cells[2].text_content()
                            else ""
                        )

                        if zone_code:
                            zones.append(
                                {
                                    "zone_code": zone_code,
                                    "zone_subtype": zone_subtype,
                                    "area_acres": area_acres,
                                    "description": description,
                                }
                            )

                except Exception as e:
                    self.logger.debug(f"Error parsing row: {e}")

        except Exception as e:
            self.logger.error(f"Error processing city zoning: {e}")

        return {"city_url": city_url, "zones": zones}

    def _load_and_find_table_with_browser(
        self, browser_util: PlaywrightUtil, city_url: str
    ):
        """
        Load page and find zoning table using specific browser instance.

        Args:
            browser_util: The PlaywrightUtil instance to use
            city_url: URL to load

        Returns:
            table element or None
        """
        browser_util.goto(city_url, wait_until="networkidle")

        page_title = browser_util.title
        if "Application error" in page_title or "error" in page_title.lower():
            self.logger.warning(f"Page error detected: {page_title}")
            return None

        time.sleep(2)

        browser_util.page.evaluate("window.scrollTo(0, document.body.scrollHeight / 2)")
        time.sleep(1)

        try:
            expand_button = browser_util.page.query_selector(
                "button[class*='address-explanation__content--expand']"
            )
            if expand_button:
                button_text = expand_button.text_content().strip().lower()
                if "expand" in button_text:
                    expand_button.scroll_into_view_if_needed()
                    expand_button.click()
                    time.sleep(2)
        except Exception:
            pass

        tables = browser_util.query_selector_all(
            "tbody[class*='RowTable_table-body-container']"
        )

        for table in tables:
            first_strong = table.query_selector("tr td strong")
            if first_strong:
                return table

        return None

    def save_city_zoning(self, zoning_data: dict) -> str:
        """
        Save a city's zoning data to a CSV file using pandas.

        Files are organized as: {download_directory}/{state_slug}/{city_slug}.csv

        Args:
            zoning_data: Dict containing city info and zones list.

        Returns:
            str: Path to the saved CSV file.
        """
        state_slug = zoning_data.get("state_slug", "unknown")
        city_slug = zoning_data.get("city_slug", "unknown")

        # Create state directory
        state_dir = os.path.join(self.download_directory(), state_slug)
        os.makedirs(state_dir, exist_ok=True)

        # CSV file path
        csv_path = os.path.join(state_dir, f"{city_slug}.csv")

        zones = zoning_data.get("zones", [])

        if not zones:
            self.logger.warning(f"No zones to save for {city_slug}, {state_slug}")
            # Save empty DataFrame with headers
            df = pd.DataFrame(
                columns=["zone_code", "zone_subtype", "area_acres", "description"]
            )
        else:
            df = pd.DataFrame(zones)

        df.to_csv(csv_path, index=False)
        self.logger.info(f"Saved {len(zones)} zones to {csv_path}")
        return csv_path

    def is_city_processed(self, state_slug: str, city_slug: str) -> bool:
        """
        Check if a city has already been processed (CSV file exists).

        Args:
            state_slug: The state's URL slug.
            city_slug: The city's URL slug.

        Returns:
            bool: True if the city's CSV file already exists.
        """
        csv_path = os.path.join(
            self.download_directory(), state_slug, f"{city_slug}.csv"
        )
        return os.path.exists(csv_path)

    def gcp_storage_parent_directory(self) -> str:
        """Return the GCS parent directory for this collector."""
        return "zoning_codes/zoneomics"

    def upload_to_gcs(self):
        """
        Upload all collected CSV files to GCS.

        Uploads the entire download directory to GCS, preserving folder structure.
        """
        if not self.gcp_storage:
            self.logger.warning("GCS not available. Skipping upload.")
            return

        download_dir = self.download_directory()
        gcs_parent_dir = self.gcp_storage_parent_directory()

        uploaded_count = 0
        skipped_count = 0

        for root, _dirs, files in os.walk(download_dir):
            for filename in files:
                if not filename.endswith(".csv"):
                    continue

                local_path = os.path.join(root, filename)
                rel_path = os.path.relpath(local_path, start=download_dir)
                rel_path = rel_path.replace(os.sep, "/")
                gcs_blob_path = f"{gcs_parent_dir}/{rel_path}"

                try:
                    self.gcp_storage.upload_file(local_path, gcs_blob_path)
                    self.logger.info(f"Uploaded {gcs_blob_path}")
                    uploaded_count += 1
                except Exception as e:
                    self.logger.error(f"Error uploading {gcs_blob_path}: {e}")
                    skipped_count += 1
                    continue

        self.logger.info(
            f"GCS upload complete. Uploaded: {uploaded_count}, Failed: {skipped_count}"
        )

    def upload_to_db(self):
        """
        Upload all collected zoning codes from CSV files to the database.

        Reads all CSV files from the download directory and inserts into zoning_codes table.
        """
        self._create_zoning_codes_table()

        download_dir = self.download_directory()
        uploaded_count = 0
        error_count = 0

        for root, _dirs, files in os.walk(download_dir):
            for filename in files:
                if not filename.endswith(".csv"):
                    continue

                csv_path = os.path.join(root, filename)

                # Extract state and city from path
                rel_path = os.path.relpath(csv_path, start=download_dir)
                parts = rel_path.replace(os.sep, "/").split("/")
                if len(parts) < 2:
                    continue

                state_slug = parts[0]
                city_slug = filename.replace(".csv", "")

                # Convert slugs to display names
                state_name = state_slug.replace("-", " ").title()
                city_name = city_slug.replace("-", " ").title()

                try:
                    # Get or create city in database
                    city_id = self._get_or_create_city_id(city_name, state_name)

                    # Read CSV and insert zones
                    df = pd.read_csv(csv_path)

                    for _, row in df.iterrows():
                        zone_code = row.get("zone_code", "")
                        # Handle NaN values from pandas
                        if pd.isna(zone_code) or not zone_code:
                            continue

                        # Convert potential NaN values to None for optional fields
                        zone_subtype = row.get("zone_subtype")
                        zone_subtype = None if pd.isna(zone_subtype) else zone_subtype

                        area_acres = row.get("area_acres")
                        area_acres = None if pd.isna(area_acres) else area_acres

                        description = row.get("description")
                        description = None if pd.isna(description) else description

                        self._insert_zoning_code(
                            city_id=city_id,
                            zone_code=zone_code,
                            zone_subtype=zone_subtype,
                            area_acres=area_acres,
                            description=description,
                        )

                    uploaded_count += 1
                    self.logger.info(f"Uploaded {city_name}, {state_name} to database")

                except Exception as e:
                    self.logger.error(f"Error uploading {city_name}, {state_name}: {e}")
                    error_count += 1
                    continue

        self.logger.info(
            f"Database upload complete. Cities uploaded: {uploaded_count}, Errors: {error_count}"
        )

    def collect(
        self,
        test_mode: bool = False,
        state_slug: str = None,
        use_concurrent: bool = True,
    ):
        """
        Main collection method to gather all zoning code data.

        Saves each city to CSV immediately after processing.
        Skips cities that have already been processed (resume capability).

        Args:
            test_mode: If True, only process the first state (Alabama) to test the scraper.
            state_slug: If provided, only process this specific state (e.g., "california").
                       Use this for parallel processing across multiple Vertex AI jobs.
            use_concurrent: If True, process cities concurrently within each state.
                           Set to False for sequential processing.
        """
        try:
            self.logger.info("Starting Zoneomics zoning codes collection")
            if test_mode:
                self.logger.info("TEST MODE: Only processing first state")
            if state_slug:
                self.logger.info(f"SINGLE STATE MODE: Only processing {state_slug}")
            if use_concurrent:
                self.logger.info(f"CONCURRENT MODE: Using {self.max_workers} workers")

            # Step 1: Get states to process
            if state_slug:
                state = self.get_state_by_slug(state_slug)
                if not state:
                    raise ValueError(
                        f"Unknown state slug: {state_slug}. Valid slugs: {[s[1] for s in self.US_STATES]}"
                    )
                states = [state]
            else:
                states = self.find_states()
                if test_mode:
                    states = states[:1]  # Only first state in test mode

            # Step 2: Process each state and its cities
            processed_count = 0
            skipped_count = 0
            error_count = 0
            total_cities = 0

            for state_idx, state in enumerate(states):
                self.logger.info(
                    f"Processing state {state_idx + 1}/{len(states)}: {state['name']}"
                )

                try:
                    cities = self.find_cities(state["url"])
                    for city in cities:
                        city["state_name"] = state["name"]

                    if test_mode:
                        cities = cities[:3]  # Only first 3 cities in test mode
                        self.logger.info(f"TEST MODE: Only processing first 3 cities")

                    self.logger.info(f"Found {len(cities)} cities in {state['name']}")

                    # Filter out already processed cities
                    cities_to_process = []
                    for city in cities:
                        total_cities += 1
                        state_slug_city = city.get("state_slug", "")
                        city_slug = city.get("slug", "")

                        if self.is_city_processed(state_slug_city, city_slug):
                            self.logger.debug(
                                f"Skipping already processed: {city['name']}, {state['name']}"
                            )
                            skipped_count += 1
                        else:
                            cities_to_process.append(city)

                    self.logger.info(
                        f"Cities to process: {len(cities_to_process)} (skipped {skipped_count} already processed)"
                    )

                    if use_concurrent and len(cities_to_process) > 1:
                        # Concurrent processing
                        processed, errors = self._process_cities_concurrent(
                            cities_to_process
                        )
                        processed_count += processed
                        error_count += errors
                    else:
                        # Sequential processing (original method)
                        for city_idx, city in enumerate(cities_to_process):
                            self.logger.info(
                                f"Processing city {city_idx + 1}/{len(cities_to_process)} in {state['name']}: {city['name']}"
                            )

                            try:
                                zoning_data = self.process_city_zoning(city["url"])
                                zoning_data["city_name"] = city["name"]
                                zoning_data["city_slug"] = city.get("slug", "")
                                zoning_data["state_name"] = city.get("state_name", "")
                                zoning_data["state_slug"] = city.get("state_slug", "")

                                self.save_city_zoning(zoning_data)
                                processed_count += 1

                                time.sleep(1)
                            except Exception as e:
                                self.logger.error(
                                    f"Error processing city {city['name']}: {e}"
                                )
                                error_count += 1
                                continue

                    # Be polite between states
                    time.sleep(1)

                except Exception as e:
                    self.logger.error(f"Error processing state {state['name']}: {e}")
                    continue

            self.logger.info(
                f"Collection complete. Processed: {processed_count}, Skipped: {skipped_count}, "
                f"Errors: {error_count}, Total cities: {total_cities}"
            )

            # Step 3: Upload all CSV files to GCS
            self.upload_to_gcs()

            # Step 4: Upload to database
            self.upload_to_db()

            return {
                "processed": processed_count,
                "skipped": skipped_count,
                "errors": error_count,
            }

        except Exception as e:
            self.logger.error(f"Collection failed: {e}")
            raise
        finally:
            self.browser_util.quit()

    def _process_cities_concurrent(self, cities: list[dict]) -> tuple[int, int]:
        """
        Process multiple cities concurrently using ThreadPoolExecutor.

        Args:
            cities: List of city dicts to process

        Returns:
            Tuple of (processed_count, error_count)
        """
        processed_count = 0
        error_count = 0

        self.logger.info(
            f"Starting concurrent processing of {len(cities)} cities with {self.max_workers} workers"
        )

        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            # Submit all cities for processing
            future_to_city = {
                executor.submit(self._process_city_worker, city): city
                for city in cities
            }

            # Process results as they complete
            for future in as_completed(future_to_city):
                city = future_to_city[future]
                try:
                    result = future.result()
                    if result["success"]:
                        processed_count += 1
                        self.logger.info(f"✓ Completed: {result['city_name']}")
                    else:
                        error_count += 1
                        self.logger.error(
                            f"✗ Failed: {result['city_name']} - {result.get('error', 'Unknown error')}"
                        )
                except Exception as e:
                    error_count += 1
                    self.logger.error(
                        f"✗ Exception for {city.get('name', 'unknown')}: {e}"
                    )

        self.logger.info(
            f"Concurrent processing complete. Processed: {processed_count}, Errors: {error_count}"
        )
        return processed_count, error_count
