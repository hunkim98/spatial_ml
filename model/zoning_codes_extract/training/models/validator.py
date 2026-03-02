#!/usr/bin/env python3
"""
Train and evaluate the validator model (sequence classification for zone code validation).
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
    AutoModelForSequenceClassification,
    TrainingArguments,
    Trainer,
    DataCollatorWithPadding,
)
from datasets import Dataset
from sklearn.metrics import classification_report, confusion_matrix
import wandb

# Import shared modules
from .callbacks import MPSMemoryCallback, MetricHighlightCallback, ProgressCallback, EpochProgressCallback
from .metrics import create_sequence_classification_metrics

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

def load_examples_from_jsonl(file_path: Path, tokenizer) -> List[Dict]:
    """Load validator examples from a JSONL file."""
    examples = []
    with open(file_path) as f:
        for line in f:
            ex = json.loads(line)

            # Handle both 'text' and 'passages' fields
            if 'text' in ex:
                text = ex['text']
            elif 'passages' in ex:
                # Join passages with newline separator
                text = ' '.join(ex['passages'])
            else:
                raise ValueError(f"Example missing 'text' or 'passages' field: {ex}")

            encoding = tokenizer(
                text,
                truncation=True,
                max_length=512,
                padding=False
            )
            examples.append({
                'input_ids': encoding['input_ids'],
                'attention_mask': encoding['attention_mask'],
                'label': ex['label'],
                'text': text,
                'city': ex.get('city', ''),
                'state': ex.get('state', ''),
            })
    return examples


def load_datasets():
    """Load train and test datasets."""
    ID_TO_LABEL = {0: "not_zone", 1: "zone"}
    LABEL_TO_ID = {0: 0, 1: 1}

    tokenizer = AutoTokenizer.from_pretrained(config.model_name)

    train_file = DATA_DIR / "train_validator.jsonl"
    test_file = DATA_DIR / "test_validator.jsonl"

    if not train_file.exists():
        raise FileNotFoundError(f"Training data not found: {train_file}")

    train_examples = load_examples_from_jsonl(train_file, tokenizer)

    # Check if test file exists and has data
    test_examples = []
    if test_file.exists():
        test_examples = load_examples_from_jsonl(test_file, tokenizer)

    # If test set is empty, create one from train data (15% split)
    if not test_examples:
        print("WARNING: Test set is empty. Creating validation split from train data (15%)...")
        random.shuffle(train_examples)
        split_idx = int(len(train_examples) * 0.85)
        test_examples = train_examples[split_idx:]
        train_examples = train_examples[:split_idx]
        print(f"Created test split: {len(test_examples)} examples")

    train_ds = Dataset.from_list(train_examples)
    test_ds = Dataset.from_list(test_examples)

    print(f"Loaded {len(train_examples)} train examples, {len(test_examples)} test examples")

    return train_ds, test_ds, tokenizer, LABEL_TO_ID, ID_TO_LABEL


# ============================================================================
# Training
# ============================================================================

def train_validator():
    """Train the validator model."""
    print("\n" + "="*60)
    print("TRAINING VALIDATOR MODEL (Sequence Classification)")
    print("="*60)

    # Load data
    train_ds, test_ds, tokenizer, label_to_id, id_to_label = load_datasets()

    # Count labels
    label_counts = {id_to_label[0]: 0, id_to_label[1]: 0}
    for ex in train_ds:
        label_counts[id_to_label[ex['label']]] += 1
    print(f"\nLabel distribution in train: {label_counts}")

    # Create model
    model = AutoModelForSequenceClassification.from_pretrained(
        config.model_name,
        num_labels=2,
        id2label=id_to_label,
        label2id=label_to_id
    )

    # Create compute_metrics and data collator
    compute_metrics = create_sequence_classification_metrics(id_to_label)
    data_collator = DataCollatorWithPadding(tokenizer=tokenizer)

    # Training arguments
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_dir = OUTPUT_DIR / f"validator_{timestamp}"
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
        metric_for_best_model=config.validator_metric,
        greater_is_better=True,
        seed=config.seed,
        report_to="wandb",
        run_name=f"validator_{timestamp}",
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
            ProgressCallback('validator'),
            EpochProgressCallback('validator'),
            MetricHighlightCallback('f1', 'validator')
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
                "model_type": "validator",
                "test_results": test_results,
                "training_config": {
                    "model_name": config.validator.model_name,
                    "num_epochs": config.validator.num_epochs,
                    "batch_size": config.validator.batch_size,
                    "learning_rate": config.validator.learning_rate,
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
                model_type="validator",
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

def qualitative_analysis(trainer, test_ds, tokenizer, id_to_label):
    """Perform qualitative analysis on validator predictions."""
    print("\n" + "="*60)
    print("QUALITATIVE ANALYSIS - VALIDATOR")
    print("="*60)

    predictions = trainer.predict(test_ds)
    pred_ids = np.argmax(predictions.predictions, axis=1)
    true_labels = predictions.label_ids

    # Show sample predictions
    print("\n--- Sample Predictions ---\n")

    num_examples = min(10, len(test_ds))
    indices = random.sample(range(len(test_ds)), num_examples)

    for idx in indices:
        example = test_ds[idx]
        true_label = id_to_label[true_labels[idx]]
        pred_label = id_to_label[pred_ids[idx]]

        print(f"Example {idx} ({example.get('city', 'unknown')}, {example.get('state', 'unknown')}):")
        print(f"  Text: {example['text'][:100]}...")
        print(f"  True: {true_label}, Pred: {pred_label}")

        if true_label == pred_label:
            print("  ✓ CORRECT")
        else:
            print("  ✗ INCORRECT")
        print()

    # Confusion matrix
    cm = confusion_matrix(true_labels, pred_ids)
    print("\n--- Confusion Matrix ---")
    print("                 Predicted")
    print("                 Not Zone  Zone")
    print(f"Actual Not Zone    {cm[0,0]:4d}    {cm[0,1]:4d}")
    print(f"       Zone        {cm[1,0]:4d}    {cm[1,1]:4d}")

    # Classification report
    print("\n--- Classification Report ---")
    print(classification_report(true_labels, pred_ids,
                               target_names=['Not Zone', 'Zone']))

    # Log to W&B
    try:
        # Get probabilities for confidence scores
        probs = np.exp(predictions.predictions) / np.exp(predictions.predictions).sum(axis=1, keepdims=True)
        confidences = np.max(probs, axis=1)

        # Create sample predictions table
        table_data = []

        # Collect false positives and false negatives
        fps = [(i, confidences[i]) for i in range(len(test_ds)) if true_labels[i] == 0 and pred_ids[i] == 1]
        fns = [(i, confidences[i]) for i in range(len(test_ds)) if true_labels[i] == 1 and pred_ids[i] == 0]
        tps = [(i, confidences[i]) for i in range(len(test_ds)) if true_labels[i] == 1 and pred_ids[i] == 1]
        tns = [(i, confidences[i]) for i in range(len(test_ds)) if true_labels[i] == 0 and pred_ids[i] == 0]

        # Sample from each category
        for category, samples in [("FP", fps[:5]), ("FN", fns[:5]), ("TP", tps[:5]), ("TN", tns[:5])]:
            for idx, conf in samples:
                example = test_ds[idx]
                true_label = id_to_label[true_labels[idx]]
                pred_label = id_to_label[pred_ids[idx]]

                table_data.append([
                    category,
                    example.get('city', 'unknown'),
                    example.get('state', 'unknown'),
                    example['text'][:150] + "...",  # Truncate for display
                    true_label,
                    pred_label,
                    f"{conf:.3f}"
                ])

        table = wandb.Table(
            columns=["Type", "City", "State", "Text", "True Label", "Predicted Label", "Confidence"],
            data=table_data
        )
        wandb.log({"test/sample_predictions": table})

        # Log confusion matrix values
        tn, fp, fn, tp = cm.ravel()
        wandb.log({
            "test/true_negatives": int(tn),
            "test/false_positives": int(fp),
            "test/false_negatives": int(fn),
            "test/true_positives": int(tp),
            "test/fp_examples_count": len(fps),
            "test/fn_examples_count": len(fns),
        })

    except Exception as e:
        print(f"Warning: Could not log to W&B: {e}")


# ============================================================================
# Main
# ============================================================================

def main():
    # Print configuration
    config.print_config("validator")

    print(f"Data directory: {DATA_DIR}")
    print(f"Output directory: {OUTPUT_DIR}")

    # Load data stats for logging
    train_file = DATA_DIR / "train_validator.jsonl"
    test_file = DATA_DIR / "test_validator.jsonl"
    stats_file = DATA_DIR / "validator_stats.json"
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
    train_positive = 0
    train_negative = 0
    test_positive = 0
    test_negative = 0

    if train_file.exists():
        with open(train_file) as f:
            for line in f:
                ex = json.loads(line)
                train_cities.add(f"{ex.get('city', '')}_{ex.get('state', '')}")
                if ex.get('label') == 1:
                    train_positive += 1
                else:
                    train_negative += 1

    if test_file.exists():
        with open(test_file) as f:
            for line in f:
                ex = json.loads(line)
                test_cities.add(f"{ex.get('city', '')}_{ex.get('state', '')}")
                if ex.get('label') == 1:
                    test_positive += 1
                else:
                    test_negative += 1

    # Initialize wandb with comprehensive config
    wandb.init(
        entity=WANDB_ENTITY,
        project=WANDB_PROJECT,
        name=f"validator_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
        config={
            # Model config
            "model_type": "validator",
            "model_name": config.model_name,
            "task": "binary_classification",

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
            "data/positive_examples": data_stats.get('positive_examples', 0),
            "data/negative_examples": data_stats.get('negative_examples', 0),
            "data/train_positive": train_positive,
            "data/train_negative": train_negative,
            "data/test_positive": test_positive,
            "data/test_negative": test_negative,
            "data/class_balance_ratio": train_positive / train_negative if train_negative > 0 else 0,

            # City splits info
            "data/n_cities_requested": city_splits.get('metadata', {}).get('total_cities'),
            "data/train_ratio": city_splits.get('metadata', {}).get('train_ratio', 0.85),
            "data/test_ratio": city_splits.get('metadata', {}).get('test_ratio', 0.15),

            # Reproducibility
            "data_prep_timestamp": data_stats.get('timestamp', 'unknown'),
        },
        tags=["validator", "binary-classification", "zone-validation"]
    )

    # Log city lists as artifacts
    if city_splits:
        wandb.config.update({
            "cities/train": city_splits.get('train', []),
            "cities/test": city_splits.get('test', []),
        }, allow_val_change=True)

    print(f"Wandb initialized: {wandb.run.url}")

    # Train
    trainer, test_ds, tokenizer, id_to_label = train_validator()

    # Qualitative analysis
    qualitative_analysis(trainer, test_ds, tokenizer, id_to_label)

    print("\n" + "="*60)
    print("TRAINING COMPLETE")
    print("="*60)

    wandb.finish()


if __name__ == "__main__":
    main()
