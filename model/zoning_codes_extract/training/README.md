# Zone Code Extraction Model Training

Complete training guide for the zone code extraction system's two BERT-based models.

## 📋 Table of Contents

- [Overview](#overview)
- [Quick Start](#quick-start)
- [Training CLI](#training-cli)
- [Configuration](#configuration)
- [Data Preparation](#data-preparation)
- [Model Training](#model-training)
- [Evaluation](#evaluation)
- [GCP Training](#gcp-training)
- [Troubleshooting](#troubleshooting)

## 🎯 Overview

The system consists of two models trained sequentially:

1. **Extractor** (Token Classification)
   - Identifies zone codes in text using BIO tagging
   - Input: Ordinance text passage
   - Output: BIO tags (B-ZONE, I-ZONE, O) for each token
   - Primary metric: Recall (maximize detection)

2. **Validator** (Sequence Classification)
   - Filters false positives from extractor
   - Input: Zone code + supporting passages
   - Output: Binary classification (valid/invalid)
   - Primary metric: F1 (balance precision/recall)

## 🚀 Quick Start

### Option 1: Full Pipeline (Recommended)

Train both models with one command:

```bash
# Default settings (100 cities, 3 epochs)
python -m training.train pipeline

# Custom settings
python -m training.train pipeline \
    --epochs 5 \
    --batch-size 4 \
    --learning-rate 5e-5
```

**What it does:**
1. Prepares extractor data (if needed)
2. Trains extractor model
3. Prepares validator data using trained extractor
4. Trains validator model

**Time:** ~2-3 hours on CPU for 100 cities, 3 epochs

### Option 2: Step-by-Step

```bash
# 1. Prepare data
python -m training.train prepare extractor --cities 100
python -m training.train prepare validator --cities 100

# 2. Train models
python -m training.train extractor --epochs 3
python -m training.train validator --epochs 3

# 3. Evaluate
python -m training.train evaluate
```

### Option 3: GCP VM Training (Cost-Effective)

```bash
# Launch GCP VM with automatic training
bash scripts/launch_gcp_training.sh \
    --states california texas \
    --n-cities 50

# Models automatically uploaded to GCS
```

**Cost:** ~$1.50 for full training (~2-3 hours on n1-highmem-8)

## 🖥️ Training CLI

### Main Commands

```bash
# Show current configuration
python -m training.train config

# Train extractor
python -m training.train extractor [OPTIONS]

# Train validator
python -m training.train validator [OPTIONS]

# Train both sequentially
python -m training.train pipeline [OPTIONS]

# Prepare data
python -m training.train prepare {extractor|validator} [OPTIONS]

# Evaluate models
python -m training.train evaluate [OPTIONS]
```

### Common Options

```bash
--epochs N              # Number of training epochs (default: from config)
--batch-size N          # Batch size per device (default: 2)
--learning-rate FLOAT   # Learning rate (default: 3e-5)
--metric {f1,recall,precision,accuracy}  # Metric to highlight
--cities N              # Number of cities for data prep
```

### Examples

```bash
# Quick test (1 epoch, 10 cities)
python -m training.train prepare extractor --cities 10
python -m training.train extractor --epochs 1

# Production training
python -m training.train pipeline \
    --epochs 5 \
    --batch-size 4 \
    --learning-rate 3e-5

# Override specific model
python -m training.train validator \
    --epochs 10 \
    --metric accuracy

# Evaluate specific models
python -m training.train evaluate \
    --extractor extractor_20240301_120000 \
    --validator validator_20240301_130000
```

## ⚙️ Configuration

### Configuration Files

**`.env`** (infrastructure - NOT committed):
```bash
# GCP/GCS
GCP_PROJECT=your-project
GCS_BUCKET_NAME=your-bucket
GOOGLE_APPLICATION_CREDENTIALS=/path/to/key.json

# W&B
WANDB_API_KEY=your-key
WANDB_PROJECT=zoning-code-extraction
WANDB_ENTITY=your-team

# GCS Upload
UPLOAD_TO_GCS=1  # Enable model upload to GCS
```

**`training/.env.training`** (hyperparameters - committed):
```bash
# Model Configuration
MODEL_NAME=bert-base-uncased
SEED=42
MAX_SEQ_LENGTH=512

# Training Hyperparameters
NUM_EPOCHS=3
BATCH_SIZE=2
GRADIENT_ACCUMULATION_STEPS=8  # Effective batch size: 16
LEARNING_RATE=3e-5
WEIGHT_DECAY=0.01
WARMUP_STEPS=50

# Data Preparation
TRAIN_RATIO=0.85
TEST_RATIO=0.15
CONTEXT_WINDOW=500

# Inference Parameters
MIN_EXTRACTION_SCORE=0.5
MIN_VALIDATION_CONFIDENCE=0.5
EXTRACTOR_OVERLAP=128
VALIDATOR_MAX_PASSAGES=5

# Model-Specific
EXTRACTOR_METRIC=recall
VALIDATOR_METRIC=f1
VALIDATOR_NEG_POS_RATIO=1.0

# Advanced
GRADIENT_CHECKPOINTING=1
PRECISION=none  # none, fp16, bf16
```

### Configuration Hierarchy

1. **Default values** in `utils/config.py`
2. **`.env.training` file** (hyperparameters)
3. **CLI arguments** (runtime overrides)

**Example:**
```bash
# .env.training has NUM_EPOCHS=3
# This overrides to 5
python -m training.train extractor --epochs 5
```

## 📊 Data Preparation

### Extractor Data

Generates BIO-tagged training data from zoneomics CSVs and ordinance text.

```bash
python -m training.train prepare extractor [OPTIONS]
```

**Options:**
- `--cities N` - Number of cities to include (default: 100)
- `--output-dir PATH` - Output directory (default: training/data)

**What it does:**
1. Matches cities between zoneomics and ordinance data
2. Parses ordinance documents
3. Aligns zone codes with ordinance text using fuzzy matching
4. Creates BIO tags for each token
5. Splits by city into train/test sets
6. Saves to JSONL format

**Output:**
```
training/data/
├── train_extractor.jsonl       # Training examples
├── test_extractor.jsonl        # Test examples
└── city_splits.json            # City-level splits
```

**Example format:**
```json
{
  "tokens": ["The", "R", "-", "1", "Zone", "permits", "..."],
  "tags": ["O", "B-ZONE", "I-ZONE", "I-ZONE", "O", "O", "..."],
  "city": "birmingham",
  "state": "alabama"
}
```

### Validator Data

Generates binary classification data using the trained extractor to find false positives.

```bash
python -m training.train prepare validator [OPTIONS]
```

**Requirements:**
- Must have trained extractor model
- Extractor data must be prepared

**What it does:**
1. Uses trained extractor to find all zone code candidates
2. Labels as positive (in ground truth) or negative (false positive)
3. Balances negative/positive ratio
4. Splits by city
5. Saves to JSONL format

**Output:**
```
training/data/
├── train_validator.jsonl       # Training examples
└── test_validator.jsonl        # Test examples
```

**Example format:**
```json
{
  "code": "R-1",
  "passages": ["The R-1 Zone permits...", "R-1 properties must..."],
  "label": 1,
  "city": "birmingham",
  "state": "alabama"
}
```

### City-Level Splitting

All data splits are done at the **city level** to prevent data leakage:
- Examples from the same city always stay together
- Train/test split is 85%/15% by default
- Splits are cached in `city_splits.json` for consistency

## 🎓 Model Training

### Extractor Training

```bash
python -m training.train extractor [OPTIONS]
```

**Architecture:**
- Base: `bert-base-uncased`
- Task: Token classification (3 labels: O, B-ZONE, I-ZONE)
- Training: Fine-tuning with cross-entropy loss

**Key Features:**
- Custom tokenization (optional) to prevent zone code fragmentation
- Entity-level metrics using seqeval
- Gradient checkpointing for memory efficiency
- WandB logging (if API key provided)
- GCS upload (if enabled)

**Training output:**
```
artifacts/models/extractor_YYYYMMDD_HHMMSS/
├── config.json                 # Model configuration
├── model.safetensors          # Model weights
├── tokenizer.json             # Tokenizer
├── test_results.json          # Test set metrics
└── training_args.bin          # Training arguments
```

**Metrics:**
- **Precision**: Entity-level precision
- **Recall**: Entity-level recall (PRIMARY)
- **F1**: Entity-level F1
- Per-tag metrics (B-ZONE, I-ZONE, O)
- Token-level accuracy

### Validator Training

```bash
python -m training.train validator [OPTIONS]
```

**Architecture:**
- Base: `bert-base-uncased`
- Task: Sequence classification (2 labels: 0=invalid, 1=valid)
- Input format: `[CODE] zone_code [SEP] passage1 [SEP] passage2 ...`

**Key Features:**
- Balanced negative/positive examples
- Comprehensive binary classification metrics
- ROC-AUC scoring
- Confusion matrix logging to WandB

**Training output:**
```
artifacts/models/validator_YYYYMMDD_HHMMSS/
├── config.json
├── model.safetensors
├── tokenizer.json
├── test_results.json
└── training_args.bin
```

**Metrics:**
- **Accuracy**: Overall classification accuracy
- **Precision**: Positive class precision
- **Recall**: Positive class recall
- **F1**: Positive class F1 (PRIMARY)
- **ROC-AUC**: Area under ROC curve
- False positive/negative rates

### Training Callbacks

Both models use a unified callback system:

**MPSMemoryCallback:**
- Clears GPU/MPS cache periodically
- Prevents memory buildup during training

**UnifiedProgressCallback:**
- Live training progress with ETA
- Per-epoch summaries
- Evaluation metrics display
- Highlights best model based on metric

### Experiment Tracking

**Weights & Biases (W&B):**
```bash
# Set API key in .env
WANDB_API_KEY=your-key

# Training automatically logs to W&B
python -m training.train extractor
```

**Logged metrics:**
- Training/validation loss
- Evaluation metrics
- Confusion matrices
- Learning rate schedule
- System metrics (GPU, memory)

## 📈 Evaluation

### Generate Metrics

```bash
python -m training.train evaluate [OPTIONS]
```

**Options:**
- `--extractor NAME` - Extractor model name (default: "extractor")
- `--validator NAME` - Validator model name (default: "validator")
- `--skip-city-comparison` - Skip city-level comparison (faster)

**What it computes:**
1. Overall extractor metrics (precision, recall, F1)
2. Overall validator metrics (accuracy, precision, recall, F1)
3. Per-city performance comparison
4. Sample predictions for dashboard

**Output:**
```
artifacts/models/
├── cached_metrics.json              # Overall metrics
├── cached_extractor_examples.json   # Sample predictions
├── cached_validator_examples.json   # Sample predictions
└── cached_city_comparison.json      # Per-city performance
```

### View in Dashboard

```bash
cd ../model_dashboard
python app.py
# Open http://localhost:5000
```

Dashboard displays:
- Model performance metrics
- Sample predictions
- Per-city comparison
- Confusion matrices

## ☁️ GCP Training

### Launch GCP VM Training

```bash
bash scripts/launch_gcp_training.sh [OPTIONS]
```

**Options:**
- `--states STATE1 STATE2 ...` - Specific states to process
- `--all-states` - Process all available states
- `--n-cities N` - Number of cities per state
- `--preemptible` - Use preemptible VM (70% cost savings)

**What it does:**
1. Creates GCP VM (n1-highmem-8 by default)
2. Installs dependencies
3. Clones repository
4. Downloads data from GCS (if available)
5. Runs training pipeline
6. Uploads models to GCS
7. Shuts down VM automatically

**Example:**
```bash
# Train on California and Texas (50 cities each)
bash scripts/launch_gcp_training.sh \
    --states california texas \
    --n-cities 50

# Train on all states with preemptible VM
bash scripts/launch_gcp_training.sh \
    --all-states \
    --preemptible
```

**Cost estimate:**
- n1-highmem-8: ~$0.50/hour
- Full training: ~2-3 hours = ~$1.50
- Preemptible: ~$0.15/hour = ~$0.45 total

### Manual GCP Setup

```bash
# SSH into VM
gcloud compute ssh training-vm

# Clone repo
git clone <repo-url>
cd spatial_ml/model/zoning_codes_extract

# Install dependencies
pip install -e .

# Train
python -m training.train pipeline

# Upload to GCS (if UPLOAD_TO_GCS=1 in .env)
```

## 🐛 Troubleshooting

### Training Data Not Found

```bash
# Error: FileNotFoundError: Training data not found
# Solution: Prepare data first
python -m training.train prepare extractor --cities 100
```

### Extractor Required for Validator Data

```bash
# Error: No trained extractor found
# Solution: Train extractor first
python -m training.train extractor
```

### Out of Memory

```bash
# Reduce batch size
python -m training.train extractor --batch-size 1

# Or edit .env.training
BATCH_SIZE=1
GRADIENT_ACCUMULATION_STEPS=16  # Keep effective batch size
```

### Import Errors

```bash
# Error: No module named 'training'
# Solution: Run from correct directory
cd /path/to/spatial_ml/model/zoning_codes_extract
python -m training.train config
```

### WandB Not Logging

```bash
# Check API key is set
echo $WANDB_API_KEY

# Or in .env
cat .env | grep WANDB_API_KEY

# Test WandB
python -c "import wandb; wandb.init(project='test')"
```

### GCS Upload Fails

```bash
# Check credentials
echo $GOOGLE_APPLICATION_CREDENTIALS

# Test GCS access
gsutil ls gs://your-bucket/

# Enable upload
export UPLOAD_TO_GCS=1
```

### Configuration Issues

```bash
# View current config
python -m training.train config

# Check .env files
ls -la .env .env.example training/.env.training

# Test config loading
python -c "from training.utils.config import get_config; print(get_config().model_name)"
```

## 📊 Advanced Topics

### Custom Tokenization

Enable zone-aware tokenization to prevent code fragmentation:

```bash
# In .env.training
USE_CUSTOM_TOKENIZATION=1
```

This protects zone codes like "R-1-A" from being split into ["R", "-", "1", "-", "A"].

### Hyperparameter Tuning

Edit `training/.env.training`:

```bash
# Larger model
MODEL_NAME=bert-large-uncased

# More aggressive training
LEARNING_RATE=5e-5
NUM_EPOCHS=5
BATCH_SIZE=4

# Stronger regularization
WEIGHT_DECAY=0.05
WARMUP_STEPS=100
```

### Data Augmentation

```bash
# Increase context window for more context
CONTEXT_WINDOW=750

# Adjust validator negative/positive ratio
VALIDATOR_NEG_POS_RATIO=2.0  # 2x negatives per positive
```

### Performance Optimization

```bash
# Enable mixed precision (requires compatible GPU)
PRECISION=fp16

# Increase workers (if enough RAM)
DATALOADER_WORKERS=4

# Enable memory optimizations
GRADIENT_CHECKPOINTING=1
PIN_MEMORY=1
```

## 📚 Additional Resources

### Documentation
- **[Main README](../README.md)** - Project overview
- **[Refactoring Summary](../REFACTORING_SUMMARY.md)** - Recent changes
- **[.env.example](../.env.example)** - Configuration template

### Training Modules
- **`trainers/base.py`** - Shared training infrastructure
- **`trainers/extractor.py`** - Extractor-specific training
- **`trainers/validator.py`** - Validator-specific training
- **`utils/config.py`** - Configuration management

### Legacy Documentation
Some older guides are still available for reference:
- `GCP_VM_TRAINING.md` - GCP VM setup (being updated)
- `GCS_MODEL_STORAGE.md` - GCS model management (being updated)
- `HYPERPARAMETERS.md` - Hyperparameter reference (now in .env.training)

## 🎯 Best Practices

### Development Workflow

1. **Start small:** Test with 10 cities, 1 epoch
2. **Validate:** Check metrics match expectations
3. **Scale up:** Increase to 100 cities, 3 epochs
4. **Production:** Full 163 cities, 5+ epochs

### Training Tips

- **Monitor W&B:** Track training progress in real-time
- **Save checkpoints:** Training saves best model automatically
- **Compare metrics:** Always compare before/after changes
- **Use GCP:** For large-scale training (cost-effective)
- **Test locally:** Validate changes with small runs first

### Data Quality

- **City-level splits:** Prevents data leakage
- **Balanced classes:** Especially important for validator
- **Clean data:** Review examples with low scores
- **Diverse training:** Include cities from multiple states

## 🤝 Contributing

When making training changes:

1. Test with small dataset first (10 cities, 1 epoch)
2. Compare metrics with baseline
3. Update configuration if needed
4. Update this README if workflow changes
5. Test full pipeline before committing

---

**For questions or issues:**
1. Check this guide and main README
2. Review error messages carefully
3. Test with `python -m training.train config`
4. Check previous session logs in `~/.claude/projects/`
