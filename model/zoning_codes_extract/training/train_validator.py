"""
Train the validator model (binary classification).

Fine-tunes a BERT model to distinguish real zone codes from false positives.
"""

import json
from pathlib import Path
from dataclasses import dataclass
from typing import List, Dict, Optional

import numpy as np
import torch
from transformers import (
    AutoTokenizer,
    AutoModelForSequenceClassification,
    TrainingArguments,
    Trainer,
    DataCollatorWithPadding,
)
from datasets import Dataset, DatasetDict
from sklearn.metrics import (
    accuracy_score,
    precision_recall_fscore_support,
    classification_report
)
from torch import nn


class WeightedTrainer(Trainer):
    """Trainer with class-weighted loss for imbalanced datasets."""

    def __init__(self, class_weights=None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.class_weights = class_weights

    def compute_loss(self, model, inputs, return_outputs=False, **kwargs):
        """Compute weighted cross-entropy loss."""
        labels = inputs.pop("labels")
        outputs = model(**inputs)
        logits = outputs.logits

        if self.class_weights is not None:
            weight = self.class_weights.to(logits.device)
            loss_fct = nn.CrossEntropyLoss(weight=weight)
        else:
            loss_fct = nn.CrossEntropyLoss()

        loss = loss_fct(logits, labels)
        return (loss, outputs) if return_outputs else loss


@dataclass
class TrainingConfig:
    """Configuration for training."""
    model_name: str = "bert-base-uncased"
    output_dir: str = "model/zoning_codes_extract/trained_models/validator"
    data_dir: str = "model/zoning_codes_extract/training/data"
    num_epochs: int = 5
    batch_size: int = 16
    learning_rate: float = 2e-5
    weight_decay: float = 0.01
    warmup_ratio: float = 0.1  # Use ratio instead of fixed steps
    max_seq_length: int = 512
    seed: int = 42
    val_split: float = 0.15  # Split training data for validation


class ValidatorTrainer:
    """
    Trainer for the validator binary classification model.

    Handles:
    - Loading validator training data
    - Fine-tuning BERT for binary classification
    - Evaluation with precision, recall, F1
    - Model saving and checkpointing
    """

    def __init__(self, config: TrainingConfig):
        """
        Initialize trainer with config.

        Args:
            config: Training configuration
        """
        self.config = config
        self.class_weights = None  # Will be set during data loading

        # Set seed for reproducibility
        torch.manual_seed(config.seed)
        np.random.seed(config.seed)

        # Initialize tokenizer
        self.tokenizer = AutoTokenizer.from_pretrained(config.model_name)

        # Initialize model (2 labels: 0 = invalid, 1 = valid)
        self.model = AutoModelForSequenceClassification.from_pretrained(
            config.model_name,
            num_labels=2
        )

        print(f"Initialized model: {config.model_name}")
        print(f"Binary classification: 0 = invalid, 1 = valid zone code")

    def load_data(self) -> DatasetDict:
        """
        Load training data from JSONL files.

        Returns:
            DatasetDict with train/val/test splits
        """
        data_path = Path(self.config.data_dir)

        datasets = {}
        all_examples = {}

        for split in ['train', 'val', 'test']:
            file_path = data_path / f"validator_{split}.jsonl"

            if not file_path.exists():
                if split != 'val':  # val is optional, we'll create it from train
                    print(f"Warning: {split} file not found: {file_path}")
                continue

            # Load JSONL
            examples = []
            with open(file_path) as f:
                for line in f:
                    example = json.loads(line)
                    examples.append(example)

            all_examples[split] = examples

        # If no validation set, split from training data
        if 'val' not in all_examples and 'train' in all_examples:
            train_examples = all_examples['train']
            np.random.shuffle(train_examples)

            val_size = int(len(train_examples) * self.config.val_split)
            all_examples['val'] = train_examples[:val_size]
            all_examples['train'] = train_examples[val_size:]
            print(f"Created validation split: {val_size} examples from training data")

        # Calculate class weights from training data
        if 'train' in all_examples:
            train_labels = [ex['label'] for ex in all_examples['train']]
            n_samples = len(train_labels)
            n_classes = 2
            class_counts = [train_labels.count(i) for i in range(n_classes)]
            # Balanced class weights: n_samples / (n_classes * count_per_class)
            self.class_weights = torch.tensor([
                n_samples / (n_classes * count) if count > 0 else 1.0
                for count in class_counts
            ], dtype=torch.float32)
            print(f"Class weights: Invalid={self.class_weights[0]:.2f}, Valid={self.class_weights[1]:.2f}")

        # Process all splits
        for split, examples in all_examples.items():
            # Prepare inputs for BERT
            processed_examples = []
            for ex in examples:
                # Combine code and passages
                input_text = self._prepare_input(ex['code'], ex['passages'])

                processed_examples.append({
                    'text': input_text,
                    'label': ex['label'],
                    'city': ex['city'],
                    'state': ex['state']
                })

            # Tokenize
            def tokenize_function(examples):
                return self.tokenizer(
                    examples['text'],
                    padding=False,  # Will pad in DataCollator
                    truncation=True,
                    max_length=self.config.max_seq_length
                )

            # Create dataset
            ds = Dataset.from_list(processed_examples)
            ds = ds.map(tokenize_function, batched=True, remove_columns=['text'])
            datasets[split] = ds

        print(f"Loaded datasets:")
        for split, ds in datasets.items():
            label_counts = {}
            for label in ds['label']:
                label_counts[label] = label_counts.get(label, 0) + 1
            print(f"  {split}: {len(ds)} examples (valid: {label_counts.get(1, 0)}, invalid: {label_counts.get(0, 0)})")

        return DatasetDict(datasets)

    def _prepare_input(self, code: str, passages: List[str]) -> str:
        """
        Prepare input text for BERT.

        Format: "[CODE] {zone_code} [SEP] {passage1} [SEP] {passage2} ..."
        """
        # Limit passages to avoid exceeding max_length
        combined_passages = " [SEP] ".join(passages[:5])
        return f"[CODE] {code} [SEP] {combined_passages}"

    def compute_metrics(self, eval_pred):
        """
        Compute classification metrics for evaluation.

        Args:
            eval_pred: Predictions from trainer

        Returns:
            Dictionary of metrics
        """
        predictions, labels = eval_pred
        predictions = np.argmax(predictions, axis=1)

        # Compute metrics
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

    def train(self):
        """
        Train the model.

        Returns:
            Trained model and trainer
        """
        # Load data
        datasets = self.load_data()

        if 'train' not in datasets:
            raise ValueError("No training data found!")

        # Determine if we have validation data
        has_val = 'val' in datasets and len(datasets['val']) > 0

        # Training arguments
        training_args = TrainingArguments(
            output_dir=self.config.output_dir,
            eval_strategy="epoch" if has_val else "no",
            save_strategy="epoch",
            learning_rate=self.config.learning_rate,
            per_device_train_batch_size=self.config.batch_size,
            per_device_eval_batch_size=self.config.batch_size,
            num_train_epochs=self.config.num_epochs,
            weight_decay=self.config.weight_decay,
            warmup_ratio=self.config.warmup_ratio,  # Use ratio instead of fixed steps
            logging_dir=f"{self.config.output_dir}/logs",
            logging_steps=10,  # Log more frequently for small datasets
            load_best_model_at_end=has_val,
            metric_for_best_model="f1" if has_val else None,
            greater_is_better=True if has_val else None,
            seed=self.config.seed,
            push_to_hub=False,
            report_to="none",
        )

        # Data collator (handles padding)
        data_collator = DataCollatorWithPadding(tokenizer=self.tokenizer)

        # Initialize trainer with class weights for imbalanced data
        trainer = WeightedTrainer(
            class_weights=self.class_weights,
            model=self.model,
            args=training_args,
            train_dataset=datasets['train'],
            eval_dataset=datasets.get('val'),
            processing_class=self.tokenizer,
            data_collator=data_collator,
            compute_metrics=self.compute_metrics,
        )

        # Train
        print("\n=== Starting Training ===")
        trainer.train()

        # Evaluate on test set if available
        if 'test' in datasets:
            print("\n=== Evaluating on Test Set ===")
            test_results = trainer.evaluate(datasets['test'])
            print(f"Test Results: {test_results}")

            # Save test results
            output_path = Path(self.config.output_dir)
            with open(output_path / "test_results.json", 'w') as f:
                json.dump(test_results, f, indent=2)

            # Detailed classification report
            predictions = trainer.predict(datasets['test'])
            pred_labels = np.argmax(predictions.predictions, axis=1)
            true_labels = predictions.label_ids

            report = classification_report(
                true_labels,
                pred_labels,
                target_names=['Invalid', 'Valid'],
                output_dict=True
            )

            print("\n=== Classification Report ===")
            print(classification_report(
                true_labels,
                pred_labels,
                target_names=['Invalid', 'Valid']
            ))

            # Save detailed report
            with open(output_path / "detailed_report.json", 'w') as f:
                json.dump(report, f, indent=2)

        # Save model
        print(f"\n=== Saving Model to {self.config.output_dir} ===")
        trainer.save_model(self.config.output_dir)
        self.tokenizer.save_pretrained(self.config.output_dir)

        return trainer


def main():
    """Main entry point."""
    import argparse

    parser = argparse.ArgumentParser(description="Train validator model")
    parser.add_argument("--model-name", default="bert-base-uncased",
                        help="Base model to fine-tune")
    parser.add_argument("--output-dir", default="model/zoning_codes_extract/trained_models/validator",
                        help="Output directory for trained model")
    parser.add_argument("--data-dir", default="model/zoning_codes_extract/training/data",
                        help="Directory with training data")
    parser.add_argument("--epochs", type=int, default=3,
                        help="Number of training epochs")
    parser.add_argument("--batch-size", type=int, default=16,
                        help="Batch size")
    parser.add_argument("--learning-rate", type=float, default=2e-5,
                        help="Learning rate")

    args = parser.parse_args()

    # Create config
    config = TrainingConfig(
        model_name=args.model_name,
        output_dir=args.output_dir,
        data_dir=args.data_dir,
        num_epochs=args.epochs,
        batch_size=args.batch_size,
        learning_rate=args.learning_rate
    )

    # Train
    trainer_obj = ValidatorTrainer(config)
    trainer = trainer_obj.train()

    print("\n=== Training Complete ===")


if __name__ == "__main__":
    main()
