"""PyTorch dataset for zone segmentation training data.

Loads (image, pattern, mask) triplets from the generated dataset.
Each sample in the dataset directory has:
    images/{id}.png
    masks/{id}/zone_XX/mask.png
    masks/{id}/zone_XX/pattern.png
    annotations/{id}.json

Supports stratified train/val splitting (by source GeoJSON) and
stratified batch sampling (by density, hatching, old-map effects).
"""

from __future__ import annotations

import json
import logging
import random
from collections import defaultdict, deque
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterator

import torch
from PIL import Image
from torch.utils.data import Dataset, Sampler
from torchvision import transforms

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# 1. SampleMetadata — lightweight annotation index for stratification
# ---------------------------------------------------------------------------
# Why: We scan all annotation JSONs once at startup and store just the fields
# needed for splitting and batch construction. This avoids re-reading JSON
# files and keeps stratification logic separate from the Dataset.

TILE_PROVIDERS = {
    "CartoDB.Positron", "CartoDB.Voyager", "CartoDB.DarkMatter",
    "Esri.WorldTopoMap", "Esri.WorldTerrain",
}


@dataclass
class SampleMetadata:
    """Metadata for one annotation, used for splitting and stratification."""
    sample_id: str
    image_path: str               # absolute path to image
    source_file: str              # normalized path to source GeoJSON
    n_zones: int
    has_hatching: bool
    has_old_map: bool             # old_map_intensity > 0
    density_bin: str              # "sparse", "medium", "dense"
    strat_key: str                # composite key for batch stratification
    zones: list[dict]             # [{mask: str, pattern: str, pixel_count: int}, ...]


@dataclass
class StratificationConfig:
    """Configuration for dataset stratification and splitting."""
    val_fraction: float = 0.15
    seed: int = 42
    density_bins: dict[str, tuple[int, int]] = field(default_factory=lambda: {
        "sparse": (1, 4),
        "medium": (5, 15),
        "dense": (16, 999_999),
    })
    use_stratified_batches: bool = True


# ---------------------------------------------------------------------------
# 2. _load_sample_index — scan annotations once, build metadata index
# ---------------------------------------------------------------------------
# Why: Reads every annotation JSON, validates file existence, computes
# density bin and composite strat key. Returns a list ready for splitting.

def _classify_density(n_zones: int, bins: dict[str, tuple[int, int]]) -> str:
    """Map zone count to a density bin name."""
    for name, (lo, hi) in bins.items():
        if lo <= n_zones <= hi:
            return name
    return "dense"  # fallback


def _load_sample_index(
    root: Path,
    density_bins: dict[str, tuple[int, int]],
) -> list[SampleMetadata]:
    """Scan annotations/ and build metadata index for all valid samples."""
    ann_dir = root / "annotations"
    samples = []

    for ann_file in sorted(ann_dir.glob("*.json")):
        with open(ann_file) as f:
            ann = json.load(f)

        image_path = root / ann["image"]
        if not image_path.exists():
            continue

        # Validate zones — keep only those with existing mask + pattern files
        zones = []
        for zone in ann["zones"]:
            mask_path = root / zone["mask"]
            pattern_path = root / zone["pattern"]
            if mask_path.exists() and pattern_path.exists():
                zones.append({
                    "mask": str(mask_path),
                    "pattern": str(pattern_path),
                    "pixel_count": zone.get("pixel_count", 0),
                })
        if not zones:
            continue

        # Normalize source path (Windows backslashes → forward slashes)
        source = ann.get("source_file", ann.get("sample_id", "unknown"))
        source = source.replace("\\", "/")

        n_zones = ann.get("n_zones", len(zones))
        has_hatching = bool(ann.get("has_hatching", False))
        has_old_map = (ann.get("old_map_intensity", 0) or 0) > 0
        density_bin = _classify_density(n_zones, density_bins)

        # Composite strat key: density × hatching × old_map = 3×2×2 = 12 strata
        # (has_labels excluded — 91% positive gives almost no signal)
        strat_key = (
            f"{density_bin}"
            f"|{'H' if has_hatching else 'h'}"
            f"|{'O' if has_old_map else 'o'}"
        )

        samples.append(SampleMetadata(
            sample_id=ann["sample_id"],
            image_path=str(image_path),
            source_file=source,
            n_zones=n_zones,
            has_hatching=has_hatching,
            has_old_map=has_old_map,
            density_bin=density_bin,
            strat_key=strat_key,
            zones=zones,
        ))

    logger.info(f"Loaded {len(samples)} samples from {ann_dir}")
    return samples


# ---------------------------------------------------------------------------
# 3. _source_aware_split — group by source, no geographic leakage
# ---------------------------------------------------------------------------
# Why: The old split (i % 10) put different renders of the SAME city into
# both train and val. The model memorized geography instead of learning
# pattern matching. Now all samples from one source GeoJSON go to the
# same split. We balance by density bin using greedy allocation.

def _source_aware_split(
    samples: list[SampleMetadata],
    val_fraction: float = 0.15,
    seed: int = 42,
) -> tuple[list[SampleMetadata], list[SampleMetadata]]:
    """Split samples so all samples from the same source go to one split.

    Uses greedy allocation balanced by density bin.
    """
    # Group samples by source
    source_groups: dict[str, list[SampleMetadata]] = defaultdict(list)
    for s in samples:
        source_groups[s.source_file].append(s)

    # For each source, determine dominant density bin
    source_info = []
    for source, group in source_groups.items():
        bin_counts: dict[str, int] = defaultdict(int)
        for s in group:
            bin_counts[s.density_bin] += 1
        dominant_bin = max(bin_counts, key=bin_counts.get)
        n_pairs = sum(len(s.zones) for s in group)
        source_info.append((source, dominant_bin, len(group), n_pairs))

    # Shuffle deterministically
    rng = random.Random(seed)
    rng.shuffle(source_info)

    # Greedy allocation: add sources to val until we reach target
    total_samples = len(samples)
    target_val = int(total_samples * val_fraction)

    val_sources: set[str] = set()
    val_count = 0
    # Track per-bin counts to maintain rough balance
    bin_val_counts: dict[str, int] = defaultdict(int)
    bin_total_counts: dict[str, int] = defaultdict(int)
    for _, dominant_bin, n_samples, _ in source_info:
        bin_total_counts[dominant_bin] += n_samples

    for source, dominant_bin, n_samples, _ in source_info:
        if val_count >= target_val:
            break
        # Check if this bin is already over-represented in val
        bin_target = bin_total_counts[dominant_bin] * val_fraction
        if bin_val_counts[dominant_bin] + n_samples > bin_target * 1.5:
            continue  # skip — would over-represent this bin
        val_sources.add(source)
        val_count += n_samples
        bin_val_counts[dominant_bin] += n_samples

    # If we haven't reached the target (due to skipping), do a second pass
    if val_count < target_val * 0.8:
        for source, dominant_bin, n_samples, _ in source_info:
            if source in val_sources:
                continue
            if val_count >= target_val:
                break
            val_sources.add(source)
            val_count += n_samples

    train_samples = [s for s in samples if s.source_file not in val_sources]
    val_samples = [s for s in samples if s.source_file in val_sources]

    # Log split statistics
    train_sources = set(s.source_file for s in train_samples)
    val_source_set = set(s.source_file for s in val_samples)
    train_pairs = sum(len(s.zones) for s in train_samples)
    val_pairs = sum(len(s.zones) for s in val_samples)

    logger.info(
        f"Split: {len(train_samples)} train samples ({train_pairs} pairs, "
        f"{len(train_sources)} sources), "
        f"{len(val_samples)} val samples ({val_pairs} pairs, "
        f"{len(val_source_set)} sources)"
    )

    # Verify no source overlap
    overlap = train_sources & val_source_set
    if overlap:
        logger.error(f"Source overlap between train/val: {overlap}")

    return train_samples, val_samples


# ---------------------------------------------------------------------------
# 4. ZoneSegmentationDataset — refactored to accept pre-split samples
# ---------------------------------------------------------------------------
# Why: The Dataset no longer does its own splitting. It receives a pre-split
# list of SampleMetadata and builds a flat index for O(1) __getitem__.
# The old version did O(N) linear scan per access — with 4,221 samples,
# that's thousands of iterations for every single training pair.

class ZoneSegmentationDataset(Dataset):
    """Dataset that yields (image, pattern, mask) triplets.

    Accepts a pre-split list of SampleMetadata. Each __getitem__ maps a
    flat index to (sample_idx, zone_idx) in O(1).

    Returns:
        image:   (3, H, W) float32 normalized
        pattern: (3, 32, 32) float32 normalized
        mask:    (1, H, W) float32 binary
    """

    def __init__(
        self,
        root: str,
        samples: list[SampleMetadata],
        image_size: tuple[int, int] = (512, 512),
        augment: bool = True,
    ):
        self.root = Path(root)
        self.image_size = image_size
        self.augment = augment
        self.samples = samples

        # Build flat index: list of (sample_idx, zone_idx) for O(1) lookup.
        # Old code did a linear scan through all samples on every __getitem__.
        self._flat_index: list[tuple[int, int]] = []
        for si, sample in enumerate(self.samples):
            for zi in range(len(sample.zones)):
                self._flat_index.append((si, zi))

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
        return len(self._flat_index)

    def __getitem__(self, idx: int):
        si, zi = self._flat_index[idx]
        sample = self.samples[si]
        zone = sample.zones[zi]

        image = Image.open(sample.image_path).convert("RGB")
        mask = Image.open(zone["mask"]).convert("L")
        pattern = Image.open(zone["pattern"]).convert("RGB")

        image = self.image_transform(image)
        pattern = self.pattern_transform(pattern)
        mask = self.mask_transform(mask)
        mask = (mask > 0.5).float()

        return image, pattern, mask


# ---------------------------------------------------------------------------
# 5. StratifiedBatchSampler — diverse, balanced batches
# ---------------------------------------------------------------------------
# Why: With random shuffle, 93.3% of training pairs come from dense maps.
# Most batches are all tiny ambiguous masks — the model barely sees sparse,
# clear-signal examples. This sampler reorders all indices (no duplication)
# into batches that balance density bins, hatching, old-map effects, and
# ensure each batch draws from different source GeoJSONs.

class StratifiedBatchSampler(Sampler[list[int]]):
    """BatchSampler that produces source-diverse, density-stratified batches.

    Every flat index is yielded exactly once per epoch (like shuffle=True),
    but arranged so each batch has:
    - Samples from different source GeoJSONs (source diversity)
    - Roughly proportional representation of strat keys (density balance)

    Args:
        dataset: ZoneSegmentationDataset with .samples metadata.
        batch_size: Target batch size.
        drop_last: Whether to drop the last incomplete batch.
        seed: Random seed (combined with epoch for reproducibility).
    """

    def __init__(
        self,
        dataset: ZoneSegmentationDataset,
        batch_size: int = 4,
        drop_last: bool = True,
        seed: int = 42,
    ):
        self.dataset = dataset
        self.batch_size = batch_size
        self.drop_last = drop_last
        self.seed = seed
        self._epoch = 0

    def set_epoch(self, epoch: int):
        """Update RNG for the new epoch — different ordering each epoch."""
        self._epoch = epoch

    def __iter__(self) -> Iterator[list[int]]:
        rng = random.Random(self.seed + self._epoch)
        samples = self.dataset.samples
        flat_index = self.dataset._flat_index

        # Group flat indices by strat_key
        strat_queues: dict[str, deque[int]] = defaultdict(deque)
        for flat_idx, (si, _zi) in enumerate(flat_index):
            key = samples[si].strat_key
            strat_queues[key].append(flat_idx)

        # Shuffle within each stratum
        for key in strat_queues:
            items = list(strat_queues[key])
            rng.shuffle(items)
            strat_queues[key] = deque(items)

        # Build round-robin schedule weighted by stratum size
        # Larger strata appear more often in the schedule
        schedule: list[str] = []
        for key, q in strat_queues.items():
            # Number of times this key appears in one full pass of the schedule
            count = max(1, round(len(q) / self.batch_size))
            schedule.extend([key] * count)
        rng.shuffle(schedule)

        # Index for looking up which source a flat_idx belongs to
        def source_of(flat_idx: int) -> str:
            si, _ = flat_index[flat_idx]
            return samples[si].source_file

        # Assemble batches
        schedule_pos = 0
        remaining = sum(len(q) for q in strat_queues.values())

        while remaining >= self.batch_size:
            batch: list[int] = []
            sources_in_batch: set[str] = set()

            for _ in range(self.batch_size):
                found = False
                # Try strat keys from schedule, looking for source diversity
                for attempt in range(len(schedule)):
                    key = schedule[(schedule_pos + attempt) % len(schedule)]
                    q = strat_queues[key]
                    if not q:
                        continue
                    # Try to find an index from a source not already in this batch
                    # Check the front of the queue
                    src = source_of(q[0])
                    if src not in sources_in_batch:
                        idx = q.popleft()
                        batch.append(idx)
                        sources_in_batch.add(src)
                        schedule_pos = (schedule_pos + attempt + 1) % len(schedule)
                        found = True
                        break
                if not found:
                    # Relax source constraint — just take from any non-empty queue
                    for key in strat_queues:
                        if strat_queues[key]:
                            batch.append(strat_queues[key].popleft())
                            found = True
                            break
                if not found:
                    break  # all queues empty

            remaining = sum(len(q) for q in strat_queues.values())

            if len(batch) == self.batch_size:
                yield batch
            elif not self.drop_last and batch:
                yield batch

        # Yield any remaining indices if not dropping last
        if not self.drop_last:
            leftover = []
            for q in strat_queues.values():
                leftover.extend(q)
            if leftover:
                yield leftover

    def __len__(self) -> int:
        total = len(self.dataset)
        if self.drop_last:
            return total // self.batch_size
        return (total + self.batch_size - 1) // self.batch_size


# ---------------------------------------------------------------------------
# 6. get_dataloaders — wires everything together
# ---------------------------------------------------------------------------

def get_dataloaders(
    root: str,
    image_size: tuple[int, int] = (512, 512),
    batch_size: int = 4,
    num_workers: int = 4,
    stratification: StratificationConfig | None = None,
) -> tuple:
    """Create train and validation dataloaders.

    With default settings, uses source-aware splitting and stratified
    batch sampling. Pass StratificationConfig(use_stratified_batches=False)
    to fall back to standard shuffle.
    """
    if stratification is None:
        stratification = StratificationConfig()

    # 1. Build sample index from annotations
    all_samples = _load_sample_index(Path(root), stratification.density_bins)

    # 2. Source-aware split
    train_samples, val_samples = _source_aware_split(
        all_samples,
        val_fraction=stratification.val_fraction,
        seed=stratification.seed,
    )

    # Log density distribution
    from collections import Counter
    train_bins = Counter(s.density_bin for s in train_samples)
    train_strat = Counter(s.strat_key for s in train_samples)
    logger.info(f"Train density bins: {dict(train_bins)}")
    logger.info(f"Train strat keys (top 6): {train_strat.most_common(6)}")

    # 3. Build datasets
    train_ds = ZoneSegmentationDataset(
        root, train_samples, image_size=image_size, augment=True,
    )
    val_ds = ZoneSegmentationDataset(
        root, val_samples, image_size=image_size, augment=False,
    )

    # 4. Build loaders
    if stratification.use_stratified_batches:
        train_sampler = StratifiedBatchSampler(
            train_ds, batch_size=batch_size,
            drop_last=True, seed=stratification.seed,
        )
        train_loader = torch.utils.data.DataLoader(
            train_ds,
            batch_sampler=train_sampler,
            num_workers=num_workers,
            pin_memory=True,
        )
    else:
        train_loader = torch.utils.data.DataLoader(
            train_ds, batch_size=batch_size, shuffle=True,
            num_workers=num_workers, pin_memory=True, drop_last=True,
        )

    val_loader = torch.utils.data.DataLoader(
        val_ds, batch_size=batch_size, shuffle=False,
        num_workers=num_workers, pin_memory=True,
    )

    return train_loader, val_loader
