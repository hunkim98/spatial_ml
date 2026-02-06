# Zoning Code Extraction Pipeline

A 3-stage token classification pipeline for automatically extracting zoning codes from municipal ordinance documents.

## Overview

This system extracts zone codes (like R-1, C-2, I-1, etc.) from ordinance text using a three-stage approach:

1. **Extractor** (Stage 1): Token classification model (BERT) that identifies potential zone code mentions in text
2. **Validator** (Stage 2): Binary classification model (BERT) that distinguishes real zone codes from false positives
3. **Categorizer** (Stage 3): Keyword-based category assignment (Residential, Commercial, Industrial, etc.)

## Architecture

```
Ordinance Text
     ↓
[Extractor: BERT Token Classification]
  → Identifies candidate zone codes with BIO tags
  → Examples: "R-1", "C-2", "I-1" + their passages
     ↓
[Validator: BERT Binary Classification]
  → Input: Candidate code + all passages where it appears
  → Output: Real zone code vs. false positive (e.g., section reference)
  → Examples: ✓ "R-1 Zone permits..." vs. ✗ "See Appendix R-1"
     ↓
[Categorizer: Keyword Matching]
  → Assigns category and subtype
     ↓
Extracted Zone Codes (CSV)
```

## Installation

1. Install dependencies:
```bash
cd model/zoning_codes_extract
pip install -e .
```

This will install:
- `transformers` (BERT models)
- `torch` (PyTorch)
- `datasets` (HuggingFace datasets)
- `seqeval` (NER metrics)
- `pandas`, `scikit-learn`
- Existing dependencies: `python-docx`, `rapidfuzz`

## Quick Start

### 1. Prepare Training Data for Extractor

Generate BIO-tagged training data from zoneomics CSVs and municode ordinances:

```bash
cd model/zoning_codes_extract
python training/prepare_token_classification_data.py \
    --states alabama \
    --output-dir training/data
```

This will:
- Match cities between zoneomics (ground truth) and municode (ordinances)
- Find zone codes in ordinance text
- Create BIO tags for each token
- Split into train/val/test by city
- Save to JSONL files

**Output:**
- `training/data/train.jsonl`
- `training/data/val.jsonl`
- `training/data/test.jsonl`
- `training/data/stats.json`

### 2. Prepare Training Data for Validator

Generate binary classification data (real zone codes vs. false positives):

```bash
python training/prepare_validator_data.py \
    --states alabama \
    --output-dir training/data \
    --neg-pos-ratio 1.0
```

This will:
- Find all candidate codes matching zone code patterns in ordinances
- Label as positive (in ground truth) or negative (false positive)
- Balance negative and positive examples
- Split by city

**Output:**
- `training/data/validator_train.jsonl`
- `training/data/validator_val.jsonl`
- `training/data/validator_test.jsonl`
- `training/data/validator_stats.json`

### 3. Train the Extractor Model

Fine-tune BERT on the BIO-tagged data:

```bash
python training/train_extractor.py \
    --model-name bert-base-uncased \
    --data-dir training/data \
    --output-dir trained_models/extractor \
    --epochs 3 \
    --batch-size 16
```

This will:
- Load BIO-tagged training data
- Fine-tune BERT for token classification
- Evaluate on validation set each epoch
- Save best model based on F1 score

**Output:**
- `trained_models/extractor/` (trained model)
- `trained_models/extractor/test_results.json`
- `trained_models/extractor/detailed_report.json`

### 4. Train the Validator Model

Fine-tune BERT for binary classification:

```bash
python training/train_validator.py \
    --model-name bert-base-uncased \
    --data-dir training/data \
    --output-dir trained_models/validator \
    --epochs 3 \
    --batch-size 16
```

This will:
- Load validator training data
- Fine-tune BERT for binary classification
- Evaluate on validation set each epoch
- Save best model based on F1 score

**Output:**
- `trained_models/validator/` (trained model)
- `trained_models/validator/test_results.json`
- `trained_models/validator/detailed_report.json`

### 5. Evaluate the Pipeline

Test the full pipeline on the test set:

```bash
python evaluation/evaluate.py \
    --extractor-model trained_models/extractor \
    --validator-model trained_models/validator \
    --data-dir training/data \
    --output-dir evaluation/results
```

This will:
- Load test cities
- Run full 3-stage pipeline (Extractor + Validator + Categorizer)
- Compare predictions to ground truth
- Compute precision, recall, F1

**Output:**
- `evaluation/results/per_city_metrics.json`
- `evaluation/results/aggregate_metrics.json`
- `evaluation/results/summary.csv`

### 6. Use the Pipeline

Extract zone codes from a new city's ordinances:

```python
from model.zoning_codes_extract import ZoningCodePipeline

# Initialize pipeline with both trained models
pipeline = ZoningCodePipeline(
    extractor_model_path="model/zoning_codes_extract/trained_models/extractor",
    validator_model_path="model/zoning_codes_extract/trained_models/validator"
)

# Extract from ordinance directory
results = pipeline.extract_from_ordinances(
    "tmp/zoning_ordinance/az/phoenix",
    zoning_only=True
)

# Save to CSV (zoneomics format)
pipeline.save_to_csv(results, "output/phoenix.csv")
```

**Note:** If you don't have a trained validator model, you can omit `validator_model_path` and it will use a rule-based fallback validation.

## File Structure

```
model/zoning_codes_extract/
├── README.md                    # This file
├── pyproject.toml               # Dependencies
├── __init__.py                  # Public API
│
├── Core Pipeline Components:
├── extractor.py                 # Stage 1: Token classification model
├── validator.py                 # Stage 2: Binary classification model
├── categorizer.py               # Stage 3: Category assignment (rule-based)
├── pipeline.py                  # End-to-end orchestration
│
├── Utilities (kept from old system):
├── city_matcher.py              # Match zoneomics ↔ municode
├── ordinance_parser.py          # Parse DOCX files
├── text_aligner.py              # Fuzzy text matching
│
├── training/
│   ├── prepare_token_classification_data.py  # Generate BIO tags for extractor
│   ├── prepare_validator_data.py             # Generate binary labels for validator
│   ├── train_extractor.py                    # Train extractor BERT model
│   ├── train_validator.py                    # Train validator BERT model
│   └── data/                                  # Training data (generated)
│       ├── train.jsonl                        # Extractor training
│       ├── val.jsonl                          # Extractor validation
│       ├── test.jsonl                         # Extractor test
│       ├── validator_train.jsonl              # Validator training
│       ├── validator_val.jsonl                # Validator validation
│       ├── validator_test.jsonl               # Validator test
│       ├── stats.json
│       └── validator_stats.json
│
├── evaluation/
│   ├── evaluate.py              # Pipeline evaluation
│   └── results/                 # Evaluation results (generated)
│
└── trained_models/              # Trained models (generated)
    ├── extractor/               # Token classification model
    └── validator/               # Binary classification model
```

## Training Data Formats

### Extractor Training Data (BIO-tagged)

For token classification:

```json
{
  "tokens": ["The", "R", "-", "1", "Zone", "is", "for", "residential", "..."],
  "tags": ["O", "B-ZONE", "I-ZONE", "I-ZONE", "O", "O", "O", "O", "..."],
  "city": "birmingham",
  "state": "alabama"
}
```

**Tags:**
- `O`: Outside (not a zone code)
- `B-ZONE`: Begin zone code
- `I-ZONE`: Inside zone code (continuation)

### Validator Training Data (Binary Classification)

For distinguishing real zone codes from false positives:

```json
{
  "code": "R-1",
  "passages": [
    "The purpose of the R-1 Zone is to provide for single family residences...",
    "R-1 zoning district regulations are set forth in this section..."
  ],
  "label": 1,
  "city": "birmingham",
  "state": "alabama"
}
```

**Labels:**
- `1`: Valid zone code (exists in ground truth)
- `0`: False positive (pattern match but not a real zone code)

**Examples of False Positives:**
- Section references: "See Appendix R-1"
- Table labels: "Table C-2 shows..."
- Form numbers: "File Form I-1"

## Output Format

Matches zoneomics CSV format:

```csv
zone_code,zone_subtype,area_acres,description
R-1,Single Family Residential,null,"The purpose of the R-1 Zone is to provide..."
C-2,General Business,null,"The purpose of the C-2 Zone is to provide..."
I-1,Light Industrial,null,"The purpose of the I-1 Zone is to provide..."
```

## Configuration Options

### Pipeline Parameters

```python
pipeline = ZoningCodePipeline(
    extractor_model_path="path/to/model",      # Trained model
    min_validation_confidence=0.5,              # Validator threshold
    min_extraction_score=0.5,                   # Extractor threshold
    max_sample_passages=3                       # Passages to keep per zone
)
```

### Training Parameters

```python
config = TrainingConfig(
    model_name="bert-base-uncased",            # Base model
    num_epochs=3,                               # Training epochs
    batch_size=16,                              # Batch size
    learning_rate=2e-5,                         # Learning rate
    max_seq_length=512                          # Max sequence length
)
```

### Validation Rules

The validator checks:
1. **Format**: Matches zone code patterns (R-1, C-2, AG, etc.)
2. **Frequency**: Appears at least N times (default: 2)
3. **Context**: Near zoning keywords ("zone", "district", etc.)
4. **Definitional**: Has purpose statement (optional)

## Performance Metrics

Success criteria (from plan):
- **F1 > 0.80** on test set
- **Precision > 0.85** (minimize false positives)

Evaluation metrics:
- **Precision**: % of extracted codes that are correct
- **Recall**: % of ground truth codes extracted
- **F1**: Harmonic mean of precision and recall
- **Micro-averaged**: Aggregate TP/FP/FN across all cities
- **Macro-averaged**: Average metrics across cities

## Advanced Usage

### Extract from Raw Text

```python
from model.zoning_codes_extract import ZoningCodePipeline

pipeline = ZoningCodePipeline(extractor_model_path="...")

text = """
The R-1 Residential Zone is intended for single family homes.
The C-2 Commercial Zone allows retail and service uses.
"""

zones = pipeline.extract_from_text(text)

for zone in zones:
    print(f"{zone.zone_code}: {zone.zone_subtype}")
    print(f"Confidence: {zone.confidence:.2f}")
    print(f"Description: {zone.description[:100]}...")
```

### Use Individual Components

```python
from model.zoning_codes_extract import (
    ZoneExtractor,
    ZoneValidator,
    ZoneCategorizer
)

# Stage 1: Extract candidates
extractor = ZoneExtractor(model_path="...")
spans = extractor.extract(text)

# Stage 2: Validate
validator = ZoneValidator()
# ... (create CandidateZone objects)
results = validator.validate_batch(candidates)

# Stage 3: Categorize
categorizer = ZoneCategorizer()
categorized = categorizer.categorize("R-1", description)
```

## Troubleshooting

### Low Precision (too many false positives)
- Increase `min_validation_confidence` in pipeline
- Set `require_definitional=True` in validator
- Increase `min_occurrences` in validator

### Low Recall (missing codes)
- Decrease `min_extraction_score` in extractor
- Set `require_definitional=False` in validator
- Train on more diverse data

### Training Issues
- Check that training data exists in `training/data/`
- Verify GPU availability: `torch.cuda.is_available()`
- Reduce batch size if OOM errors occur
- Use `bert-base-uncased` instead of larger models

## Next Steps

1. **Expand training data**: Add more states beyond Alabama
2. **Tune hyperparameters**: Experiment with learning rates, epochs
3. **Error analysis**: Review false positives/negatives manually
4. **Deploy**: Create API or batch processing script
5. **Monitor**: Track performance on new cities

## Comparison to Old Approach

| Aspect | Old (LLM Fine-tuning) | New (Token Classification) |
|--------|----------------------|---------------------------|
| Model | GPT-4o-mini | BERT-base |
| Task | Text generation | Token classification |
| Training | OpenAI API | Local PyTorch |
| Explainability | Black box | Interpretable stages |
| Cost | Per-token API costs | One-time training |
| Inference | Slow (API calls) | Fast (local) |
| Validation | Implicit | Explicit rules |

## References

- [BERT Paper](https://arxiv.org/abs/1810.04805)
- [HuggingFace Transformers](https://huggingface.co/docs/transformers)
- [Token Classification Guide](https://huggingface.co/docs/transformers/tasks/token_classification)
- [Seqeval Metrics](https://github.com/chakki-works/seqeval)
