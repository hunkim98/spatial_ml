# Validator Data Preparation - Quick Start Guide

## Generate Full Dataset

```bash
# From project root: /Users/devraj/Documents/Development/spatial_ml

python model/zoning_codes_extract/training/prepare_validator_data.py \
  --output-dir model/zoning_codes_extract/artifacts/data/validator_full \
  --municode-dir collector/tmp/zoning_ordinance_md \
  --extractor-model model/zoning_codes_extract/artifacts/models/extractor
```

**Expected output:**
- `validator_train.jsonl` - Training examples (positives from all cities)
- `validator_val.jsonl` - Validation examples (positives + negatives from val cities)
- `validator_test.jsonl` - Test examples (positives + negatives from test cities)
- `validator_stats.json` - Dataset statistics
- `city_splits.json` - City assignments (shared with extractor)

## Generate Test Dataset (Few Cities)

```bash
python model/zoning_codes_extract/training/prepare_validator_data.py \
  --max-cities 20 \
  --output-dir model/zoning_codes_extract/artifacts/data/validator_small \
  --municode-dir collector/tmp/zoning_ordinance_md \
  --extractor-model model/zoning_codes_extract/artifacts/models/extractor
```

## Generate Positives Only (No Extractor)

```bash
python model/zoning_codes_extract/training/prepare_validator_data.py \
  --states california \
  --max-cities 5 \
  --output-dir model/zoning_codes_extract/artifacts/data/validator_pos_only \
  --municode-dir collector/tmp/zoning_ordinance_md \
  --no-extractor-negatives
```

## Inspect Generated Data

```python
import json

# Load examples
with open('model/zoning_codes_extract/artifacts/data/validator_full/validator_train.jsonl') as f:
    train_examples = [json.loads(line) for line in f]

# Check distribution
positives = sum(1 for ex in train_examples if ex['label'] == 1)
negatives = sum(1 for ex in train_examples if ex['label'] == 0)
print(f"Train: {len(train_examples)} total ({positives} pos, {negatives} neg)")

# View example
example = train_examples[0]
print(f"\nCode: {example['code']}")
print(f"Label: {example['label']} (1=positive, 0=negative)")
print(f"City: {example['city']}, {example['state']}")
print(f"Passages: {len(example['passages'])}")
print(f"Sample: {example['passages'][0][:150]}...")
```

## Verify Data Quality

### Check Label Distribution
```python
import json

for split in ['train', 'val', 'test']:
    with open(f'model/zoning_codes_extract/artifacts/data/validator_full/validator_{split}.jsonl') as f:
        examples = [json.loads(line) for line in f]

    pos = sum(1 for ex in examples if ex['label'] == 1)
    neg = sum(1 for ex in examples if ex['label'] == 0)

    print(f"{split.upper()}: {len(examples)} total ({pos} pos, {neg} neg)")
```

**Expected:**
- Train: Many positives, 0 negatives
- Val: Some positives, some negatives (from val cities)
- Test: Some positives, some negatives (from test cities)

### Check for Data Leakage
```python
import json

# Load city splits
with open('model/zoning_codes_extract/artifacts/data/validator_full/city_splits.json') as f:
    splits = json.load(f)

train_cities = set(splits['train'])

# Check negatives don't come from train cities
with open('model/zoning_codes_extract/artifacts/data/validator_full/validator_train.jsonl') as f:
    for line in f:
        ex = json.loads(line)
        if ex['label'] == 0:  # Negative
            city_key = f"{ex['state']}_{ex['city']}"
            if city_key in train_cities:
                print(f"❌ WARNING: Negative from train city: {city_key}")
```

**Expected:** No output (no negatives from training cities)

## Troubleshooting

### Error: "No extractor model available"
- Check that `--extractor-model` points to a valid model directory
- Default path: `model/zoning_codes_extract/artifacts/models/extractor`
- Train extractor first if needed

### Error: "Module not found"
- Run from project root: `/Users/devraj/Documents/Development/spatial_ml`
- Check `sys.path` includes parent modules

### Low negative count
- Normal! Negatives only come from val/test cities (held-out from extractor training)
- To increase: Use more cities or lower `--neg-pos-ratio`
- To test without negatives: Use `--no-extractor-negatives`

### Token length warning
- Normal for long ordinance documents
- Extractor chunks text automatically (512 token max with overlap)
- Warning doesn't affect results

## Configuration

### Adjust Negative/Positive Ratio
```bash
--neg-pos-ratio 2.0  # 2:1 ratio (more negatives)
--neg-pos-ratio 0.5  # 1:2 ratio (fewer negatives)
```

### Filter by State
```bash
--states california texas florida
```

### Limit Cities
```bash
--max-cities 50  # Process only first 50 matched cities
```

### Change Context Window
Modify in code:
```python
preparator = ValidatorDataPreparator(
    context_window=300,  # Smaller context (default: 500)
    max_passages_per_code=5,  # Fewer passages (default: 10)
    min_passages_per_code=1   # More lenient (default: 2)
)
```
