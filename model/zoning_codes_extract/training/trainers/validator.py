"""
Validator model trainer (sequence classification for zone code validation).

Handles:
- Binary classification (valid zone vs. not valid)
- Negative sampling for balanced training
- Precision/recall/F1 metrics
"""

import json
import random
from pathlib import Path
from typing import Dict, List

import numpy as np
from sklearn.metrics import (
    accuracy_score,
    confusion_matrix,
    precision_recall_fscore_support,
    roc_auc_score,
)
from transformers import (
    AutoModelForSequenceClassification,
    DataCollatorWithPadding,
    PreTrainedModel,
    PreTrainedTokenizer,
)
import wandb

from .base import BaseTrainer


class ValidatorTrainer(BaseTrainer):
    """
    Trainer for validator model (sequence classification).

    Uses binary classification to distinguish:
    - 1 (zone): Valid zone code
    - 0 (not_zone): False positive (acronym, section reference, etc.)
    """

    def get_model_type(self) -> str:
        """Return 'validator'."""
        return "validator"

    def get_label_list(self) -> List[str]:
        """Return binary classification labels."""
        # Note: Label list is different for validator (not strings)
        # We'll override this in id_to_label mapping
        return ["not_zone", "zone"]

    def load_examples_from_jsonl(
        self,
        file_path: Path,
        tokenizer: PreTrainedTokenizer,
        label_to_id: Dict[str, int]
    ) -> List[Dict]:
        """
        Load validator examples from JSONL file.

        Each line should have:
        - text OR passages: Input text or list of passages
        - label: Binary label (0 = not_zone, 1 = zone)
        - city, state: Optional metadata

        Args:
            file_path: Path to JSONL file
            tokenizer: Tokenizer instance
            label_to_id: Mapping from labels to IDs (not used, labels are already numeric)

        Returns:
            List of example dictionaries
        """
        examples = []
        with open(file_path) as f:
            for line in f:
                ex = json.loads(line)

                # Handle both 'text' and 'passages' fields
                if 'text' in ex:
                    text = ex['text']
                elif 'passages' in ex:
                    # Join passages with separator
                    text = ' '.join(ex['passages'])
                else:
                    raise ValueError(f"Example missing 'text' or 'passages' field: {ex}")

                # Tokenize
                encoding = tokenizer(
                    text,
                    truncation=True,
                    max_length=512,
                    padding=False
                )

                examples.append({
                    'input_ids': encoding['input_ids'],
                    'attention_mask': encoding['attention_mask'],
                    'label': ex['label'],  # Already numeric (0 or 1)
                    'text': text,
                    'city': ex.get('city', ''),
                    'state': ex.get('state', ''),
                })
        return examples

    def create_model(self, label_to_id: Dict, id_to_label: Dict) -> PreTrainedModel:
        """
        Create sequence classification model.

        Args:
            label_to_id: Mapping from labels to IDs
            id_to_label: Mapping from IDs to labels

        Returns:
            AutoModelForSequenceClassification instance
        """
        model = AutoModelForSequenceClassification.from_pretrained(
            self.config.model_name,
            num_labels=2,  # Binary classification
            id2label=id_to_label,
            label2id=label_to_id
        )
        return model

    def create_data_collator(self):
        """
        Create data collator for sequence classification.

        Returns:
            DataCollatorWithPadding instance
        """
        return DataCollatorWithPadding(tokenizer=self.tokenizer)

    def create_compute_metrics(self, id_to_label: Dict):
        """
        Create compute_metrics function for sequence classification.

        Computes binary classification metrics with focus on class 1 (zone).

        Args:
            id_to_label: Mapping from label IDs to label names

        Returns:
            Function that computes metrics for sequence classification
        """
        def compute_metrics(eval_pred):
            logits, labels = eval_pred
            predictions = np.argmax(logits, axis=1)
            probabilities = np.exp(logits) / np.exp(logits).sum(axis=1, keepdims=True)  # Softmax

            # Binary metrics (treating class 1 as positive)
            precision, recall, f1, _ = precision_recall_fscore_support(
                labels, predictions, average='binary', pos_label=1
            )
            accuracy = accuracy_score(labels, predictions)

            # Per-class metrics
            precision_per_class, recall_per_class, f1_per_class, support_per_class = precision_recall_fscore_support(
                labels, predictions, average=None, labels=[0, 1]
            )

            # Macro averages
            precision_macro, recall_macro, f1_macro, _ = precision_recall_fscore_support(
                labels, predictions, average='macro'
            )

            metrics = {
                "accuracy": accuracy,
                "precision": precision,  # Precision for class 1 (zone)
                "recall": recall,  # Recall for class 1 (zone)
                "f1": f1,  # F1 for class 1 (zone)
                "precision_macro": precision_macro,
                "recall_macro": recall_macro,
                "f1_macro": f1_macro,
            }

            # Per-class metrics (explicit float conversion for W&B)
            for i, label_name in id_to_label.items():
                if i < len(precision_per_class):
                    metrics[f"precision_{label_name}"] = float(precision_per_class[i])
                    metrics[f"recall_{label_name}"] = float(recall_per_class[i])
                    metrics[f"f1_{label_name}"] = float(f1_per_class[i])
                    metrics[f"support_{label_name}"] = int(support_per_class[i])

            # False positive/negative rates
            cm = confusion_matrix(labels, predictions, labels=[0, 1])
            tn, fp, fn, tp = cm.ravel()

            metrics["false_positive_rate"] = fp / (fp + tn) if (fp + tn) > 0 else 0
            metrics["false_negative_rate"] = fn / (fn + tp) if (fn + tp) > 0 else 0
            metrics["true_negatives"] = int(tn)
            metrics["false_positives"] = int(fp)
            metrics["false_negatives"] = int(fn)
            metrics["true_positives"] = int(tp)

            # ROC-AUC if we have both classes
            try:
                if len(np.unique(labels)) > 1:
                    # Use probability of positive class
                    pos_probs = probabilities[:, 1]
                    roc_auc = roc_auc_score(labels, pos_probs)
                    metrics["roc_auc"] = float(roc_auc)
            except:
                pass

            # Log visualizations to W&B
            try:
                if wandb.run is not None:
                    class_names = [id_to_label[0], id_to_label[1]]

                    # Confusion matrix
                    wandb.log({
                        "eval/confusion_matrix": wandb.plot.confusion_matrix(
                            probs=None,
                            y_true=labels.tolist(),
                            preds=predictions.tolist(),
                            class_names=class_names
                        )
                    })

                    # ROC curve (if both classes present)
                    if len(np.unique(labels)) > 1:
                        from sklearn.metrics import roc_curve
                        pos_probs = probabilities[:, 1]
                        fpr, tpr, thresholds = roc_curve(labels, pos_probs)

                        wandb.log({
                            "eval/roc_curve": wandb.plot.roc_curve(
                                labels,
                                probabilities,
                                labels=class_names
                            )
                        })

                        # Precision-Recall curve
                        from sklearn.metrics import precision_recall_curve
                        precision_curve, recall_curve, pr_thresholds = precision_recall_curve(labels, pos_probs)

                        wandb.log({
                            "eval/pr_curve": wandb.plot.pr_curve(
                                labels,
                                probabilities,
                                labels=class_names
                            )
                        })
            except Exception as e:
                pass  # Skip if wandb logging fails

            return metrics

        return compute_metrics

    def load_datasets(
        self,
        train_file: Path = None,
        test_file: Path = None
    ):
        """
        Load train and test datasets.

        Override to handle validator-specific label mappings and
        automatic test split if test file is empty.

        Args:
            train_file: Path to training JSONL file (optional)
            test_file: Path to test JSONL file (optional)

        Returns:
            Tuple of (train_dataset, test_dataset, tokenizer, label_to_id, id_to_label)
        """
        # Use default paths if not provided
        if train_file is None:
            train_file = self.data_dir / "train_validator.jsonl"
        if test_file is None:
            test_file = self.data_dir / "test_validator.jsonl"

        if not train_file.exists():
            raise FileNotFoundError(f"Training data not found: {train_file}")

        # Validator uses numeric labels (0, 1)
        label_to_id = {0: 0, 1: 1}
        id_to_label = {0: "not_zone", 1: "zone"}

        # Load tokenizer
        from transformers import AutoTokenizer
        tokenizer = AutoTokenizer.from_pretrained(self.config.model_name)
        self.tokenizer = tokenizer

        # Load examples
        train_examples = self.load_examples_from_jsonl(train_file, tokenizer, label_to_id)

        # Check if test file exists and has data
        test_examples = []
        if test_file.exists():
            test_examples = self.load_examples_from_jsonl(test_file, tokenizer, label_to_id)

        # If test set is empty, create one from train data (15% split)
        if not test_examples:
            print("WARNING: Test set is empty. Creating validation split from train data (15%)...")
            random.shuffle(train_examples)
            split_idx = int(len(train_examples) * 0.85)
            test_examples = train_examples[split_idx:]
            train_examples = train_examples[:split_idx]
            print(f"Created test split: {len(test_examples)} examples")

        # Create datasets
        from datasets import Dataset
        train_ds = Dataset.from_list(train_examples)
        test_ds = Dataset.from_list(test_examples)

        print(f"Loaded {len(train_examples)} train examples, {len(test_examples)} test examples")

        return train_ds, test_ds, tokenizer, label_to_id, id_to_label

    def train(
        self,
        train_file: Path = None,
        test_file: Path = None,
        highlight_metric: str = "f1"
    ):
        """
        Train validator model.

        Args:
            train_file: Path to training data (optional)
            test_file: Path to test data (optional)
            highlight_metric: Metric to highlight (default: 'f1')

        Returns:
            Tuple of (trainer, test_dataset, tokenizer, id_to_label)
        """
        print("\nNote: Validator uses binary classification for zone code validation")
        print("Labels: 0 (not_zone), 1 (zone)\n")

        return super().train(train_file, test_file, highlight_metric)


if __name__ == "__main__":
    """
    Example usage:
        python -m training.trainers.validator
    """
    trainer = ValidatorTrainer()
    trainer.train()
