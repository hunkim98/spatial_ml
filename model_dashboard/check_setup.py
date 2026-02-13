#!/usr/bin/env python3
"""
Quick setup check for the dashboard.
Run this before starting the dashboard to verify everything is configured correctly.
"""

import sys
from pathlib import Path

def check_file(path, description):
    """Check if a file exists."""
    if path.exists():
        size = path.stat().st_size
        size_str = f"{size / 1024:.1f} KB" if size < 1024 * 1024 else f"{size / (1024 * 1024):.1f} MB"
        print(f"✅ {description}: {path} ({size_str})")
        return True
    else:
        print(f"❌ {description}: {path} (NOT FOUND)")
        return False

def check_dir(path, description):
    """Check if a directory exists."""
    if path.exists() and path.is_dir():
        print(f"✅ {description}: {path}")
        return True
    else:
        print(f"❌ {description}: {path} (NOT FOUND)")
        return False

def main():
    print("Dashboard Setup Verification")
    print("=" * 60)
    print()

    BASE_DIR = Path(__file__).parent.parent
    MODEL_DIR = BASE_DIR / "model" / "zoning_codes_extract"
    TRAINED_MODELS_DIR = MODEL_DIR / "artifacts" / "models"
    DATA_DIR = MODEL_DIR / "artifacts" / "data" / "full"

    all_ok = True

    # Check model directories
    print("📁 Model Directories:")
    all_ok &= check_dir(TRAINED_MODELS_DIR / "extractor", "Extractor model")
    all_ok &= check_dir(TRAINED_MODELS_DIR / "validator", "Validator model")
    print()

    # Check data files
    print("📊 Data Files:")
    all_ok &= check_file(DATA_DIR / "train.jsonl", "Training data (extractor)")
    all_ok &= check_file(DATA_DIR / "test.jsonl", "Test data (extractor)")
    all_ok &= check_file(DATA_DIR / "validator_train.jsonl", "Training data (validator)")
    all_ok &= check_file(DATA_DIR / "validator_test.jsonl", "Test data (validator)")
    print()

    # Check cached metrics (optional but recommended)
    print("⚡ Cached Metrics (optional, for fast loading):")
    has_cache = True
    has_cache &= check_file(TRAINED_MODELS_DIR / "cached_metrics.json", "Metrics cache")
    has_cache &= check_file(TRAINED_MODELS_DIR / "cached_extractor_examples.json", "Extractor examples cache")
    has_cache &= check_file(TRAINED_MODELS_DIR / "cached_validator_examples.json", "Validator examples cache")
    has_cache &= check_file(TRAINED_MODELS_DIR / "cached_city_comparison.json", "City comparison cache")

    if not has_cache:
        print("ℹ️  Note: Cached metrics not found. Dashboard will compute metrics on-the-fly (slower).")
        print("   To speed up, run: cd model/zoning_codes_extract/evaluation && python compute_metrics.py")
    print()

    # Check dependencies
    print("🐍 Python Dependencies:")
    try:
        import flask
        print(f"✅ Flask: {flask.__version__}")
    except ImportError:
        print("❌ Flask: NOT INSTALLED")
        all_ok = False

    try:
        import transformers
        print(f"✅ Transformers: {transformers.__version__}")
    except ImportError:
        print("❌ Transformers: NOT INSTALLED")
        all_ok = False

    try:
        import torch
        print(f"✅ PyTorch: {torch.__version__}")
    except ImportError:
        print("❌ PyTorch: NOT INSTALLED")
        all_ok = False

    try:
        import seqeval
        print(f"✅ seqeval: {seqeval.__version__}")
    except ImportError:
        print("⚠️  seqeval: NOT INSTALLED (optional, but recommended)")
    print()

    # Summary
    print("=" * 60)
    if all_ok:
        print("✅ All checks passed! You can start the dashboard:")
        print()
        print("   python app.py")
        print()
        print("   Then open: http://localhost:5001")
        return 0
    else:
        print("❌ Some checks failed. Please fix the issues above.")
        print()
        if not has_cache:
            print("To install dependencies:")
            print("   cd model_dashboard")
            print("   uv sync")
        return 1

if __name__ == "__main__":
    sys.exit(main())
