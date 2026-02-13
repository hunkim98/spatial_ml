# Model Dashboard - Quick Start Guide

Web interface for visualizing zone code extraction model performance.

## Features

- **Overview Metrics**: Precision, Recall, F1 scores for both extractor and validator
- **Extractor Examples**: View BIO-tagged predictions with token-level highlighting
- **Validator Examples**: See validation decisions with confidence scores
- **City Comparison**: Compare model performance across different cities
- **Live Predictions**: Test the models on custom text input
- **Model Selection**: Switch between different trained model checkpoints

## Setup

### 1. Install Dependencies

```bash
cd model_dashboard

# Using uv (recommended)
uv sync

# Or using pip
pip install -r requirements.txt  # if you have requirements.txt
# Or manually:
pip install flask transformers torch seqeval
```

### 2. Update Model Paths (if needed)

The dashboard expects models and data at these locations:

```
model/zoning_codes_extract/
├── trained_models/          # Trained model checkpoints
│   ├── extractor/           # Extractor model
│   ├── validator/           # Validator model
│   ├── cached_metrics.json  # Pre-computed metrics (optional, for speed)
│   └── ...
└── training/
    └── data_full/           # Training/test data
        ├── train.jsonl
        ├── test.jsonl
        ├── validator_train.jsonl
        └── validator_test.jsonl
```

**If your models are in `artifacts/models/`:**

Create symlinks or update paths in `app.py`:

```bash
# Option 1: Create symlinks
cd model/zoning_codes_extract
ln -s artifacts/models trained_models
ln -s artifacts/data training/data_full

# Option 2: Edit app.py and change:
# TRAINED_MODELS_DIR = MODEL_DIR / "artifacts" / "models"
# DATA_DIR = MODEL_DIR / "artifacts" / "data"
```

### 3. Run the Dashboard

```bash
cd model_dashboard

# Using Python directly
python app.py

# Or using uv
uv run python app.py
```

The dashboard will start at: **http://localhost:5001**

## Usage

### Main Dashboard

Open http://localhost:5001 in your browser to see:

1. **Metrics Overview**
   - Extractor: Precision, Recall, F1
   - Validator: Accuracy, Precision, Recall, F1, Confusion Matrix
   - Training/test dataset sizes
   - Cities used for training/testing

2. **Extractor Examples** Tab
   - View token-level predictions
   - Color-coded highlighting:
     - Green: Correct zone code prediction
     - Yellow: Partial match
     - Red: Incorrect prediction
   - See which tokens are tagged as B-ZONE / I-ZONE

3. **Validator Examples** Tab
   - See validation decisions (Valid/Invalid)
   - Confidence scores
   - False positives and false negatives
   - Context passages used for validation

4. **City Comparison** Tab
   - Performance breakdown by city
   - Compare extractor-only vs. extractor+validator
   - See CSV ground truth codes
   - Identify missed zones and false positives

5. **Live Prediction** Tab
   - Enter custom ordinance text
   - See real-time zone code extraction
   - Token-level highlighting

### API Endpoints

The dashboard also provides a REST API:

- `GET /api/metrics` - Get model performance metrics
- `GET /api/extractor/examples` - Get extractor test examples
- `GET /api/validator/examples` - Get validator test examples
- `GET /api/city-comparison` - Get city-level performance
- `POST /api/predict` - Run prediction on custom text
- `GET /api/models` - List available models
- `POST /api/models/select` - Switch to different models
- `POST /api/refresh` - Reload models from disk

## Performance Optimization

### Pre-compute Metrics (Recommended)

The dashboard loads pre-computed metrics from cache files for instant loading:

```bash
# Generate cached metrics (if compute_metrics.py exists)
cd model/zoning_codes_extract/evaluation
python compute_metrics.py

# This creates:
# - trained_models/cached_metrics.json
# - trained_models/cached_extractor_examples.json
# - trained_models/cached_validator_examples.json
# - trained_models/cached_city_comparison.json
```

Without cached metrics, the dashboard will compute them on-the-fly (slow).

## Troubleshooting

### Error: "No module named 'flask'"
```bash
cd model_dashboard
uv sync
# or
pip install flask transformers torch seqeval
```

### Error: "Models not found"
Check that models exist at:
- `model/zoning_codes_extract/trained_models/extractor/`
- `model/zoning_codes_extract/trained_models/validator/`

Or update `TRAINED_MODELS_DIR` path in `app.py`.

### Error: "Test data not found"
Check that test data exists at:
- `model/zoning_codes_extract/training/data_full/test.jsonl`
- `model/zoning_codes_extract/training/data_full/validator_test.jsonl`

Or update `DATA_DIR` path in `app.py`.

### Dashboard is slow
- Pre-compute metrics using `compute_metrics.py`
- Reduce number of examples loaded (edit `app.py`)
- Limit cities in city comparison (currently samples 100 examples per city)

### Port 5001 already in use
Change the port in `app.py`:
```python
app.run(debug=True, port=5002)  # Use different port
```

## Configuration

### Change Model Paths

Edit `app.py` (lines 24-28):

```python
BASE_DIR = Path(__file__).parent.parent
MODEL_DIR = BASE_DIR / "model" / "zoning_codes_extract"
TRAINED_MODELS_DIR = MODEL_DIR / "artifacts" / "models"  # Change this
DATA_DIR = MODEL_DIR / "artifacts" / "data"              # Change this
```

### Adjust Example Limits

Edit `app.py`:

```python
# Line 606: Limit extractor examples
for i, ex in enumerate(extractor_data[:50]):  # Change 50 to show more/fewer

# Line 812: Limit city comparison samples
sample_size = min(100, len(city_examples))  # Change 100 to sample more/fewer
```

### Enable/Disable Debug Mode

Edit `app.py` (line 912):

```python
app.run(debug=True, port=5001)  # debug=False for production
```

## Development

### Project Structure

```
model_dashboard/
├── app.py                  # Flask application
├── templates/
│   └── index.html         # Dashboard UI
├── pyproject.toml         # Dependencies
└── README.md              # This file
```

### Adding New Features

The dashboard uses a REST API + single-page app architecture:
- Backend: Flask (app.py) provides JSON APIs
- Frontend: HTML/JavaScript (templates/index.html) with fetch() calls
- Models: PyTorch + Transformers for inference

To add a new tab or feature:
1. Add API endpoint in `app.py` (e.g., `@app.route('/api/new-feature')`)
2. Add UI in `templates/index.html`
3. Connect with JavaScript `fetch()` call

## Credits

- Framework: Flask
- ML: PyTorch, Transformers (Hugging Face)
- Evaluation: seqeval
