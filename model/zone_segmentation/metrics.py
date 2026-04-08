"""Evaluation metrics for binary segmentation."""

import torch


def iou_score(pred: torch.Tensor, target: torch.Tensor, threshold: float = 0.5) -> float:
    """Intersection over Union for binary masks.

    Args:
        pred: (B, 1, H, W) logits or probabilities
        target: (B, 1, H, W) binary ground truth
        threshold: binarization threshold for predictions

    Returns:
        Mean IoU across the batch.
    """
    pred_binary = (torch.sigmoid(pred) > threshold).float()
    target_binary = (target > 0.5).float()

    intersection = (pred_binary * target_binary).sum(dim=(1, 2, 3))
    union = pred_binary.sum(dim=(1, 2, 3)) + target_binary.sum(dim=(1, 2, 3)) - intersection

    iou = (intersection + 1e-6) / (union + 1e-6)
    return iou.mean().item()


def dice_score(pred: torch.Tensor, target: torch.Tensor, threshold: float = 0.5) -> float:
    """Dice coefficient for binary masks."""
    pred_binary = (torch.sigmoid(pred) > threshold).float()
    target_binary = (target > 0.5).float()

    intersection = (pred_binary * target_binary).sum(dim=(1, 2, 3))
    total = pred_binary.sum(dim=(1, 2, 3)) + target_binary.sum(dim=(1, 2, 3))

    dice = (2.0 * intersection + 1e-6) / (total + 1e-6)
    return dice.mean().item()


def pixel_accuracy(pred: torch.Tensor, target: torch.Tensor, threshold: float = 0.5) -> float:
    """Per-pixel accuracy."""
    pred_binary = (torch.sigmoid(pred) > threshold).float()
    target_binary = (target > 0.5).float()

    correct = (pred_binary == target_binary).float().sum()
    total = target_binary.numel()

    return (correct / total).item()


def precision_recall_f1(
    pred: torch.Tensor, target: torch.Tensor, threshold: float = 0.5
) -> tuple[float, float, float]:
    """Pixel-level precision / recall / F1 for binary masks.

    Returns:
        (precision, recall, f1)
    """
    pred_binary = (torch.sigmoid(pred) > threshold).float()
    target_binary = (target > 0.5).float()

    tp = (pred_binary * target_binary).sum()
    fp = (pred_binary * (1 - target_binary)).sum()
    fn = ((1 - pred_binary) * target_binary).sum()

    precision = (tp + 1e-6) / (tp + fp + 1e-6)
    recall = (tp + 1e-6) / (tp + fn + 1e-6)
    f1 = (2 * precision * recall) / (precision + recall + 1e-6)
    return precision.item(), recall.item(), f1.item()
