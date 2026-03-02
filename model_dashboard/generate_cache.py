#!/usr/bin/env python3
"""
Generate cache files for the dashboard to enable instant loading.

This script precomputes all metrics and examples and saves them to cache files.
Run this after training new models to update the dashboard data.

Usage:
    python generate_cache.py --extractor extractor_20260221_162851 --validator validator_20260221_173736
"""

import json
import os
import sys
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
ENV_FILE = Path(__file__).parent.parent / "secrets" / "teamspatially-project.env"
if ENV_FILE.exists():
    load_dotenv(ENV_FILE)

# Add parent directory to path to import app modules
sys.path.insert(0, str(Path(__file__).parent))

# Import after path modification
from app import (
    TRAINED_MODELS_DIR,
    DATA_DIR,
    CACHED_METRICS_FILE,
    CACHED_EXTRACTOR_EXAMPLES_FILE,
    CACHED_VALIDATOR_EXAMPLES_FILE,
    CACHED_CITY_COMPARISON_FILE,
    load_models,
    load_test_data,
    compute_extractor_metrics,
    compute_validator_confusion_matrix,
    compute_metrics_from_confusion_matrix,
    count_jsonl_lines,
    get_cities_from_jsonl,
    format_city_list,
    predict_extractor,
    predict_validator,
    extract_zones_from_bio,
    normalize_zone_code,
    load_csv_zone_codes,
    models,
)


def generate_metrics_cache(extractor_model: str, validator_model: str):
    """Generate and save metrics cache."""
    print("Generating metrics cache...")
    print(f"  Extractor: {extractor_model}")
    print(f"  Validator: {validator_model}")

    # Load models
    print("\nLoading models...")
    load_models(force_reload=True)

    # Load metrics
    print("Computing extractor metrics...")
    extractor_metrics = compute_extractor_metrics()

    # Count examples from data files
    train_examples = count_jsonl_lines(DATA_DIR / "train_extractor.jsonl")
    test_examples = count_jsonl_lines(DATA_DIR / "test_extractor.jsonl")
    validator_train = count_jsonl_lines(DATA_DIR / "train_validator.jsonl")
    validator_test = count_jsonl_lines(DATA_DIR / "test_validator.jsonl")

    # Get cities from data files
    extractor_train_cities = get_cities_from_jsonl(DATA_DIR / "train_extractor.jsonl")
    extractor_test_cities = get_cities_from_jsonl(DATA_DIR / "test_extractor.jsonl")
    validator_train_cities = get_cities_from_jsonl(DATA_DIR / "train_validator.jsonl")
    validator_test_cities = get_cities_from_jsonl(DATA_DIR / "test_validator.jsonl")

    # Compute validator confusion matrix
    print("Computing validator confusion matrix...")
    confusion_matrix = compute_validator_confusion_matrix()
    validator_metrics = compute_metrics_from_confusion_matrix(confusion_matrix)

    # Build metrics object
    metrics = {
        'extractor_model': extractor_model,
        'validator_model': validator_model,
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
            'metrics_source': 'Computed from test data',
            'model_name': extractor_model,
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
            'metrics_source': 'Computed from test set',
            'model_name': validator_model,
        }
    }

    # Save to cache
    print(f"Saving metrics to {CACHED_METRICS_FILE}...")
    with open(CACHED_METRICS_FILE, 'w') as f:
        json.dump(metrics, f, indent=2)

    print("✓ Metrics cache generated")
    return metrics


def generate_extractor_examples_cache():
    """Generate and save extractor examples cache."""
    print("\nGenerating extractor examples cache...")

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
        for token, true_label, pred_label in zip(tokens, true_labels, pred_labels):
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

        if (i + 1) % 10 == 0:
            print(f"  Processed {i + 1} examples...")

    # Calculate summary stats
    correct = sum(1 for e in examples if e['status'] == 'correct')
    partial = sum(1 for e in examples if e['status'] == 'partial')
    incorrect = sum(1 for e in examples if e['status'] == 'incorrect')

    result = {
        'examples': examples,
        'summary': {
            'total': len(examples),
            'correct': correct,
            'partial': partial,
            'incorrect': incorrect,
        }
    }

    # Save to cache
    print(f"Saving extractor examples to {CACHED_EXTRACTOR_EXAMPLES_FILE}...")
    with open(CACHED_EXTRACTOR_EXAMPLES_FILE, 'w') as f:
        json.dump(result, f, indent=2)

    print("✓ Extractor examples cache generated")
    return result


def generate_validator_examples_cache():
    """Generate and save validator examples cache."""
    print("\nGenerating validator examples cache...")

    _, validator_data = load_test_data()

    examples = []
    for i, ex in enumerate(validator_data):
        code = ex['code']
        passages = ex['passages']
        true_label = ex['label']  # 1 = valid, 0 = invalid

        # Get predictions
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

        if (i + 1) % 10 == 0:
            print(f"  Processed {i + 1} examples...")

    # Calculate summary stats
    correct = sum(1 for e in examples if e['is_correct'])
    false_positives = sum(1 for e in examples if e['true_label'] == 'Invalid' and e['pred_label'] == 'Valid')
    false_negatives = sum(1 for e in examples if e['true_label'] == 'Valid' and e['pred_label'] == 'Invalid')

    result = {
        'examples': examples,
        'summary': {
            'total': len(examples),
            'correct': correct,
            'false_positives': false_positives,
            'false_negatives': false_negatives,
        }
    }

    # Save to cache
    print(f"Saving validator examples to {CACHED_VALIDATOR_EXAMPLES_FILE}...")
    with open(CACHED_VALIDATOR_EXAMPLES_FILE, 'w') as f:
        json.dump(result, f, indent=2)

    print("✓ Validator examples cache generated")
    return result


def generate_city_comparison_cache():
    """Generate and save city comparison cache."""
    print("\nGenerating city comparison cache...")
    import numpy as np

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
                'pred_zones_raw': set(),
                'pred_zones_validated': set(),
                'example_count': 0,
            }

        # Extract true zones and normalize them
        true_zones = extract_zones_from_bio(ex['tokens'], ex['tags'])
        for z in true_zones:
            city_data[city_key]['true_zones'].add(normalize_zone_code(z))

        city_data[city_key]['example_count'] += 1

    # Run predictions for a sample from each city
    print("Running predictions for each city...")
    for idx, (city_key, data) in enumerate(city_data.items()):
        print(f"  Processing city {idx + 1}/{len(city_data)}: {city_key}")

        # Get examples for this city
        city_examples = [ex for ex in extractor_data
                        if f"{ex.get('city', 'unknown')}, {ex.get('state', 'unknown')}" == city_key]

        # Sample up to 100 examples per city for prediction
        sample_size = min(100, len(city_examples))
        sample_indices = np.random.choice(len(city_examples), sample_size, replace=False)

        for idx_sample in sample_indices:
            ex = city_examples[idx_sample]
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
        true_set = data['true_zones']
        pred_set_raw = data['pred_zones_raw']
        pred_set_validated = data['pred_zones_validated']

        # Load CSV zone codes
        csv_zones = load_csv_zone_codes(data['state'], data['city'])

        # Calculate metrics for RAW predictions (extractor only)
        common_raw = true_set & pred_set_raw
        precision_raw = len(common_raw) / len(pred_set_raw) if pred_set_raw else 0
        recall_raw = len(common_raw) / len(true_set) if true_set else 0
        f1_raw = 2 * precision_raw * recall_raw / (precision_raw + recall_raw) if (precision_raw + recall_raw) > 0 else 0

        # Calculate VALIDATOR metrics
        correct_extractor_preds = pred_set_raw & true_set
        incorrect_extractor_preds = pred_set_raw - true_set

        validator_tp = pred_set_validated & correct_extractor_preds
        validator_tn = incorrect_extractor_preds - pred_set_validated
        validator_fp = pred_set_validated & incorrect_extractor_preds
        validator_fn = correct_extractor_preds - pred_set_validated

        validator_precision = len(validator_tp) / (len(validator_tp) + len(validator_fp)) if (len(validator_tp) + len(validator_fp)) > 0 else 0
        validator_recall = len(validator_tp) / (len(validator_tp) + len(validator_fn)) if (len(validator_tp) + len(validator_fn)) > 0 else 0
        validator_f1 = 2 * validator_precision * validator_recall / (validator_precision + validator_recall) if (validator_precision + validator_recall) > 0 else 0

        # Calculate metrics for VALIDATED predictions
        common_validated = true_set & pred_set_validated
        precision_validated = len(common_validated) / len(pred_set_validated) if pred_set_validated else 0
        recall_validated = len(common_validated) / len(true_set) if true_set else 0
        f1_validated = 2 * precision_validated * recall_validated / (precision_validated + recall_validated) if (precision_validated + recall_validated) > 0 else 0

        # Calculate CSV coverage
        csv_in_test = csv_zones & true_set if csv_zones else set()
        csv_coverage = len(csv_in_test) / len(csv_zones) if csv_zones else 0

        results.append({
            'city': data['city'],
            'state': data['state'],
            'example_count': data['example_count'],
            'true_zones': sorted(true_set),
            'true_count': len(true_set),
            'pred_zones_raw': sorted(pred_set_raw),
            'pred_count_raw': len(pred_set_raw),
            'common_zones_raw': sorted(common_raw),
            'extra_zones_raw': sorted(pred_set_raw - true_set),
            'precision_raw': round(precision_raw, 2),
            'recall_raw': round(recall_raw, 2),
            'f1_raw': round(f1_raw, 2),
            'validator_precision': round(validator_precision, 2),
            'validator_recall': round(validator_recall, 2),
            'validator_f1': round(validator_f1, 2),
            'validator_tp': len(validator_tp),
            'validator_tn': len(validator_tn),
            'validator_fp': len(validator_fp),
            'validator_fn': len(validator_fn),
            'pred_zones_validated': sorted(pred_set_validated),
            'pred_count_validated': len(pred_set_validated),
            'common_zones_validated': sorted(common_validated),
            'extra_zones_validated': sorted(pred_set_validated - true_set),
            'precision_validated': round(precision_validated, 2),
            'recall_validated': round(recall_validated, 2),
            'f1_validated': round(f1_validated, 2),
            'missed_zones': sorted(true_set - pred_set_raw),
            'missed_zones_validated': sorted(true_set - pred_set_validated),
            'csv_zones': sorted(csv_zones),
            'csv_count': len(csv_zones),
            'csv_coverage': round(csv_coverage, 2),
            'csv_in_test': sorted(csv_in_test),
            'csv_missing_from_test': sorted(csv_zones - true_set) if csv_zones else [],
            'precision': round(precision_raw, 2),
            'recall': round(recall_raw, 2),
            'f1': round(f1_raw, 2),
        })

    # Sort by state, then city
    results.sort(key=lambda x: (x['state'], x['city']))

    # Wrap in expected format
    result_obj = {
        'cities': results,
        'total_cities': len(results),
    }

    # Save to cache
    print(f"Saving city comparison to {CACHED_CITY_COMPARISON_FILE}...")
    with open(CACHED_CITY_COMPARISON_FILE, 'w') as f:
        json.dump(result_obj, f, indent=2)

    print("✓ City comparison cache generated")
    return result_obj


def main():
    """Generate all cache files."""
    import argparse

    parser = argparse.ArgumentParser(description='Generate cache files for dashboard')
    parser.add_argument('--extractor', required=True, help='Extractor model name (e.g., extractor_20260221_162851)')
    parser.add_argument('--validator', required=True, help='Validator model name (e.g., validator_20260221_173736)')

    args = parser.parse_args()

    # Verify models exist
    extractor_path = TRAINED_MODELS_DIR / args.extractor
    validator_path = TRAINED_MODELS_DIR / args.validator

    if not extractor_path.exists():
        print(f"Error: Extractor model not found at {extractor_path}")
        sys.exit(1)

    if not validator_path.exists():
        print(f"Error: Validator model not found at {validator_path}")
        sys.exit(1)

    print("="*60)
    print("DASHBOARD CACHE GENERATION")
    print("="*60)

    # Update app.py with current models
    import app
    app.current_extractor_model = args.extractor
    app.current_validator_model = args.validator

    # Generate all caches
    generate_metrics_cache(args.extractor, args.validator)
    generate_extractor_examples_cache()
    generate_validator_examples_cache()
    generate_city_comparison_cache()

    print("\n" + "="*60)
    print("CACHE GENERATION COMPLETE")
    print("="*60)
    print("\nAll cache files have been generated. The dashboard will now load instantly.")
    print("Restart the dashboard server to see the changes.")

    # Upload to GCS if enabled
    upload_to_gcs = os.getenv("UPLOAD_TO_GCS", "0") == "1"
    if upload_to_gcs:
        try:
            print("\n" + "=" * 60)
            print("Uploading cache files to GCS...")
            print("=" * 60)

            # Import GCS model manager
            model_dir = Path(__file__).parent.parent / "model" / "zoning_codes_extract"
            sys.path.append(str(model_dir / "training" / "utils"))
            from gcs_model_manager import GCSModelManager

            # Upload cache files
            manager = GCSModelManager()
            uploaded_paths = manager.upload_cache_files(cache_dir=TRAINED_MODELS_DIR)

            print(f"\n✓ Uploaded {len(uploaded_paths)} cache files to GCS")

        except Exception as e:
            print(f"\n⚠ Failed to upload cache files to GCS: {e}")
            print("Cache files are still available locally")


if __name__ == "__main__":
    main()
