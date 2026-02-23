"""DOCX to Markdown converter for Municode ordinances"""

import os
import tempfile
from pathlib import Path
from typing import Optional
from markitdown import MarkItDown
from google.cloud import storage


class DocxToMarkdownConverter:
    """Converts DOCX files from GCS to Markdown and saves back to GCS"""

    def __init__(self, state: str, gcp_project: str, bucket_name: str):
        """
        Initialize the converter.

        Args:
            state: State abbreviation (e.g., "ri", "ma", "ca")
            gcp_project: GCP project ID
            bucket_name: GCS bucket name
        """
        self.state = state
        self.gcp_project = gcp_project
        self.bucket_name = bucket_name

        # Initialize GCS client
        self.client = storage.Client(project=gcp_project)
        self.bucket = self.client.bucket(bucket_name)

        # Initialize MarkItDown converter
        self.converter = MarkItDown()

        # Statistics
        self.stats = {
            "total_files": 0,
            "converted": 0,
            "skipped": 0,
            "errors": 0,
        }

    def convert_state(self):
        """Convert all DOCX files for the state to Markdown"""
        print(f"Starting conversion for state: {self.state}")

        # List all DOCX files for this state
        prefix = f"zoning_ordinance/{self.state}/"
        blobs = self.bucket.list_blobs(prefix=prefix)

        docx_blobs = [blob for blob in blobs if blob.name.endswith('.docx')]
        self.stats["total_files"] = len(docx_blobs)

        print(f"Found {len(docx_blobs)} DOCX files to convert")

        # Convert each DOCX file
        for blob in docx_blobs:
            try:
                self._convert_file(blob)
                self.stats["converted"] += 1
            except Exception as e:
                print(f"Error converting {blob.name}: {str(e)}")
                self.stats["errors"] += 1

        self._print_stats()

    def _convert_file(self, blob: storage.Blob):
        """
        Convert a single DOCX file to Markdown.

        Args:
            blob: GCS blob object for the DOCX file
        """
        print(f"Converting: {blob.name}")

        # Check if markdown already exists
        md_path = self._get_markdown_path(blob.name)
        md_blob = self.bucket.blob(md_path)
        if md_blob.exists():
            print(f"  Skipping (already exists): {md_path}")
            self.stats["skipped"] += 1
            return

        # Download DOCX to temp file
        with tempfile.NamedTemporaryFile(suffix='.docx', delete=False) as tmp_file:
            tmp_path = tmp_file.name

        try:
            blob.download_to_filename(tmp_path)

            # Convert to Markdown
            result = self.converter.convert(tmp_path)
            markdown_content = result.text_content

            # Upload to GCS
            md_blob.upload_from_string(
                markdown_content,
                content_type='text/markdown'
            )

            print(f"  ✓ Converted to: {md_path}")

        finally:
            # Clean up temp file
            if os.path.exists(tmp_path):
                os.unlink(tmp_path)

    def _get_markdown_path(self, docx_path: str) -> str:
        """
        Convert DOCX path to Markdown path.

        Example:
            zoning_ordinance/ri/city/file.docx
            -> zoning_ordinance_markdown/ri/city/file.md
        """
        md_path = docx_path.replace(
            'zoning_ordinance/',
            'zoning_ordinance_markdown/'
        ).replace('.docx', '.md')
        return md_path

    def _print_stats(self):
        """Print conversion statistics"""
        print("\n" + "=" * 60)
        print("CONVERSION STATISTICS")
        print("=" * 60)
        print(f"State: {self.state}")
        print(f"Total files: {self.stats['total_files']}")
        print(f"Converted: {self.stats['converted']}")
        print(f"Skipped (already exists): {self.stats['skipped']}")
        print(f"Errors: {self.stats['errors']}")
        print("=" * 60)
