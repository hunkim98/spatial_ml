"""PyTorch dataset for zone segmentation training data.

Loads (image, pattern, mask) triplets from the generated dataset.
Each sample in the dataset directory has:
    images/{id}.png
    masks/{id}/zone_XX/mask.png
    masks/{id}/zone_XX/pattern.png
    annotations/{id}.json

During training, we randomly pick one zone per image to create a
(image, pattern, mask) triplet.
"""

import json
import random
from pathlib import Path

import numpy as np
import torch
from PIL import Image
from torch.utils.data import Dataset
from torchvision import transforms


class ZoneSegmentationDataset(Dataset):
    """Dataset that yields (image, pattern, mask) triplets.

    Each __getitem__ picks a random zone from a random sample,
    returning:
        image:   (3, H, W) float32 normalized
        pattern: (3, 32, 32) float32 normalized
        mask:    (1, H, W) float32 binary
    """

    def __init__(
        self,
        root: str,
        split: str = "train",
        image_size: tuple[int, int] = (512, 512),
        augment: bool = True,
    ):
        self.root = Path(root)
        self.image_size = image_size
        self.augment = augment

        # Load all annotations
        ann_dir = self.root / "annotations"
        self.samples = []  # list of (image_path, zone_info_list)

        for ann_file in sorted(ann_dir.glob("*.json")):
            with open(ann_file) as f:
                ann = json.load(f)

            image_path = self.root / ann["image"]
            if not image_path.exists():
                continue

            zones = []
            for zone in ann["zones"]:
                mask_path = self.root / zone["mask"]
                pattern_path = self.root / zone["pattern"]
                if mask_path.exists() and pattern_path.exists():
                    zones.append({
                        "mask": str(mask_path),
                        "pattern": str(pattern_path),
                        "pixel_count": zone.get("pixel_count", 0),
                    })

            if zones:
                self.samples.append({
                    "image": str(image_path),
                    "zones": zones,
                })

        # Split: use sample_id hash for deterministic train/val split
        if split in ("train", "val"):
            train_samples = []
            val_samples = []
            for i, s in enumerate(self.samples):
                if i % 10 == 0:  # 10% validation
                    val_samples.append(s)
                else:
                    train_samples.append(s)
            self.samples = train_samples if split == "train" else val_samples

        # Image transforms
        self.image_transform = transforms.Compose([
            transforms.Resize(image_size),
            transforms.ToTensor(),
            transforms.Normalize(mean=[0.485, 0.456, 0.406],
                                 std=[0.229, 0.224, 0.225]),
        ])

        self.pattern_transform = transforms.Compose([
            transforms.Resize((32, 32)),
            transforms.ToTensor(),
            transforms.Normalize(mean=[0.485, 0.456, 0.406],
                                 std=[0.229, 0.224, 0.225]),
        ])

        self.mask_transform = transforms.Compose([
            transforms.Resize(image_size, interpolation=transforms.InterpolationMode.NEAREST),
            transforms.ToTensor(),
        ])

    def __len__(self) -> int:
        """Total number of (image, zone) pairs across all samples."""
        return sum(len(s["zones"]) for s in self.samples)

    def __getitem__(self, idx: int):
        """Get one (image, pattern, mask) triplet.

        Flattens all (sample, zone) pairs into a single index space.
        """
        # Map flat index to (sample_idx, zone_idx)
        running = 0
        for sample in self.samples:
            n_zones = len(sample["zones"])
            if idx < running + n_zones:
                zone_idx = idx - running
                break
            running += n_zones
        else:
            # Fallback: random sample
            sample = random.choice(self.samples)
            zone_idx = random.randint(0, len(sample["zones"]) - 1)

        zone = sample["zones"][zone_idx]

        # Load image
        image = Image.open(sample["image"]).convert("RGB")

        # Load mask
        mask = Image.open(zone["mask"]).convert("L")

        # Load pattern
        pattern = Image.open(zone["pattern"]).convert("RGB")

        # Apply transforms
        image = self.image_transform(image)
        pattern = self.pattern_transform(pattern)
        mask = self.mask_transform(mask)

        # Binarize mask (threshold at 0.5)
        mask = (mask > 0.5).float()

        return image, pattern, mask


def get_dataloaders(
    root: str,
    image_size: tuple[int, int] = (512, 512),
    batch_size: int = 4,
    num_workers: int = 4,
):
    """Create train and validation dataloaders."""
    train_ds = ZoneSegmentationDataset(root, split="train", image_size=image_size)
    val_ds = ZoneSegmentationDataset(root, split="val", image_size=image_size, augment=False)

    train_loader = torch.utils.data.DataLoader(
        train_ds, batch_size=batch_size, shuffle=True,
        num_workers=num_workers, pin_memory=True, drop_last=True,
    )
    val_loader = torch.utils.data.DataLoader(
        val_ds, batch_size=batch_size, shuffle=False,
        num_workers=num_workers, pin_memory=True,
    )

    return train_loader, val_loader
