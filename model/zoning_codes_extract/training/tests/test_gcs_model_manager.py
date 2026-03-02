#!/usr/bin/env python3
"""
Unit tests for GCSModelManager.

These tests verify the upload, download, registry, and error handling
functionality of the GCS model management system.

Usage:
    pytest test_gcs_model_manager.py
    python -m pytest test_gcs_model_manager.py -v
"""

import os
import json
import tempfile
import shutil
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
import pytest

# Import the module to test
import sys
sys.path.append(str(Path(__file__).parent.parent / "utils"))
from gcs_model_manager import GCSModelManager, upload_model_to_gcs, download_model_from_gcs


@pytest.fixture
def mock_gcp_storage():
    """Mock GCPStorage to avoid actual GCS calls."""
    with patch('gcs_model_manager.GCPStorage') as mock:
        storage_instance = MagicMock()
        mock.return_value = storage_instance
        storage_instance.bucket.name = "spatially-models"
        yield storage_instance


@pytest.fixture
def temp_model_dir():
    """Create a temporary model directory with required files."""
    temp_dir = Path(tempfile.mkdtemp(prefix="test_model_"))

    # Create required model files
    (temp_dir / "config.json").write_text(json.dumps({"model_type": "bert"}))
    (temp_dir / "model.safetensors").write_bytes(b"fake model weights")
    (temp_dir / "tokenizer.json").write_text(json.dumps({"vocab_size": 30000}))
    (temp_dir / "tokenizer_config.json").write_text(json.dumps({"do_lower_case": True}))
    (temp_dir / "special_tokens_map.json").write_text(json.dumps({"cls_token": "[CLS]"}))
    (temp_dir / "vocab.txt").write_text("[PAD]\n[UNK]\n[CLS]\n[SEP]")
    (temp_dir / "test_results.json").write_text(json.dumps({"accuracy": 0.95}))

    yield temp_dir

    # Cleanup
    shutil.rmtree(temp_dir, ignore_errors=True)


@pytest.fixture
def temp_cache_dir():
    """Create a temporary cache directory with cache files."""
    temp_dir = Path(tempfile.mkdtemp(prefix="test_cache_"))

    # Create cache files
    (temp_dir / "cached_metrics.json").write_text(json.dumps({"f1": 0.93}))
    (temp_dir / "cached_extractor_examples.json").write_text(json.dumps([{"text": "example"}]))
    (temp_dir / "cached_validator_examples.json").write_text(json.dumps([{"label": 1}]))
    (temp_dir / "cached_city_comparison.json").write_text(json.dumps({"cities": []}))

    yield temp_dir

    # Cleanup
    shutil.rmtree(temp_dir, ignore_errors=True)


class TestGCSModelManager:
    """Test suite for GCSModelManager class."""

    def test_initialization(self, mock_gcp_storage):
        """Test that GCSModelManager initializes correctly."""
        with patch.dict(os.environ, {'GCP_PROJECT': 'test-project', 'GCS_MODEL_BUCKET': 'test-bucket'}):
            manager = GCSModelManager()
            assert manager.bucket_name == 'test-bucket'

    def test_initialization_missing_project(self):
        """Test that initialization fails without GCP_PROJECT."""
        with patch.dict(os.environ, {}, clear=True):
            with pytest.raises(ValueError, match="GCP_PROJECT must be set"):
                GCSModelManager()

    def test_upload_model_success(self, mock_gcp_storage, temp_model_dir):
        """Test successful model upload."""
        with patch.dict(os.environ, {'GCP_PROJECT': 'test-project'}):
            manager = GCSModelManager()

            # Mock list_files to return uploaded files
            mock_gcp_storage.list_files.return_value = [
                "models/extractor_20260223/config.json",
                "models/extractor_20260223/model.safetensors"
            ]

            # Mock registry operations
            with patch.object(manager, '_load_registry', return_value={"version": "1.0", "models": {"extractor": {}, "validator": {}}}):
                with patch.object(manager, '_update_registry'):
                    gcs_path = manager.upload_model(
                        model_dir=temp_model_dir,
                        model_type="extractor",
                        metadata={"test_f1": 0.93}
                    )

            assert gcs_path.startswith("gs://spatially-models/models/extractor_")
            mock_gcp_storage.upload_dir.assert_called_once()

    def test_upload_model_missing_directory(self, mock_gcp_storage):
        """Test that upload fails with non-existent directory."""
        with patch.dict(os.environ, {'GCP_PROJECT': 'test-project'}):
            manager = GCSModelManager()

            with pytest.raises(ValueError, match="Model directory does not exist"):
                manager.upload_model(
                    model_dir=Path("/nonexistent/path"),
                    model_type="extractor"
                )

    def test_upload_model_missing_files(self, mock_gcp_storage):
        """Test that upload fails with missing required files."""
        with patch.dict(os.environ, {'GCP_PROJECT': 'test-project'}):
            manager = GCSModelManager()

            # Create incomplete model directory
            temp_dir = Path(tempfile.mkdtemp(prefix="incomplete_model_"))
            (temp_dir / "config.json").write_text("{}")
            # Missing model.safetensors and tokenizer.json

            try:
                with pytest.raises(ValueError, match="Missing required model files"):
                    manager.upload_model(
                        model_dir=temp_dir,
                        model_type="extractor"
                    )
            finally:
                shutil.rmtree(temp_dir, ignore_errors=True)

    def test_upload_model_with_retry(self, mock_gcp_storage, temp_model_dir):
        """Test that upload retries on failure."""
        with patch.dict(os.environ, {'GCP_PROJECT': 'test-project'}):
            manager = GCSModelManager()

            # First call fails, second succeeds
            mock_gcp_storage.upload_dir.side_effect = [
                Exception("Network error"),
                None  # Success on retry
            ]
            mock_gcp_storage.list_files.return_value = ["models/extractor_20260223/config.json"]

            with patch.object(manager, '_load_registry', return_value={"version": "1.0", "models": {"extractor": {}, "validator": {}}}):
                with patch.object(manager, '_update_registry'):
                    with patch('time.sleep'):  # Skip actual sleep
                        gcs_path = manager.upload_model(
                            model_dir=temp_model_dir,
                            model_type="extractor",
                            max_retries=3
                        )

            assert gcs_path is not None
            assert mock_gcp_storage.upload_dir.call_count == 2

    def test_download_model_success(self, mock_gcp_storage):
        """Test successful model download."""
        with patch.dict(os.environ, {'GCP_PROJECT': 'test-project'}):
            manager = GCSModelManager()

            # Mock registry to return latest model
            with patch.object(manager, '_get_latest_model_timestamp', return_value="20260223_003120"):
                with tempfile.TemporaryDirectory() as cache_dir:
                    cache_path = Path(cache_dir)

                    # Mock download_dir to create required files
                    def mock_download(source_path, destination_path):
                        dest = Path(destination_path)
                        dest.mkdir(parents=True, exist_ok=True)
                        (dest / "config.json").write_text("{}")
                        (dest / "model.safetensors").write_bytes(b"weights")
                        (dest / "tokenizer.json").write_text("{}")

                    mock_gcp_storage.download_dir.side_effect = mock_download

                    model_dir = manager.download_model(
                        model_type="extractor",
                        cache_dir=cache_path
                    )

                    assert model_dir.exists()
                    assert (model_dir / "config.json").exists()
                    mock_gcp_storage.download_dir.assert_called_once()

    def test_download_model_no_models_available(self, mock_gcp_storage):
        """Test that download fails when no models are available."""
        with patch.dict(os.environ, {'GCP_PROJECT': 'test-project'}):
            manager = GCSModelManager()

            with patch.object(manager, '_get_latest_model_timestamp', return_value=None):
                with pytest.raises(ValueError, match="No extractor models found"):
                    manager.download_model(model_type="extractor")

    def test_list_models(self, mock_gcp_storage):
        """Test listing available models."""
        with patch.dict(os.environ, {'GCP_PROJECT': 'test-project'}):
            manager = GCSModelManager()

            mock_registry = {
                "version": "1.0",
                "models": {
                    "extractor": {
                        "20260223_003120": {
                            "gcs_path": "gs://spatially-models/models/extractor_20260223_003120",
                            "test_results": {"f1": 0.93}
                        },
                        "20260222_120000": {
                            "gcs_path": "gs://spatially-models/models/extractor_20260222_120000",
                            "test_results": {"f1": 0.91}
                        }
                    },
                    "validator": {
                        "20260223_140818": {
                            "gcs_path": "gs://spatially-models/models/validator_20260223_140818",
                            "test_results": {"accuracy": 0.95}
                        }
                    }
                }
            }

            with patch.object(manager, '_load_registry', return_value=mock_registry):
                # List all models
                all_models = manager.list_models()
                assert len(all_models) == 3

                # List only extractor models
                extractor_models = manager.list_models(model_type="extractor")
                assert len(extractor_models) == 2
                assert all(m["type"] == "extractor" for m in extractor_models)

                # Check sorting (newest first)
                assert extractor_models[0]["timestamp"] == "20260223_003120"
                assert extractor_models[1]["timestamp"] == "20260222_120000"

    def test_upload_cache_files(self, mock_gcp_storage, temp_cache_dir):
        """Test uploading cache files."""
        with patch.dict(os.environ, {'GCP_PROJECT': 'test-project'}):
            manager = GCSModelManager()

            uploaded_paths = manager.upload_cache_files(cache_dir=temp_cache_dir)

            assert len(uploaded_paths) == 4
            assert all(path.startswith("gs://spatially-models/cache/") for path in uploaded_paths)
            assert mock_gcp_storage.upload_file.call_count == 4

    def test_upload_cache_files_no_files(self, mock_gcp_storage):
        """Test uploading cache files when directory is empty."""
        with patch.dict(os.environ, {'GCP_PROJECT': 'test-project'}):
            manager = GCSModelManager()

            with tempfile.TemporaryDirectory() as empty_dir:
                uploaded_paths = manager.upload_cache_files(cache_dir=Path(empty_dir))
                assert len(uploaded_paths) == 0

    def test_download_cache_files(self, mock_gcp_storage):
        """Test downloading cache files."""
        with patch.dict(os.environ, {'GCP_PROJECT': 'test-project'}):
            manager = GCSModelManager()

            # Mock list_files to return cache files
            mock_gcp_storage.list_files.return_value = [
                "cache/cached_metrics.json",
                "cache/cached_extractor_examples.json"
            ]

            with tempfile.TemporaryDirectory() as cache_dir:
                cache_path = Path(cache_dir)

                # Mock download_file to create files
                def mock_download(source_path, destination_path):
                    Path(destination_path).write_text("{}")

                mock_gcp_storage.download_file.side_effect = mock_download

                downloaded = manager.download_cache_files(cache_dir=cache_path)

                assert len(downloaded) == 2
                assert all(p.exists() for p in downloaded)

    def test_get_model_metadata(self, mock_gcp_storage):
        """Test retrieving model metadata."""
        with patch.dict(os.environ, {'GCP_PROJECT': 'test-project'}):
            manager = GCSModelManager()

            mock_registry = {
                "version": "1.0",
                "models": {
                    "extractor": {
                        "20260223_003120": {
                            "gcs_path": "gs://spatially-models/models/extractor_20260223_003120",
                            "test_results": {"f1": 0.93},
                            "wandb_url": "https://wandb.ai/test"
                        }
                    }
                }
            }

            with patch.object(manager, '_load_registry', return_value=mock_registry):
                metadata = manager.get_model_metadata("extractor", "20260223_003120")

                assert metadata is not None
                assert metadata["test_results"]["f1"] == 0.93
                assert "wandb_url" in metadata

                # Test non-existent model
                none_metadata = manager.get_model_metadata("extractor", "nonexistent")
                assert none_metadata is None


class TestConvenienceFunctions:
    """Test suite for convenience functions."""

    def test_upload_model_to_gcs(self, mock_gcp_storage, temp_model_dir):
        """Test upload_model_to_gcs convenience function."""
        with patch.dict(os.environ, {'GCP_PROJECT': 'test-project'}):
            with patch('gcs_model_manager.GCSModelManager') as mock_manager_class:
                mock_manager = MagicMock()
                mock_manager.upload_model.return_value = "gs://spatially-models/models/extractor_20260223"
                mock_manager_class.return_value = mock_manager

                gcs_path = upload_model_to_gcs(
                    model_dir=temp_model_dir,
                    model_type="extractor",
                    metadata={"f1": 0.93}
                )

                assert gcs_path == "gs://spatially-models/models/extractor_20260223"
                mock_manager.upload_model.assert_called_once()

    def test_upload_model_to_gcs_error_handling(self, mock_gcp_storage, temp_model_dir):
        """Test that upload_model_to_gcs handles errors gracefully."""
        with patch.dict(os.environ, {'GCP_PROJECT': 'test-project'}):
            with patch('gcs_model_manager.GCSModelManager') as mock_manager_class:
                mock_manager_class.side_effect = Exception("Connection error")

                gcs_path = upload_model_to_gcs(
                    model_dir=temp_model_dir,
                    model_type="extractor"
                )

                assert gcs_path is None  # Should return None on error

    def test_download_model_from_gcs(self, mock_gcp_storage):
        """Test download_model_from_gcs convenience function."""
        with patch.dict(os.environ, {'GCP_PROJECT': 'test-project'}):
            with patch('gcs_model_manager.GCSModelManager') as mock_manager_class:
                mock_manager = MagicMock()
                mock_manager.download_model.return_value = Path("/tmp/extractor_20260223")
                mock_manager_class.return_value = mock_manager

                model_dir = download_model_from_gcs(
                    model_type="extractor",
                    timestamp="20260223_003120"
                )

                assert model_dir == Path("/tmp/extractor_20260223")
                mock_manager.download_model.assert_called_once()

    def test_download_model_from_gcs_error_handling(self, mock_gcp_storage):
        """Test that download_model_from_gcs handles errors gracefully."""
        with patch.dict(os.environ, {'GCP_PROJECT': 'test-project'}):
            with patch('gcs_model_manager.GCSModelManager') as mock_manager_class:
                mock_manager_class.side_effect = Exception("Network error")

                model_dir = download_model_from_gcs(model_type="extractor")

                assert model_dir is None  # Should return None on error


if __name__ == "__main__":
    # Run tests with pytest
    pytest.main([__file__, "-v"])
