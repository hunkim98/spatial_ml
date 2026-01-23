"""Chicago Zoning Code Data Collector.

This module contains the ChicagoZoningCollector class for downloading
the Municipal Code of Chicago from the amlegal.com code library.
"""

import os
import time
import logging
from pathlib import Path
from typing import Optional

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

from .base import ZoningOrdinanceBaseCollector

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class ChicagoZoningCollector(ZoningOrdinanceBaseCollector):
    """Collector for Chicago Municipal Code data from amlegal.com."""

    def __init__(self, headless: bool = True, download_dir: Optional[str] = None):
        """Initialize the Chicago zoning code collector.

        Args:
            headless: Whether to run Chrome in headless mode
            download_dir: Directory to save downloaded files. Defaults to
                         collector/zoning_ordinance/chicago_collected_data/
        """
        super().__init__(headless=headless, download_dir=download_dir)
        self.base_url = "https://codelibrary.amlegal.com/codes/chiscago/latest/overview"

    def _get_default_download_dir(self) -> Path:
        """Get the default download directory for Chicago collector."""
        return Path(__file__).parent.parent.parent / "downloads" / "zoning_ordinance" / "chicago"

    def _wait_for_download_complete(self, timeout: int = 600) -> bool:
        """Wait for download to complete by checking for .crdownload files.

        Also checks default Downloads folder as fallback since Chrome sometimes
        ignores download path in headless mode.

        Args:
            timeout: Maximum seconds to wait for download (default 600s / 10 minutes)

        Returns:
            True if download completed, False if timeout
        """
        start_time = time.time()
        last_count = 0

        # Also check default Downloads folder as fallback
        default_downloads = Path.home() / "Downloads"

        while time.time() - start_time < timeout:
            elapsed = int(time.time() - start_time)

            # Check for .crdownload files in both locations
            crdownload_files = list(self.download_dir.glob("*.crdownload")) + list(
                default_downloads.glob("chicago*.crdownload")
            )

            # Check for downloaded files in target directory
            downloaded_files = [
                f
                for f in self.download_dir.iterdir()
                if f.is_file()
                and not f.name.startswith(".")
                and not f.name.endswith(".crdownload")
            ]

            # Also check for Chicago files in default Downloads folder
            chicago_files_in_downloads = [
                f
                for f in default_downloads.glob("chicago*.pdf")
                if f.stat().st_mtime > start_time  # Only files created after we started
            ]

            current_count = len(downloaded_files) + len(chicago_files_in_downloads)

            # Log progress every 5 seconds or when count changes
            if elapsed % 5 == 0 or current_count != last_count:
                logger.info(
                    f"Waiting for download... ({elapsed}s elapsed, {len(crdownload_files)} in progress, {current_count} completed)"
                )
                last_count = current_count

            # If we found a file in default Downloads, move it to our directory
            if chicago_files_in_downloads and not crdownload_files:
                for file in chicago_files_in_downloads:
                    dest = self.download_dir / file.name
                    logger.info(
                        f"Moving {file.name} from Downloads to {self.download_dir}"
                    )
                    file.rename(dest)
                    logger.info(f"Download complete: {dest.name}")
                return True

            # If we have completed files in our directory and no temp files, download is done
            if downloaded_files and not crdownload_files:
                logger.info(f"Download complete: {downloaded_files[-1].name}")
                return True

            time.sleep(1)

        logger.error(f"Download did not complete within {timeout} seconds")
        return False

    def collect(self) -> dict:
        """Download the Municipal Code of Chicago.

        Returns:
            Dictionary with collection results:
            {
                'success': bool,
                'files_downloaded': list of file paths,
                'errors': list of error messages
            }
        """
        results = {"success": False, "files_downloaded": [], "errors": []}

        try:
            self._setup_driver()
            logger.info("Starting Chicago zoning code collection")
            logger.info(f"Target URL: {self.base_url}")
            logger.info(f"Download directory: {self.download_dir}")

            # Navigate to the page
            logger.info("Loading page...")
            self.driver.get(self.base_url)
            logger.info("Waiting for page to load...")
            time.sleep(5)  # Let page load completely

            # Click the download button
            logger.info("Searching for download button...")

            # Try to find the download button - try multiple selectors
            download_button = None
            selectors = [
                'button[aria-label="Download"]',
                'button[aria-label="download"]',
                'button:has-text("Download")',
                "button.download-button",
                '//button[contains(text(), "Download")]',
            ]

            for selector in selectors:
                try:
                    logger.info(f"Trying selector: {selector}")
                    # Use shorter wait for each attempt
                    wait = WebDriverWait(self.driver, 5)
                    if selector.startswith("//"):
                        download_button = wait.until(
                            EC.element_to_be_clickable((By.XPATH, selector))
                        )
                    else:
                        download_button = wait.until(
                            EC.element_to_be_clickable((By.CSS_SELECTOR, selector))
                        )
                    logger.info(f"Found download button with selector: {selector}")
                    break
                except Exception as e:
                    logger.info(f"Selector {selector} not found, trying next...")
                    continue

            if not download_button:
                raise Exception(
                    "Could not find download button with any known selector"
                )

            logger.info("Clicking download button...")
            download_button.click()
            time.sleep(2)

            # Wait for modal to appear
            logger.info("Waiting for download modal...")
            wait = WebDriverWait(self.driver, 10)
            modal = wait.until(
                EC.presence_of_element_located((By.CSS_SELECTOR, ".modal-content"))
            )
            logger.info("Modal opened")

            # Find and click the "Municipal Code of Chicago" checkbox
            logger.info("Searching for 'Municipal Code of Chicago' checkbox...")

            # Wait for checkboxes to be present
            time.sleep(1)
            checkboxes = self.driver.find_elements(
                By.CSS_SELECTOR, '.modal-content input[type="checkbox"]'
            )

            target_checkbox = None
            for checkbox in checkboxes:
                # Find the parent label to get the text
                parent = checkbox.find_element(By.XPATH, "..")
                label_text = parent.text.strip()

                if "Municipal Code of Chicago" in label_text:
                    target_checkbox = checkbox
                    logger.info(f"Found checkbox: {label_text}")
                    break

            if not target_checkbox:
                raise Exception("Could not find 'Municipal Code of Chicago' checkbox")

            # Click the checkbox if not already selected
            if not target_checkbox.is_selected():
                logger.info("Selecting checkbox...")
                # Click the parent label for better reliability
                parent = target_checkbox.find_element(By.XPATH, "..")
                parent.click()
                time.sleep(0.5)
            else:
                logger.info("Checkbox already selected")

            # Wait for and click the Download button in the modal
            logger.info("Waiting for Download button to be enabled...")

            # Find all buttons in the modal footer and select the one with "Download" text
            time.sleep(2)

            modal_download_button = None
            try:
                # Get all buttons in modal footer
                modal_buttons = self.driver.find_elements(
                    By.CSS_SELECTOR, ".modal-footer button"
                )
                logger.info(f"Found {len(modal_buttons)} buttons in modal footer")

                for button in modal_buttons:
                    button_text = button.text.strip()
                    logger.info(f"Button text: '{button_text}'")
                    if "download" in button_text.lower():
                        modal_download_button = button
                        logger.info(f"Selected download button: '{button_text}'")
                        break
            except Exception as e:
                logger.warning(f"Could not enumerate buttons: {e}")

            # Fallback to XPath if we didn't find it
            if not modal_download_button:
                logger.info("Trying XPath to find Download button...")
                try:
                    modal_download_button = wait.until(
                        EC.element_to_be_clickable(
                            (
                                By.XPATH,
                                '//div[@class="modal-footer"]//button[contains(translate(text(), "DOWNLOAD", "download"), "download")]',
                            )
                        )
                    )
                    logger.info("Found Download button via XPath")
                except Exception as e:
                    logger.error(f"XPath search failed: {e}")
                    raise Exception("Could not find Download button in modal")

            if not modal_download_button:
                raise Exception("Could not find Download button in modal")

            logger.info("Clicking Download button...")

            # Try both regular click and JavaScript click
            try:
                modal_download_button.click()
            except Exception as e:
                logger.warning(f"Regular click failed: {e}, trying JavaScript click")
                self.driver.execute_script(
                    "arguments[0].click();", modal_download_button
                )

            # Give the download time to start
            time.sleep(3)

            # Wait for format selection modal
            logger.info("Waiting for format selection modal...")
            time.sleep(2)

            # Find and click "Save PDF" button
            logger.info("Looking for 'Save PDF' button...")
            format_buttons = self.driver.find_elements(
                By.CSS_SELECTOR, "button.export-button"
            )
            logger.info(f"Found {len(format_buttons)} format buttons")

            pdf_button = None
            for button in format_buttons:
                button_text = button.text.strip()
                logger.info(f"Format button text: '{button_text}'")
                if "PDF" in button_text:
                    pdf_button = button
                    logger.info(f"Selected PDF button: '{button_text}'")
                    break

            if not pdf_button:
                raise Exception("Could not find 'Save PDF' button")

            logger.info("Clicking 'Save PDF' button...")
            try:
                pdf_button.click()
            except Exception as e:
                logger.warning(f"Regular click failed: {e}, trying JavaScript click")
                self.driver.execute_script("arguments[0].click();", pdf_button)

            # Wait for file preparation to complete
            # A bottom bar appears showing "Preparing 1 item..." which can take several minutes
            logger.info("Waiting for server to prepare file...")
            logger.info("This may take 10-30 minutes for large files...")

            # Wait for the download link to appear (indicated by data-request-uuid)
            wait = WebDriverWait(self.driver, 1800)  # 30 minute timeout for preparation

            try:
                # Wait for the element with data-request-uuid attribute to be present
                download_link_element = wait.until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, "a[data-request-uuid]"))
                )
                logger.info("File preparation complete - download link is available")
            except Exception as e:
                logger.error(f"File preparation did not complete: {e}")
                raise Exception("Download link did not appear after file preparation")

            # Extract the download URL from the href attribute
            download_url = download_link_element.get_attribute("href")
            if not download_url:
                raise Exception("Could not extract download URL from link element")

            logger.info(f"Found download URL: {download_url}")

            # Navigate directly to the download URL
            logger.info("Navigating to download URL...")
            self.driver.get(download_url)

            # Give download time to start
            time.sleep(10)

            # Wait for download to complete
            logger.info("Waiting for download to complete...")
            if self._wait_for_download_complete():
                # Get the downloaded files
                downloaded_files = [
                    f
                    for f in self.download_dir.iterdir()
                    if f.is_file()
                    and not f.name.startswith(".")
                ]

                if downloaded_files:
                    results["success"] = True
                    results["files_downloaded"] = [str(f) for f in downloaded_files]
                    logger.info(
                        f"Successfully downloaded {len(downloaded_files)} file(s)"
                    )
                else:
                    results["errors"].append("No files found in download directory")
            else:
                results["errors"].append("Download did not complete in time")

        except Exception as e:
            error_msg = f"Error during collection: {str(e)}"
            logger.error(error_msg)
            results["errors"].append(error_msg)

        finally:
            self._cleanup_driver()

        return results

    def validate(self, data: dict) -> bool:
        """Validate the collected data.

        Args:
            data: The collection results to validate

        Returns:
            True if validation passes, False otherwise
        """
        if not data.get("success"):
            logger.error("Collection was not successful")
            return False

        if not data.get("files_downloaded"):
            logger.error("No files were downloaded")
            return False

        # Check that files exist
        for file_path in data["files_downloaded"]:
            if not Path(file_path).exists():
                logger.error(f"Downloaded file not found: {file_path}")
                return False

            # Check file size
            file_size = Path(file_path).stat().st_size
            if file_size < 1000:  # Less than 1KB is suspicious
                logger.error(
                    f"Downloaded file seems too small: {file_path} ({file_size} bytes)"
                )
                return False

        logger.info("Validation passed")
        return True
