# Quick Reference - Zone Code Extractor Training

## Full Dataset Training (Production)

```bash
cd /Users/devraj/Documents/Development/spatial_ml/model/zoning_codes_extract

# 1. Generate all training data
python training/prepare_token_classification_data.py --output-dir training/data_full_v2
python training/prepare_negative_examples.py --output training/data_full_v2/negative.jsonl --count 4000
python training/prepare_validator_data.py --output-dir training/data_full_v2

# 2. Update DATA_DIR in train_and_evaluate.py (line 70)
# DATA_DIR = SCRIPT_DIR / "training" / "data_full_v2"

# 3. Train models (2-4 hours)
python train_and_evaluate.py

# 4. Update dashboard
python compute_metrics.py

# 5. Launch dashboard
cd ../../../model_dashboard && python app.py
# Open http://localhost:5000
```

---

## Subset Training (Quick Testing)

```bash
cd /Users/devraj/Documents/Development/spatial_ml/model/zoning_codes_extract

# 1. Generate subset data (Alabama only, ~15 min)
python training/prepare_token_classification_data.py \
  --output-dir training/data_alabama \
  --states alabama

python training/prepare_negative_examples.py \
  --output training/data_alabama/negative.jsonl \
  --count 500

python training/prepare_validator_data.py \
  --output-dir training/data_alabama \
  --states alabama

# 2. Update DATA_DIR in train_and_evaluate.py (line 70)
# DATA_DIR = SCRIPT_DIR / "training" / "data_alabama"

# 3. Train models (~30 min)
python train_and_evaluate.py

# 4. Update dashboard
python compute_metrics.py

# 5. Launch dashboard
cd ../../../model_dashboard && python app.py
```

---

## Minimal Testing (10 cities, ~10 min)

```bash
cd /Users/devraj/Documents/Development/spatial_ml/model/zoning_codes_extract

# Quick test run
python training/prepare_token_classification_data.py \
  --output-dir training/data_test \
  --states alabama \
  --max-cities 10

python training/prepare_negative_examples.py \
  --output training/data_test/negative.jsonl \
  --count 200

# Update DATA_DIR in train_and_evaluate.py to training/data_test
python train_and_evaluate.py
```

---

## Command Reference

| Task | Command |
|------|---------|
| **Prepare extractor data (full)** | `python training/prepare_token_classification_data.py --output-dir training/data_full_v2` |
| **Prepare extractor data (subset)** | `python training/prepare_token_classification_data.py --output-dir training/data_alabama --states alabama` |
| **Generate negative examples** | `python training/prepare_negative_examples.py --output training/data_full_v2/negative.jsonl --count 4000` |
| **Prepare validator data** | `python training/prepare_validator_data.py --output-dir training/data_full_v2` |
| **Train both models** | `python train_and_evaluate.py` |
| **Update dashboard** | `python compute_metrics.py` |
| **Launch dashboard** | `cd ../../../model_dashboard && python app.py` |
| **Run tests** | `python training/test_new_implementations.py` |

---

## Important Files to Edit

| File | What to Change | Line |
|------|----------------|------|
| `train_and_evaluate.py` | `DATA_DIR` path | 70 |
| `train_and_evaluate.py` | `NUM_EPOCHS` | 76 |
| `train_and_evaluate.py` | `BATCH_SIZE` | 77 |
| `train_and_evaluate.py` | Enable GPU | 605 |

---

## File Outputs

### Training Data Files
```
training/data_full_v2/
├── train.jsonl              # Extractor training examples
├── test.jsonl               # Extractor test examples
├── negative.jsonl           # Negative examples (NEW)
├── validator_train.jsonl    # Validator training examples
├── validator_test.jsonl     # Validator test examples
├── stats.json              # Dataset statistics
└── city_splits.json        # Train/test city assignments
```

### Trained Model Files
```
trained_models/
├── extractor/
│   ├── pytorch_model.bin
│   ├── config.json
│   └── tokenizer files
├── validator/
│   ├── pytorch_model.bin
│   ├── config.json
│   └── tokenizer files
├── cached_metrics.json                  # Dashboard metrics
├── cached_extractor_examples.json       # Sample predictions
├── cached_validator_examples.json       # Sample predictions
└── cached_city_comparison.json          # Per-city results
```

---

## Checking Results

### View training data statistics:
```bash
cat training/data_full_v2/stats.json | jq
```

### Check negative examples:
```bash
wc -l training/data_full_v2/negative.jsonl
head -n 1 training/data_full_v2/negative.jsonl | jq
```

### View cached metrics:
```bash
cat trained_models/cached_metrics.json | jq
```

### Launch dashboard:
```bash
cd ../../../model_dashboard
python app.py
# Open http://localhost:5000
```

---

## Troubleshooting Quick Fixes

| Problem | Quick Fix |
|---------|-----------|
| Out of memory | Reduce `BATCH_SIZE = 2` in `train_and_evaluate.py` |
| Training too slow | Use `--max-cities 10` for quick test |
| Dashboard empty | Run `python compute_metrics.py` |
| Wikipedia fetch fails | Check internet; script will use synthetic examples |
| Tests failing | Check `ZONE_CODE_PATTERN` hasn't changed |

---

## Performance Expectations

| Dataset Size | Training Time | Expected F1 | Use Case |
|--------------|--------------|-------------|----------|
| Full (163 cities) | 2-4 hours | 0.85-0.90 | Production |
| Alabama (~10 cities) | 15-30 min | 0.80-0.88 | Validation |
| Test (10 cities) | 10-15 min | 0.75-0.85 | Debugging |

**Note:** With new regex-based tagging + negative examples, precision should improve from 50-70% to 80-90%.
