from utils.gcp_storage import GCPStorage
from template import BaseCollector
from abc import ABC, abstractmethod
import logging
import os
import sys


class ZoningOrdinanceBaseCollector(BaseCollector, ABC):
    def __init__(self):
        super().__init__()
        self.logger = logging.getLogger(f"{self.__class__.__name__}")
        if not self.logger.hasHandlers():
            # Use stdout instead of stderr for Vertex AI logging
            handler = logging.StreamHandler(sys.stdout)
            formatter = logging.Formatter("%(asctime)s %(levelname)s: %(message)s")
            handler.setFormatter(formatter)
            self.logger.addHandler(handler)
            self.logger.setLevel(logging.INFO)

        self.gcp_storage = None
        self.bucket_name = os.environ.get("GCS_BUCKET_NAME")
        self.gcp_project = os.environ.get("GCP_PROJECT")

        if self.bucket_name and self.gcp_project:
            try:
                self.gcp_storage = GCPStorage(
                    gcp_project=self.gcp_project, bucket_name=self.bucket_name
                )
                self.logger.info("GCS connection established")
            except Exception as e:
                self.logger.warning(
                    f"Could not connect to GCS: {e}. Will operate without GCS features."
                )
        else:
            self.logger.warning(
                "GCS credentials not found (GCS_BUCKET_NAME or GCP_PROJECT). Will operate without GCS features."
            )

    def gcp_storage_parent_directory(self) -> str:
        """Return the GCS storage path for this collector."""
        return f"zoning_ordinance/{self.city()}"

    def download_directory(self) -> str:
        """Return the download directory path for this collector."""
        return os.path.abspath(f"tmp/zoning_ordinance/{self.city()}")

    @abstractmethod
    def resource_url(self) -> str:
        """Return the resource URL for this collector."""
        pass

    @abstractmethod
    def upload_metadata(self):
        """Upload the data to the database."""
        pass

    @abstractmethod
    def upload_to_gcs(self):
        """Upload the data to GCS."""
        pass
