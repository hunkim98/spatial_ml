#!/usr/bin/env python3
"""
Pre-compute metrics for the dashboard.

Run this script after training to generate cached metrics that the dashboard
can load instantly without running inference on every page load.

Usage:
    python compute_metrics.py [--extractor NAME] [--validator NAME]
"""

import argparse
import json
from pathlib import Path
from typing import List, Dict
from datetime import datetime

import numpy as np
import torch
from transformers import (
    AutoTokenizer,
    AutoModelForTokenClassification,
    AutoModelForSequenceClassification,
)

# Paths
SCRIPT_DIR = Path(__file__).parent.resolve()
DATA_DIR = SCRIPT_DIR / "training" / "data"
TRAINED_MODELS_DIR = SCRIPT_DIR / "trained_models"

# Label mappings
EXTRACTOR_LABELS = ['O', 'B-ZONE', 'I-ZONE']
EXTRACTOR_ID_TO_LABEL = {i: l for i, l in enumerate(EXTRACTOR_LABELS)}


def normalize_zone_code(code: str) -> str:
    """Normalize zone code by removing hyphens/spaces and uppercasing."""
    return code.replace('-', '').replace(' ', '').upper()


def extract_zones_from_bio(tokens: List[str], labels: List[str]) -> List[str]:
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

    zones = [z for z in zones if z not in ['[CLS]', '[SEP]', '[PAD]', '']]
    return zones


def load_jsonl(file_path: Path) -> List[dict]:
    """Load JSONL file."""
    if not file_path.exists():
        return []
    with open(file_path) as f:
        return [json.loads(line) for line in f]


def get_cities_from_data(data: List[dict]) -> List[str]:
    """Extract unique cities from data."""
    cities = set()
    for ex in data:
        city = ex.get('city', 'unknown').replace('_', ' ').title()
        state = ex.get('state', 'unknown').upper()
        cities.add(f"{city}, {state}")
    return sorted(cities)


def compute_extractor_metrics(
    model_path: Path,
    test_data: List[dict],
) -> Dict:
    """Compute extractor metrics and per-example predictions."""
    print(f"Loading extractor model from {model_path}...")
    tokenizer = AutoTokenizer.from_pretrained(str(model_path))
    model = AutoModelForTokenClassification.from_pretrained(str(model_path))
    model.eval()

    all_true_labels = []
    all_pred_labels = []
    examples_with_predictions = []

    print(f"Running inference on {len(test_data)} examples...")

    for i, ex in enumerate(test_data):
        if (i + 1) % 100 == 0:
            print(f"  Processed {i + 1}/{len(test_data)}")

        tokens = ex['tokens']
        true_tags = ex['tags']

        # Run prediction
        input_ids = tokenizer.convert_tokens_to_ids(tokens)
        inputs = torch.tensor([input_ids])

        with torch.no_grad():
            outputs = model(inputs)
            predictions = torch.argmax(outputs.logits, dim=2)

        pred_tags = [EXTRACTOR_ID_TO_LABEL[p.item()] for p in predictions[0]][:len(tokens)]

        # Filter special tokens for seqeval metrics
        filtered_true = []
        filtered_pred = []
        for j, (t_tag, p_tag) in enumerate(zip(true_tags, pred_tags)):
            if tokens[j] not in ['[CLS]', '[SEP]', '[PAD]']:
                filtered_true.append(t_tag)
                filtered_pred.append(p_tag)

        if filtered_true:
            all_true_labels.append(filtered_true)
            all_pred_labels.append(filtered_pred)

        # Extract zones for per-example analysis
        true_zones = extract_zones_from_bio(tokens, true_tags)
        pred_zones = extract_zones_from_bio(tokens, pred_tags)

        if set(true_zones) == set(pred_zones):
            status = 'correct'
        elif set(true_zones) & set(pred_zones):
            status = 'partial'
        else:
            status = 'incorrect'

        examples_with_predictions.append({
            'id': i,
            'city': ex.get('city', 'unknown'),
            'state': ex.get('state', 'unknown'),
            'true_zones': true_zones,
            'pred_zones': pred_zones,
            'status': status,
            'tokens': [
                {
                    'token': token,
                    'true_label': t_tag,
                    'pred_label': p_tag,
                    'is_true_zone': t_tag in ['B-ZONE', 'I-ZONE'],
                    'is_pred_zone': p_tag in ['B-ZONE', 'I-ZONE'],
                }
                for token, t_tag, p_tag in zip(tokens, true_tags, pred_tags)
            ],
            'text_preview': ' '.join(tokens[1:50]).replace(' ##', '').replace('##', '') + '...',
        })

    # Compute seqeval metrics
    try:
        from seqeval.metrics import precision_score, recall_score, f1_score
        precision = precision_score(all_true_labels, all_pred_labels)
        recall = recall_score(all_true_labels, all_pred_labels)
        f1 = f1_score(all_true_labels, all_pred_labels)
    except ImportError:
        # Fallback
        flat_true = sum(all_true_labels, [])
        flat_pred = sum(all_pred_labels, [])
        correct = sum(1 for t, p in zip(flat_true, flat_pred) if t == p)
        total = len(flat_true)
        precision = recall = f1 = correct / total if total > 0 else 0

    # Summary stats
    correct_count = sum(1 for e in examples_with_predictions if e['status'] == 'correct')
    partial_count = sum(1 for e in examples_with_predictions if e['status'] == 'partial')
    incorrect_count = sum(1 for e in examples_with_predictions if e['status'] == 'incorrect')

    return {
        'metrics': {
            'precision': round(precision, 4),
            'recall': round(recall, 4),
            'f1': round(f1, 4),
        },
        'examples': examples_with_predictions,
        'summary': {
            'total': len(examples_with_predictions),
            'correct': correct_count,
            'partial': partial_count,
            'incorrect': incorrect_count,
        }
    }


def compute_validator_metrics(
    model_path: Path,
    tokenizer_path: Path,
    test_data: List[dict],
) -> Dict:
    """Compute validator metrics and per-example predictions."""
    print(f"Loading validator model from {model_path}...")
    tokenizer = AutoTokenizer.from_pretrained(str(tokenizer_path))
    model = AutoModelForSequenceClassification.from_pretrained(str(model_path))
    model.eval()

    tp = tn = fp = fn = 0
    examples_with_predictions = []

    print(f"Running inference on {len(test_data)} examples...")

    for i, ex in enumerate(test_data):
        if (i + 1) % 50 == 0:
            print(f"  Processed {i + 1}/{len(test_data)}")

        code = ex['code']
        passages = ex['passages']
        true_label = ex['label']

        # Prepare input
        combined_passages = " [SEP] ".join(passages[:5])
        input_text = f"[CODE] {code} [SEP] {combined_passages}"

        inputs = tokenizer(
            input_text,
            truncation=True,
            max_length=512,
            return_tensors="pt"
        )

        with torch.no_grad():
            outputs = model(**inputs)
            probs = torch.softmax(outputs.logits, dim=1)

        valid_prob = probs[0][1].item()
        pred_label = 1 if valid_prob >= 0.5 else 0
        prediction = "Valid" if pred_label == 1 else "Invalid"

        # Update confusion matrix
        if true_label == 1 and pred_label == 1:
            tp += 1
        elif true_label == 0 and pred_label == 0:
            tn += 1
        elif true_label == 0 and pred_label == 1:
            fp += 1
        else:
            fn += 1

        is_correct = pred_label == true_label

        examples_with_predictions.append({
            'id': i,
            'code': code,
            'city': ex.get('city', 'unknown'),
            'state': ex.get('state', 'unknown'),
            'true_label': 'Valid' if true_label == 1 else 'Invalid',
            'pred_label': prediction,
            'confidence': round(valid_prob, 4),
            'is_correct': is_correct,
            'passages': passages[:3],
            'passage_preview': passages[0][:200] + '...' if passages else 'N/A',
        })

    # Compute metrics from confusion matrix
    total = tp + tn + fp + fn
    accuracy = (tp + tn) / total if total > 0 else 0
    precision = tp / (tp + fp) if (tp + fp) > 0 else 0
    recall = tp / (tp + fn) if (tp + fn) > 0 else 0
    f1 = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0

    confusion_matrix = {
        'true_valid_pred_valid': tp,
        'true_invalid_pred_invalid': tn,
        'true_invalid_pred_valid': fp,
        'true_valid_pred_invalid': fn,
    }

    # Summary stats
    correct_count = sum(1 for e in examples_with_predictions if e['is_correct'])
    false_positives = fp
    false_negatives = fn

    return {
        'metrics': {
            'accuracy': round(accuracy, 4),
            'precision': round(precision, 4),
            'recall': round(recall, 4),
            'f1': round(f1, 4),
        },
        'confusion_matrix': confusion_matrix,
        'examples': examples_with_predictions,
        'summary': {
            'total': len(examples_with_predictions),
            'correct': correct_count,
            'false_positives': false_positives,
            'false_negatives': false_negatives,
        }
    }


def compute_city_comparison(
    extractor_path: Path,
    validator_path: Path,
    test_data: List[dict],
) -> Dict:
    """Compute city-level zone code comparison."""
    print(f"Loading models for city comparison...")
    tokenizer = AutoTokenizer.from_pretrained(str(extractor_path))
    extractor = AutoModelForTokenClassification.from_pretrained(str(extractor_path))
    validator = AutoModelForSequenceClassification.from_pretrained(str(validator_path))
    extractor.eval()
    validator.eval()

    # Group by city
    city_data = {}
    for ex in test_data:
        city_key = f"{ex.get('city', 'unknown')}, {ex.get('state', 'unknown')}"
        if city_key not in city_data:
            city_data[city_key] = {
                'city': ex.get('city', 'unknown'),
                'state': ex.get('state', 'unknown'),
                'true_zones': set(),
                'pred_zones_raw': set(),
                'pred_zones_validated': set(),
                'example_count': 0,
                'examples': [],
            }

        # Extract true zones
        true_zones = extract_zones_from_bio(ex['tokens'], ex['tags'])
        for z in true_zones:
            city_data[city_key]['true_zones'].add(normalize_zone_code(z))

        city_data[city_key]['example_count'] += 1
        city_data[city_key]['examples'].append(ex)

    print(f"Processing {len(city_data)} cities...")

    # Run predictions for each city
    for city_key, data in city_data.items():
        print(f"  Processing {city_key}...")
        city_examples = data['examples']

        # Sample up to 100 examples per city
        sample_size = min(100, len(city_examples))
        indices = np.random.choice(len(city_examples), sample_size, replace=False)

        for idx in indices:
            ex = city_examples[idx]
            tokens = ex['tokens']

            # Extractor prediction
            input_ids = tokenizer.convert_tokens_to_ids(tokens)
            inputs = torch.tensor([input_ids])

            with torch.no_grad():
                outputs = extractor(inputs)
                predictions = torch.argmax(outputs.logits, dim=2)

            pred_tags = [EXTRACTOR_ID_TO_LABEL[p.item()] for p in predictions[0]][:len(tokens)]
            pred_zones = extract_zones_from_bio(tokens, pred_tags)

            # Reconstruct passage for validator
            passage_text = ' '.join(tokens).replace(' ##', '').replace('##', '')

            for z in pred_zones:
                normalized = normalize_zone_code(z)
                data['pred_zones_raw'].add(normalized)

                # Validator prediction
                input_text = f"[CODE] {z} [SEP] {passage_text}"
                val_inputs = tokenizer(
                    input_text,
                    truncation=True,
                    max_length=512,
                    return_tensors="pt"
                )

                with torch.no_grad():
                    val_outputs = validator(**val_inputs)
                    probs = torch.softmax(val_outputs.logits, dim=1)

                if probs[0][1].item() >= 0.5:
                    data['pred_zones_validated'].add(normalized)

        # Remove examples from output (too large)
        del data['examples']

    # Build results
    results = []
    for city_key, data in city_data.items():
        true_set = data['true_zones']
        pred_set_raw = data['pred_zones_raw']
        pred_set_validated = data['pred_zones_validated']

        # Raw metrics
        common_raw = true_set & pred_set_raw
        precision_raw = len(common_raw) / len(pred_set_raw) if pred_set_raw else 0
        recall_raw = len(common_raw) / len(true_set) if true_set else 0
        f1_raw = 2 * precision_raw * recall_raw / (precision_raw + recall_raw) if (precision_raw + recall_raw) > 0 else 0

        # Validated metrics
        common_validated = true_set & pred_set_validated
        precision_validated = len(common_validated) / len(pred_set_validated) if pred_set_validated else 0
        recall_validated = len(common_validated) / len(true_set) if true_set else 0
        f1_validated = 2 * precision_validated * recall_validated / (precision_validated + recall_validated) if (precision_validated + recall_validated) > 0 else 0

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
            'pred_zones_validated': sorted(pred_set_validated),
            'pred_count_validated': len(pred_set_validated),
            'common_zones_validated': sorted(common_validated),
            'extra_zones_validated': sorted(pred_set_validated - true_set),
            'precision_validated': round(precision_validated, 2),
            'recall_validated': round(recall_validated, 2),
            'f1_validated': round(f1_validated, 2),
            'missed_zones': sorted(true_set - pred_set_raw),
            'missed_zones_validated': sorted(true_set - pred_set_validated),
            # Legacy fields
            'pred_zones': sorted(pred_set_raw),
            'pred_count': len(pred_set_raw),
            'common_zones': sorted(common_raw),
            'extra_zones': sorted(pred_set_raw - true_set),
            'precision': round(precision_raw, 2),
            'recall': round(recall_raw, 2),
            'f1': round(f1_raw, 2),
        })

    results.sort(key=lambda x: (x['state'], x['city']))

    return {
        'cities': results,
        'total_cities': len(results),
    }


def main():
    parser = argparse.ArgumentParser(description='Pre-compute metrics for dashboard')
    parser.add_argument('--extractor', default='extractor_v1', help='Extractor model name')
    parser.add_argument('--validator', default='validator_v3', help='Validator model name')
    parser.add_argument('--skip-city-comparison', action='store_true', help='Skip city comparison (slow)')
    args = parser.parse_args()

    extractor_path = TRAINED_MODELS_DIR / args.extractor
    validator_path = TRAINED_MODELS_DIR / args.validator

    if not extractor_path.exists():
        print(f"Error: Extractor model not found at {extractor_path}")
        return
    if not validator_path.exists():
        print(f"Error: Validator model not found at {validator_path}")
        return

    # Load test data
    print("Loading test data...")
    extractor_test = load_jsonl(DATA_DIR / "test.jsonl")
    validator_test = load_jsonl(DATA_DIR / "validator_test.jsonl")
    extractor_train = load_jsonl(DATA_DIR / "train.jsonl")
    validator_train = load_jsonl(DATA_DIR / "validator_train.jsonl")

    print(f"  Extractor: {len(extractor_train)} train, {len(extractor_test)} test")
    print(f"  Validator: {len(validator_train)} train, {len(validator_test)} test")

    # Compute extractor metrics
    print("\n" + "="*60)
    print("COMPUTING EXTRACTOR METRICS")
    print("="*60)
    extractor_results = compute_extractor_metrics(extractor_path, extractor_test)

    # Compute validator metrics
    print("\n" + "="*60)
    print("COMPUTING VALIDATOR METRICS")
    print("="*60)
    validator_results = compute_validator_metrics(validator_path, extractor_path, validator_test)

    # Compute city comparison (optional, slow)
    city_comparison = None
    if not args.skip_city_comparison:
        print("\n" + "="*60)
        print("COMPUTING CITY COMPARISON")
        print("="*60)
        city_comparison = compute_city_comparison(extractor_path, validator_path, extractor_test)

    # Get city lists
    extractor_train_cities = get_cities_from_data(extractor_train)
    extractor_test_cities = get_cities_from_data(extractor_test)
    validator_train_cities = get_cities_from_data(validator_train)
    validator_test_cities = get_cities_from_data(validator_test)

    # Build final metrics object
    metrics = {
        'computed_at': datetime.now().isoformat(),
        'extractor_model': args.extractor,
        'validator_model': args.validator,
        'extractor': {
            **extractor_results['metrics'],
            'train_examples': len(extractor_train),
            'test_examples': len(extractor_test),
            'train_city': format_city_list(extractor_train_cities),
            'test_city': format_city_list(extractor_test_cities),
            'train_city_count': len(extractor_train_cities),
            'test_city_count': len(extractor_test_cities),
            'train_cities_list': extractor_train_cities,
            'test_cities_list': extractor_test_cities,
            'metrics_source': 'Pre-computed from test data',
            'model_name': args.extractor,
        },
        'validator': {
            **validator_results['metrics'],
            'train_examples': len(validator_train),
            'test_examples': len(validator_test),
            'train_city': format_city_list(validator_train_cities),
            'test_city': format_city_list(validator_test_cities),
            'train_city_count': len(validator_train_cities),
            'test_city_count': len(validator_test_cities),
            'train_cities_list': validator_train_cities,
            'test_cities_list': validator_test_cities,
            'confusion_matrix': validator_results['confusion_matrix'],
            'metrics_source': 'Pre-computed from test data',
            'model_name': args.validator,
        },
    }

    # Save metrics summary
    metrics_file = TRAINED_MODELS_DIR / "cached_metrics.json"
    print(f"\nSaving metrics to {metrics_file}...")
    with open(metrics_file, 'w') as f:
        json.dump(metrics, f, indent=2)

    # Save extractor examples
    extractor_examples_file = TRAINED_MODELS_DIR / "cached_extractor_examples.json"
    print(f"Saving extractor examples to {extractor_examples_file}...")
    with open(extractor_examples_file, 'w') as f:
        json.dump({
            'examples': extractor_results['examples'][:50],  # Limit to 50 for dashboard
            'summary': extractor_results['summary'],
        }, f, indent=2)

    # Save validator examples
    validator_examples_file = TRAINED_MODELS_DIR / "cached_validator_examples.json"
    print(f"Saving validator examples to {validator_examples_file}...")
    with open(validator_examples_file, 'w') as f:
        json.dump({
            'examples': validator_results['examples'],
            'summary': validator_results['summary'],
        }, f, indent=2)

    # Save city comparison
    if city_comparison:
        city_comparison_file = TRAINED_MODELS_DIR / "cached_city_comparison.json"
        print(f"Saving city comparison to {city_comparison_file}...")
        with open(city_comparison_file, 'w') as f:
            json.dump(city_comparison, f, indent=2)

    print("\n" + "="*60)
    print("METRICS COMPUTATION COMPLETE")
    print("="*60)
    print(f"\nExtractor: P={metrics['extractor']['precision']:.2f}, R={metrics['extractor']['recall']:.2f}, F1={metrics['extractor']['f1']:.2f}")
    print(f"Validator: A={metrics['validator']['accuracy']:.2f}, P={metrics['validator']['precision']:.2f}, R={metrics['validator']['recall']:.2f}, F1={metrics['validator']['f1']:.2f}")
    print(f"\nCached files saved to: {TRAINED_MODELS_DIR}")


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


if __name__ == "__main__":
    main()
