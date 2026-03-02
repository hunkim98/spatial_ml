"""
Shared metrics computation functions with comprehensive W&B logging.
"""

import numpy as np
from typing import Dict
from seqeval.metrics import f1_score, precision_score, recall_score, classification_report
from sklearn.metrics import accuracy_score, precision_recall_fscore_support, confusion_matrix, roc_auc_score, roc_curve
import wandb


def create_token_classification_metrics(id_to_label: Dict[int, str]):
    """
    Create compute_metrics function for token classification (extractor).

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

        for pred_seq, label_seq in zip(predictions, labels):
            true_seq = []
            pred_seq_labels = []

            for pred_id, label_id in zip(pred_seq, label_seq):
                if label_id != -100:
                    true_seq.append(id_to_label[label_id])
                    pred_seq_labels.append(id_to_label[pred_id])

            if true_seq:
                true_labels.append(true_seq)
                pred_labels.append(pred_seq_labels)

        # Overall metrics
        overall_precision = precision_score(true_labels, pred_labels)
        overall_recall = recall_score(true_labels, pred_labels)
        overall_f1 = f1_score(true_labels, pred_labels)

        # Per-class metrics using seqeval's classification_report
        report = classification_report(true_labels, pred_labels, output_dict=True)

        metrics = {
            "precision": overall_precision,
            "recall": overall_recall,
            "f1": overall_f1,
        }

        # Flatten labels for token-level metrics
        flat_true = [label for seq in true_labels for label in seq]
        flat_pred = [label for seq in pred_labels for label in seq]

        # Token-level accuracy
        token_accuracy = sum(1 for t, p in zip(flat_true, flat_pred) if t == p) / len(flat_true) if flat_true else 0
        metrics["token_accuracy"] = token_accuracy

        # Per-tag metrics using sklearn on flattened labels
        all_tags = ['O', 'B-ZONE', 'I-ZONE']
        for tag in all_tags:
            # Count true positives, false positives, false negatives for this tag
            tag_true = [1 if t == tag else 0 for t in flat_true]
            tag_pred = [1 if p == tag else 0 for p in flat_pred]

            if sum(tag_true) > 0:  # Only compute if tag exists in ground truth
                precision, recall, f1, support = precision_recall_fscore_support(
                    tag_true, tag_pred, average='binary', zero_division=0
                )
                metrics[f"precision_{tag}"] = float(precision)
                metrics[f"recall_{tag}"] = float(recall)
                metrics[f"f1_{tag}"] = float(f1)
                metrics[f"support_{tag}"] = int(sum(tag_true))

        # Add entity-level metrics from seqeval report if available
        if 'ZONE' in report:
            metrics["precision_ZONE_entity"] = report['ZONE']['precision']
            metrics["recall_ZONE_entity"] = report['ZONE']['recall']
            metrics["f1_ZONE_entity"] = report['ZONE']['f1-score']
            metrics["support_ZONE_entity"] = report['ZONE']['support']

        # Log confusion matrix to W&B
        try:
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


def create_sequence_classification_metrics(id_to_label: Dict[int, str]):
    """
    Create compute_metrics function for sequence classification (validator).

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
                    wandb.log({
                        "eval/roc_curve": wandb.plot.roc_curve(
                            labels,
                            probabilities,
                            labels=class_names
                        )
                    })

                    # Precision-Recall curve
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
