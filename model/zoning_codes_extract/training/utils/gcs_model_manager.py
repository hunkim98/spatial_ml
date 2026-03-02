"""
GCS Model Manager - Upload/download trained models to/from Google Cloud Storage.

This module handles uploading trained model artifacts (extractor and validator)
to GCS bucket 'spatially-models' and downloading them for inference or dashboard use.
"""

import os
import json
import time
from pathlib import Path
from typing import Optional, Dict, List, Tuple
from datetime import datetime
from dotenv import load_dotenv

# Import GCPStorage from collector
import sys
sys.path.append(str(Path(__file__).parent.parent.parent.parent.parent))
from collector.utils.gcp_storage import GCPStorage


class GCSModelManager:
    """
    Manages upload/download of trained models to/from GCS.

    GCS Structure:
        gs://spatially-models/
        ├── models/
        │   ├── extractor_20260223_003120/
        │   │   ├── config.json
        │   │   ├── model.safetensors
        │   │   ├── tokenizer.json
        │   │   ├── tokenizer_config.json
        │   │   ├── special_tokens_map.json
        │   │   ├── vocab.txt
        │   │   └── test_results.json
        │   └── validator_20260223_140818/
        │       └── ... (same structure)
        ├── cache/
        │   ├── cached_metrics.json
        │   ├── cached_extractor_examples.json
        │   ├── cached_validator_examples.json
        │   └── cached_city_comparison.json
        └── registry.json
    """

    def __init__(
        self,
        gcp_project: Optional[str] = None,
        bucket_name: Optional[str] = None,
        credentials_path: Optional[str] = None
    ):
        """
        Initialize GCS model manager.

        Args:
            gcp_project: GCP project ID (defaults to GCP_PROJECT env var)
            bucket_name: GCS bucket name (defaults to GCS_MODEL_BUCKET env var)
            credentials_path: Path to service account JSON (defaults to auto-discovery)
        """
        # Load from environment if not provided
        if gcp_project is None:
            gcp_project = os.getenv("GCP_PROJECT")
        if bucket_name is None:
            bucket_name = os.getenv("GCS_MODEL_BUCKET", "spatially-models")

        if not gcp_project:
            raise ValueError("GCP_PROJECT must be set (env var or parameter)")
        if not bucket_name:
            raise ValueError("GCS_MODEL_BUCKET must be set (env var or parameter)")

        # Auto-discover credentials if not provided
        if credentials_path is None:
            # Look for service account JSON in secrets folder
            secrets_dir = Path(__file__).parent.parent.parent.parent.parent / "secrets"
            potential_creds = [
                secrets_dir / "teamspatially-storage-accessor-keys.json",
                secrets_dir / "service-account.json",
                secrets_dir / "gcp-credentials.json"
            ]
            for cred_file in potential_creds:
                if cred_file.exists():
                    credentials_path = str(cred_file)
                    print(f"Using credentials: {cred_file.name}")
                    break

        # Initialize GCS client
        self.storage = GCPStorage(
            gcp_project=gcp_project,
            bucket_name=bucket_name,
            credentials_path=credentials_path
        )

        self.bucket_name = bucket_name
        print(f"GCS Model Manager initialized")
        print(f"  Project: {gcp_project}")
        print(f"  Bucket: gs://{bucket_name}")

    def upload_model(
        self,
        model_dir: Path,
        model_type: str,
        metadata: Optional[Dict] = None,
        max_retries: int = 3
    ) -> str:
        """
        Upload a trained model directory to GCS.

        Args:
            model_dir: Local directory containing model artifacts
            model_type: Type of model ('extractor' or 'validator')
            metadata: Optional metadata to include in registry (test_results, config, etc.)
            max_retries: Maximum number of upload retries on failure

        Returns:
            GCS path of uploaded model (e.g., 'gs://spatially-models/models/extractor_20260223_003120')

        Raises:
            ValueError: If model_dir doesn't exist or required files missing
            Exception: If upload fails after all retries
        """
        if not model_dir.exists():
            raise ValueError(f"Model directory does not exist: {model_dir}")

        # Verify required files exist
        required_files = ['config.json', 'model.safetensors', 'tokenizer.json']
        missing_files = [f for f in required_files if not (model_dir / f).exists()]
        if missing_files:
            raise ValueError(f"Missing required model files: {missing_files}")

        # Extract timestamp from model directory name
        # Expected format: extractor_20260223_003120 or validator_20260223_140818
        model_name = model_dir.name
        timestamp = model_name.split('_', 1)[-1] if '_' in model_name else datetime.now().strftime("%Y%m%d_%H%M%S")

        # GCS destination path
        gcs_prefix = f"models/{model_type}_{timestamp}"
        gcs_path = f"gs://{self.bucket_name}/{gcs_prefix}"

        print(f"\nUploading {model_type} model to GCS...")
        print(f"  Local:  {model_dir}")
        print(f"  GCS:    {gcs_path}")

        # Upload with retry logic
        for attempt in range(1, max_retries + 1):
            try:
                # Upload all files in the model directory
                self.storage.upload_dir(
                    source_path=str(model_dir),
                    destination_path=gcs_prefix
                )

                # Verify upload by listing files
                uploaded_files = self.storage.list_files(prefix=gcs_prefix, recursive=True)
                print(f"  ✓ Uploaded {len(uploaded_files)} files")

                # Update registry with metadata
                self._update_registry(
                    model_type=model_type,
                    timestamp=timestamp,
                    gcs_path=gcs_path,
                    metadata=metadata or {}
                )

                print(f"✓ Model uploaded successfully to {gcs_path}")
                return gcs_path

            except Exception as e:
                if attempt < max_retries:
                    wait_time = 2 ** attempt  # Exponential backoff
                    print(f"  ✗ Upload failed (attempt {attempt}/{max_retries}): {e}")
                    print(f"  Retrying in {wait_time} seconds...")
                    time.sleep(wait_time)
                else:
                    print(f"  ✗ Upload failed after {max_retries} attempts")
                    raise Exception(f"Failed to upload model to GCS: {e}")

    def download_model(
        self,
        model_type: str,
        timestamp: Optional[str] = None,
        cache_dir: Optional[Path] = None,
        force_download: bool = False,
        max_retries: int = 3
    ) -> Path:
        """
        Download a model from GCS to local cache.

        Args:
            model_type: Type of model ('extractor' or 'validator')
            timestamp: Specific model timestamp to download (None = latest)
            cache_dir: Local directory to cache models (None = default cache)
            force_download: If True, re-download even if cache exists
            max_retries: Maximum number of download retries on failure

        Returns:
            Path to local model directory

        Raises:
            ValueError: If model not found in GCS
            Exception: If download fails after all retries
        """
        # Determine which model to download
        if timestamp is None:
            # Get latest model from registry
            timestamp = self._get_latest_model_timestamp(model_type)
            if not timestamp:
                raise ValueError(f"No {model_type} models found in GCS registry")
            print(f"Using latest {model_type} model: {timestamp}")

        # Setup cache directory
        if cache_dir is None:
            cache_dir = Path(__file__).parent.parent.parent / "artifacts" / "models"
        cache_dir.mkdir(parents=True, exist_ok=True)

        local_model_dir = cache_dir / f"{model_type}_{timestamp}"

        # Check if already cached
        if local_model_dir.exists() and not force_download:
            print(f"Using cached {model_type} model: {local_model_dir}")
            return local_model_dir

        # GCS source path
        gcs_prefix = f"models/{model_type}_{timestamp}"
        gcs_path = f"gs://{self.bucket_name}/{gcs_prefix}"

        print(f"\nDownloading {model_type} model from GCS...")
        print(f"  GCS:    {gcs_path}")
        print(f"  Local:  {local_model_dir}")

        # Download with retry logic
        for attempt in range(1, max_retries + 1):
            try:
                # Create local directory
                local_model_dir.mkdir(parents=True, exist_ok=True)

                # Download all files
                self.storage.download_dir(
                    source_path=gcs_prefix,
                    destination_path=local_model_dir
                )

                # Verify download
                required_files = ['config.json', 'model.safetensors', 'tokenizer.json']
                missing_files = [f for f in required_files if not (local_model_dir / f).exists()]
                if missing_files:
                    raise ValueError(f"Download incomplete - missing files: {missing_files}")

                print(f"✓ Model downloaded successfully to {local_model_dir}")
                return local_model_dir

            except Exception as e:
                if attempt < max_retries:
                    wait_time = 2 ** attempt  # Exponential backoff
                    print(f"  ✗ Download failed (attempt {attempt}/{max_retries}): {e}")
                    print(f"  Retrying in {wait_time} seconds...")
                    time.sleep(wait_time)

                    # Clean up partial download
                    if local_model_dir.exists():
                        import shutil
                        shutil.rmtree(local_model_dir, ignore_errors=True)
                else:
                    print(f"  ✗ Download failed after {max_retries} attempts")
                    raise Exception(f"Failed to download model from GCS: {e}")

    def list_models(self, model_type: Optional[str] = None) -> List[Dict]:
        """
        List all available models in GCS.

        Args:
            model_type: Filter by model type ('extractor' or 'validator'). None = all models.

        Returns:
            List of model info dictionaries with keys: type, timestamp, gcs_path, metadata
        """
        registry = self._load_registry()

        models = []
        for mtype, versions in registry.get("models", {}).items():
            if model_type and mtype != model_type:
                continue

            for timestamp, model_info in versions.items():
                models.append({
                    "type": mtype,
                    "timestamp": timestamp,
                    "gcs_path": model_info.get("gcs_path"),
                    "metadata": model_info
                })

        # Sort by timestamp (newest first)
        models.sort(key=lambda x: x["timestamp"], reverse=True)
        return models

    def upload_cache_files(
        self,
        cache_dir: Path,
        max_retries: int = 3
    ) -> List[str]:
        """
        Upload dashboard cache files to GCS.

        Args:
            cache_dir: Directory containing cached_*.json files
            max_retries: Maximum number of upload retries on failure

        Returns:
            List of uploaded GCS paths

        Raises:
            ValueError: If cache_dir doesn't exist
            Exception: If upload fails after all retries
        """
        if not cache_dir.exists():
            raise ValueError(f"Cache directory does not exist: {cache_dir}")

        # Find all cached_*.json files
        cache_files = list(cache_dir.glob("cached_*.json"))
        if not cache_files:
            print("No cache files found to upload")
            return []

        print(f"\nUploading {len(cache_files)} cache files to GCS...")

        uploaded_paths = []
        for cache_file in cache_files:
            gcs_path = f"cache/{cache_file.name}"

            for attempt in range(1, max_retries + 1):
                try:
                    self.storage.upload_file(
                        file_path=str(cache_file),
                        destination_path=gcs_path
                    )

                    full_gcs_path = f"gs://{self.bucket_name}/{gcs_path}"
                    uploaded_paths.append(full_gcs_path)
                    print(f"  ✓ {cache_file.name}")
                    break

                except Exception as e:
                    if attempt < max_retries:
                        wait_time = 2 ** attempt
                        print(f"  ✗ Upload failed for {cache_file.name} (attempt {attempt}/{max_retries}): {e}")
                        print(f"  Retrying in {wait_time} seconds...")
                        time.sleep(wait_time)
                    else:
                        print(f"  ✗ Upload failed for {cache_file.name} after {max_retries} attempts")
                        raise Exception(f"Failed to upload cache file {cache_file.name}: {e}")

        print(f"✓ Uploaded {len(uploaded_paths)} cache files")
        return uploaded_paths

    def download_cache_files(
        self,
        cache_dir: Path,
        force_download: bool = False,
        max_retries: int = 3
    ) -> List[Path]:
        """
        Download dashboard cache files from GCS.

        Args:
            cache_dir: Local directory to save cache files
            force_download: If True, re-download even if cache exists
            max_retries: Maximum number of download retries on failure

        Returns:
            List of downloaded file paths
        """
        cache_dir.mkdir(parents=True, exist_ok=True)

        # List all cache files in GCS
        gcs_cache_files = self.storage.list_files(prefix="cache/", recursive=False)

        if not gcs_cache_files:
            print("No cache files found in GCS")
            return []

        print(f"\nDownloading {len(gcs_cache_files)} cache files from GCS...")

        downloaded_paths = []
        for gcs_path in gcs_cache_files:
            filename = Path(gcs_path).name
            local_path = cache_dir / filename

            # Skip if already cached
            if local_path.exists() and not force_download:
                print(f"  ✓ {filename} (cached)")
                downloaded_paths.append(local_path)
                continue

            for attempt in range(1, max_retries + 1):
                try:
                    self.storage.download_file(
                        source_path=gcs_path,
                        destination_path=str(local_path)
                    )

                    downloaded_paths.append(local_path)
                    print(f"  ✓ {filename}")
                    break

                except Exception as e:
                    if attempt < max_retries:
                        wait_time = 2 ** attempt
                        print(f"  ✗ Download failed for {filename} (attempt {attempt}/{max_retries}): {e}")
                        print(f"  Retrying in {wait_time} seconds...")
                        time.sleep(wait_time)
                    else:
                        print(f"  ✗ Download failed for {filename} after {max_retries} attempts: {e}")

        print(f"✓ Downloaded {len(downloaded_paths)} cache files")
        return downloaded_paths

    def _load_registry(self) -> Dict:
        """
        Load model registry from GCS.

        Returns:
            Registry dictionary with model metadata
        """
        registry_path = "registry.json"

        try:
            # Download registry to temporary file
            import tempfile
            with tempfile.NamedTemporaryFile(mode='w+', suffix='.json', delete=False) as tmp:
                tmp_path = tmp.name

            self.storage.download_file(
                source_path=registry_path,
                destination_path=tmp_path
            )

            with open(tmp_path, 'r') as f:
                registry = json.load(f)

            # Clean up temp file
            os.unlink(tmp_path)

            return registry

        except Exception:
            # Registry doesn't exist yet - return empty structure
            return {
                "version": "1.0",
                "models": {
                    "extractor": {},
                    "validator": {}
                }
            }

    def _update_registry(
        self,
        model_type: str,
        timestamp: str,
        gcs_path: str,
        metadata: Dict
    ):
        """
        Update model registry with new model entry.

        Args:
            model_type: Type of model ('extractor' or 'validator')
            timestamp: Model timestamp
            gcs_path: GCS path to model
            metadata: Model metadata (test_results, config, etc.)
        """
        # Load existing registry
        registry = self._load_registry()

        # Ensure model type exists in registry
        if model_type not in registry["models"]:
            registry["models"][model_type] = {}

        # Add/update model entry
        registry["models"][model_type][timestamp] = {
            "gcs_path": gcs_path,
            "uploaded_at": datetime.now().isoformat(),
            **metadata
        }

        # Upload updated registry
        self.storage.upload_json(
            data=registry,
            destination_path="registry.json"
        )

        print(f"  ✓ Updated registry")

    def _get_latest_model_timestamp(self, model_type: str) -> Optional[str]:
        """
        Get timestamp of the latest model of a given type.

        Args:
            model_type: Type of model ('extractor' or 'validator')

        Returns:
            Timestamp string or None if no models found
        """
        registry = self._load_registry()

        model_versions = registry.get("models", {}).get(model_type, {})
        if not model_versions:
            return None

        # Get latest timestamp (assumes timestamps are sortable strings)
        timestamps = sorted(model_versions.keys(), reverse=True)
        return timestamps[0] if timestamps else None

    def get_model_metadata(self, model_type: str, timestamp: str) -> Optional[Dict]:
        """
        Get metadata for a specific model.

        Args:
            model_type: Type of model ('extractor' or 'validator')
            timestamp: Model timestamp

        Returns:
            Model metadata dictionary or None if not found
        """
        registry = self._load_registry()
        return registry.get("models", {}).get(model_type, {}).get(timestamp)


def upload_model_to_gcs(
    model_dir: Path,
    model_type: str,
    metadata: Optional[Dict] = None
) -> Optional[str]:
    """
    Convenience function to upload a model to GCS.

    Loads GCP credentials from environment variables (GCP_PROJECT, GCS_MODEL_BUCKET).

    Args:
        model_dir: Local directory containing model artifacts
        model_type: Type of model ('extractor' or 'validator')
        metadata: Optional metadata to include in registry

    Returns:
        GCS path of uploaded model, or None if upload failed

    Example:
        >>> from utils.gcs_model_manager import upload_model_to_gcs
        >>> model_dir = Path("artifacts/models/extractor_20260223_003120")
        >>> gcs_path = upload_model_to_gcs(
        ...     model_dir=model_dir,
        ...     model_type="extractor",
        ...     metadata={"test_f1": 0.93, "num_epochs": 3}
        ... )
    """
    try:
        manager = GCSModelManager()
        gcs_path = manager.upload_model(
            model_dir=model_dir,
            model_type=model_type,
            metadata=metadata
        )
        return gcs_path
    except Exception as e:
        print(f"Failed to upload model to GCS: {e}")
        return None


def download_model_from_gcs(
    model_type: str,
    timestamp: Optional[str] = None,
    cache_dir: Optional[Path] = None
) -> Optional[Path]:
    """
    Convenience function to download a model from GCS.

    Loads GCP credentials from environment variables (GCP_PROJECT, GCS_MODEL_BUCKET).

    Args:
        model_type: Type of model ('extractor' or 'validator')
        timestamp: Specific model timestamp to download (None = latest)
        cache_dir: Local directory to cache models (None = default cache)

    Returns:
        Path to local model directory, or None if download failed

    Example:
        >>> from utils.gcs_model_manager import download_model_from_gcs
        >>> # Download latest extractor model
        >>> model_dir = download_model_from_gcs(model_type="extractor")
        >>> # Download specific model version
        >>> model_dir = download_model_from_gcs(
        ...     model_type="validator",
        ...     timestamp="20260223_140818"
        ... )
    """
    try:
        manager = GCSModelManager()
        model_dir = manager.download_model(
            model_type=model_type,
            timestamp=timestamp,
            cache_dir=cache_dir
        )
        return model_dir
    except Exception as e:
        print(f"Failed to download model from GCS: {e}")
        return None


if __name__ == "__main__":
    """Example usage and testing."""
    import argparse

    parser = argparse.ArgumentParser(description="GCS Model Manager")
    subparsers = parser.add_subparsers(dest="command", help="Command to execute")

    # Upload command
    upload_parser = subparsers.add_parser("upload", help="Upload model to GCS")
    upload_parser.add_argument("model_dir", type=str, help="Local model directory")
    upload_parser.add_argument("model_type", type=str, choices=["extractor", "validator"],
                              help="Type of model")

    # Download command
    download_parser = subparsers.add_parser("download", help="Download model from GCS")
    download_parser.add_argument("model_type", type=str, choices=["extractor", "validator"],
                                help="Type of model")
    download_parser.add_argument("--timestamp", type=str, default=None,
                                help="Model timestamp (default: latest)")
    download_parser.add_argument("--cache-dir", type=str, default=None,
                                help="Local cache directory")

    # List command
    list_parser = subparsers.add_parser("list", help="List available models")
    list_parser.add_argument("--model-type", type=str, choices=["extractor", "validator"],
                            default=None, help="Filter by model type")

    args = parser.parse_args()

    # Load environment variables
    env_file = Path(__file__).parent.parent.parent.parent.parent / "secrets" / "teamspatially-project.env"
    if env_file.exists():
        load_dotenv(env_file)

    # Execute command
    if args.command == "upload":
        gcs_path = upload_model_to_gcs(
            model_dir=Path(args.model_dir),
            model_type=args.model_type
        )
        if gcs_path:
            print(f"\nSuccess! Model uploaded to: {gcs_path}")

    elif args.command == "download":
        cache_dir = Path(args.cache_dir) if args.cache_dir else None
        model_dir = download_model_from_gcs(
            model_type=args.model_type,
            timestamp=args.timestamp,
            cache_dir=cache_dir
        )
        if model_dir:
            print(f"\nSuccess! Model downloaded to: {model_dir}")

    elif args.command == "list":
        manager = GCSModelManager()
        models = manager.list_models(model_type=args.model_type)

        print(f"\nAvailable models ({len(models)}):")
        for model in models:
            print(f"  {model['type']:10s} {model['timestamp']:20s} {model['gcs_path']}")

    else:
        parser.print_help()
