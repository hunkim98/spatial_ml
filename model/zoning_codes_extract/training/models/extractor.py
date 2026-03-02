#!/usr/bin/env python3
"""
Train and evaluate the extractor model (token classification for zone code extraction).
"""

import json
import os
import random
from pathlib import Path
from typing import List, Dict
from datetime import datetime

import numpy as np
import torch

# Disable MPS to force CPU-only training (avoid memory issues)
os.environ['PYTORCH_ENABLE_MPS_FALLBACK'] = '0'
torch.backends.mps.is_available = lambda: False

from dotenv import load_dotenv
from transformers import (
    AutoTokenizer,
    AutoModelForTokenClassification,
    TrainingArguments,
    Trainer,
    DataCollatorForTokenClassification,
)
from datasets import Dataset
from seqeval.metrics import classification_report as ner_classification_report
import wandb

# Import shared modules
from .callbacks import MPSMemoryCallback, MetricHighlightCallback, ProgressCallback, EpochProgressCallback
from .metrics import create_token_classification_metrics

# Import configuration
sys.path.append(str(Path(__file__).parent.parent / "utils"))
from config import get_config

# Load environment variables
ENV_FILE = Path(__file__).parent.parent.parent.parent / "secrets" / "teamspatially-project.env"
if ENV_FILE.exists():
    load_dotenv(ENV_FILE)

WANDB_PROJECT = os.getenv("WANDB_PROJECT", "zoning-code-extraction")
WANDB_ENTITY = os.getenv("WANDB_ENTITY", "spatially")

# Load training configuration
config = get_config()

# Configuration
SCRIPT_DIR = Path(__file__).parent.parent.resolve()
PROJECT_DIR = SCRIPT_DIR.parent
DATA_DIR = SCRIPT_DIR / "data"
OUTPUT_DIR = PROJECT_DIR / "artifacts" / "models"

# Set seeds
torch.manual_seed(config.seed)
np.random.seed(config.seed)
random.seed(config.seed)


# ============================================================================
# Data Loading
# ============================================================================

def load_examples_from_jsonl(file_path: Path, tokenizer, label_to_id: Dict[str, int]) -> List[Dict]:
    """Load examples from a JSONL file."""
    examples = []
    with open(file_path) as f:
        for line in f:
            ex = json.loads(line)
            input_ids = tokenizer.convert_tokens_to_ids(ex['tokens'])
            labels = [label_to_id[tag] for tag in ex['tags']]
            examples.append({
                'input_ids': input_ids,
                'labels': labels,
                'city': ex.get('city', ''),
                'state': ex.get('state', ''),
                'tokens': ex['tokens']
            })
    return examples


def load_datasets():
    """Load train and test datasets."""
    LABEL_LIST = ['O', 'B-ZONE', 'I-ZONE']
    LABEL_TO_ID = {label: i for i, label in enumerate(LABEL_LIST)}
    ID_TO_LABEL = {i: label for label, i in LABEL_TO_ID.items()}

    tokenizer = AutoTokenizer.from_pretrained(config.model_name)

    train_file = DATA_DIR / "train_extractor.jsonl"
    test_file = DATA_DIR / "test_extractor.jsonl"

    if not train_file.exists():
        raise FileNotFoundError(f"Training data not found: {train_file}")
    if not test_file.exists():
        raise FileNotFoundError(f"Test data not found: {test_file}")

    train_examples = load_examples_from_jsonl(train_file, tokenizer, LABEL_TO_ID)
    test_examples = load_examples_from_jsonl(test_file, tokenizer, LABEL_TO_ID)

    train_ds = Dataset.from_list(train_examples)
    test_ds = Dataset.from_list(test_examples)

    print(f"Loaded {len(train_examples)} train examples, {len(test_examples)} test examples")

    return train_ds, test_ds, tokenizer, LABEL_TO_ID, ID_TO_LABEL


# ============================================================================
# Training
# ============================================================================

def train_extractor():
    """Train the extractor model."""
    print("\n" + "="*60)
    print("TRAINING EXTRACTOR MODEL (Token Classification)")
    print("="*60)

    # Load data
    train_ds, test_ds, tokenizer, label_to_id, id_to_label = load_datasets()

    # Count labels
    label_counts = {label: 0 for label in id_to_label.values()}
    for ex in train_ds:
        for label_id in ex['labels']:
            label_counts[id_to_label[label_id]] += 1
    print(f"\nLabel distribution in train: {label_counts}")

    # Create model
    model = AutoModelForTokenClassification.from_pretrained(
        config.model_name,
        num_labels=len(label_to_id),
        id2label=id_to_label,
        label2id=label_to_id
    )

    # Create compute_metrics and data collator
    compute_metrics = create_token_classification_metrics(id_to_label)
    data_collator = DataCollatorForTokenClassification(
        tokenizer=tokenizer,
        padding=True,
        max_length=config.max_seq_length
    )

    # Training arguments
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_dir = OUTPUT_DIR / f"extractor_{timestamp}"
    output_dir.mkdir(parents=True, exist_ok=True)

    training_args = TrainingArguments(
        output_dir=str(output_dir),
        eval_strategy=config.eval_strategy,
        save_strategy=config.save_strategy,
        learning_rate=config.learning_rate,
        per_device_train_batch_size=config.batch_size,
        per_device_eval_batch_size=config.batch_size,
        gradient_accumulation_steps=config.gradient_accumulation_steps,
        num_train_epochs=config.num_epochs,
        weight_decay=config.weight_decay,
        warmup_steps=config.warmup_steps,
        logging_steps=config.logging_steps,
        load_best_model_at_end=config.load_best_model,
        metric_for_best_model=config.extractor_metric,
        greater_is_better=True,
        seed=config.seed,
        report_to="wandb",
        run_name=f"extractor_{timestamp}",
        dataloader_pin_memory=config.pin_memory,
        dataloader_num_workers=config.dataloader_workers,
        fp16=config.fp16,
        bf16=config.bf16,
        gradient_checkpointing=config.gradient_checkpointing,
        disable_tqdm=False,  # Enable tqdm progress bars
        log_level="info",
    )

    # Enable gradient checkpointing
    model.gradient_checkpointing_enable()

    # Trainer
    trainer = Trainer(
        model=model,
        args=training_args,
        train_dataset=train_ds,
        eval_dataset=test_ds,
        processing_class=tokenizer,
        data_collator=data_collator,
        compute_metrics=compute_metrics,
        callbacks=[
            MPSMemoryCallback(),
            ProgressCallback('extractor'),
            EpochProgressCallback('extractor'),
            MetricHighlightCallback('recall', 'extractor')
        ],
    )

    # Train
    print("\nStarting training...")
    try:
        trainer.train()
    except KeyboardInterrupt:
        print("\n\nTraining interrupted by user. Saving current model state...")
    except Exception as e:
        print(f"\n\nTraining failed with error: {e}")
        print("Saving current model state...")

    # Evaluate on test set
    print("\n--- Test Set Evaluation ---")
    test_results = trainer.evaluate(test_ds)
    print(f"Test Results: {json.dumps(test_results, indent=2)}")

    # Save model (ensure this always happens)
    print(f"\nSaving model to {output_dir}...")
    trainer.save_model(str(output_dir))
    tokenizer.save_pretrained(str(output_dir))
    print(f"✓ Model saved successfully")

    # Verify model files exist
    required_files = ['config.json', 'model.safetensors', 'tokenizer.json']
    missing_files = [f for f in required_files if not (output_dir / f).exists()]
    if missing_files:
        print(f"WARNING: Missing files: {missing_files}")
        print("Model may not load correctly!")
    else:
        print(f"✓ All required files present")

    # Save test results
    with open(output_dir / "test_results.json", 'w') as f:
        json.dump(test_results, f, indent=2)

    # Upload to GCS if enabled
    upload_to_gcs = os.getenv("UPLOAD_TO_GCS", "0") == "1"
    if upload_to_gcs:
        try:
            print("\n" + "=" * 60)
            print("Uploading model to GCS...")
            print("=" * 60)

            # Import GCS model manager
            import sys
            sys.path.append(str(Path(__file__).parent.parent / "utils"))
            from gcs_model_manager import upload_model_to_gcs

            # Prepare metadata
            metadata = {
                "model_type": "extractor",
                "test_results": test_results,
                "training_config": {
                    "model_name": config.extractor.model_name,
                    "num_epochs": config.extractor.num_epochs,
                    "batch_size": config.extractor.batch_size,
                    "learning_rate": config.extractor.learning_rate,
                },
                "dataset_size": len(train_ds) + len(test_ds),
                "train_size": len(train_ds),
                "test_size": len(test_ds),
            }

            # Add W&B URL if available
            if wandb.run is not None:
                metadata["wandb_url"] = wandb.run.get_url()

            # Upload model
            gcs_path = upload_model_to_gcs(
                model_dir=output_dir,
                model_type="extractor",
                metadata=metadata
            )

            if gcs_path:
                print(f"✓ Model uploaded to: {gcs_path}")
            else:
                print("⚠ Model upload failed, but training completed successfully")

        except Exception as e:
            print(f"⚠ Failed to upload model to GCS: {e}")
            print("Training completed successfully, model saved locally")

    return trainer, test_ds, tokenizer, id_to_label


# ============================================================================
# Qualitative Analysis
# ============================================================================

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

    zones = [z for z in zones if z not in ['[CLS]', '[SEP]', '[PAD]']]
    return zones


def qualitative_analysis(trainer, test_ds, tokenizer, id_to_label):
    """Perform qualitative analysis on extractor predictions."""
    print("\n" + "="*60)
    print("QUALITATIVE ANALYSIS - EXTRACTOR")
    print("="*60)

    predictions = trainer.predict(test_ds)
    pred_ids = np.argmax(predictions.predictions, axis=2)

    # Show sample predictions
    print("\n--- Sample Predictions ---\n")

    num_examples = min(10, len(test_ds))
    indices = random.sample(range(len(test_ds)), num_examples)

    for idx in indices:
        example = test_ds[idx]
        tokens = example['tokens']
        true_labels = [id_to_label.get(l, 'PAD') if l != -100 else 'PAD' for l in example['labels']]
        pred_labels = [id_to_label[p] for p in pred_ids[idx][:len(tokens)]]

        true_zones = extract_zones_from_bio(tokens, true_labels)
        pred_zones = extract_zones_from_bio(tokens, pred_labels)

        print(f"Example {idx} ({example.get('city', 'unknown')}, {example.get('state', 'unknown')}):")
        print(f"  True zones: {true_zones}")
        print(f"  Pred zones: {pred_zones}")

        if set(true_zones) == set(pred_zones):
            print("  ✓ CORRECT")
        elif set(true_zones) & set(pred_zones):
            print("  ~ PARTIAL")
        else:
            print("  ✗ INCORRECT")
        print()

    # Overall statistics
    all_true_zones = []
    all_pred_zones = []

    for idx in range(len(test_ds)):
        example = test_ds[idx]
        tokens = example['tokens']
        true_labels = [id_to_label.get(l, 'PAD') if l != -100 else 'PAD' for l in example['labels']]
        pred_labels = [id_to_label[p] for p in pred_ids[idx][:len(tokens)]]

        true_zones = extract_zones_from_bio(tokens, true_labels)
        pred_zones = extract_zones_from_bio(tokens, pred_labels)

        all_true_zones.extend(true_zones)
        all_pred_zones.extend(pred_zones)

    print("\n--- Zone Code Statistics ---")
    print(f"Unique true zone codes: {len(set(all_true_zones))}")
    print(f"Unique pred zone codes: {len(set(all_pred_zones))}")

    # Exact match rate
    correct = sum(
        1 for idx in range(len(test_ds))
        if set(extract_zones_from_bio(
            test_ds[idx]['tokens'],
            [id_to_label.get(l, 'PAD') if l != -100 else 'PAD' for l in test_ds[idx]['labels']]
        )) == set(extract_zones_from_bio(
            test_ds[idx]['tokens'],
            [id_to_label[p] for p in pred_ids[idx][:len(test_ds[idx]['tokens'])]]
        ))
    )
    print(f"\nExact match rate: {correct}/{len(test_ds)} = {correct/len(test_ds)*100:.1f}%")

    # Log to W&B
    try:
        # Log overall entity-level metrics
        wandb.log({
            "test/exact_match_rate": correct/len(test_ds),
            "test/unique_true_zones": len(set(all_true_zones)),
            "test/unique_pred_zones": len(set(all_pred_zones)),
        })

        # Create sample predictions table
        table_data = []
        for idx in indices[:20]:  # Log up to 20 samples
            example = test_ds[idx]
            tokens = example['tokens']
            true_labels = [id_to_label.get(l, 'PAD') if l != -100 else 'PAD' for l in example['labels']]
            pred_labels = [id_to_label[p] for p in pred_ids[idx][:len(tokens)]]

            true_zones = extract_zones_from_bio(tokens, true_labels)
            pred_zones = extract_zones_from_bio(tokens, pred_labels)

            # Determine correctness
            if set(true_zones) == set(pred_zones):
                status = "✓ Correct"
            elif set(true_zones) & set(pred_zones):
                status = "~ Partial"
            else:
                status = "✗ Incorrect"

            table_data.append([
                example.get('city', 'unknown'),
                example.get('state', 'unknown'),
                " ".join(tokens)[:100] + "...",  # Truncate for display
                ", ".join(true_zones),
                ", ".join(pred_zones),
                status
            ])

        table = wandb.Table(
            columns=["City", "State", "Text", "True Zones", "Predicted Zones", "Status"],
            data=table_data
        )
        wandb.log({"test/sample_predictions": table})
    except Exception as e:
        print(f"Warning: Could not log to W&B: {e}")


# ============================================================================
# Main
# ============================================================================

def main():
    # Print configuration
    config.print_config("extractor")

    print(f"Data directory: {DATA_DIR}")
    print(f"Output directory: {OUTPUT_DIR}")

    # Load data stats for logging
    train_file = DATA_DIR / "train_extractor.jsonl"
    test_file = DATA_DIR / "test_extractor.jsonl"
    stats_file = DATA_DIR / "extractor_stats.json"
    city_splits_file = DATA_DIR / "city_splits.json"

    # Load statistics
    data_stats = {}
    if stats_file.exists():
        with open(stats_file) as f:
            data_stats = json.load(f)

    # Load city splits
    city_splits = {}
    if city_splits_file.exists():
        with open(city_splits_file) as f:
            city_splits = json.load(f)

    # Compute additional stats from data files
    train_cities = set()
    test_cities = set()
    train_tokens = 0
    test_tokens = 0
    train_zone_tokens = 0
    test_zone_tokens = 0

    with open(train_file) as f:
        for line in f:
            ex = json.loads(line)
            train_cities.add(f"{ex.get('city', '')}_{ex.get('state', '')}")
            train_tokens += len(ex['tokens'])
            train_zone_tokens += sum(1 for tag in ex['tags'] if tag != 'O')

    with open(test_file) as f:
        for line in f:
            ex = json.loads(line)
            test_cities.add(f"{ex.get('city', '')}_{ex.get('state', '')}")
            test_tokens += len(ex['tokens'])
            test_zone_tokens += sum(1 for tag in ex['tags'] if tag != 'O')

    # Initialize wandb with comprehensive config
    wandb.init(
        entity=WANDB_ENTITY,
        project=WANDB_PROJECT,
        name=f"extractor_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
        config={
            # Model config
            "model_type": "extractor",
            "model_name": config.model_name,
            "task": "token_classification",

            # Training hyperparameters
            "num_epochs": config.num_epochs,
            "batch_size": config.batch_size,
            "gradient_accumulation_steps": config.gradient_accumulation_steps,
            "effective_batch_size": config.effective_batch_size,
            "learning_rate": config.learning_rate,
            "warmup_steps": config.warmup_steps,
            "weight_decay": config.weight_decay,
            "seed": config.seed,

            # Data statistics
            "data/train_examples": data_stats.get('splits', {}).get('train', 0),
            "data/test_examples": data_stats.get('splits', {}).get('test', 0),
            "data/train_cities": len(train_cities),
            "data/test_cities": len(test_cities),
            "data/total_cities": data_stats.get('num_cities', len(train_cities) + len(test_cities)),
            "data/train_tokens": train_tokens,
            "data/test_tokens": test_tokens,
            "data/train_zone_tokens": train_zone_tokens,
            "data/test_zone_tokens": test_zone_tokens,
            "data/zone_token_ratio_train": train_zone_tokens / train_tokens if train_tokens > 0 else 0,

            # City splits info
            "data/n_cities_requested": city_splits.get('metadata', {}).get('total_cities'),
            "data/train_ratio": city_splits.get('metadata', {}).get('train_ratio', 0.85),
            "data/test_ratio": city_splits.get('metadata', {}).get('test_ratio', 0.15),

            # Reproducibility
            "data_prep_timestamp": data_stats.get('timestamp', 'unknown'),
        },
        tags=["extractor", "token-classification", "zone-extraction"]
    )

    # Log city lists as artifacts
    if city_splits:
        wandb.config.update({
            "cities/train": city_splits.get('train', []),
            "cities/test": city_splits.get('test', []),
        }, allow_val_change=True)

    print(f"Wandb initialized: {wandb.run.url}")

    # Train
    trainer, test_ds, tokenizer, id_to_label = train_extractor()

    # Qualitative analysis
    qualitative_analysis(trainer, test_ds, tokenizer, id_to_label)

    print("\n" + "="*60)
    print("TRAINING COMPLETE")
    print("="*60)

    wandb.finish()


if __name__ == "__main__":
    main()
