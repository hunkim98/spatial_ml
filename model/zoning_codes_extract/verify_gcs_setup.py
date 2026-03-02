#!/usr/bin/env python3
"""
GCS Setup Verification Script

Verifies that your GCS buckets are properly configured and accessible.

Usage:
    python verify_gcs_setup.py
"""

import os
import sys
from pathlib import Path
from dotenv import load_dotenv

# Colors for terminal output
class Colors:
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    BOLD = '\033[1m'
    END = '\033[0m'

def print_header(text):
    """Print colored header."""
    print(f"\n{Colors.BOLD}{Colors.BLUE}{'='*80}{Colors.END}")
    print(f"{Colors.BOLD}{Colors.BLUE}{text}{Colors.END}")
    print(f"{Colors.BOLD}{Colors.BLUE}{'='*80}{Colors.END}\n")

def print_success(text):
    """Print success message."""
    print(f"{Colors.GREEN}✓{Colors.END} {text}")

def print_error(text):
    """Print error message."""
    print(f"{Colors.RED}✗{Colors.END} {text}")

def print_warning(text):
    """Print warning message."""
    print(f"{Colors.YELLOW}⚠{Colors.END} {text}")

def print_info(text):
    """Print info message."""
    print(f"{Colors.BLUE}ℹ{Colors.END} {text}")


def check_env_files():
    """Check that environment files exist."""
    print_header("1. Checking Environment Files")

    root_env = Path(".env")
    training_env = Path("training/.env.training")
    example_env = Path(".env.example")

    all_good = True

    # Check .env.example
    if example_env.exists():
        print_success(f".env.example exists")
    else:
        print_error(f".env.example missing")
        all_good = False

    # Check .env
    if root_env.exists():
        print_success(f".env exists (infrastructure config)")
    else:
        print_warning(f".env not found - copy from .env.example")
        print_info(f"   Run: cp .env.example .env")
        all_good = False

    # Check training/.env.training
    if training_env.exists():
        print_success(f"training/.env.training exists (hyperparameters)")
    else:
        print_error(f"training/.env.training missing")
        all_good = False

    return all_good


def check_environment_variables():
    """Check that required environment variables are set."""
    print_header("2. Checking Environment Variables")

    # Load .env files
    if Path(".env").exists():
        load_dotenv(".env")
        print_info("Loaded .env")

    if Path("training/.env.training").exists():
        load_dotenv("training/.env.training")
        print_info("Loaded training/.env.training")

    required_vars = {
        "GCP_PROJECT": "GCP project ID",
        "GCS_DATA_BUCKET": "Data bucket (zoneomics + ordinances)",
        "GCS_MODEL_BUCKET": "Model bucket (trained models)",
    }

    optional_vars = {
        "GOOGLE_APPLICATION_CREDENTIALS": "Path to service account JSON",
        "WANDB_API_KEY": "Weights & Biases API key",
        "UPLOAD_TO_GCS": "Enable model upload after training",
    }

    all_good = True
    env_values = {}

    print("\n📋 Required Variables:")
    for var, description in required_vars.items():
        value = os.getenv(var)
        env_values[var] = value
        if value:
            print_success(f"{var} = {value}")
        else:
            print_error(f"{var} not set ({description})")
            all_good = False

    print("\n📋 Optional Variables:")
    for var, description in optional_vars.items():
        value = os.getenv(var)
        env_values[var] = value
        if value:
            if var == "WANDB_API_KEY":
                print_success(f"{var} = {'*' * 20} (hidden)")
            else:
                print_success(f"{var} = {value}")
        else:
            print_warning(f"{var} not set ({description})")

    return all_good, env_values


def check_gcs_buckets(env_values):
    """Check GCS bucket accessibility."""
    print_header("3. Checking GCS Bucket Access")

    # Try to import GCS libraries
    try:
        from google.cloud import storage
        print_success("google-cloud-storage library installed")
    except ImportError:
        print_error("google-cloud-storage not installed")
        print_info("   Run: pip install google-cloud-storage")
        return False

    # Check credentials
    creds_path = env_values.get("GOOGLE_APPLICATION_CREDENTIALS")
    if creds_path and Path(creds_path).exists():
        print_success(f"Credentials file exists: {creds_path}")
        os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = creds_path
    else:
        print_warning("GOOGLE_APPLICATION_CREDENTIALS not set or file doesn't exist")
        print_info("   Will try default credentials (gcloud auth)")

    # Try to connect to GCS
    try:
        client = storage.Client(project=env_values.get("GCP_PROJECT"))
        print_success("Successfully connected to GCS")
    except Exception as e:
        print_error(f"Failed to connect to GCS: {e}")
        print_info("   Try: gcloud auth application-default login")
        return False

    # Check buckets
    all_good = True

    buckets_to_check = [
        ("GCS_DATA_BUCKET", "Data bucket (source data)", ["zoning_codes/zoneomics", "zoning_ordinance_markdown"]),
        ("GCS_MODEL_BUCKET", "Model bucket (trained models)", ["models", "cache"]),
    ]

    for bucket_var, description, expected_prefixes in buckets_to_check:
        bucket_name = env_values.get(bucket_var)
        if not bucket_name:
            print_warning(f"\n{bucket_var} not set, skipping check")
            continue

        print(f"\n📦 Checking {description}: gs://{bucket_name}")

        try:
            bucket = client.bucket(bucket_name)

            # Check if bucket exists
            if bucket.exists():
                print_success(f"  Bucket exists: gs://{bucket_name}")
            else:
                print_error(f"  Bucket does not exist: gs://{bucket_name}")
                all_good = False
                continue

            # Check read access
            try:
                blobs = list(bucket.list_blobs(max_results=1))
                print_success(f"  Read access: OK")
            except Exception as e:
                print_error(f"  Read access: DENIED ({e})")
                all_good = False

            # Check write access (for model bucket)
            if bucket_var == "GCS_MODEL_BUCKET":
                try:
                    test_blob = bucket.blob("_test_write_access.txt")
                    test_blob.upload_from_string("test")
                    test_blob.delete()
                    print_success(f"  Write access: OK")
                except Exception as e:
                    print_error(f"  Write access: DENIED ({e})")
                    all_good = False

            # Check expected structure
            print(f"\n  Expected structure:")
            for prefix in expected_prefixes:
                blobs = list(bucket.list_blobs(prefix=prefix, max_results=1))
                if blobs:
                    print_success(f"    ✓ {prefix}/ exists")
                else:
                    print_warning(f"    ⚠ {prefix}/ not found (may be empty)")

        except Exception as e:
            print_error(f"  Error checking bucket: {e}")
            all_good = False

    return all_good


def check_bucket_contents(env_values):
    """Check bucket contents in detail."""
    print_header("4. Checking Bucket Contents (Sample)")

    try:
        from google.cloud import storage
        client = storage.Client(project=env_values.get("GCP_PROJECT"))
    except:
        print_warning("Skipping content check (GCS not accessible)")
        return

    # Check data bucket
    data_bucket_name = env_values.get("GCS_DATA_BUCKET")
    if data_bucket_name:
        print(f"\n📊 Data Bucket: gs://{data_bucket_name}")
        try:
            bucket = client.bucket(data_bucket_name)

            # Check zoneomics
            zoneomics_blobs = list(bucket.list_blobs(prefix="zoning_codes/zoneomics/", max_results=5))
            if zoneomics_blobs:
                print_success(f"  Zoneomics CSVs: {len(zoneomics_blobs)} files (showing first 5)")
                for blob in zoneomics_blobs[:5]:
                    print(f"    - {blob.name}")
            else:
                print_warning(f"  No zoneomics files found")

            # Check ordinances
            ordinance_blobs = list(bucket.list_blobs(prefix="zoning_ordinance_markdown/", max_results=5))
            if ordinance_blobs:
                print_success(f"  Ordinance files: {len(ordinance_blobs)} files (showing first 5)")
                for blob in ordinance_blobs[:5]:
                    print(f"    - {blob.name}")
            else:
                print_warning(f"  No ordinance files found")

        except Exception as e:
            print_error(f"  Error: {e}")

    # Check model bucket
    model_bucket_name = env_values.get("GCS_MODEL_BUCKET")
    if model_bucket_name:
        print(f"\n🤖 Model Bucket: gs://{model_bucket_name}")
        try:
            bucket = client.bucket(model_bucket_name)

            # Check models
            model_blobs = list(bucket.list_blobs(prefix="models/", delimiter="/"))
            if model_blobs or bucket.list_blobs(prefix="models/", max_results=1):
                print_success(f"  Models directory exists")
                # List model directories
                model_dirs = set()
                for blob in bucket.list_blobs(prefix="models/"):
                    parts = blob.name.split("/")
                    if len(parts) >= 2:
                        model_dirs.add(parts[1])

                if model_dirs:
                    print_info(f"  Found {len(model_dirs)} model(s):")
                    for model_dir in sorted(model_dirs)[:5]:
                        print(f"    - {model_dir}")
                else:
                    print_warning(f"  No models uploaded yet")
            else:
                print_warning(f"  No models directory found")

        except Exception as e:
            print_error(f"  Error: {e}")


def print_summary():
    """Print configuration summary."""
    print_header("5. Configuration Summary")

    print("Your GCS setup should have TWO buckets:\n")

    print("1️⃣  DATA BUCKET (source data - READ ONLY during training)")
    print("   Variable: GCS_DATA_BUCKET")
    print("   Example: spatially-data")
    print("   Contains:")
    print("     - zoning_codes/zoneomics/*.csv (ground truth)")
    print("     - zoning_ordinance_markdown/**/*.md (source ordinances)")
    print("")

    print("2️⃣  MODEL BUCKET (trained models - WRITE during training)")
    print("   Variable: GCS_MODEL_BUCKET")
    print("   Example: spatially-models")
    print("   Contains:")
    print("     - models/extractor_*/ (trained extractors)")
    print("     - models/validator_*/ (trained validators)")
    print("     - cache/*.json (evaluation metrics)")
    print("")

    print("📝 Your .env should look like:")
    print(f"{Colors.BLUE}")
    print("GCP_PROJECT=teamspatially")
    print("GCS_DATA_BUCKET=spatially-data")
    print("GCS_MODEL_BUCKET=spatially-models")
    print("GOOGLE_APPLICATION_CREDENTIALS=/path/to/key.json")
    print("UPLOAD_TO_GCS=1")
    print(f"{Colors.END}")


def main():
    """Main verification function."""
    print(f"\n{Colors.BOLD}GCS Setup Verification Tool{Colors.END}")
    print("This script checks your Google Cloud Storage configuration.\n")

    # Change to script directory
    script_dir = Path(__file__).parent
    os.chdir(script_dir)

    # Run checks
    results = {}

    results["env_files"] = check_env_files()
    results["env_vars"], env_values = check_environment_variables()

    if env_values.get("GCP_PROJECT") and (env_values.get("GCS_DATA_BUCKET") or env_values.get("GCS_MODEL_BUCKET")):
        results["gcs_access"] = check_gcs_buckets(env_values)
        check_bucket_contents(env_values)
    else:
        print_warning("\nSkipping GCS checks - environment variables not set")
        results["gcs_access"] = False

    print_summary()

    # Final summary
    print_header("Verification Results")

    all_passed = all(results.values())

    if all_passed:
        print_success("All checks passed! Your GCS setup is ready. ✨")
        print("\nNext steps:")
        print("  1. Run training: python -m training.train pipeline")
        print("  2. Models will upload to GCS if UPLOAD_TO_GCS=1")
        return 0
    else:
        print_warning("Some checks failed. Please fix the issues above.")
        print("\nCommon fixes:")
        print("  1. Copy .env.example to .env and fill in your values")
        print("  2. Set GCS_DATA_BUCKET and GCS_MODEL_BUCKET in .env")
        print("  3. Ensure service account has proper permissions")
        print("  4. Run: gcloud auth application-default login")
        return 1


if __name__ == "__main__":
    sys.exit(main())
