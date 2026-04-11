"""Dataset variant that also returns a legend grid image for context-aware models.

Extends ZoneSegmentationDataset — returns (image, pattern, legend, mask)
instead of (image, pattern, mask). The legend is a 128×128 grid of ALL
pattern thumbnails for the current map.
"""

from __future__ import annotations

import logging
from pathlib import Path

from PIL import Image
from torch.utils.data import DataLoader
from torchvision import transforms

from .dataset import (
    StratificationConfig,
    StratifiedBatchSampler,
    ZoneSegmentationDataset,
    _load_sample_index,
    _source_aware_split,
    SampleMetadata,
)
from .unet_context import build_legend_image

logger = logging.getLogger(__name__)

LEGEND_SIZE = 128


class ContextDataset(ZoneSegmentationDataset):
    """Dataset that yields (image, pattern, legend, mask) tuples.

    The legend image is a fixed-size grid of ALL pattern thumbnails for the
    current map. This gives the model context about what other zones exist.
    """

    def __init__(
        self,
        root: str,
        samples: list[SampleMetadata],
        image_size: tuple[int, int] = (512, 512),
        augment: bool = True,
        min_coverage: float = 0.0,
        legend_size: int = LEGEND_SIZE,
    ):
        super().__init__(root, samples, image_size, augment, min_coverage)
        self.legend_size = legend_size
        self.legend_transform = transforms.Compose([
            transforms.Resize((legend_size, legend_size)),
            transforms.ToTensor(),
            transforms.Normalize(mean=[0.485, 0.456, 0.406],
                                 std=[0.229, 0.224, 0.225]),
        ])

        # Pre-build legend images per sample (they're shared across zones)
        # Only stores paths, not images — build_legend_image is called in __getitem__
        self._sample_pattern_paths: list[list[str]] = []
        for sample in self.samples:
            paths = [z["pattern"] for z in sample.zones]
            self._sample_pattern_paths.append(paths)

    def __getitem__(self, idx: int):
        si, zi = self._flat_index[idx]
        sample = self.samples[si]
        zone = sample.zones[zi]

        image = Image.open(sample.image_path).convert("RGB")
        mask = Image.open(zone["mask"]).convert("L")
        pattern = Image.open(zone["pattern"]).convert("RGB")

        # Build legend grid from ALL patterns for this map
        legend = build_legend_image(
            self._sample_pattern_paths[si],
            canvas_size=self.legend_size,
        )

        image = self.image_transform(image)
        pattern = self.pattern_transform(pattern)
        legend = self.legend_transform(legend)
        mask = self.mask_transform(mask)
        mask = (mask > 0.5).float()

        return image, pattern, legend, mask


def get_context_dataloaders(
    root: str,
    image_size: tuple[int, int] = (512, 512),
    batch_size: int = 4,
    num_workers: int = 4,
    stratification: StratificationConfig | None = None,
    legend_size: int = LEGEND_SIZE,
) -> tuple:
    """Create train and validation dataloaders with legend context."""
    if stratification is None:
        stratification = StratificationConfig()

    all_samples = _load_sample_index(Path(root), stratification.density_bins)
    train_samples, val_samples = _source_aware_split(
        all_samples,
        val_fraction=stratification.val_fraction,
        seed=stratification.seed,
    )

    from collections import Counter
    train_bins = Counter(s.density_bin for s in train_samples)
    logger.info(f"Train density bins: {dict(train_bins)}")

    train_ds = ContextDataset(
        root, train_samples, image_size=image_size, augment=True,
        min_coverage=stratification.min_coverage, legend_size=legend_size,
    )
    val_ds = ContextDataset(
        root, val_samples, image_size=image_size, augment=False,
        legend_size=legend_size,
    )

    if stratification.use_stratified_batches:
        train_sampler = StratifiedBatchSampler(
            train_ds, batch_size=batch_size,
            drop_last=True, seed=stratification.seed,
        )
        train_loader = DataLoader(
            train_ds, batch_sampler=train_sampler,
            num_workers=num_workers, pin_memory=True,
        )
    else:
        train_loader = DataLoader(
            train_ds, batch_size=batch_size, shuffle=True,
            num_workers=num_workers, pin_memory=True, drop_last=True,
        )

    val_loader = DataLoader(
        val_ds, batch_size=batch_size, shuffle=False,
        num_workers=num_workers, pin_memory=True,
    )

    return train_loader, val_loader
