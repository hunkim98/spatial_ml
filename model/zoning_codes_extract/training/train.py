#!/usr/bin/env python3
"""
Train and evaluate both extractor and validator models.
Includes qualitative analysis of predictions.
"""

import json
import os
import random
from pathlib import Path
from dataclasses import dataclass
from typing import List, Dict, Tuple

import numpy as np
import torch
from dotenv import load_dotenv
from transformers import (
    AutoTokenizer,
    AutoModelForTokenClassification,
    AutoModelForSequenceClassification,
    TrainingArguments,
    Trainer,
    TrainerCallback,
    DataCollatorForTokenClassification,
    DataCollatorWithPadding,
)
import gc


class MPSMemoryCallback(TrainerCallback):
    """Callback to clear MPS cache periodically to prevent memory buildup."""

    def on_step_end(self, args, state, control, **kwargs):
        # Clear cache every 100 steps
        if state.global_step % 100 == 0:
            if torch.backends.mps.is_available():
                torch.mps.empty_cache()
            gc.collect()

    def on_epoch_end(self, args, state, control, **kwargs):
        # Clear cache at end of each epoch
        if torch.backends.mps.is_available():
            torch.mps.empty_cache()
        gc.collect()
from datasets import Dataset, DatasetDict
from seqeval.metrics import classification_report as ner_classification_report
from sklearn.metrics import (
    accuracy_score,
    precision_recall_fscore_support,
    classification_report,
    confusion_matrix
)
import wandb

# Load environment variables (for WANDB_API_KEY)
ENV_FILE = Path(__file__).parent.parent.parent / "secrets" / "teamspatially-project.env"
if ENV_FILE.exists():
    load_dotenv(ENV_FILE)

# Initialize wandb
WANDB_PROJECT = "zoning-code-extraction"


# ============================================================================
# Configuration
# ============================================================================

# Get the script's directory for relative paths
SCRIPT_DIR = Path(__file__).parent.resolve()
PROJECT_DIR = SCRIPT_DIR.parent
DATA_DIR = PROJECT_DIR / "artifacts" / "data" / "full"
OUTPUT_DIR = PROJECT_DIR / "artifacts" / "models"
MODEL_NAME = "bert-base-uncased"
SEED = 42

# Training hyperparameters
NUM_EPOCHS = 3
BATCH_SIZE = 2  # Smaller batch to reduce per-step memory for MPS
GRADIENT_ACCUMULATION_STEPS = 8  # Effective batch size = 2 * 8 = 16
LEARNING_RATE = 3e-5
WARMUP_STEPS = 50

# Set seeds
torch.manual_seed(SEED)
np.random.seed(SEED)
random.seed(SEED)


# ============================================================================
# Extractor Training
# ============================================================================

def load_examples_from_jsonl(file_path: Path, tokenizer, label_to_id: Dict[str, int]) -> List[Dict]:
    """Load examples from a JSONL file."""
    examples = []
    with open(file_path) as f:
        for line in f:
            ex = json.loads(line)
            # Convert tokens back to input_ids
            input_ids = tokenizer.convert_tokens_to_ids(ex['tokens'])
            labels = [label_to_id[tag] for tag in ex['tags']]
            examples.append({
                'input_ids': input_ids,
                'labels': labels,
                'city': ex.get('city', ''),
                'state': ex.get('state', ''),
                'tokens': ex['tokens']  # Keep for analysis
            })
    return examples


def train_extractor():
    """Train the zone code extractor (token classification) model."""
    print("\n" + "="*60)
    print("TRAINING EXTRACTOR MODEL (Token Classification)")
    print("="*60)

    # Label mapping
    LABEL_LIST = ['O', 'B-ZONE', 'I-ZONE']
    LABEL_TO_ID = {label: i for i, label in enumerate(LABEL_LIST)}
    ID_TO_LABEL = {i: label for label, i in LABEL_TO_ID.items()}

    # Load tokenizer and model
    tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME)
    model = AutoModelForTokenClassification.from_pretrained(
        MODEL_NAME,
        num_labels=len(LABEL_LIST),
        id2label=ID_TO_LABEL,
        label2id=LABEL_TO_ID
    )

    # Load data
    datasets = {}
    for split in ['train', 'test']:
        file_path = DATA_DIR / f"{split}.jsonl"
        if not file_path.exists():
            continue

        examples = load_examples_from_jsonl(file_path, tokenizer, LABEL_TO_ID)
        datasets[split] = Dataset.from_list(examples)

    # Load negative examples and add to training data
    negative_file = DATA_DIR / "negative.jsonl"
    if negative_file.exists():
        print(f"\nLoading negative examples from {negative_file}...")
        negative_examples = load_examples_from_jsonl(negative_file, tokenizer, LABEL_TO_ID)
        print(f"  Loaded {len(negative_examples)} negative examples")

        # Merge with training data
        train_examples = list(datasets['train'])
        train_examples.extend(negative_examples)
        random.shuffle(train_examples)
        datasets['train'] = Dataset.from_list(train_examples)
        print(f"  Training set now has {len(datasets['train'])} examples")
    else:
        print(f"\nNo negative examples found at {negative_file}")
    
    # Use a portion of train as val
    train_ds = datasets['train']
    train_test_split = train_ds.train_test_split(test_size=0.15, seed=SEED)
    datasets['train'] = train_test_split['train']
    datasets['val'] = train_test_split['test']
    
    print(f"\nDataset sizes:")
    print(f"  Train: {len(datasets['train'])}")
    print(f"  Val: {len(datasets['val'])}")
    print(f"  Test: {len(datasets['test'])}")
    
    # Count labels in train
    label_counts = {l: 0 for l in LABEL_LIST}
    for ex in datasets['train']:
        for label_id in ex['labels']:
            label_counts[ID_TO_LABEL[label_id]] += 1
    print(f"\nLabel distribution in train: {label_counts}")
    
    # Compute metrics
    def compute_metrics(eval_pred):
        predictions, labels = eval_pred
        predictions = np.argmax(predictions, axis=2)
        
        true_labels = []
        pred_labels = []
        
        for pred_seq, label_seq in zip(predictions, labels):
            true_seq = []
            pred_seq_labels = []
            
            for pred_id, label_id in zip(pred_seq, label_seq):
                if label_id != -100:
                    true_seq.append(ID_TO_LABEL[label_id])
                    pred_seq_labels.append(ID_TO_LABEL[pred_id])
            
            if true_seq:
                true_labels.append(true_seq)
                pred_labels.append(pred_seq_labels)
        
        # Compute seqeval metrics
        from seqeval.metrics import f1_score, precision_score, recall_score
        return {
            "precision": precision_score(true_labels, pred_labels),
            "recall": recall_score(true_labels, pred_labels),
            "f1": f1_score(true_labels, pred_labels),
        }
    
    # Training arguments
    output_dir = OUTPUT_DIR / "extractor"
    output_dir.mkdir(parents=True, exist_ok=True)
    
    training_args = TrainingArguments(
        output_dir=str(output_dir),
        eval_strategy="epoch",
        save_strategy="epoch",
        learning_rate=LEARNING_RATE,
        per_device_train_batch_size=BATCH_SIZE,
        per_device_eval_batch_size=BATCH_SIZE,
        gradient_accumulation_steps=GRADIENT_ACCUMULATION_STEPS,
        num_train_epochs=NUM_EPOCHS,
        weight_decay=0.01,
        warmup_steps=WARMUP_STEPS,
        logging_steps=20,
        load_best_model_at_end=True,
        metric_for_best_model="f1",
        greater_is_better=True,
        seed=SEED,
        report_to="wandb",
        run_name="extractor",
        # MPS memory optimizations
        dataloader_pin_memory=False,  # MPS doesn't support pinned memory
        dataloader_num_workers=0,  # Avoid memory duplication from workers
        fp16=False,  # MPS doesn't support fp16
        bf16=False,  # bf16 can cause issues on some MPS versions
        gradient_checkpointing=True,  # Trade compute for memory
    )
    
    # Data collator
    data_collator = DataCollatorForTokenClassification(
        tokenizer=tokenizer,
        padding=True,
        max_length=512
    )

    # Enable gradient checkpointing on model for memory efficiency
    model.gradient_checkpointing_enable()

    # Trainer with MPS memory callback
    trainer = Trainer(
        model=model,
        args=training_args,
        train_dataset=datasets['train'],
        eval_dataset=datasets['val'],
        processing_class=tokenizer,
        data_collator=data_collator,
        compute_metrics=compute_metrics,
        callbacks=[MPSMemoryCallback()],
    )

    # Train
    print("\nStarting training...")
    trainer.train()
    
    # Evaluate on test set
    print("\n--- Test Set Evaluation ---")
    test_results = trainer.evaluate(datasets['test'])
    print(f"Test Results: {json.dumps(test_results, indent=2)}")
    
    # Detailed analysis on test
    predictions = trainer.predict(datasets['test'])
    pred_logits = predictions.predictions
    label_ids = predictions.label_ids
    pred_ids = np.argmax(pred_logits, axis=2)
    
    true_labels_all = []
    pred_labels_all = []
    
    for pred_seq, label_seq in zip(pred_ids, label_ids):
        true_seq = []
        pred_seq_labels = []
        for pred_id, label_id in zip(pred_seq, label_seq):
            if label_id != -100:
                true_seq.append(ID_TO_LABEL[label_id])
                pred_seq_labels.append(ID_TO_LABEL[pred_id])
        if true_seq:
            true_labels_all.append(true_seq)
            pred_labels_all.append(pred_seq_labels)
    
    print("\n--- Classification Report ---")
    print(ner_classification_report(true_labels_all, pred_labels_all))
    
    # Save model
    trainer.save_model(str(output_dir))
    tokenizer.save_pretrained(str(output_dir))
    
    return trainer, datasets, tokenizer, ID_TO_LABEL


def qualitative_analysis_extractor(trainer, datasets, tokenizer, ID_TO_LABEL):
    """Perform qualitative analysis on extractor predictions."""
    print("\n" + "="*60)
    print("QUALITATIVE ANALYSIS - EXTRACTOR")
    print("="*60)
    
    test_ds = datasets['test']
    predictions = trainer.predict(test_ds)
    pred_ids = np.argmax(predictions.predictions, axis=2)
    
    # Show some examples
    print("\n--- Sample Predictions ---\n")
    
    num_examples = min(10, len(test_ds))
    indices = random.sample(range(len(test_ds)), num_examples)
    
    for idx in indices:
        example = test_ds[idx]
        tokens = example['tokens']
        true_labels = [ID_TO_LABEL.get(l, 'PAD') if l != -100 else 'PAD' for l in example['labels']]
        pred_labels = [ID_TO_LABEL[p] for p in pred_ids[idx][:len(tokens)]]
        
        # Find zone code spans
        true_zones = extract_zones_from_bio(tokens, true_labels)
        pred_zones = extract_zones_from_bio(tokens, pred_labels)
        
        print(f"Example {idx} ({example.get('city', 'unknown')}, {example.get('state', 'unknown')}):")
        print(f"  True zones: {true_zones}")
        print(f"  Pred zones: {pred_zones}")
        
        # Check if correct
        if set(true_zones) == set(pred_zones):
            print("  ✓ CORRECT")
        elif set(true_zones) & set(pred_zones):
            print("  ~ PARTIAL (some overlap)")
        else:
            print("  ✗ INCORRECT")
        print()
    
    # Overall statistics
    all_true_zones = []
    all_pred_zones = []
    
    for idx in range(len(test_ds)):
        example = test_ds[idx]
        tokens = example['tokens']
        true_labels = [ID_TO_LABEL.get(l, 'PAD') if l != -100 else 'PAD' for l in example['labels']]
        pred_labels = [ID_TO_LABEL[p] for p in pred_ids[idx][:len(tokens)]]
        
        true_zones = extract_zones_from_bio(tokens, true_labels)
        pred_zones = extract_zones_from_bio(tokens, pred_labels)
        
        all_true_zones.extend(true_zones)
        all_pred_zones.extend(pred_zones)
    
    # Unique zone codes found
    print("\n--- Zone Codes Statistics ---")
    print(f"Unique true zone codes: {len(set(all_true_zones))} - {sorted(set(all_true_zones))[:20]}")
    print(f"Unique pred zone codes: {len(set(all_pred_zones))} - {sorted(set(all_pred_zones))[:20]}")
    
    # Exact match rate
    correct = 0
    for idx in range(len(test_ds)):
        example = test_ds[idx]
        tokens = example['tokens']
        true_labels = [ID_TO_LABEL.get(l, 'PAD') if l != -100 else 'PAD' for l in example['labels']]
        pred_labels = [ID_TO_LABEL[p] for p in pred_ids[idx][:len(tokens)]]
        
        true_zones = set(extract_zones_from_bio(tokens, true_labels))
        pred_zones = set(extract_zones_from_bio(tokens, pred_labels))
        
        if true_zones == pred_zones:
            correct += 1
    
    print(f"\nExact match rate: {correct}/{len(test_ds)} = {correct/len(test_ds)*100:.1f}%")


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
    
    # Clean up special tokens
    zones = [z for z in zones if z not in ['[CLS]', '[SEP]', '[PAD]']]
    return zones


# ============================================================================
# Validator Training
# ============================================================================

def train_validator():
    """Train the validator (binary classification) model."""
    print("\n" + "="*60)
    print("TRAINING VALIDATOR MODEL (Binary Classification)")
    print("="*60)
    
    # Load tokenizer and model
    tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME)
    model = AutoModelForSequenceClassification.from_pretrained(
        MODEL_NAME,
        num_labels=2
    )
    
    def prepare_input(code: str, passages: List[str]) -> str:
        combined_passages = " [SEP] ".join(passages[:5])
        return f"[CODE] {code} [SEP] {combined_passages}"
    
    # Load data
    datasets = {}
    for split in ['train', 'test']:
        file_path = DATA_DIR / f"validator_{split}.jsonl"
        if not file_path.exists():
            continue
        
        examples = []
        with open(file_path) as f:
            for line in f:
                ex = json.loads(line)
                examples.append({
                    'text': prepare_input(ex['code'], ex['passages']),
                    'label': ex['label'],
                    'code': ex['code'],
                    'city': ex['city'],
                    'state': ex['state'],
                    'passages': ex['passages']
                })
        
        # Tokenize
        def tokenize_fn(batch):
            return tokenizer(
                batch['text'],
                padding=False,
                truncation=True,
                max_length=512
            )
        
        ds = Dataset.from_list(examples)
        ds = ds.map(tokenize_fn, batched=True, remove_columns=['text'])
        datasets[split] = ds
    
    # Split train for validation
    train_ds = datasets['train']
    train_test_split = train_ds.train_test_split(test_size=0.2, seed=SEED)
    datasets['train'] = train_test_split['train']
    datasets['val'] = train_test_split['test']
    
    print(f"\nDataset sizes:")
    for split, ds in datasets.items():
        pos = sum(1 for l in ds['label'] if l == 1)
        neg = sum(1 for l in ds['label'] if l == 0)
        print(f"  {split}: {len(ds)} (valid: {pos}, invalid: {neg})")
    
    # Compute metrics
    def compute_metrics(eval_pred):
        predictions, labels = eval_pred
        predictions = np.argmax(predictions, axis=1)
        
        accuracy = accuracy_score(labels, predictions)
        precision, recall, f1, _ = precision_recall_fscore_support(
            labels, predictions, average='binary', pos_label=1
        )
        
        return {
            "accuracy": accuracy,
            "precision": precision,
            "recall": recall,
            "f1": f1,
        }
    
    # Training arguments
    output_dir = OUTPUT_DIR / "validator"
    output_dir.mkdir(parents=True, exist_ok=True)
    
    training_args = TrainingArguments(
        output_dir=str(output_dir),
        eval_strategy="epoch",
        save_strategy="epoch",
        learning_rate=LEARNING_RATE,
        per_device_train_batch_size=BATCH_SIZE,
        per_device_eval_batch_size=BATCH_SIZE,
        gradient_accumulation_steps=GRADIENT_ACCUMULATION_STEPS,
        num_train_epochs=NUM_EPOCHS,
        weight_decay=0.01,
        warmup_steps=WARMUP_STEPS,
        logging_steps=10,
        load_best_model_at_end=True,
        metric_for_best_model="f1",
        greater_is_better=True,
        seed=SEED,
        report_to="wandb",
        run_name="validator",
        # MPS memory optimizations
        dataloader_pin_memory=False,
        dataloader_num_workers=0,
        fp16=False,
        bf16=False,
        gradient_checkpointing=True,
    )
    
    # Data collator
    data_collator = DataCollatorWithPadding(tokenizer=tokenizer)

    # Enable gradient checkpointing on model for memory efficiency
    model.gradient_checkpointing_enable()

    # Trainer with MPS memory callback
    trainer = Trainer(
        model=model,
        args=training_args,
        train_dataset=datasets['train'],
        eval_dataset=datasets['val'],
        processing_class=tokenizer,
        data_collator=data_collator,
        compute_metrics=compute_metrics,
        callbacks=[MPSMemoryCallback()],
    )

    # Train
    print("\nStarting training...")
    trainer.train()
    
    # Evaluate on test set
    print("\n--- Test Set Evaluation ---")
    test_results = trainer.evaluate(datasets['test'])
    print(f"Test Results: {json.dumps(test_results, indent=2)}")
    
    # Detailed analysis
    predictions = trainer.predict(datasets['test'])
    pred_labels = np.argmax(predictions.predictions, axis=1)
    true_labels = predictions.label_ids
    
    print("\n--- Classification Report ---")
    print(classification_report(true_labels, pred_labels, target_names=['Invalid', 'Valid']))
    
    print("\n--- Confusion Matrix ---")
    cm = confusion_matrix(true_labels, pred_labels)
    print(f"                Predicted")
    print(f"              Invalid  Valid")
    print(f"True Invalid    {cm[0][0]:4d}   {cm[0][1]:4d}")
    print(f"     Valid      {cm[1][0]:4d}   {cm[1][1]:4d}")
    
    # Save model
    trainer.save_model(str(output_dir))
    tokenizer.save_pretrained(str(output_dir))
    
    return trainer, datasets


def qualitative_analysis_validator(trainer, datasets):
    """Perform qualitative analysis on validator predictions."""
    print("\n" + "="*60)
    print("QUALITATIVE ANALYSIS - VALIDATOR")
    print("="*60)
    
    test_ds = datasets['test']
    predictions = trainer.predict(test_ds)
    pred_labels = np.argmax(predictions.predictions, axis=1)
    pred_probs = torch.softmax(torch.tensor(predictions.predictions), dim=1).numpy()
    
    print("\n--- Sample Predictions ---\n")
    
    # Show all test examples (since it's small)
    for idx in range(len(test_ds)):
        example = test_ds[idx]
        code = example['code']
        true_label = example['label']
        pred_label = pred_labels[idx]
        confidence = pred_probs[idx][pred_label]
        
        true_str = "Valid" if true_label == 1 else "Invalid"
        pred_str = "Valid" if pred_label == 1 else "Invalid"
        
        status = "✓" if true_label == pred_label else "✗"
        
        print(f"{status} Code: {code:10s} | True: {true_str:8s} | Pred: {pred_str:8s} (conf: {confidence:.3f}) | {example['city']}, {example['state']}")
        
        # Show passage snippet for incorrect predictions
        if true_label != pred_label:
            passage_snippet = example['passages'][0][:100] + "..." if example['passages'] else "N/A"
            print(f"   Passage: {passage_snippet}")
    
    # Error analysis
    print("\n--- Error Analysis ---")
    false_positives = []
    false_negatives = []
    
    for idx in range(len(test_ds)):
        example = test_ds[idx]
        true_label = example['label']
        pred_label = pred_labels[idx]
        
        if true_label == 0 and pred_label == 1:
            false_positives.append(example['code'])
        elif true_label == 1 and pred_label == 0:
            false_negatives.append(example['code'])
    
    print(f"False Positives (predicted valid but invalid): {false_positives}")
    print(f"False Negatives (predicted invalid but valid): {false_negatives}")


# ============================================================================
# Main
# ============================================================================

def main():
    print("="*60)
    print("ZONE CODE EXTRACTION MODEL TRAINING & EVALUATION")
    print("="*60)
    print(f"\nData directory: {DATA_DIR}")
    print(f"Output directory: {OUTPUT_DIR}")
    print(f"Base model: {MODEL_NAME}")
    print(f"Epochs: {NUM_EPOCHS}, Batch size: {BATCH_SIZE}, LR: {LEARNING_RATE}")

    # Check for GPU - force CPU to avoid MPS memory issues with large datasets
    # device = "cuda" if torch.cuda.is_available() else "mps" if torch.backends.mps.is_available() else "cpu"
    device = "cpu"  # Force CPU for stability with large dataset
    print(f"Device: {device}")

    # Initialize wandb
    wandb.init(
        entity="spatially",
        project=WANDB_PROJECT,
        config={
            "model_name": MODEL_NAME,
            "num_epochs": NUM_EPOCHS,
            "batch_size": BATCH_SIZE,
            "learning_rate": LEARNING_RATE,
            "warmup_steps": WARMUP_STEPS,
            "seed": SEED,
            "device": device,
        }
    )
    print(f"Wandb initialized: {wandb.run.url}")
    
    # Train extractor
    extractor_trainer, extractor_datasets, tokenizer, id_to_label = train_extractor()
    qualitative_analysis_extractor(extractor_trainer, extractor_datasets, tokenizer, id_to_label)

    # Clear memory before training validator
    print("\nClearing memory before validator training...")
    del extractor_trainer
    gc.collect()
    if torch.backends.mps.is_available():
        torch.mps.empty_cache()

    # Train validator
    validator_trainer, validator_datasets = train_validator()
    qualitative_analysis_validator(validator_trainer, validator_datasets)
    
    print("\n" + "="*60)
    print("TRAINING AND EVALUATION COMPLETE")
    print("="*60)
    print(f"\nModels saved to: {OUTPUT_DIR}")

    # Finish wandb run
    wandb.finish()


if __name__ == "__main__":
    main()
