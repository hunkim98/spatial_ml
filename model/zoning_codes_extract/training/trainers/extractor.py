"""
Extractor model trainer (token classification for zone code extraction).

Handles:
- BIO tagging for zone codes
- Token classification metrics (precision, recall, F1)
- Custom tokenization (if enabled)
"""

import json
from pathlib import Path
from typing import Dict, List

import numpy as np
from seqeval.metrics import classification_report as ner_classification_report
from seqeval.metrics import f1_score, precision_score, recall_score
from sklearn.metrics import confusion_matrix
from transformers import (
    AutoModelForTokenClassification,
    DataCollatorForTokenClassification,
    PreTrainedModel,
    PreTrainedTokenizer,
)
import wandb

from .base import BaseTrainer


class ExtractorTrainer(BaseTrainer):
    """
    Trainer for extractor model (token classification).

    Uses BIO tagging to identify zone codes in text:
    - B-ZONE: Beginning of zone code
    - I-ZONE: Inside (continuation) of zone code
    - O: Outside (not a zone code)
    """

    def get_model_type(self) -> str:
        """Return 'extractor'."""
        return "extractor"

    def get_label_list(self) -> List[str]:
        """Return BIO tag labels."""
        return ['O', 'B-ZONE', 'I-ZONE']

    def load_examples_from_jsonl(
        self,
        file_path: Path,
        tokenizer: PreTrainedTokenizer,
        label_to_id: Dict[str, int]
    ) -> List[Dict]:
        """
        Load extractor examples from JSONL file.

        Each line should have:
        - tokens: List of token strings
        - tags: Corresponding BIO tags
        - city, state: Optional metadata

        Args:
            file_path: Path to JSONL file
            tokenizer: Tokenizer instance
            label_to_id: Mapping from labels to IDs

        Returns:
            List of example dictionaries
        """
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

    def create_model(self, label_to_id: Dict, id_to_label: Dict) -> PreTrainedModel:
        """
        Create token classification model.

        Args:
            label_to_id: Mapping from labels to IDs
            id_to_label: Mapping from IDs to labels

        Returns:
            AutoModelForTokenClassification instance
        """
        model = AutoModelForTokenClassification.from_pretrained(
            self.config.model_name,
            num_labels=len(label_to_id),
            id2label=id_to_label,
            label2id=label_to_id
        )
        return model

    def create_data_collator(self):
        """
        Create data collator for token classification.

        Returns:
            DataCollatorForTokenClassification instance
        """
        return DataCollatorForTokenClassification(
            tokenizer=self.tokenizer,
            padding=True,
            max_length=self.config.max_seq_length
        )

    def create_compute_metrics(self, id_to_label: Dict):
        """
        Create compute_metrics function for token classification.

        Uses seqeval for proper BIO tag evaluation.

        Args:
            id_to_label: Mapping from label IDs to label names

        Returns:
            Function that computes metrics for token classification
        """
        def compute_metrics(eval_pred):
            predictions, labels = eval_pred
            predictions = np.argmax(predictions, axis=2)

            true_labels = []
            pred_labels = []

            # Convert IDs to labels, filtering out padding (-100)
            for pred_seq, label_seq in zip(predictions, labels):
                true_seq = []
                pred_seq_labels = []

                for pred_id, label_id in zip(pred_seq, label_seq):
                    if label_id != -100:  # Ignore padding
                        true_seq.append(id_to_label[label_id])
                        pred_seq_labels.append(id_to_label[pred_id])

                if true_seq:
                    true_labels.append(true_seq)
                    pred_labels.append(pred_seq_labels)

            # Overall metrics (seqeval for proper entity-level evaluation)
            overall_precision = precision_score(true_labels, pred_labels)
            overall_recall = recall_score(true_labels, pred_labels)
            overall_f1 = f1_score(true_labels, pred_labels)

            # Per-class metrics using seqeval's classification_report
            report = ner_classification_report(true_labels, pred_labels, output_dict=True)

            metrics = {
                "precision": overall_precision,
                "recall": overall_recall,
                "f1": overall_f1,
            }

            # Add per-tag metrics if available
            for tag in ['B-ZONE', 'I-ZONE', 'O']:
                if tag in report:
                    metrics[f"precision_{tag}"] = report[tag]['precision']
                    metrics[f"recall_{tag}"] = report[tag]['recall']
                    metrics[f"f1_{tag}"] = report[tag]['f1-score']
                    metrics[f"support_{tag}"] = report[tag]['support']

            # Flatten labels for token-level confusion matrix
            flat_true = [label for seq in true_labels for label in seq]
            flat_pred = [label for seq in pred_labels for label in seq]

            # Token-level accuracy
            token_accuracy = sum(1 for t, p in zip(flat_true, flat_pred) if t == p) / len(flat_true) if flat_true else 0
            metrics["token_accuracy"] = token_accuracy

            # Log confusion matrix to W&B
            try:
                if wandb.run is not None:
                    label_names = ['O', 'B-ZONE', 'I-ZONE']
                    cm = confusion_matrix(flat_true, flat_pred, labels=label_names)

                    wandb.log({
                        "eval/confusion_matrix": wandb.plot.confusion_matrix(
                            probs=None,
                            y_true=[label_names.index(l) for l in flat_true],
                            preds=[label_names.index(l) for l in flat_pred],
                            class_names=label_names
                        )
                    })
            except:
                pass  # Skip if wandb logging fails

            return metrics

        return compute_metrics

    def train(
        self,
        train_file: Path = None,
        test_file: Path = None,
        highlight_metric: str = "recall"
    ):
        """
        Train extractor model.

        Args:
            train_file: Path to training data (optional)
            test_file: Path to test data (optional)
            highlight_metric: Metric to highlight (default: 'recall')

        Returns:
            Tuple of (trainer, test_dataset, tokenizer, id_to_label)
        """
        print("\nNote: Extractor uses BIO tagging for zone code extraction")
        print("Labels: O (outside), B-ZONE (beginning), I-ZONE (inside)\n")

        return super().train(train_file, test_file, highlight_metric)


if __name__ == "__main__":
    """
    Example usage:
        python -m training.trainers.extractor
    """
    trainer = ExtractorTrainer()
    trainer.train()
