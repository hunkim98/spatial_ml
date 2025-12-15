"""
Generic Municode Zoning Ordinance Collector

This collector can dynamically collect zoning ordinances from any municipality
available on library.municode.com.

Usage:
    collector = MunicodeZoningOrdinanceCollector.from_state_and_municipality('al', 'birmingham')
    collector.collect()
"""

from .base import ZoningOrdinanceBaseCollector
from utils.scrapers.municode_scraper import MunicodeScraper
from utils.scrapers.municode_discovery import MunicodeDiscovery
import time
import json
import os
from typing import Optional


class MunicodeZoningOrdinanceCollector(ZoningOrdinanceBaseCollector):
    """Generic collector for any Municode municipality."""

    def __init__(self, state_abbrev: str, municipality: str, resource_url: str):
        """
        Initialize the collector.

        Args:
            state_abbrev: Two-letter state abbreviation (e.g., 'ma', 'al')
            municipality: Municipality name/slug (e.g., 'boston', 'birmingham')
            resource_url: Full URL to the codes/ordinances page
        """
        self._state_abbrev = state_abbrev.lower()
        self._municipality = municipality.lower().replace(" ", "-")
        self._resource_url = resource_url

        super().__init__()

        # Ensure download directory exists
        os.makedirs(self.download_directory(), exist_ok=True)

        self.scraper = MunicodeScraper(
            url=self._resource_url,
            download_dir=self.download_directory()
        )

    @classmethod
    def from_state_and_municipality(
        cls,
        state_abbrev: str,
        municipality: str,
        headless: bool = True
    ) -> Optional["MunicodeZoningOrdinanceCollector"]:
        """
        Create a collector by automatically discovering the codes URL.

        Args:
            state_abbrev: Two-letter state abbreviation (e.g., 'al', 'ma')
            municipality: Municipality name/slug (e.g., 'birmingham', 'boston')
            headless: Whether to run browser in headless mode

        Returns:
            MunicodeZoningOrdinanceCollector instance, or None if codes URL not found
        """
        discovery = MunicodeDiscovery(headless=headless)
        municipality_slug = municipality.lower().replace(" ", "-")

        codes_url = discovery.get_municipality_codes_url(state_abbrev, municipality_slug)

        if not codes_url:
            print(f"Could not find codes URL for {municipality}, {state_abbrev.upper()}")
            return None

        return cls(
            state_abbrev=state_abbrev,
            municipality=municipality,
            resource_url=codes_url
        )

    def city(self) -> str:
        """Return city identifier (state_abbrev/municipality)."""
        return f"{self._state_abbrev}/{self._municipality}"

    def resource_url(self) -> str:
        """Return the resource URL."""
        return self._resource_url

    def upload_to_gcs(self, downloaded_files: list):
        """Upload all downloaded files to GCS."""
        if not self.gcp_storage:
            self.logger.warning("GCS not configured, skipping upload")
            return

        for file_path in downloaded_files:
            max_retries = 3
            for attempt in range(max_retries):
                try:
                    self.gcp_storage.upload_file(
                        file_path=str(file_path),
                        destination_path=f"{self.gcp_storage_parent_directory()}/{file_path.name}"
                    )
                    self.logger.info(f"Uploaded {file_path.name} to GCS")
                    break
                except OSError as e:
                    if e.errno == 35 and attempt < max_retries - 1:
                        self.logger.warning(
                            f"File lock on {file_path.name}, retrying in 2s... "
                            f"(attempt {attempt + 1}/{max_retries})"
                        )
                        time.sleep(2)
                    else:
                        self.logger.error(f"Failed to upload {file_path.name}: {e}")
                        break
                except Exception as e:
                    self.logger.error(f"Failed to upload {file_path.name}: {e}")
                    break

    def upload_metadata(self):
        """Upload metadata to GCS."""
        if not self.gcp_storage:
            self.logger.warning("GCS not configured, skipping metadata upload")
            return

        metadata = {
            "state_abbrev": self._state_abbrev,
            "municipality": self._municipality,
            "resource_url": self._resource_url,
        }

        metadata_path = f"{self.download_directory()}/metadata.json"
        with open(metadata_path, "w") as f:
            json.dump(metadata, f, indent=2)

        self.gcp_storage.upload_file(
            file_path=metadata_path,
            destination_path=f"{self.gcp_storage_parent_directory()}/metadata.json"
        )
        self.logger.info("Uploaded metadata to GCS")

    def collect(self):
        """Collect zoning ordinance documents."""
        self.logger.info(
            f"Collecting zoning ordinance for {self._municipality}, {self._state_abbrev.upper()}"
        )
        self.logger.info(f"Resource URL: {self._resource_url}")

        downloaded_files = self.scraper.scrape()
        self.logger.info(f"Downloaded {len(downloaded_files)} sections")

        # Wait for files to be fully flushed
        self.logger.info("Waiting for files to be fully released...")
        time.sleep(3)

        self.upload_to_gcs(downloaded_files)
        self.upload_metadata()

        return downloaded_files
