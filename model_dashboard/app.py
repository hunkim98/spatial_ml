#!/usr/bin/env python3
"""
Model Dashboard - Web interface for zone code extraction model evaluation.

Performance: This dashboard loads pre-computed metrics from cached JSON files
for instant loading. Run `python compute_metrics.py` after training to regenerate.
"""

import csv
import json
import os
from pathlib import Path
from flask import Flask, render_template, jsonify, request
import torch
import numpy as np
from transformers import (
    AutoTokenizer,
    AutoModelForTokenClassification,
    AutoModelForSequenceClassification,
)
from dotenv import load_dotenv

# Load environment variables
ENV_FILE = Path(__file__).parent.parent / "model" / "zoning_codes_extract" / ".env"
if ENV_FILE.exists():
    load_dotenv(ENV_FILE)

app = Flask(__name__)

# Paths
BASE_DIR = Path(__file__).parent.parent
MODEL_DIR = BASE_DIR / "model" / "zoning_codes_extract"
TRAINED_MODELS_DIR = MODEL_DIR / "artifacts" / "models"
DATA_DIR = MODEL_DIR / "training" / "data"  # New data location

# Cached metrics files
CACHED_METRICS_FILE = TRAINED_MODELS_DIR / "cached_metrics.json"
CACHED_EXTRACTOR_EXAMPLES_FILE = TRAINED_MODELS_DIR / "cached_extractor_examples.json"
CACHED_VALIDATOR_EXAMPLES_FILE = TRAINED_MODELS_DIR / "cached_validator_examples.json"
CACHED_CITY_COMPARISON_FILE = TRAINED_MODELS_DIR / "cached_city_comparison.json"


def ensure_cache_files():
    """Download cache files from GCS if USE_GCS_MODELS is enabled and files don't exist locally."""
    use_gcs = os.getenv("USE_GCS_MODELS", "0") == "1"

    if not use_gcs:
        return

    # Check if any cache files are missing
    cache_files = [
        CACHED_METRICS_FILE,
        CACHED_EXTRACTOR_EXAMPLES_FILE,
        CACHED_VALIDATOR_EXAMPLES_FILE,
        CACHED_CITY_COMPARISON_FILE,
    ]

    missing_files = [f for f in cache_files if not f.exists()]

    if missing_files:
        try:
            print("Downloading cache files from GCS...")
            # Import GCS model manager
            import sys
            sys.path.append(str(MODEL_DIR / "training" / "utils"))
            from gcs_model_manager import GCSModelManager

            manager = GCSModelManager()
            manager.download_cache_files(
                cache_dir=TRAINED_MODELS_DIR,
                force_download=False
            )
        except Exception as e:
            print(f"Warning: Failed to download cache files from GCS: {e}")
            print("Dashboard will use local cache files if available")

# Label mappings
EXTRACTOR_LABELS = ['O', 'B-ZONE', 'I-ZONE']
EXTRACTOR_ID_TO_LABEL = {i: l for i, l in enumerate(EXTRACTOR_LABELS)}
EXTRACTOR_LABEL_TO_ID = {l: i for i, l in enumerate(EXTRACTOR_LABELS)}


def normalize_zone_code(code: str) -> str:
    """Normalize zone code by removing hyphens/spaces and uppercasing."""
    return code.replace('-', '').replace(' ', '').upper()


def load_csv_zone_codes(state: str, city: str) -> set:
    """
    Load zone codes from Zoneomics CSV file.

    Returns normalized zone codes from the CSV.
    """
    # Map state abbreviations to full names (kebab-cased)
    state_map = {
        'al': 'alabama', 'ak': 'alaska', 'az': 'arizona', 'ar': 'arkansas',
        'ca': 'california', 'co': 'colorado', 'ct': 'connecticut', 'de': 'delaware',
        'fl': 'florida', 'ga': 'georgia', 'hi': 'hawaii', 'id': 'idaho',
        'il': 'illinois', 'in': 'indiana', 'ia': 'iowa', 'ks': 'kansas',
        'ky': 'kentucky', 'la': 'louisiana', 'me': 'maine', 'md': 'maryland',
        'ma': 'massachusetts', 'mi': 'michigan', 'mn': 'minnesota', 'ms': 'mississippi',
        'mo': 'missouri', 'mt': 'montana', 'ne': 'nebraska', 'nv': 'nevada',
        'nh': 'new-hampshire', 'nj': 'new-jersey', 'nm': 'new-mexico', 'ny': 'new-york',
        'nc': 'north-carolina', 'nd': 'north-dakota', 'oh': 'ohio', 'ok': 'oklahoma',
        'or': 'oregon', 'pa': 'pennsylvania', 'ri': 'rhode-island', 'sc': 'south-carolina',
        'sd': 'south-dakota', 'tn': 'tennessee', 'tx': 'texas', 'ut': 'utah',
        'vt': 'vermont', 'va': 'virginia', 'wa': 'washington', 'wv': 'west-virginia',
        'wi': 'wisconsin', 'wy': 'wyoming'
    }

    # Normalize state to kebab-case folder name
    state_lower = state.lower()
    if state_lower in state_map:
        state_folder = state_map[state_lower]
    else:
        # Assume it's already a full name, convert to kebab-case
        state_folder = state_lower.replace(' ', '-')

    # Normalize city to kebab-case filename
    city_filename = city.lower().replace(' ', '-') + '.csv'

    csv_path = BASE_DIR / "data" / "zoneomics" / state_folder / city_filename

    if not csv_path.exists():
        return set()

    zone_codes = set()
    try:
        with open(csv_path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                code = row.get('zone_code', '')
                if code:
                    zone_codes.add(normalize_zone_code(code))
    except Exception:
        pass

    return zone_codes

# Global model cache
models = {
    'extractor': None,
    'validator': None,
    'tokenizer': None,
}

# Current model names (can be overridden by environment variables)
current_extractor_model = os.getenv("EXTRACTOR_MODEL_NAME", "extractor_20260221_162851")
current_validator_model = os.getenv("VALIDATOR_MODEL_NAME", "validator_20260221_191608")


def get_model_path(model_type: str, model_name: str) -> Path:
    """
    Get path to model, downloading from GCS if USE_GCS_MODELS is enabled.

    Args:
        model_type: 'extractor' or 'validator'
        model_name: Model name (e.g., 'extractor_20260221_162851')

    Returns:
        Path to local model directory
    """
    # Check if GCS models are enabled
    use_gcs = os.getenv("USE_GCS_MODELS", "0") == "1"

    if use_gcs:
        try:
            # Import GCS model manager
            import sys
            sys.path.append(str(MODEL_DIR / "training" / "utils"))
            from gcs_model_manager import download_model_from_gcs

            # Extract timestamp from model name
            timestamp = model_name.split('_', 1)[-1] if '_' in model_name else None

            # Download from GCS
            print(f"Downloading {model_type} model from GCS...")
            model_path = download_model_from_gcs(
                model_type=model_type,
                timestamp=timestamp,
                cache_dir=TRAINED_MODELS_DIR
            )

            if model_path:
                return model_path
            else:
                print(f"Failed to download from GCS, falling back to local model")

        except Exception as e:
            print(f"Error downloading from GCS: {e}")
            print("Falling back to local model")

    # Use local model
    return TRAINED_MODELS_DIR / model_name


def load_models(extractor_name=None, validator_name=None, force_reload=False):
    """Load trained models.

    Args:
        extractor_name: Name of extractor model to load (default: use current)
        validator_name: Name of validator model to load (default: use current)
        force_reload: Force reload even if models are already loaded
    """
    global current_extractor_model, current_validator_model

    if extractor_name:
        current_extractor_model = extractor_name
    if validator_name:
        current_validator_model = validator_name

    if models['tokenizer'] is None or force_reload:
        # Get model paths (potentially from GCS)
        extractor_path = get_model_path('extractor', current_extractor_model)
        validator_path = get_model_path('validator', current_validator_model)

        if extractor_path.exists():
            models['tokenizer'] = AutoTokenizer.from_pretrained(str(extractor_path))
            models['extractor'] = AutoModelForTokenClassification.from_pretrained(str(extractor_path))
            models['extractor'].eval()
            print(f"Loaded extractor from {extractor_path}")

        if validator_path.exists():
            models['validator'] = AutoModelForSequenceClassification.from_pretrained(str(validator_path))
            models['validator'].eval()
            print(f"Loaded validator from {validator_path}")


def load_test_data():
    """Load test data for visualization."""
    extractor_data = []
    validator_data = []
    
    # Load extractor test data
    extractor_test_file = DATA_DIR / "test_extractor.jsonl"
    if extractor_test_file.exists():
        with open(extractor_test_file) as f:
            for line in f:
                ex = json.loads(line)
                extractor_data.append(ex)

    # Load validator test data
    validator_test_file = DATA_DIR / "test_validator.jsonl"
    if validator_test_file.exists():
        with open(validator_test_file) as f:
            for line in f:
                ex = json.loads(line)
                validator_data.append(ex)
    
    return extractor_data, validator_data


def extract_zones_from_bio(tokens, labels):
    """Extract zone code strings from BIO-tagged sequence."""
    zones = []
    current_zone = []
    
    for token, label in zip(tokens, labels):
        if label == 'B-ZONE':
            if current_zone:
                zones.append(''.join(current_zone).replace('##', '').strip())
            current_zone = [token]
        elif label == 'I-ZONE' and current_zone:
            current_zone.append(token)
        else:
            if current_zone:
                zones.append(''.join(current_zone).replace('##', '').strip())
                current_zone = []
    
    if current_zone:
        zones.append(''.join(current_zone).replace('##', '').strip())
    
    # Clean up special tokens and artifacts
    zones = [z for z in zones if z not in ['[CLS]', '[SEP]', '[PAD]', '[UNK]', '']]
    return zones


def predict_extractor(tokens):
    """Run extractor model on tokens."""
    if models['extractor'] is None or models['tokenizer'] is None:
        return []
    
    # Convert tokens to input_ids
    input_ids = models['tokenizer'].convert_tokens_to_ids(tokens)
    inputs = torch.tensor([input_ids])
    
    with torch.no_grad():
        outputs = models['extractor'](inputs)
        predictions = torch.argmax(outputs.logits, dim=2)
    
    pred_labels = [EXTRACTOR_ID_TO_LABEL[p.item()] for p in predictions[0]]
    return pred_labels[:len(tokens)]


def predict_validator(code, passages):
    """Run validator model on code + passages."""
    if models['validator'] is None or models['tokenizer'] is None:
        return 0.5, "Unknown"
    
    # Prepare input
    combined_passages = " [SEP] ".join(passages[:5])
    input_text = f"[CODE] {code} [SEP] {combined_passages}"
    
    inputs = models['tokenizer'](
        input_text,
        truncation=True,
        max_length=512,
        return_tensors="pt"
    )
    
    with torch.no_grad():
        outputs = models['validator'](**inputs)
        probs = torch.softmax(outputs.logits, dim=1)
    
    valid_prob = probs[0][1].item()
    prediction = "Valid" if valid_prob >= 0.5 else "Invalid"
    
    return valid_prob, prediction


@app.route('/')
def index():
    """Main dashboard page."""
    return render_template('index.html')


def load_trainer_state(model_name: str) -> dict:
    """Load trainer state and extract best metrics."""
    model_path = TRAINED_MODELS_DIR / model_name

    # Find the latest checkpoint with trainer_state.json
    trainer_state = None
    checkpoints = sorted(model_path.glob("checkpoint-*"), key=lambda x: int(x.name.split("-")[1]))

    if checkpoints:
        latest_checkpoint = checkpoints[-1]
        state_file = latest_checkpoint / "trainer_state.json"
        if state_file.exists():
            with open(state_file) as f:
                trainer_state = json.load(f)

    if not trainer_state:
        return {}

    # Find best eval metrics from log_history
    best_metrics = {}
    best_step = trainer_state.get("best_global_step", 0)

    for entry in trainer_state.get("log_history", []):
        if entry.get("step") == best_step and "eval_f1" in entry:
            best_metrics = {
                "precision": entry.get("eval_precision", 0),
                "recall": entry.get("eval_recall", 0),
                "f1": entry.get("eval_f1", 0),
                "accuracy": entry.get("eval_accuracy", 0),
                "loss": entry.get("eval_loss", 0),
            }
            break

    # If no best step match, get the last eval entry
    if not best_metrics:
        for entry in reversed(trainer_state.get("log_history", [])):
            if "eval_f1" in entry:
                best_metrics = {
                    "precision": entry.get("eval_precision", 0),
                    "recall": entry.get("eval_recall", 0),
                    "f1": entry.get("eval_f1", 0),
                    "accuracy": entry.get("eval_accuracy", 0),
                    "loss": entry.get("eval_loss", 0),
                }
                break

    return best_metrics


def count_jsonl_lines(file_path: Path) -> int:
    """Count lines in a JSONL file."""
    if not file_path.exists():
        return 0
    with open(file_path) as f:
        return sum(1 for _ in f)


def get_cities_from_jsonl(file_path: Path) -> list:
    """Extract unique cities from a JSONL file."""
    if not file_path.exists():
        return []
    cities = set()
    with open(file_path) as f:
        for line in f:
            ex = json.loads(line)
            city = ex.get('city', 'unknown')
            state = ex.get('state', 'unknown')
            cities.add(f"{city}, {state.upper()}")
    return sorted(cities)


def compute_validator_confusion_matrix():
    """Compute confusion matrix from validator test data."""
    load_models()
    _, validator_data = load_test_data()

    if not validator_data or models['validator'] is None:
        return None

    # Compute confusion matrix
    tp = tn = fp = fn = 0
    for ex in validator_data:
        code = ex['code']
        passages = ex['passages']
        true_label = ex['label']  # 1 = valid, 0 = invalid

        _, prediction = predict_validator(code, passages)
        pred_label = 1 if prediction == "Valid" else 0

        if true_label == 1 and pred_label == 1:
            tp += 1
        elif true_label == 0 and pred_label == 0:
            tn += 1
        elif true_label == 0 and pred_label == 1:
            fp += 1
        else:
            fn += 1

    return {
        'true_valid_pred_valid': tp,
        'true_invalid_pred_invalid': tn,
        'true_invalid_pred_valid': fp,
        'true_valid_pred_invalid': fn,
    }


def compute_extractor_metrics():
    """Compute extractor metrics from test data predictions."""
    load_models()
    extractor_data, _ = load_test_data()

    if not extractor_data or models['extractor'] is None:
        return {}

    # Collect all true and predicted labels for seqeval
    all_true_labels = []
    all_pred_labels = []

    for ex in extractor_data:
        tokens = ex['tokens']
        true_tags = ex['tags']

        # Get predictions
        pred_tags = predict_extractor(tokens)

        # Filter out special tokens (-100 equivalent: [CLS], [SEP], [PAD])
        filtered_true = []
        filtered_pred = []
        for i, (t_tag, p_tag) in enumerate(zip(true_tags, pred_tags)):
            if tokens[i] not in ['[CLS]', '[SEP]', '[PAD]']:
                filtered_true.append(t_tag)
                filtered_pred.append(p_tag)

        if filtered_true:
            all_true_labels.append(filtered_true)
            all_pred_labels.append(filtered_pred)

    if not all_true_labels:
        return {}

    # Compute seqeval metrics
    try:
        from seqeval.metrics import precision_score, recall_score, f1_score
        precision = precision_score(all_true_labels, all_pred_labels)
        recall = recall_score(all_true_labels, all_pred_labels)
        f1 = f1_score(all_true_labels, all_pred_labels)
        return {
            'precision': precision,
            'recall': recall,
            'f1': f1,
        }
    except ImportError:
        # Fallback to simple token-level accuracy
        correct = sum(1 for t, p in zip(sum(all_true_labels, []), sum(all_pred_labels, []))
                      if t == p)
        total = len(sum(all_true_labels, []))
        return {
            'precision': correct / total if total > 0 else 0,
            'recall': correct / total if total > 0 else 0,
            'f1': correct / total if total > 0 else 0,
        }


def format_city_list(cities: list) -> str:
    """Format a list of cities into a display string."""
    if not cities:
        return "N/A"
    if len(cities) == 1:
        return cities[0]
    elif len(cities) <= 3:
        return ", ".join(cities)
    else:
        return f"{len(cities)} cities"


def compute_metrics_from_confusion_matrix(cm):
    """Compute accuracy, precision, recall, f1 from confusion matrix."""
    if not cm:
        return {}
    tp = cm.get('true_valid_pred_valid', 0)
    tn = cm.get('true_invalid_pred_invalid', 0)
    fp = cm.get('true_invalid_pred_valid', 0)
    fn = cm.get('true_valid_pred_invalid', 0)

    total = tp + tn + fp + fn
    accuracy = (tp + tn) / total if total > 0 else 0
    precision = tp / (tp + fp) if (tp + fp) > 0 else 0
    recall = tp / (tp + fn) if (tp + fn) > 0 else 0
    f1 = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0

    return {'accuracy': accuracy, 'precision': precision, 'recall': recall, 'f1': f1}


@app.route('/api/refresh', methods=['POST'])
def refresh_models():
    """Force reload models from disk."""
    global models
    models = {'extractor': None, 'validator': None, 'tokenizer': None}
    load_models(force_reload=True)
    return jsonify({'success': True, 'message': 'Models reloaded from disk'})


@app.route('/api/models')
def get_available_models():
    """List available extractor and validator models."""
    extractors = []
    validators = []

    for path in TRAINED_MODELS_DIR.iterdir():
        if path.is_dir() and not path.name.startswith('.'):
            if 'extractor' in path.name:
                extractors.append(path.name)
            elif 'validator' in path.name:
                validators.append(path.name)

    return jsonify({
        'extractors': sorted(extractors),
        'validators': sorted(validators),
        'current_extractor': current_extractor_model,
        'current_validator': current_validator_model,
    })


@app.route('/api/models/select', methods=['POST'])
def select_models():
    """Select which models to use."""
    global current_extractor_model, current_validator_model

    data = request.json
    new_extractor = data.get('extractor')
    new_validator = data.get('validator')

    changed = False

    if new_extractor and new_extractor != current_extractor_model:
        extractor_path = TRAINED_MODELS_DIR / new_extractor
        if extractor_path.exists():
            current_extractor_model = new_extractor
            changed = True

    if new_validator and new_validator != current_validator_model:
        validator_path = TRAINED_MODELS_DIR / new_validator
        if validator_path.exists():
            current_validator_model = new_validator
            changed = True

    if changed:
        # Reload models with new selections
        load_models(force_reload=True)

    return jsonify({
        'success': True,
        'current_extractor': current_extractor_model,
        'current_validator': current_validator_model,
    })


def load_cached_metrics():
    """Load pre-computed metrics from cache file."""
    if CACHED_METRICS_FILE.exists():
        try:
            with open(CACHED_METRICS_FILE) as f:
                return json.load(f)
        except Exception as e:
            print(f"Warning: Could not load cached metrics: {e}")
    return None


@app.route('/api/metrics')
def get_metrics():
    """Get model performance metrics from cached file (instant) or compute dynamically (slow)."""
    # Try to load from cache first (instant)
    cached = load_cached_metrics()
    if cached:
        # Use cached metrics if available (ignore model name mismatch since we're in cache-only mode)
        return jsonify(cached)

    # Fall back to dynamic computation (slow) if no cache or model mismatch
    print("Warning: No cached metrics found or model mismatch. Computing dynamically (slow)...")

    # Load metrics from trainer state
    extractor_metrics = load_trainer_state(current_extractor_model)
    validator_metrics = load_trainer_state(current_validator_model)

    # If extractor metrics not in trainer state, compute from test data
    extractor_source = 'Training validation (best checkpoint)'
    if not extractor_metrics.get('f1'):
        extractor_metrics = compute_extractor_metrics()
        extractor_source = 'Computed from test data'

    # Count examples from data files
    train_examples = count_jsonl_lines(DATA_DIR / "train_extractor.jsonl")
    test_examples = count_jsonl_lines(DATA_DIR / "test_extractor.jsonl")
    validator_train = count_jsonl_lines(DATA_DIR / "train_validator.jsonl")
    validator_test = count_jsonl_lines(DATA_DIR / "test_validator.jsonl")

    # Get cities from extractor data files
    extractor_train_cities = get_cities_from_jsonl(DATA_DIR / "train_extractor.jsonl")
    extractor_test_cities = get_cities_from_jsonl(DATA_DIR / "test_extractor.jsonl")

    # Get cities from validator data files
    validator_train_cities = get_cities_from_jsonl(DATA_DIR / "train_validator.jsonl")
    validator_test_cities = get_cities_from_jsonl(DATA_DIR / "test_validator.jsonl")

    # Compute validator confusion matrix dynamically
    confusion_matrix = compute_validator_confusion_matrix()

    # Always compute validator metrics from confusion matrix (test set)
    # since trainer_state metrics are from validation set, not test set
    validator_source = 'Training validation (best checkpoint)'
    if confusion_matrix:
        validator_metrics = compute_metrics_from_confusion_matrix(confusion_matrix)
        validator_source = 'Computed from test set'

    metrics = {
        'extractor': {
            'precision': round(extractor_metrics.get('precision', 0), 2),
            'recall': round(extractor_metrics.get('recall', 0), 2),
            'f1': round(extractor_metrics.get('f1', 0), 2),
            'train_examples': train_examples,
            'test_examples': test_examples,
            'train_city': format_city_list(extractor_train_cities),
            'test_city': format_city_list(extractor_test_cities),
            'train_city_count': len(extractor_train_cities),
            'test_city_count': len(extractor_test_cities),
            'train_cities_list': extractor_train_cities,
            'test_cities_list': extractor_test_cities,
            'metrics_source': extractor_source,
            'model_name': current_extractor_model,
        },
        'validator': {
            'accuracy': round(validator_metrics.get('accuracy', 0), 2),
            'precision': round(validator_metrics.get('precision', 0), 2),
            'recall': round(validator_metrics.get('recall', 0), 2),
            'f1': round(validator_metrics.get('f1', 0), 2),
            'train_examples': validator_train,
            'test_examples': validator_test,
            'train_city': format_city_list(validator_train_cities),
            'test_city': format_city_list(validator_test_cities),
            'train_city_count': len(validator_train_cities),
            'test_city_count': len(validator_test_cities),
            'train_cities_list': validator_train_cities,
            'test_cities_list': validator_test_cities,
            'confusion_matrix': confusion_matrix,
            'metrics_source': validator_source,
            'model_name': current_validator_model,
        }
    }
    return jsonify(metrics)


@app.route('/api/extractor/examples')
def get_extractor_examples():
    """Get extractor test examples with predictions from cache (instant) or compute (slow)."""
    # Try to load from cache first
    if CACHED_EXTRACTOR_EXAMPLES_FILE.exists():
        try:
            with open(CACHED_EXTRACTOR_EXAMPLES_FILE) as f:
                return jsonify(json.load(f))
        except Exception as e:
            print(f"Warning: Could not load cached extractor examples: {e}")

    # Fall back to dynamic computation (slow)
    print("Warning: No cached extractor examples found. Computing dynamically (slow)...")

    load_models()
    extractor_data, _ = load_test_data()

    examples = []
    for i, ex in enumerate(extractor_data[:50]):  # Limit to 50 examples
        tokens = ex['tokens']
        true_labels = ex['tags']

        # Get predictions
        pred_labels = predict_extractor(tokens)

        # Extract zone codes
        true_zones = extract_zones_from_bio(tokens, true_labels)
        pred_zones = extract_zones_from_bio(tokens, pred_labels)

        # Determine correctness
        if set(true_zones) == set(pred_zones):
            status = 'correct'
        elif set(true_zones) & set(pred_zones):
            status = 'partial'
        else:
            status = 'incorrect'

        # Create highlighted text
        highlighted_tokens = []
        for j, (token, true_label, pred_label) in enumerate(zip(tokens, true_labels, pred_labels)):
            highlighted_tokens.append({
                'token': token,
                'true_label': true_label,
                'pred_label': pred_label,
                'is_true_zone': true_label in ['B-ZONE', 'I-ZONE'],
                'is_pred_zone': pred_label in ['B-ZONE', 'I-ZONE'],
            })

        examples.append({
            'id': i,
            'city': ex.get('city', 'unknown'),
            'state': ex.get('state', 'unknown'),
            'true_zones': true_zones,
            'pred_zones': pred_zones,
            'status': status,
            'tokens': highlighted_tokens,
            'text_preview': ' '.join(tokens[1:50]).replace(' ##', '').replace('##', '') + '...',
        })

    # Calculate summary stats
    correct = sum(1 for e in examples if e['status'] == 'correct')
    partial = sum(1 for e in examples if e['status'] == 'partial')
    incorrect = sum(1 for e in examples if e['status'] == 'incorrect')

    return jsonify({
        'examples': examples,
        'summary': {
            'total': len(examples),
            'correct': correct,
            'partial': partial,
            'incorrect': incorrect,
        }
    })


@app.route('/api/validator/examples')
def get_validator_examples():
    """Get validator test examples with predictions from cache (instant) or compute (slow)."""
    # Try to load from cache first
    if CACHED_VALIDATOR_EXAMPLES_FILE.exists():
        try:
            with open(CACHED_VALIDATOR_EXAMPLES_FILE) as f:
                return jsonify(json.load(f))
        except Exception as e:
            print(f"Warning: Could not load cached validator examples: {e}")

    # Fall back to dynamic computation (slow)
    print("Warning: No cached validator examples found. Computing dynamically (slow)...")

    load_models()
    _, validator_data = load_test_data()

    examples = []
    for i, ex in enumerate(validator_data):
        code = ex['code']
        passages = ex['passages']
        true_label = ex['label']

        # Get prediction
        confidence, prediction = predict_validator(code, passages)

        # Determine correctness
        pred_label = 1 if prediction == "Valid" else 0
        is_correct = pred_label == true_label

        examples.append({
            'id': i,
            'code': code,
            'city': ex.get('city', 'unknown'),
            'state': ex.get('state', 'unknown'),
            'true_label': 'Valid' if true_label == 1 else 'Invalid',
            'pred_label': prediction,
            'confidence': round(confidence, 3),
            'is_correct': is_correct,
            'passages': passages[:3],  # First 3 passages
            'passage_preview': passages[0][:200] + '...' if passages else 'N/A',
        })

    # Calculate summary stats
    correct = sum(1 for e in examples if e['is_correct'])
    false_positives = sum(1 for e in examples if e['true_label'] == 'Invalid' and e['pred_label'] == 'Valid')
    false_negatives = sum(1 for e in examples if e['true_label'] == 'Valid' and e['pred_label'] == 'Invalid')

    return jsonify({
        'examples': examples,
        'summary': {
            'total': len(examples),
            'correct': correct,
            'false_positives': false_positives,
            'false_negatives': false_negatives,
        }
    })


@app.route('/api/predict', methods=['POST'])
def predict_text():
    """Run prediction on custom text."""
    load_models()
    
    data = request.json
    text = data.get('text', '')
    
    if not text or models['tokenizer'] is None:
        return jsonify({'error': 'No text provided or models not loaded'}), 400
    
    # Tokenize
    encoding = models['tokenizer'](
        text,
        truncation=True,
        max_length=512,
        return_tensors='pt'
    )
    tokens = models['tokenizer'].convert_ids_to_tokens(encoding['input_ids'][0])
    
    # Get extractor predictions
    with torch.no_grad():
        outputs = models['extractor'](**encoding)
        predictions = torch.argmax(outputs.logits, dim=2)
    
    pred_labels = [EXTRACTOR_ID_TO_LABEL[p.item()] for p in predictions[0]]
    
    # Extract zones
    zones = extract_zones_from_bio(tokens, pred_labels)
    
    # Highlight tokens
    highlighted = []
    for token, label in zip(tokens, pred_labels):
        highlighted.append({
            'token': token,
            'label': label,
            'is_zone': label in ['B-ZONE', 'I-ZONE'],
        })
    
    return jsonify({
        'zones': zones,
        'tokens': highlighted,
    })


@app.route('/api/city-comparison')
def get_city_comparison():
    """Get city-level comparison from cache (instant) or compute (slow)."""
    # Try to load from cache first
    if CACHED_CITY_COMPARISON_FILE.exists():
        try:
            with open(CACHED_CITY_COMPARISON_FILE) as f:
                return jsonify(json.load(f))
        except Exception as e:
            print(f"Warning: Could not load cached city comparison: {e}")

    # Fall back to dynamic computation (slow)
    print("Warning: No cached city comparison found. Computing dynamically (very slow)...")

    load_models()
    extractor_data, _ = load_test_data()

    # Group by city
    city_data = {}
    for ex in extractor_data:
        city_key = f"{ex.get('city', 'unknown')}, {ex.get('state', 'unknown')}"
        if city_key not in city_data:
            city_data[city_key] = {
                'city': ex.get('city', 'unknown'),
                'state': ex.get('state', 'unknown'),
                'true_zones': set(),
                'pred_zones_raw': set(),       # All extractor outputs
                'pred_zones_validated': set(),  # Filtered through validator
                'example_count': 0,
            }

        # Extract true zones and normalize them
        true_zones = extract_zones_from_bio(ex['tokens'], ex['tags'])
        for z in true_zones:
            city_data[city_key]['true_zones'].add(normalize_zone_code(z))

        city_data[city_key]['example_count'] += 1

    # Run predictions for a sample from each city (limit to avoid timeout)
    for city_key, data in city_data.items():
        # Get examples for this city
        city_examples = [ex for ex in extractor_data
                        if f"{ex.get('city', 'unknown')}, {ex.get('state', 'unknown')}" == city_key]

        # Sample up to 100 examples per city for prediction
        sample_size = min(100, len(city_examples))
        sample_indices = np.random.choice(len(city_examples), sample_size, replace=False)

        for idx in sample_indices:
            ex = city_examples[idx]
            pred_labels = predict_extractor(ex['tokens'])
            pred_zones = extract_zones_from_bio(ex['tokens'], pred_labels)

            # Reconstruct passage text for validator context
            passage_text = ' '.join(ex['tokens']).replace(' ##', '').replace('##', '')

            for z in pred_zones:
                normalized = normalize_zone_code(z)
                data['pred_zones_raw'].add(normalized)

                # Filter through validator
                confidence, prediction = predict_validator(z, [passage_text])
                if prediction == "Valid":
                    data['pred_zones_validated'].add(normalized)

    # Convert sets to sorted lists and calculate metrics
    results = []
    for city_key, data in city_data.items():
        true_set = data['true_zones']  # From test.jsonl (BIO tags)
        pred_set_raw = data['pred_zones_raw']
        pred_set_validated = data['pred_zones_validated']

        # Load CSV zone codes (actual ground truth from Zoneomics)
        csv_zones = load_csv_zone_codes(data['state'], data['city'])

        # Calculate metrics for RAW predictions (extractor only)
        common_raw = true_set & pred_set_raw
        precision_raw = len(common_raw) / len(pred_set_raw) if pred_set_raw else 0
        recall_raw = len(common_raw) / len(true_set) if true_set else 0
        f1_raw = 2 * precision_raw * recall_raw / (precision_raw + recall_raw) if (precision_raw + recall_raw) > 0 else 0

        # Calculate VALIDATOR metrics (how well validator filters extractor outputs)
        # Validator's job: accept correct predictions, reject incorrect predictions
        correct_extractor_preds = pred_set_raw & true_set  # Extractor got these right
        incorrect_extractor_preds = pred_set_raw - true_set  # Extractor got these wrong (false positives)

        # TP: Correct predictions that validator kept
        validator_tp = pred_set_validated & correct_extractor_preds
        # TN: Incorrect predictions that validator rejected
        validator_tn = incorrect_extractor_preds - pred_set_validated
        # FP: Incorrect predictions that validator kept (validator's mistakes)
        validator_fp = pred_set_validated & incorrect_extractor_preds
        # FN: Correct predictions that validator rejected (validator's mistakes)
        validator_fn = correct_extractor_preds - pred_set_validated

        # Calculate validator P/R/F1
        validator_precision = len(validator_tp) / (len(validator_tp) + len(validator_fp)) if (len(validator_tp) + len(validator_fp)) > 0 else 0
        validator_recall = len(validator_tp) / (len(validator_tp) + len(validator_fn)) if (len(validator_tp) + len(validator_fn)) > 0 else 0
        validator_f1 = 2 * validator_precision * validator_recall / (validator_precision + validator_recall) if (validator_precision + validator_recall) > 0 else 0

        # Calculate metrics for VALIDATED predictions (extractor + validator pipeline)
        common_validated = true_set & pred_set_validated
        precision_validated = len(common_validated) / len(pred_set_validated) if pred_set_validated else 0
        recall_validated = len(common_validated) / len(true_set) if true_set else 0
        f1_validated = 2 * precision_validated * recall_validated / (precision_validated + recall_validated) if (precision_validated + recall_validated) > 0 else 0

        # Calculate CSV coverage: how many CSV codes appear in test data
        csv_in_test = csv_zones & true_set if csv_zones else set()
        csv_coverage = len(csv_in_test) / len(csv_zones) if csv_zones else 0

        results.append({
            'city': data['city'],
            'state': data['state'],
            'example_count': data['example_count'],
            'true_zones': sorted(true_set),
            'true_count': len(true_set),
            # Raw extractor predictions
            'pred_zones_raw': sorted(pred_set_raw),
            'pred_count_raw': len(pred_set_raw),
            'common_zones_raw': sorted(common_raw),
            'extra_zones_raw': sorted(pred_set_raw - true_set),
            'precision_raw': round(precision_raw, 2),
            'recall_raw': round(recall_raw, 2),
            'f1_raw': round(f1_raw, 2),
            # Validator-only metrics (filtering performance)
            'validator_precision': round(validator_precision, 2),
            'validator_recall': round(validator_recall, 2),
            'validator_f1': round(validator_f1, 2),
            'validator_tp': len(validator_tp),
            'validator_tn': len(validator_tn),
            'validator_fp': len(validator_fp),
            'validator_fn': len(validator_fn),
            # Validated predictions (extractor + validator pipeline)
            'pred_zones_validated': sorted(pred_set_validated),
            'pred_count_validated': len(pred_set_validated),
            'common_zones_validated': sorted(common_validated),
            'extra_zones_validated': sorted(pred_set_validated - true_set),
            'precision_validated': round(precision_validated, 2),
            'recall_validated': round(recall_validated, 2),
            'f1_validated': round(f1_validated, 2),
            # Missed zones (same for both - based on true set)
            'missed_zones': sorted(true_set - pred_set_raw),
            'missed_zones_validated': sorted(true_set - pred_set_validated),
            # CSV ground truth data
            'csv_zones': sorted(csv_zones),
            'csv_count': len(csv_zones),
            'csv_coverage': round(csv_coverage, 2),
            'csv_in_test': sorted(csv_in_test),
            'csv_missing_from_test': sorted(csv_zones - true_set) if csv_zones else [],
            # Legacy fields for backwards compatibility (use raw values)
            'pred_zones': sorted(pred_set_raw),
            'pred_count': len(pred_set_raw),
            'common_zones': sorted(common_raw),
            'extra_zones': sorted(pred_set_raw - true_set),
            'precision': round(precision_raw, 2),
            'recall': round(recall_raw, 2),
            'f1': round(f1_raw, 2),
        })

    # Sort by state, then city
    results.sort(key=lambda x: (x['state'], x['city']))

    return jsonify({
        'cities': results,
        'total_cities': len(results),
    })


if __name__ == '__main__':
    print("Ensuring cache files are available...")
    ensure_cache_files()

    # Only load models if cache files are missing (fallback mode)
    # Models will be lazy-loaded on-demand for live prediction feature
    cache_files_exist = all([
        CACHED_METRICS_FILE.exists(),
        CACHED_EXTRACTOR_EXAMPLES_FILE.exists(),
        CACHED_VALIDATOR_EXAMPLES_FILE.exists(),
        CACHED_CITY_COMPARISON_FILE.exists(),
    ])

    if cache_files_exist:
        print("✓ All cache files available - models will be loaded on-demand if needed")
    else:
        print("Loading models (cache files missing)...")
        load_models()

    print("Starting server...")
    app.run(debug=True, port=5001)
