# Zoning Code Extraction System

A machine learning pipeline for automatically extracting zoning codes from municipal ordinance documents using BERT-based models.

## 🎯 Overview

This system extracts zone codes (like R-1, C-2, I-1) from ordinance text using a three-stage ML pipeline:

1. **Extractor** - Token classification model (BERT) that identifies zone code mentions in text
2. **Validator** - Binary classification model (BERT) that filters false positives
3. **Categorizer** - Rule-based system that assigns categories (Residential, Commercial, etc.)

## 📦 Installation

```bash
cd model/zoning_codes_extract
pip install -e .
```

**Dependencies:**
- `transformers` - BERT models
- `torch` - PyTorch
- `datasets` - HuggingFace datasets
- `seqeval` - NER metrics
- `pandas`, `scikit-learn`, `python-docx`, `rapidfuzz`

## 🚀 Quick Start

### Using Pre-trained Models

```python
from zoning_extract import ZoningCodePipeline

# Initialize pipeline with trained models
pipeline = ZoningCodePipeline(
    extractor_model_path="artifacts/models/extractor",
    validator_model_path="artifacts/models/validator"
)

# Extract from ordinance directory
results = pipeline.extract_from_ordinances("path/to/ordinances")

# Save to CSV
pipeline.save_to_csv(results, "output/zones.csv")
```

### Training New Models

See [Training Guide](training/README.md) for complete training documentation.

**Quick training:**
```bash
# Show configuration
python -m training.train config

# Train both models
python -m training.train pipeline

# Or train individually
python -m training.train extractor
python -m training.train validator
```

## 📁 Project Structure

```
zoning_codes_extract/
├── README.md                       # This file
├── REFACTORING_SUMMARY.md          # Recent changes and migration guide
├── .env.example                    # Configuration template
├── pyproject.toml                  # Dependencies
│
├── zoning_extract/                 # Main package
│   ├── __init__.py                 # Public API
│   ├── utils.py                    # Shared utilities
│   ├── pipeline.py                 # End-to-end orchestration
│   ├── city_matcher.py             # City matching logic
│   │
│   ├── core/                       # ML models
│   │   ├── extractor.py            # Token classification
│   │   ├── validator.py            # Sequence classification
│   │   └── categorizer.py          # Rule-based categorizer
│   │
│   └── parsers/                    # Document parsing
│       ├── ordinance_parser.py     # DOCX parsing
│       └── text_aligner.py         # Text alignment
│
├── training/                       # Training infrastructure
│   ├── README.md                   # Training guide
│   ├── train.py                    # Unified CLI entry point
│   ├── .env.training               # Training hyperparameters
│   │
│   ├── trainers/                   # Model training
│   │   ├── base.py                 # Shared training logic
│   │   ├── extractor.py            # Extractor trainer
│   │   └── validator.py            # Validator trainer
│   │
│   ├── data_prep/                  # Data preparation
│   │   ├── prepare_extractor.py
│   │   ├── prepare_validator.py
│   │   └── city_splits.py
│   │
│   ├── utils/                      # Training utilities
│   │   ├── config.py               # Configuration loader
│   │   ├── custom_tokenization.py
│   │   ├── post_processing.py
│   │   ├── gcs_data_fetcher.py
│   │   └── gcs_model_manager.py
│   │
│   └── scripts/                    # GCP deployment
│       ├── launch_gcp_training.sh
│       └── gcp_vm_startup.sh
│
├── evaluation/                     # Model evaluation
│   └── compute_metrics.py          # Metrics and dashboard cache
│
├── tests/                          # Unit tests
│
└── artifacts/                      # Generated outputs (gitignored)
    ├── models/                     # Trained models
    └── data/                       # Training data
```

## 🔧 Usage

### Python API

```python
from zoning_extract import ZoneExtractor, ZoneValidator, ZoningCodePipeline

# Use individual components
extractor = ZoneExtractor(model_path="artifacts/models/extractor")
spans = extractor.extract("The R-1 Zone permits single-family dwellings...")

validator = ZoneValidator(model_path="artifacts/models/validator")
result = validator.validate(candidate)

# Or use full pipeline
pipeline = ZoningCodePipeline(
    extractor_model_path="artifacts/models/extractor",
    validator_model_path="artifacts/models/validator",
    min_validation_confidence=0.5,
    min_extraction_score=0.5
)

zones = pipeline.extract_from_text(ordinance_text)
```

### Command Line Interface

```bash
# Training
python -m training.train extractor
python -m training.train validator
python -m training.train pipeline

# Data preparation
python -m training.train prepare extractor --cities 100
python -m training.train prepare validator --cities 100

# Evaluation
python -m training.train evaluate

# Configuration
python -m training.train config
```

## ⚙️ Configuration

### Environment Variables

Create `.env` from `.env.example`:

```bash
# Infrastructure (NOT committed)
GCP_PROJECT=your-project
GCS_BUCKET_NAME=your-bucket
GOOGLE_APPLICATION_CREDENTIALS=/path/to/key.json
WANDB_API_KEY=your-key
```

### Training Hyperparameters

Edit `training/.env.training`:

```bash
# Model
MODEL_NAME=bert-base-uncased
MAX_SEQ_LENGTH=512

# Training
NUM_EPOCHS=3
BATCH_SIZE=2
LEARNING_RATE=3e-5

# Inference
MIN_EXTRACTION_SCORE=0.5
MIN_VALIDATION_CONFIDENCE=0.5
CONTEXT_WINDOW=500
```

### Override at Runtime

```bash
python -m training.train extractor \
    --epochs 5 \
    --batch-size 4 \
    --learning-rate 5e-5
```

## 📊 Model Architecture

### Extractor (Token Classification)

**Input:** Text passage (max 512 tokens)
**Output:** BIO tags for each token
- `B-ZONE`: Beginning of zone code
- `I-ZONE`: Inside (continuation) of zone code
- `O`: Outside (not a zone code)

**Metrics:** Precision, Recall, F1 (uses seqeval for entity-level evaluation)

### Validator (Sequence Classification)

**Input:** `[CODE] zone_code [SEP] passage1 [SEP] passage2 ...`
**Output:** Binary classification (valid zone / not valid)

**Metrics:** Accuracy, Precision, Recall, F1, ROC-AUC

### Categorizer (Rule-based)

**Input:** Zone code + description
**Output:** Category (Residential, Commercial, Industrial, etc.) + Subtype

## 🎓 Training

See [Training Guide](training/README.md) for comprehensive documentation.

### Quick Training

```bash
# Full pipeline (data prep + training)
python -m training.train pipeline --cities 100

# Individual steps
python -m training.train prepare extractor --cities 100
python -m training.train extractor --epochs 3
python -m training.train prepare validator --cities 100
python -m training.train validator --epochs 3
```

### GCP Training (Recommended)

```bash
# Launch GCP VM training
bash training/scripts/launch_gcp_training.sh \
    --states california texas \
    --n-cities 50

# Models automatically uploaded to GCS
```

**Cost:** ~$1.50 for full training (2-3 hours)

## 📈 Evaluation

Generate metrics and dashboard cache:

```bash
python -m training.train evaluate

# Or directly
python evaluation/compute_metrics.py \
    --extractor extractor_20240301_120000 \
    --validator validator_20240301_130000
```

**Outputs:**
- `cached_metrics.json` - Overall metrics
- `cached_extractor_examples.json` - Sample predictions
- `cached_validator_examples.json` - Sample predictions
- `cached_city_comparison.json` - Per-city performance

## 🧪 Testing

```bash
# Test imports
python -c "from zoning_extract import ZoneExtractor, ZoneValidator; print('OK')"

# Test trainers
python -c "from training.trainers import ExtractorTrainer, ValidatorTrainer; print('OK')"

# Quick training test (1 epoch)
python -m training.train extractor --epochs 1
```

## 📝 Common Tasks

### Extract Zones from New City

```python
from zoning_extract import ZoningCodePipeline

pipeline = ZoningCodePipeline(
    extractor_model_path="artifacts/models/extractor",
    validator_model_path="artifacts/models/validator"
)

zones = pipeline.extract_from_ordinances("path/to/city/ordinances")
pipeline.save_to_csv(zones, "output/city_zones.csv")
```

### Retrain with More Data

```bash
# Prepare data with more cities
python -m training.train prepare extractor --cities 163
python -m training.train prepare validator --cities 163

# Train models
python -m training.train pipeline --epochs 5
```

### Evaluate Model Performance

```bash
# Generate metrics
python -m training.train evaluate

# View in dashboard
cd ../model_dashboard
python app.py
# Open http://localhost:5000
```

## 🐛 Troubleshooting

### Import Errors

**Old imports (pre-refactoring):**
```python
from src.extractor import ZoneExtractor  # ❌
```

**New imports:**
```python
from zoning_extract import ZoneExtractor  # ✅
```

### Training Data Not Found

```bash
# Prepare data first
python -m training.train prepare extractor --cities 100
python -m training.train prepare validator --cities 100
```

### CUDA/MPS Out of Memory

Training is configured for CPU by default. If using GPU and encountering OOM:

```bash
# Reduce batch size
python -m training.train extractor --batch-size 1

# Or edit training/.env.training
BATCH_SIZE=1
GRADIENT_ACCUMULATION_STEPS=16
```

### Configuration Issues

```bash
# View current configuration
python -m training.train config

# Check .env files exist
ls .env .env.example training/.env.training
```

## 📚 Documentation

- **[Training Guide](training/README.md)** - Complete training documentation
- **[Refactoring Summary](REFACTORING_SUMMARY.md)** - Recent changes and migration
- **[.env.example](.env.example)** - Configuration template

## 🔄 Recent Changes

**v2.0.0 - Major Refactoring (2024-03)**
- Renamed `src/` → `zoning_extract/` with organized subdirectories
- Created unified training CLI (`training/train.py`)
- Consolidated training infrastructure into modular trainers
- Added shared utilities module (`utils.py`)
- Fixed configuration mismatches
- Removed duplicate code (~360 lines)
- Better separation of concerns

See [REFACTORING_SUMMARY.md](REFACTORING_SUMMARY.md) for complete details.

## 🤝 Contributing

When making changes:

1. Follow the modular structure (core/, parsers/, trainers/)
2. Use shared utilities from `utils.py`
3. Update documentation if workflow changes
4. Test full pipeline before committing
5. Run verification: `python -c "from zoning_extract import *; print('OK')"`

## 📄 License

[Add license information]

## 📞 Support

For questions or issues:
1. Check documentation in `training/README.md`
2. Review `REFACTORING_SUMMARY.md` for recent changes
3. Verify configuration with `python -m training.train config`
4. Check previous session logs in `~/.claude/projects/`

---

**Note:** This is a research/development project. Model accuracy depends on training data quality and size. For production use, evaluate on your specific ordinance documents and retrain as needed.
