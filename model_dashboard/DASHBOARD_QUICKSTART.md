# Dashboard Quick Start

## Running the Web Interface

The model dashboard provides a web interface to visualize and test the zone code extraction models.

### Step 1: Install Dependencies

```bash
cd model_dashboard

# Option 1: Using uv (recommended - fast)
uv sync

# Option 2: Using pip
pip install flask transformers torch seqeval
```

### Step 2: Start the Dashboard

```bash
# From the model_dashboard directory
./start.sh

# Or run directly with Python
python app.py

# Or with uv
uv run python app.py
```

The dashboard will start at: **http://localhost:5001**

### Step 3: Open in Browser

Open your web browser and go to:
```
http://localhost:5001
```

## Dashboard Features

### 📊 Overview Tab
- **Metrics Summary**: Precision, Recall, F1 scores
- **Dataset Stats**: Training/test sizes, cities used
- **Model Info**: Current extractor and validator models

### 🔍 Extractor Examples Tab
- View token-level predictions
- Color-coded highlighting:
  - ✅ Green: Correct predictions
  - ⚠️ Yellow: Partial matches
  - ❌ Red: Incorrect predictions
- See BIO tags (B-ZONE, I-ZONE, O)

### ✓ Validator Examples Tab
- See validation decisions (Valid/Invalid)
- Confidence scores for each prediction
- Context passages used for validation
- False positives and false negatives

### 🏙️ City Comparison Tab
- Performance breakdown by city
- Compare extractor-only vs. extractor+validator pipeline
- Ground truth from Zoneomics CSV
- Identify missed zones and extra predictions

### 🧪 Live Prediction Tab
- Test models on custom text
- Real-time zone code extraction
- Token-level highlighting

## File Locations

The dashboard expects the following directory structure:

```
model/zoning_codes_extract/
├── artifacts/
│   ├── models/
│   │   ├── extractor/        # Trained extractor model
│   │   └── validator/         # Trained validator model
│   └── data/
│       ├── train.jsonl        # Training data
│       ├── test.jsonl         # Test data
│       ├── validator_train.jsonl
│       └── validator_test.jsonl
└── evaluation/
    └── cached_metrics.json    # Optional: pre-computed metrics
```

**Current paths (as configured):**
- Models: `model/zoning_codes_extract/artifacts/models/`
- Data: `model/zoning_codes_extract/artifacts/data/`
- Cached metrics: `model/zoning_codes_extract/evaluation/`

## Troubleshooting

### Dashboard won't start

**Check dependencies:**
```bash
cd model_dashboard
uv sync
```

**Check Python version:**
```bash
python --version  # Should be Python 3.12+
```

### Models not found

**Verify model paths:**
```bash
ls model/zoning_codes_extract/artifacts/models/extractor/
ls model/zoning_codes_extract/artifacts/models/validator/
```

**If models are elsewhere**, update paths in `model_dashboard/app.py` (lines 24-28):
```python
TRAINED_MODELS_DIR = MODEL_DIR / "your" / "path" / "to" / "models"
DATA_DIR = MODEL_DIR / "your" / "path" / "to" / "data"
```

### Dashboard is slow

The dashboard computes metrics on-the-fly if no cache exists.

**Generate cached metrics (recommended):**
```bash
cd model/zoning_codes_extract/evaluation
python compute_metrics.py
```

This creates cache files for instant loading:
- `cached_metrics.json` - Overall metrics
- `cached_extractor_examples.json` - Extractor predictions
- `cached_validator_examples.json` - Validator predictions
- `cached_city_comparison.json` - City-level analysis

### Port 5001 already in use

**Change the port in `app.py` (line 912):**
```python
app.run(debug=True, port=5002)  # Use different port
```

### No test data found

**Generate test data if missing:**
```bash
# Generate extractor data
python model/zoning_codes_extract/training/prepare_extractor_data.py \
  --output-dir model/zoning_codes_extract/artifacts/data \
  --max-cities 20

# Generate validator data
python model/zoning_codes_extract/training/prepare_validator_data.py \
  --output-dir model/zoning_codes_extract/artifacts/data \
  --max-cities 20 \
  --extractor-model model/zoning_codes_extract/artifacts/models/extractor
```

## API Endpoints

The dashboard also provides a REST API:

### GET /api/metrics
Get model performance metrics

**Response:**
```json
{
  "extractor": {
    "precision": 0.85,
    "recall": 0.82,
    "f1": 0.83,
    "train_examples": 1234,
    "test_examples": 234
  },
  "validator": {
    "accuracy": 0.91,
    "precision": 0.89,
    "recall": 0.87,
    "f1": 0.88
  }
}
```

### POST /api/predict
Run prediction on custom text

**Request:**
```json
{
  "text": "The R-1 zone allows single-family residential use."
}
```

**Response:**
```json
{
  "zones": ["R-1"],
  "tokens": [
    {"token": "The", "label": "O", "is_zone": false},
    {"token": "R", "label": "B-ZONE", "is_zone": true},
    {"token": "-", "label": "I-ZONE", "is_zone": true},
    {"token": "1", "label": "I-ZONE", "is_zone": true}
  ]
}
```

### Other Endpoints
- `GET /api/extractor/examples` - Extractor test examples
- `GET /api/validator/examples` - Validator test examples
- `GET /api/city-comparison` - City-level performance
- `GET /api/models` - List available models
- `POST /api/models/select` - Switch models
- `POST /api/refresh` - Reload models

## Tips

1. **Pre-compute metrics** for faster loading:
   ```bash
   cd model/zoning_codes_extract/evaluation
   python compute_metrics.py
   ```

2. **Use different models**: The dashboard can load multiple model checkpoints. Switch between them in the UI or via API.

3. **Debug mode**: Edit `app.py` to disable debug mode in production:
   ```python
   app.run(debug=False, port=5001)
   ```

4. **Performance**: The city comparison tab samples 100 examples per city. Reduce this in `app.py` (line 812) for faster loading.

## Next Steps

- Generate full dataset if you only have a small test set
- Train models on full dataset for better performance
- Pre-compute metrics for instant dashboard loading
- Explore city-level performance to identify improvement areas
