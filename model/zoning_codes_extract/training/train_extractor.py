"""
Train the zone code extractor model (token classification).

Fine-tunes a BERT model on BIO-tagged training data to identify
zone code mentions in ordinance text.
"""

import json
from pathlib import Path
from dataclasses import dataclass
from typing import List, Dict, Optional

import numpy as np
import torch
from transformers import (
    AutoTokenizer,
    AutoModelForTokenClassification,
    TrainingArguments,
    Trainer,
    DataCollatorForTokenClassification,
)
from datasets import Dataset, DatasetDict
from seqeval.metrics import (
    classification_report,
    f1_score,
    precision_score,
    recall_score
)


@dataclass
class TrainingConfig:
    """Configuration for training."""
    model_name: str = "bert-base-uncased"
    output_dir: str = "model/zoning_codes_extract/trained_models/extractor"
    data_dir: str = "model/zoning_codes_extract/training/data"
    num_epochs: int = 3
    batch_size: int = 16
    learning_rate: float = 2e-5
    weight_decay: float = 0.01
    warmup_steps: int = 500
    max_seq_length: int = 512
    seed: int = 42


class ExtractorTrainer:
    """
    Trainer for the zone code extractor model.

    Handles:
    - Loading BIO-tagged training data
    - Fine-tuning BERT for token classification
    - Evaluation with NER metrics (precision, recall, F1)
    - Model saving and checkpointing
    """

    # Label mapping
    LABEL_LIST = ['O', 'B-ZONE', 'I-ZONE']
    LABEL_TO_ID = {label: i for i, label in enumerate(LABEL_LIST)}
    ID_TO_LABEL = {i: label for label, i in LABEL_TO_ID.items()}

    def __init__(self, config: TrainingConfig):
        """
        Initialize trainer with config.

        Args:
            config: Training configuration
        """
        self.config = config

        # Set seed for reproducibility
        torch.manual_seed(config.seed)
        np.random.seed(config.seed)

        # Initialize tokenizer
        self.tokenizer = AutoTokenizer.from_pretrained(config.model_name)

        # Initialize model
        self.model = AutoModelForTokenClassification.from_pretrained(
            config.model_name,
            num_labels=len(self.LABEL_LIST),
            id2label=self.ID_TO_LABEL,
            label2id=self.LABEL_TO_ID
        )

        print(f"Initialized model: {config.model_name}")
        print(f"Labels: {self.LABEL_LIST}")

    def load_data(self) -> DatasetDict:
        """
        Load training data from JSONL files.

        Returns:
            DatasetDict with train/val/test splits
        """
        data_path = Path(self.config.data_dir)

        datasets = {}
        for split in ['train', 'val', 'test']:
            file_path = data_path / f"{split}.jsonl"

            if not file_path.exists():
                print(f"Warning: {split} file not found: {file_path}")
                continue

            # Load JSONL
            examples = []
            with open(file_path) as f:
                for line in f:
                    examples.append(json.loads(line))

            # Convert tokens to input_ids and tags to label IDs
            processed_examples = []
            for ex in examples:
                tokens = ex['tokens']
                tags = ex['tags']

                # Convert tokens to input_ids
                input_ids = self.tokenizer.convert_tokens_to_ids(tokens)

                # Convert tags to label IDs, using -100 for special tokens
                labels = []
                for i, tag in enumerate(tags):
                    # Use -100 for [CLS], [SEP], [PAD] tokens (they should be ignored in loss)
                    if tokens[i] in ['[CLS]', '[SEP]', '[PAD]']:
                        labels.append(-100)
                    else:
                        labels.append(self.LABEL_TO_ID[tag])

                processed_examples.append({
                    'input_ids': input_ids,
                    'labels': labels,
                    'attention_mask': [1] * len(input_ids),
                })

            # Create dataset
            datasets[split] = Dataset.from_list(processed_examples)

        print(f"Loaded datasets:")
        for split, ds in datasets.items():
            print(f"  {split}: {len(ds)} examples")

        return DatasetDict(datasets)

    def compute_metrics(self, eval_pred):
        """
        Compute NER metrics for evaluation.

        Args:
            eval_pred: Predictions from trainer

        Returns:
            Dictionary of metrics
        """
        predictions, labels = eval_pred
        predictions = np.argmax(predictions, axis=2)

        # Remove padding and convert to labels
        true_labels = []
        pred_labels = []

        for pred_seq, label_seq in zip(predictions, labels):
            true_seq = []
            pred_seq_labels = []

            for pred_id, label_id in zip(pred_seq, label_seq):
                if label_id != -100:  # Ignore padding
                    true_seq.append(self.ID_TO_LABEL[label_id])
                    pred_seq_labels.append(self.ID_TO_LABEL[pred_id])

            if true_seq:  # Only add non-empty sequences
                true_labels.append(true_seq)
                pred_labels.append(pred_seq_labels)

        # Compute seqeval metrics
        return {
            "precision": precision_score(true_labels, pred_labels),
            "recall": recall_score(true_labels, pred_labels),
            "f1": f1_score(true_labels, pred_labels),
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
            warmup_steps=self.config.warmup_steps,
            logging_dir=f"{self.config.output_dir}/logs",
            logging_steps=50,
            load_best_model_at_end=has_val,
            metric_for_best_model="f1" if has_val else None,
            greater_is_better=True if has_val else None,
            seed=self.config.seed,
            push_to_hub=False,
            report_to="none",
        )

        # Data collator (handles padding)
        data_collator = DataCollatorForTokenClassification(
            tokenizer=self.tokenizer,
            padding=True,
            max_length=self.config.max_seq_length
        )

        # Initialize trainer
        trainer = Trainer(
            model=self.model,
            args=training_args,
            train_dataset=datasets['train'],
            eval_dataset=datasets.get('val'),
            tokenizer=self.tokenizer,
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

        # Save model
        print(f"\n=== Saving Model to {self.config.output_dir} ===")
        trainer.save_model(self.config.output_dir)
        self.tokenizer.save_pretrained(self.config.output_dir)

        return trainer

    def evaluate_detailed(self, trainer: Trainer, dataset: Dataset) -> Dict:
        """
        Perform detailed evaluation with classification report.

        Args:
            trainer: Trained trainer
            dataset: Dataset to evaluate

        Returns:
            Dictionary with detailed metrics
        """
        predictions = trainer.predict(dataset)
        pred_logits = predictions.predictions
        label_ids = predictions.label_ids

        # Convert to labels
        pred_labels_all = []
        true_labels_all = []

        predictions = np.argmax(pred_logits, axis=2)

        for pred_seq, label_seq in zip(predictions, label_ids):
            pred_seq_labels = []
            true_seq_labels = []

            for pred_id, label_id in zip(pred_seq, label_seq):
                if label_id != -100:
                    pred_seq_labels.append(self.ID_TO_LABEL[pred_id])
                    true_seq_labels.append(self.ID_TO_LABEL[label_id])

            if true_seq_labels:
                pred_labels_all.append(pred_seq_labels)
                true_labels_all.append(true_seq_labels)

        # Generate classification report
        report = classification_report(true_labels_all, pred_labels_all, output_dict=True)

        print("\n=== Classification Report ===")
        print(classification_report(true_labels_all, pred_labels_all))

        return report


def main():
    """Main entry point."""
    import argparse

    parser = argparse.ArgumentParser(description="Train zone code extractor model")
    parser.add_argument("--model-name", default="bert-base-uncased",
                        help="Base model to fine-tune")
    parser.add_argument("--output-dir", default="model/zoning_codes_extract/trained_models/extractor",
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
    trainer_obj = ExtractorTrainer(config)
    trainer = trainer_obj.train()

    # Detailed evaluation on test set
    datasets = trainer_obj.load_data()
    if 'test' in datasets:
        report = trainer_obj.evaluate_detailed(trainer, datasets['test'])

        # Save detailed report
        output_path = Path(config.output_dir)
        with open(output_path / "detailed_report.json", 'w') as f:
            json.dump(report, f, indent=2)

    print("\n=== Training Complete ===")


if __name__ == "__main__":
    main()
