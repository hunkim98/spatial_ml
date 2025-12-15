from typing import List, Optional
from google.cloud import storage
from google.oauth2 import service_account
import os
from pathlib import Path


class GCPStorage:
    def __init__(
        self, gcp_project: str, bucket_name: str, credentials_path: Optional[str] = None
    ):
        """
        Initialize GCP Storage client.

        Args:
            gcp_project (str): GCP project ID.
            bucket_name (str): Name of the GCS bucket.
            credentials_path (Optional[str]): Path to service account JSON key file.
                If not provided, uses default credentials (environment variable or gcloud auth).
        """
        if credentials_path:
            credentials = service_account.Credentials.from_service_account_file(
                credentials_path
            )
            self.client = storage.Client(project=gcp_project, credentials=credentials)
        else:
            self.client = storage.Client(project=gcp_project)
        self.bucket = self.client.bucket(bucket_name)

    def list_files(self, prefix: str = "", recursive: bool = False) -> List[str]:
        """
        List files in the GCS bucket.

        Args:
            prefix (str, optional): Prefix path to filter files. Defaults to "".
                If empty string, returns all files in the bucket.
            recursive (bool, optional): If True, lists files recursively under prefix.
                If False, lists only files directly in the prefix directory. Defaults to True.

        Returns:
            List[str]: List of file paths (blob names).
        """
        if recursive:
            # List all files recursively under prefix
            blobs = self.bucket.list_blobs(prefix=prefix)
            # Filter out directory placeholders (blobs ending with /)
            return [blob.name for blob in blobs if not blob.name.endswith('/')]
        else:
            # List only files directly in this directory (not subdirectories)
            blobs = self.bucket.list_blobs(prefix=prefix, delimiter='/')
            return [blob.name for blob in blobs if not blob.name.endswith('/')]

    def list_dirs(self, prefix: str = "") -> List[str]:
        """
        List all directories in the GCS bucket.
        Returns list of directory prefixes (e.g., "parent/child/").
        """
        # Use delimiter to get common prefixes (directories)
        iterator = self.bucket.list_blobs(prefix=prefix, delimiter='/')

        # We need to iterate through the blobs to populate the prefixes
        # The prefixes attribute is only populated after iteration
        list(iterator)  # Force iteration to populate prefixes

        # Get the prefixes (directories)
        directories = []
        if hasattr(iterator, 'prefixes'):
            for prefix_obj in iterator.prefixes:
                directories.append(prefix_obj)

        return directories
    

    def upload_file(self, file_path: str, destination_path: str):
        blob = self.bucket.blob(destination_path)
        blob.upload_from_filename(file_path)

    def upload_json(self, data: dict, destination_path: str):
        """
        Upload a dictionary as JSON to GCS.

        Args:
            data (dict): The dictionary to upload as JSON.
            destination_path (str): Path in the GCS bucket where the JSON will be stored.
        """
        import json
        blob = self.bucket.blob(destination_path)
        blob.upload_from_string(
            json.dumps(data, indent=2),
            content_type='application/json'
        )

    def upload_dir(self, source_path: str, destination_path: str):
        """
        Uploads all files from a local directory to a GCS "directory" (prefix),
        preserving the subdirectory structure.

        Args:
            source_path (str): Local directory path to upload from.
            destination_path (str): Prefix (directory) in the GCS bucket.
        """
        source_path = Path(source_path)

        # Walk through all files in the source directory
        for local_file in source_path.rglob("*"):
            if local_file.is_file():
                # Get the relative path from source to maintain directory structure
                rel_path = local_file.relative_to(source_path)
                # Create the GCS blob path
                gcs_path = f"{destination_path}/{rel_path}".replace("\\", "/")
                blob = self.bucket.blob(gcs_path)
                blob.upload_from_filename(str(local_file))

    def download_file(self, source_path: str, destination_path: str):
        blob = self.bucket.blob(source_path)
        blob.download_to_filename(destination_path)

    def download_dir(self, source_path: str, destination_path: str):
        """
        Downloads all files from a GCS "directory" (prefix) to a local directory,
        preserving the subdirectory structure.

        Args:
            source_path (str): Prefix (directory) in the GCS bucket.
            destination_path (Path or str): Local path to save files. Should be a directory.
        """

        # Ensure destination_path is a Path
        destination_path = Path(destination_path)

        blobs = self.bucket.list_blobs(prefix=source_path)
        for blob in blobs:
            # Skip "directory placeholder" blobs (GCS may return a blob with a trailing /)
            if blob.name.endswith("/"):
                continue
            # Remove the source_path prefix to get the relative path
            rel_path = os.path.relpath(blob.name, source_path)
            local_file = destination_path / rel_path
            local_file.parent.mkdir(parents=True, exist_ok=True)
            blob.download_to_filename(str(local_file))

    def get_blob(self, blob_path: str):
        """
        Get a blob object from GCS.

        Args:
            blob_path (str): Path to the blob in the GCS bucket.

        Returns:
            google.cloud.storage.Blob: The blob object.
        """
        return self.bucket.blob(blob_path)

    def get_public_url(self, blob_path: str) -> str:
        """
        Get the public URL for a blob in GCS.

        Args:
            blob_path (str): Path to the blob in the GCS bucket.

        Returns:
            str: Public URL to access the blob (gs:// format or https:// format).
        """
        # Return the public HTTPS URL
        return f"https://storage.googleapis.com/{self.bucket.name}/{blob_path}"
