# Zone Code Extractor Training Guide

This guide explains how to train the extractor and validator models on full or subset datasets, and how to update the dashboard after training.

---

## Quick Start (Full Dataset)

```bash
cd /Users/devraj/Documents/Development/spatial_ml/model/zoning_codes_extract

# 1. Generate training data (with new regex-based tagging + negative examples)
python training/prepare_token_classification_data.py --output-dir training/data_full_v2
python training/prepare_negative_examples.py --output training/data_full_v2/negative.jsonl --count 4000
python training/prepare_validator_data.py --output-dir training/data_full_v2

# 2. Train both models (update DATA_DIR in train_and_evaluate.py first)
python train_and_evaluate.py

# 3. Update dashboard metrics
python compute_metrics.py

# 4. Launch dashboard
cd ../../../model_dashboard
python app.py
# Open http://localhost:5000
```

---

## Step-by-Step Guide

### Step 1: Prepare Training Data

#### A. Extractor Training Data (Token Classification)

**Full Dataset (all states):**
```bash
python training/prepare_token_classification_data.py \
  --output-dir training/data_full_v2 \
  --tokenizer bert-base-uncased \
  --zoneomics-dir data/zoneomics \
  --municode-dir tmp/zoning_ordinance
```

**Subset (specific states):**
```bash
# Single state
python training/prepare_token_classification_data.py \
  --output-dir training/data_alabama \
  --states alabama \
  --tokenizer bert-base-uncased

# Multiple states
python training/prepare_token_classification_data.py \
  --output-dir training/data_multi_state \
  --states alabama california texas florida \
  --tokenizer bert-base-uncased

# Limited number of cities (for quick testing)
python training/prepare_token_classification_data.py \
  --output-dir training/data_small \
  --states alabama \
  --max-cities 10 \
  --tokenizer bert-base-uncased
```

**Output Files:**
- `training/data_full_v2/train.jsonl` - Training examples
- `training/data_full_v2/test.jsonl` - Test examples
- `training/data_full_v2/stats.json` - Dataset statistics
- `training/data_full_v2/city_splits.json` - City-level train/test splits

#### B. Negative Examples (NEW - prevents false positives)

Generate negative examples from Wikipedia (highways, visas, building codes):

```bash
# Default: 4000 examples
python training/prepare_negative_examples.py \
  --output training/data_full_v2/negative.jsonl \
  --count 4000

# For smaller datasets, reduce count proportionally
python training/prepare_negative_examples.py \
  --output training/data_small/negative.jsonl \
  --count 500
```

**What this does:**
- Fetches Wikipedia articles about I-5 highway, H-1B visas, building codes, etc.
- Extracts sentences with zone-code-like patterns (I-5, R-1, H-1B)
- Tags all patterns as 'O' (NOT zone codes)
- Teaches model that "I-5 freeway" ≠ zone code, but "R-1 district" = zone code

#### C. Validator Training Data (Binary Classification)

```bash
# Full dataset
python training/prepare_validator_data.py \
  --output-dir training/data_full_v2

# Subset
python training/prepare_validator_data.py \
  --output-dir training/data_alabama \
  --states alabama
```

**Output Files:**
- `training/data_full_v2/validator_train.jsonl`
- `training/data_full_v2/validator_test.jsonl`

---

### Step 2: Train Models

#### A. Update Configuration

Edit `train_and_evaluate.py` to point to your data directory:

```python
# Line 70 - Update this path
DATA_DIR = SCRIPT_DIR / "training" / "data_full_v2"  # Change to your data dir
```

#### B. Run Training

**Train both extractor and validator:**
```bash
python train_and_evaluate.py
```

**Training Parameters (edit in train_and_evaluate.py):**
- `NUM_EPOCHS = 3` - Number of training epochs
- `BATCH_SIZE = 4` - Batch size (reduce if out of memory)
- `LEARNING_RATE = 3e-5` - Learning rate
- `DATA_DIR` - Path to training data
- `OUTPUT_DIR` - Where to save trained models (default: `trained_models/`)

**Expected Output:**
- `trained_models/extractor/` - Extractor model checkpoint
- `trained_models/validator/` - Validator model checkpoint
- Training metrics logged to W&B (Weights & Biases)

**Training Time Estimates:**
- Full dataset (163 cities): 2-4 hours on CPU, 30-60 min on GPU
- Alabama only (~10 cities): 15-30 minutes
- Small subset (10 cities): 10-15 minutes

---

### Step 3: Update Dashboard Metrics

After training, pre-compute metrics for the dashboard:

```bash
python compute_metrics.py
```

**Optional: Specify model directories:**
```bash
python compute_metrics.py \
  --extractor trained_models/extractor \
  --validator trained_models/validator
```

**What this does:**
- Loads trained models
- Runs inference on test set
- Computes precision, recall, F1 scores
- Saves cached metrics to JSON files:
  - `trained_models/cached_metrics.json` - Overall metrics
  - `trained_models/cached_extractor_examples.json` - Example predictions
  - `trained_models/cached_validator_examples.json` - Example predictions
  - `trained_models/cached_city_comparison.json` - Per-city performance

**Expected Output:**
```
Computing metrics for dashboard...
Loaded extractor from: trained_models/extractor
Loaded validator from: trained_models/validator

Extractor Metrics:
  Precision: 0.85
  Recall: 0.92
  F1: 0.88

Validator Metrics:
  Accuracy: 0.94
  Precision: 0.93
  Recall: 0.96
  F1: 0.95

Saved metrics to: trained_models/cached_metrics.json
```

---

### Step 4: Launch Dashboard

```bash
cd ../../../model_dashboard
python app.py
```

Open your browser to: **http://localhost:5000**

The dashboard will show:
- Overall model performance metrics
- Per-city comparisons
- Example predictions (correct and incorrect)
- Confusion matrices
- Zone code coverage statistics

---

## Training Data Statistics

After running `prepare_token_classification_data.py`, check the statistics:

```bash
cat training/data_full_v2/stats.json
```

**Example output:**
```json
{
  "total_examples": 21806,
  "splits": {
    "train": 17445,
    "test": 4361
  },
  "num_cities": 163,
  "train_cities": 130,
  "test_cities": 33
}
```

---

## Comparing Full vs Subset Training

| Dataset | Cities | Examples | Training Time | Use Case |
|---------|--------|----------|---------------|----------|
| **Full** | 163 | ~22K | 2-4 hours | Production model |
| **Alabama** | ~10 | ~1.5K | 15-30 min | Quick validation |
| **Small (10 cities)** | 10 | ~1K | 10-15 min | Debugging/testing |

---

## Verifying the New Implementation

### Test regex-based tagging:
```bash
python training/test_new_implementations.py
```

Expected: All tests pass ✓

### Check negative examples:
```bash
# Count negative examples
wc -l training/data_full_v2/negative.jsonl

# Inspect a few
head -n 3 training/data_full_v2/negative.jsonl | jq .
```

Expected output:
```json
{
  "tokens": ["[CLS]", "the", "i", "-", "5", "corridor", ...],
  "tags": ["O", "O", "O", "O", "O", "O", ...],
  "city": "negative",
  "state": "wiki_highway"
}
```

---

## Troubleshooting

### Issue: Out of memory during training
**Solution:** Reduce batch size in `train_and_evaluate.py`:
```python
BATCH_SIZE = 2  # Reduce from 4 to 2
GRADIENT_ACCUMULATION_STEPS = 8  # Increase to maintain effective batch size
```

### Issue: Wikipedia fetch fails
**Solution:** Check internet connection. The script has a User-Agent header and should work. If still failing, the script will fall back to synthetic negative examples.

### Issue: Dashboard shows no data
**Solution:** Make sure you ran `compute_metrics.py` after training:
```bash
python compute_metrics.py
ls trained_models/cached_*.json  # Should show 4 files
```

### Issue: Training is too slow
**Solution:** Use a smaller subset for initial testing:
```bash
python training/prepare_token_classification_data.py \
  --output-dir training/data_quick_test \
  --max-cities 5
```

---

## Advanced: Custom Training Configuration

### Change model architecture:
Edit `train_and_evaluate.py`:
```python
MODEL_NAME = "distilbert-base-uncased"  # Faster, smaller
# or
MODEL_NAME = "roberta-base"  # More accurate, larger
```

### Adjust train/val/test split:
The split is done at the city level (in `city_splits.json`). To regenerate:
```bash
python training/prepare_token_classification_data.py \
  --output-dir training/data_full_v2 \
  --force-new-splits
```

### Enable GPU training:
Edit `train_and_evaluate.py` line 605:
```python
device = "cuda" if torch.cuda.is_available() else "cpu"  # Enable GPU
```

---

## Expected Improvements with New Implementation

**Before (CSV-based tagging):**
- Precision: 50-70% (many false positives)
- Inconsistent: "R-1" tagged in city A, not tagged in city B

**After (regex-based + negative examples):**
- Precision: 80-90% (fewer false positives)
- Consistent: All zone-like patterns tagged the same way
- Better at distinguishing "I-5 highway" (not a zone) from "I-1 district" (zone)

---

## Next Steps

1. Train on full dataset with new implementation
2. Compare metrics to baseline (old model)
3. If improved, deploy to production
4. If not improved, investigate edge cases in test set

For questions or issues, check:
- Test suite: `python training/test_new_implementations.py`
- Training logs: W&B dashboard at https://wandb.ai
- Model outputs: `trained_models/` directory
