from utils.selenium import SeleniumUtil
from selenium.webdriver.common.by import By
import time
import random
from pathlib import Path


class MunicodeScraper:
    FILE_NAME_SEPARATOR = "⫸"
    REINIT_AFTER_N_DOWNLOADS = (
        5  # Reinitialize driver every N downloads to avoid detection
    )

    def __init__(self, url: str, download_dir: str):
        if not url.startswith("https://library.municode.com"):
            raise ValueError(
                "Invalid URL. Must start with https://library.municode.com"
            )
        self.url = url
        self.download_dir = download_dir
        self.selenium_util = SeleniumUtil(headless=True, download_dir=download_dir)
        self.download_count = 0

    def _download_total_excel(self):
        # This will be used to get the title (e.g. article, title) and subtitle (e.g. section, sub-section)
        # in our database, we have column document_title and document_subtitle
        pass

    def _refresh_session(self):
        """
        Refresh the browser session with new headers to avoid detection.
        Useful for long-running scraping sessions.
        """
        print(f"\n{'='*60}")
        print("Refreshing session with new headers to avoid detection...")
        print(f"{'='*60}")

        # Reinitialize with new user agent
        self.selenium_util.reinitialize_with_new_headers()

        # Navigate back to the page
        print(f"Navigating back to {self.url}")
        self.selenium_util.driver.get(self.url)

        # Dismiss any popups
        self._dismiss_popups()
        time.sleep(2)

        print("Session refreshed successfully")
        print(f"{'='*60}\n")

    def _dismiss_popups(self):
        """
        Dismiss any tour/help popups that might interfere with clicking.
        Looks for common popup close buttons and dismisses them.
        """
        popup_selectors = [
            ".hopscotch-bubble-close",  # Hopscotch tour close button
            ".hopscotch-cta button",  # Hopscotch CTA button
        ]

        for selector in popup_selectors:
            try:
                close_buttons = self.selenium_util.driver.find_elements(
                    By.CSS_SELECTOR, selector
                )
                for btn in close_buttons:
                    if btn.is_displayed():
                        btn.click()
                        time.sleep(0.5)
            except:
                # If popup doesn't exist or can't be closed, that's fine
                pass

    def _close_download_panel(self):
        """Close the download selection panel if it's open."""
        try:
            # Look for close button in offcanvas
            close_button = self.selenium_util.driver.find_element(
                By.XPATH,
                "//div[contains(@class, 'offcanvas-pane')]//button[@data-close]",
            )
            if close_button.is_displayed():
                print("Closing offcanvas panel")
                close_button.click()
                time.sleep(1)
        except:
            # Panel not open or already closed
            pass

    def _open_download_panel(self):
        """Open the download selection panel."""
        # Dismiss any popups that might block the button
        self._dismiss_popups()

        # Close panel first if it's already open
        self._close_download_panel()

        print("Looking for Download (Docx) button to open selection panel")

        # Try multiple selectors in case the page structure changed
        download_button = None
        selectors = [
            "//button[.//span[contains(text(), 'Download (Docx)')]]",
            "//button[contains(., 'Download') and contains(., 'Docx')]",
            "//button[.//span[contains(text(), 'Download')]]",
        ]

        for selector in selectors:
            try:
                print(f"Trying selector: {selector}")
                download_button = self.selenium_util.find_element(
                    By.XPATH, selector, timeout=30
                )
                if download_button:
                    print(f"Found button with selector: {selector}")
                    break
            except Exception as e:
                print(f"Selector failed: {e}")
                continue

        if not download_button:
            # Take screenshot for debugging
            try:
                screenshot_path = f"{self.download_dir}/debug_no_download_button.png"
                self.selenium_util.driver.save_screenshot(screenshot_path)
                print(f"Screenshot saved to: {screenshot_path}")
            except:
                pass
            raise Exception("Could not find Download button with any selector")

        # Use JavaScript click to avoid interception issues
        print("Clicking Download button to open selection panel")
        self.selenium_util.driver.execute_script(
            "arguments[0].click();", download_button
        )

        # Wait for offcanvas panel to appear
        print("Waiting for offcanvas panel to appear")
        self.selenium_util.find_element(
            By.CSS_SELECTOR, ".offcanvas-pane.active", timeout=10
        )
        time.sleep(2)

    def _expand_one_level(self):
        """
        Expand only the first level of sections (one click on each top-level expander).
        This reveals immediate children only.
        """
        print("Expanding one level...")

        # Find all top-level expander buttons (direct children of root ul only)
        try:
            offcanvas = self.selenium_util.find_element(
                By.CSS_SELECTOR, ".offcanvas-pane.active"
            )
            root_ul = offcanvas.find_element(By.CSS_SELECTOR, "ul.gen-toc-nav")

            # Get direct child li elements
            root_li_elements = root_ul.find_elements(By.XPATH, "./li[@data-nodeid]")

            expanders_to_click = []
            for li in root_li_elements:
                # Find expander button that is a direct child of this li (not nested deeper)
                try:
                    expander = li.find_element(
                        By.XPATH, "./button[contains(@class, 'expToc-expander')]"
                    )
                    expanders_to_click.append(expander)
                except:
                    # This li doesn't have an expander (it's a leaf)
                    pass

            print(f"Found {len(expanders_to_click)} top-level sections to expand")

            for expander in expanders_to_click:
                try:
                    expander.click()
                    time.sleep(0.1)
                except Exception as e:
                    print(f"Could not click expander: {e}")

            time.sleep(1)
            print("Finished expanding one level")
        except Exception as e:
            print(f"Error expanding one level: {e}")

    def _expand_specific_parent(self, parent_node_id):
        """
        Expand only a specific parent node by its node_id.

        Args:
            parent_node_id: The data-nodeid of the parent to expand
        """
        if parent_node_id is None:
            # This is a root node without children, no expansion needed
            return

        print(f"Expanding parent node: {parent_node_id}")
        try:
            # Find the parent li element
            parent_li = self.selenium_util.find_element(
                By.CSS_SELECTOR, f"li[data-nodeid='{parent_node_id}']", timeout=5
            )

            # Find the expander button for this parent
            try:
                expander = parent_li.find_element(
                    By.XPATH, "./button[contains(@class, 'expToc-expander')]"
                )
                expander.click()
                time.sleep(0.3)
                print(f"Expanded parent node: {parent_node_id}")
            except:
                # No expander found (shouldn't happen if parent_node_id is not None, but handle gracefully)
                print(f"Warning: No expander found for parent node {parent_node_id}")
        except Exception as e:
            print(f"Error expanding parent node {parent_node_id}: {e}")

    def _collect_sections_max_1_level(self):
        """
        Collect ALL sections at 1 level deep (all immediate children of root nodes).
        This includes both true leaves and nodes that could be expanded further.

        Returns:
            List of tuples: [(path, parent_node_id, node_id), ...]
            - For children: parent_node_id is the parent's ID, node_id is the child's ID
            - For root nodes without children: parent_node_id is None, node_id is the root's ID
            Note: We only store node_ids, not elements (to avoid stale references)
        """
        print("Collecting all sections at level 1...")
        sections = []

        try:
            # Find the root UL in the offcanvas
            offcanvas = self.selenium_util.find_element(
                By.CSS_SELECTOR, ".offcanvas-pane.active"
            )
            root_ul = offcanvas.find_element(By.CSS_SELECTOR, "ul.gen-toc-nav")

            # Get all direct child li elements
            root_nodes = root_ul.find_elements(By.XPATH, "./li[@data-nodeid]")
            print(f"Found {len(root_nodes)} top-level nodes")

            for li in root_nodes:
                try:
                    # Get the heading
                    checkbox = li.find_element(
                        By.CSS_SELECTOR, "button.expToc-selector[role='checkbox']"
                    )
                    heading_elem = checkbox.find_element(
                        By.CSS_SELECTOR, "span[data-ng-bind]"
                    )
                    parent_heading = heading_elem.text.strip()
                    parent_node_id = li.get_attribute("data-nodeid")

                    # Check if this node has children (look for child ul)
                    try:
                        child_ul = li.find_element(
                            By.XPATH, f".//ul[@id='child-nodes-{parent_node_id}']"
                        )
                        child_nodes = child_ul.find_elements(
                            By.XPATH, "./li[@data-nodeid]"
                        )

                        # Collect ALL children at level 1 (regardless of whether they have sub-children)
                        for child_li in child_nodes:
                            try:
                                child_checkbox = child_li.find_element(
                                    By.CSS_SELECTOR,
                                    "button.expToc-selector[role='checkbox']",
                                )
                                child_heading_elem = child_checkbox.find_element(
                                    By.CSS_SELECTOR, "span[data-ng-bind]"
                                )
                                child_heading = child_heading_elem.text.strip()
                                child_node_id = child_li.get_attribute("data-nodeid")

                                # Add ALL children, storing parent_node_id and child_node_id
                                path = [parent_heading, child_heading]
                                sections.append((path, parent_node_id, child_node_id))
                                print(f"  Found: {' > '.join(path)}")

                            except Exception as e:
                                print(f"Error processing child node: {e}")

                    except:
                        # No children, this parent is a section itself
                        path = [parent_heading]
                        sections.append((path, None, parent_node_id))
                        print(f"  Found: {parent_heading}")

                except Exception as e:
                    print(f"Error processing node: {e}")

        except Exception as e:
            print(f"Error collecting sections: {e}")
            import traceback

            traceback.print_exc()

        print(f"Collected {len(sections)} sections at level 1")
        return sections

    def _retry_failed_downloads(self, failed_sections, downloaded_files):
        """
        Retry downloading failed sections.

        Args:
            failed_sections: List of tuples [(path, parent_node_id, node_id, filename), ...]
            downloaded_files: List to append successfully downloaded files

        Returns:
            List of sections that still failed after retry
        """
        if not failed_sections:
            return []

        separator = self.FILE_NAME_SEPARATOR
        print(f"\n{'='*60}")
        print(f"Retrying {len(failed_sections)} failed downloads...")
        print(f"{'='*60}")

        still_failed = []

        for idx, (path, parent_node_id, node_id, filename) in enumerate(
            failed_sections, 1
        ):
            path_str = separator.join(path)
            print(f"\n[Retry {idx}/{len(failed_sections)}] Downloading: {path_str}")

            try:
                # Reopen panel and expand ONLY the specific parent
                self._open_download_panel()
                self._expand_specific_parent(parent_node_id)
                time.sleep(0.5)

                downloaded_file = self._download_single_section(node_id, filename)
                print(f"✓ Retry successful: {filename}")
                downloaded_files.append(downloaded_file)

            except Exception as e:
                print(f"✗ Retry failed for {path_str}: {e}")
                still_failed.append((path, parent_node_id, node_id, filename))

        return still_failed

    def scrape_hierarchical(self):
        """
        Download each leaf section at 1 level deep with hierarchical metadata.

        Returns:
            List of downloaded file paths
        """
        separator = self.FILE_NAME_SEPARATOR
        try:
            print(f"Navigating to {self.url}")
            self.selenium_util.driver.get(self.url)

            # Dismiss any popups
            self._dismiss_popups()
            time.sleep(1)

            # Open the download panel
            self._open_download_panel()

            # Expand only one level
            self._expand_one_level()

            # Collect leaf sections at level 1
            all_sections = self._collect_sections_max_1_level()

            # Close panel after collection to reset state
            self._close_download_panel()

            downloaded_files = []
            failed_sections = []

            # Download each section individually
            for idx, (path, parent_node_id, node_id) in enumerate(all_sections, 1):
                # Refresh session periodically to avoid detection
                if (
                    self.download_count > 0
                    and self.download_count % self.REINIT_AFTER_N_DOWNLOADS == 0
                ):
                    print(
                        f"\n[After {self.download_count} downloads] Refreshing session..."
                    )
                    self._refresh_session()

                # Create hierarchical filename
                path_str = separator.join(path)
                safe_filename = path_str.replace("/", "-").replace("\\", "-") + ".docx"

                print(f"\n[{idx}/{len(all_sections)}] Downloading: {path_str}")

                # Open panel and expand ONLY the specific parent for this download
                self._open_download_panel()
                self._expand_specific_parent(parent_node_id)
                time.sleep(0.5)

                # Download this section
                try:
                    downloaded_file = self._download_single_section(
                        node_id, safe_filename
                    )
                    print(f"Saved as: {safe_filename}")
                    downloaded_files.append(downloaded_file)
                    self.download_count += 1  # Increment successful download count

                    # Add random delay to appear more human-like
                    if idx < len(all_sections):
                        delay = random.uniform(1.0, 3.0)
                        print(f"Waiting {delay:.1f}s before next download...")
                        time.sleep(delay)

                    # Panel closes after download; next iteration will reopen and expand the next parent

                except TimeoutError as e:
                    print(f"Download timeout for: {path_str}")
                    failed_sections.append(
                        (path, parent_node_id, node_id, safe_filename)
                    )
                    # Panel closes; next iteration will handle reopening

                except Exception as e:
                    print(f"Error downloading {path_str}: {e}")
                    failed_sections.append(
                        (path, parent_node_id, node_id, safe_filename)
                    )
                    # Panel closes; next iteration will handle reopening

            # Retry failed downloads
            if failed_sections:
                still_failed = self._retry_failed_downloads(
                    failed_sections, downloaded_files
                )

                if still_failed:
                    print(f"\n{'='*60}")
                    print(
                        f"Warning: {len(still_failed)} sections still failed after retry:"
                    )
                    for path, _, _, _ in still_failed:
                        print(f"  - {separator.join(path)}")
                    print(f"{'='*60}")

            print(
                f"\nCompleted! Downloaded {len(downloaded_files)}/{len(all_sections)} sections"
            )
            if failed_sections:
                print(f"Initial failures: {len(failed_sections)}")
                if still_failed:
                    print(f"Still failed after retry: {len(still_failed)}")
                else:
                    print(f"All failures recovered on retry!")

            return downloaded_files

        except Exception as e:
            print(f"Error in hierarchical scraping: {e}")
            raise e
        finally:
            self.selenium_util.quit()

    def _wait_for_download_complete(
        self, expected_extension=".docx", timeout=60, pre_existing_files=None
    ):
        """
        Wait for download to complete by checking for NEW downloaded file.

        Args:
            expected_extension: The file extension to look for (e.g., '.pdf', '.zip')
            timeout: Maximum time to wait in seconds
            pre_existing_files: Set of files that existed before download started

        Returns:
            Path: Path to the downloaded file
        """
        download_dir = Path(self.download_dir)
        end_time = time.time() + timeout

        if pre_existing_files is None:
            pre_existing_files = set()

        print(f"Waiting for {expected_extension} download in: {download_dir}")
        print(f"Pre-existing files: {len(pre_existing_files)}")

        check_count = 0
        while time.time() < end_time:
            check_count += 1

            # Check for files with expected extension
            all_files = set(download_dir.glob(f"*{expected_extension}"))

            # Find NEW files (not in pre-existing)
            new_files = all_files - pre_existing_files

            # Check for incomplete downloads
            incomplete_files = (
                list(download_dir.glob("*.crdownload"))
                + list(download_dir.glob("*.tmp"))
                + list(download_dir.glob("*.part"))
            )

            # Filter out incomplete downloads (.crdownload, .tmp, .part)
            complete_new_files = [
                f
                for f in new_files
                if not any(
                    str(f).endswith(ext) for ext in [".crdownload", ".tmp", ".part"]
                )
            ]

            # Log status every 10 checks (every 5 seconds)
            if check_count % 10 == 0:
                elapsed = int(timeout - (end_time - time.time()))
                print(
                    f"[{elapsed}s] Checking... All files: {len(all_files)}, New: {len(new_files)}, Complete new: {len(complete_new_files)}, Incomplete: {len(incomplete_files)}"
                )

            if complete_new_files:
                # Get the most recently modified NEW file
                latest_file = max(complete_new_files, key=lambda f: f.stat().st_mtime)
                initial_size = latest_file.stat().st_size
                time.sleep(1)

                # If size hasn't changed, download is complete
                if latest_file.stat().st_size == initial_size and initial_size > 0:
                    print(
                        f"Download complete: {latest_file.name} ({initial_size} bytes)"
                    )
                    return latest_file

            time.sleep(0.5)

        # Timeout - provide diagnostic info
        all_files = set(download_dir.glob(f"*{expected_extension}"))
        new_files = all_files - pre_existing_files
        print(f"TIMEOUT DIAGNOSTICS:")
        print(f"  Total {expected_extension} files: {len(all_files)}")
        print(f"  New files detected: {len(new_files)}")
        print(f"  Incomplete downloads: {len(list(download_dir.glob('*.crdownload')))}")
        raise TimeoutError(f"Download did not complete within {timeout} seconds")

    def _download_single_section(self, node_id, filename):
        """
        Download a single section by finding it fresh from node_id.

        Args:
            node_id: The data-nodeid attribute to find the section
            filename: The filename to save as

        Returns:
            Path: Path to the downloaded file
        """
        # Capture existing files BEFORE download
        download_dir = Path(self.download_dir)
        pre_existing_files = (
            set(download_dir.glob("*.docx")) if download_dir.exists() else set()
        )
        print(f"Starting download for node_id: {node_id}")

        # Find the checkbox fresh by node_id to avoid stale element
        try:
            li_element = self.selenium_util.find_element(
                By.CSS_SELECTOR, f"li[data-nodeid='{node_id}']", timeout=10
            )
            print(f"Found element with node_id: {node_id}")
        except Exception as e:
            print(f"ERROR: Could not find element with node_id '{node_id}': {e}")
            raise

        checkbox = li_element.find_element(
            By.CSS_SELECTOR, "button.expToc-selector[role='checkbox']"
        )
        checkbox_text = checkbox.find_element(
            By.CSS_SELECTOR, "span[data-ng-bind]"
        ).text
        print(f"Found checkbox for: {checkbox_text}")

        # Select only this section
        is_checked = checkbox.get_attribute("aria-checked")
        print(f"Checkbox state: {is_checked}")
        if is_checked == "false":
            print("Clicking checkbox to select section")
            checkbox.click()
            time.sleep(0.5)  # Wait for UI to update

            # Verify checkbox was actually checked
            is_checked_after = checkbox.get_attribute("aria-checked")
            print(f"Checkbox state after click: {is_checked_after}")
            if is_checked_after != "true":
                print("WARNING: Checkbox not checked after click, trying again...")
                checkbox.click()
                time.sleep(0.5)
        else:
            print("Checkbox already selected")

        # Wait a bit for the download button to be enabled
        time.sleep(0.5)

        # Check how many sections are selected
        try:
            selected_checkboxes = self.selenium_util.driver.find_elements(
                By.XPATH, "//button[@role='checkbox' and @aria-checked='true']"
            )
            print(f"Total sections selected: {len(selected_checkboxes)}")
        except:
            print("Could not count selected checkboxes")

        # Click download button
        print("Clicking Download button...")
        try:
            download_button = self.selenium_util.find_element(
                By.XPATH,
                "//button[contains(., 'Download') and contains(@class, 'btn-primary')]",
                timeout=10,
            )

            # Check if button is disabled
            is_disabled = download_button.get_attribute("disabled")
            button_text = download_button.text
            print(f"Download button text: '{button_text}'")
            print(f"Download button disabled state: {is_disabled}")

            if is_disabled:
                print("ERROR: Download button is disabled!")
                # Take screenshot for debugging
                try:
                    screenshot_path = f"{self.download_dir}/debug_disabled_button.png"
                    self.selenium_util.driver.save_screenshot(screenshot_path)
                    print(f"Screenshot saved to: {screenshot_path}")
                except:
                    pass
                raise Exception("Download button is disabled")

            # Use JavaScript click to ensure it triggers
            print("Using JavaScript click on Download button...")
            self.selenium_util.driver.execute_script(
                "arguments[0].click();", download_button
            )
            print("Download button clicked successfully")
            time.sleep(1)  # Wait for download to start

        except Exception as e:
            print(f"ERROR: Failed to click Download button: {e}")
            # Take screenshot for debugging
            try:
                screenshot_path = f"{self.download_dir}/debug_download_error.png"
                self.selenium_util.driver.save_screenshot(screenshot_path)
                print(f"Screenshot saved to: {screenshot_path}")
            except:
                pass
            raise

        # Wait for NEW download (excluding pre-existing files)
        downloaded_file = self._wait_for_download_complete(
            expected_extension=".docx",
            timeout=60,
            pre_existing_files=pre_existing_files,
        )

        # Rename with provided filename
        new_path = Path(self.download_dir) / filename
        if downloaded_file != new_path:
            downloaded_file.rename(new_path)

        return new_path

    def scrape(self):
        """
        Default scrape method - downloads sections hierarchically.

        Args:
            separator: String to use for separating hierarchical levels in filenames

        Returns:
            List of downloaded file paths
        """
        return self.scrape_hierarchical()
