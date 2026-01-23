from .base import ZoningOrdinanceBaseCollector
from utils.scrapers.municode_scraper import MunicodeScraper
import time
import json


class BostonZoningOrdinanceCollector(ZoningOrdinanceBaseCollector):
    def __init__(self):
        super().__init__()
        self.scraper = MunicodeScraper(url=self.resource_url(), download_dir=self.download_directory())

    def city(self) -> str:
        return "boston"

    def resource_url(self) -> str:
        return "https://library.municode.com/ma/boston/codes/redevelopment_authority?nodeId=PRONZOCOBOMA"

    def upload_to_gcs(self, downloaded_files: list):
        """Upload all downloaded files to GCS."""
        if not self.gcp_storage:
            self.logger.warning("GCS not configured, skipping upload")
            return

        for file_path in downloaded_files:
            # Retry logic for handling file lock issues
            max_retries = 3
            for attempt in range(max_retries):
                try:
                    self.gcp_storage.upload_file(
                        file_path=str(file_path),
                        destination_path=f"{self.gcp_storage_parent_directory()}/{file_path.name}"
                    )
                    self.logger.info(f"Uploaded {file_path.name} to GCS")
                    break  # Success, exit retry loop
                except OSError as e:
                    if e.errno == 35 and attempt < max_retries - 1:
                        # Resource deadlock - wait and retry
                        self.logger.warning(f"File lock on {file_path.name}, retrying in 2s... (attempt {attempt + 1}/{max_retries})")
                        time.sleep(2)
                    else:
                        self.logger.error(f"Failed to upload {file_path.name}: {e}")
                        break
                except Exception as e:
                    self.logger.error(f"Failed to upload {file_path.name}: {e}")
                    break

    def upload_metadata(self):
        metadata = {
            "resource_url": self.resource_url(),
        }
        # save the metadata to a json file
        with open(f"{self.download_directory()}/metadata.json", "w") as f:
            json.dump(metadata, f)
        
        # create a json file in the gcs bucket
        self.gcp_storage.upload_file(
            file_path=f"{self.download_directory()}/metadata.json",
            destination_path=f"{self.gcp_storage_parent_directory()}/metadata.json"
        )
        
    def collect(self):
        self.logger.info(f"Collecting zoning ordinance for {self.city()}")
        downloaded_files = self.scraper.scrape()
        self.logger.info(f"Downloaded {len(downloaded_files)} sections")

        # Wait for files to be fully flushed and Chrome to release file handles
        self.logger.info("Waiting for files to be fully released...")
        time.sleep(3)

        self.upload_to_gcs(downloaded_files)
        self.upload_metadata()
        return downloaded_files