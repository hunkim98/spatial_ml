"""Fine-tune the pretrained zone-segmentation model on a small set of real USGS maps.

Implements paper/TODO.md Priority 1A — THE critical experiment for the SIGSPATIAL
paper. Compares pretrained vs random init under the same fine-tune protocol.

Pipeline:
    1. Load 2 (configurable) USGS maps as the fine-tune set.
    2. Build USGSFinetuneDataset that yields random (image_512, swatch_32, mask_512)
       triplets cropped from those maps' poly features.
    3. Load the pretrained VanillaUNet checkpoint (or build from scratch).
    4. Optionally freeze the encoder for the first N epochs.
    5. Fine-tune with low LR (1e-6 default) using SGD + Dice loss.
    6. Save checkpoints at epoch 5, 10, 20.

Evaluation: re-use eval_usgs.py with the resulting checkpoints, passing
--exclude-maps to drop the fine-tune maps from the eval set.

Usage:
    # Pretrained init
    python -m model.zone_segmentation.scripts.finetune_usgs \
        --pretrained checkpoints/zone_seg_loam_vanilla_v2/best.pt \
        --finetune-maps AR_StJoe AK_Dillingham \
        --epochs 20 --save-dir checkpoints/finetune_pretrained

    # Random init (baseline)
    python -m model.zone_segmentation.scripts.finetune_usgs \
        --random-init \
        --finetune-maps AR_StJoe AK_Dillingham \
        --epochs 20 --save-dir checkpoints/finetune_scratch
"""
from __future__ import annotations

import argparse
import json
import logging
import os
import random
import sys
from pathlib import Path

import numpy as np
import torch
import torch.nn as nn
from PIL import Image
from torch.optim import SGD
from torch.optim.lr_scheduler import CosineAnnealingLR
from torch.utils.data import DataLoader, Dataset
from torchvision import transforms
from tqdm import tqdm

from ..losses import DiceLoss
from ..metrics import dice_score, iou_score, precision_recall_f1
from ..unet_vanilla import VanillaUNet
from .eval_usgs import (
    crop_legend_swatch,
    extract_dataset,
    get_poly_features,
    load_gt_raster,
    load_map_image,
)

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Dataset — random crops from real USGS maps
# ---------------------------------------------------------------------------

class USGSFinetuneDataset(Dataset):
    """Yields (image_tile, swatch_thumbnail, mask_tile) triplets from USGS maps.

    Strategy: pre-load each (map, feature) into memory, then sample random crops
    on the fly. Maps are big (~10K×10K) but we only hold one feature's GT at a time
    — we keep map RGBs cached and load GT lazily per __getitem__.

    Args:
        feature_records: list of dicts with keys 'map', 'label', 'bbox'.
        map_arrays: dict {map_name: np.ndarray [H,W,3]}, pre-loaded full maps.
        gt_dir: directory of GT rasters.
        crop_size: tile size to crop (must match model input — 512 for VanillaUNet).
        crops_per_feature: how many random crops to draw per epoch per feature.
        positive_ratio: fraction of crops biased to land on positive-mask regions.
        clean_pattern: pass through to crop_legend_swatch.
    """

    def __init__(
        self,
        feature_records: list[dict],
        map_arrays: dict[str, np.ndarray],
        gt_dir: Path,
        crop_size: int = 512,
        crops_per_feature: int = 64,
        positive_ratio: float = 0.7,
        clean_pattern: bool = True,
        seed: int = 42,
    ):
        self.feature_records = feature_records
        self.map_arrays = map_arrays
        self.gt_dir = gt_dir
        self.crop_size = crop_size
        self.crops_per_feature = crops_per_feature
        self.positive_ratio = positive_ratio
        self.rng = random.Random(seed)

        # Cache cleaned swatches once (these are small)
        self._swatches: dict[tuple[str, str], Image.Image] = {}
        # Cache GTs and positive-pixel coords once (these can be big but we need them)
        self._gts: dict[tuple[str, str], tuple[np.ndarray, np.ndarray] | None] = {}

        # Pre-load swatches and GTs, drop features without GT
        valid_records = []
        for rec in feature_records:
            m, lbl, bbox = rec["map"], rec["label"], rec["bbox"]
            if m not in map_arrays:
                logger.warning("Map %s not loaded — skipping %s", m, lbl)
                continue
            map_arr = map_arrays[m]

            gt = load_gt_raster(gt_dir, m, lbl)
            if gt is None:
                logger.info("No GT for %s/%s — skipping", m, lbl)
                continue
            # Resize GT to map shape if necessary
            if gt.shape[:2] != map_arr.shape[:2]:
                gt_img = Image.fromarray((gt * 255).astype(np.uint8)).resize(
                    (map_arr.shape[1], map_arr.shape[0]), Image.NEAREST,
                )
                gt = (np.array(gt_img) > 0).astype(np.uint8)

            pos_coords = np.argwhere(gt > 0)
            if pos_coords.size == 0:
                logger.info("Empty GT for %s/%s — skipping", m, lbl)
                continue

            self._swatches[(m, lbl)] = crop_legend_swatch(map_arr, bbox, clean=clean_pattern)
            self._gts[(m, lbl)] = (gt, pos_coords)
            valid_records.append(rec)

        self.feature_records = valid_records
        logger.info("Loaded %d valid (map, feature) pairs for fine-tuning",
                    len(self.feature_records))

        # Standard ImageNet normalization (matches our existing dataset)
        self.image_transform = transforms.Compose([
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

    def __len__(self) -> int:
        return len(self.feature_records) * self.crops_per_feature

    def _sample_crop_origin(
        self, gt: np.ndarray, pos_coords: np.ndarray, map_h: int, map_w: int,
    ) -> tuple[int, int]:
        """Pick (y0, x0) so the crop has a good chance of overlapping positives."""
        cs = self.crop_size
        if self.rng.random() < self.positive_ratio and pos_coords.size > 0:
            # Pick a positive pixel and put it somewhere near the crop center
            i = self.rng.randrange(len(pos_coords))
            cy, cx = pos_coords[i]
            jitter = self.rng.randint(-cs // 4, cs // 4)
            y0 = int(np.clip(cy - cs // 2 + jitter, 0, map_h - cs))
            x0 = int(np.clip(cx - cs // 2 + jitter, 0, map_w - cs))
        else:
            y0 = self.rng.randint(0, max(0, map_h - cs))
            x0 = self.rng.randint(0, max(0, map_w - cs))
        return y0, x0

    def __getitem__(self, idx: int):
        rec = self.feature_records[idx % len(self.feature_records)]
        m, lbl = rec["map"], rec["label"]
        map_arr = self.map_arrays[m]
        gt, pos_coords = self._gts[(m, lbl)]
        H, W = map_arr.shape[:2]

        y0, x0 = self._sample_crop_origin(gt, pos_coords, H, W)
        cs = self.crop_size

        # Pad if map is smaller than crop_size in any dim
        img_crop = np.zeros((cs, cs, 3), dtype=np.uint8)
        msk_crop = np.zeros((cs, cs), dtype=np.uint8)
        img_src = map_arr[y0:y0 + cs, x0:x0 + cs]
        msk_src = gt[y0:y0 + cs, x0:x0 + cs]
        h_src, w_src = img_src.shape[:2]
        img_crop[:h_src, :w_src] = img_src
        msk_crop[:h_src, :w_src] = msk_src

        # Augment: random h/v flip + 0/90/180/270 rotation
        if self.rng.random() < 0.5:
            img_crop = img_crop[:, ::-1, :].copy()
            msk_crop = msk_crop[:, ::-1].copy()
        if self.rng.random() < 0.5:
            img_crop = img_crop[::-1, :, :].copy()
            msk_crop = msk_crop[::-1, :].copy()
        rot_k = self.rng.randint(0, 3)
        if rot_k:
            img_crop = np.rot90(img_crop, k=rot_k).copy()
            msk_crop = np.rot90(msk_crop, k=rot_k).copy()

        image_t = self.image_transform(Image.fromarray(img_crop))
        pattern_t = self.pattern_transform(self._swatches[(m, lbl)])
        mask_t = torch.from_numpy(msk_crop).float().unsqueeze(0)

        return image_t, pattern_t, mask_t


# ---------------------------------------------------------------------------
# Loading + freezing helpers
# ---------------------------------------------------------------------------

def freeze_encoder(model: VanillaUNet, freeze: bool) -> None:
    """Freeze/unfreeze the encoder half of the U-Net (PatternEncoder + enc1..4 + bottleneck)."""
    encoder_modules = [model.pattern_encoder, model.enc1, model.enc2,
                       model.enc3, model.enc4, model.bottleneck]
    n = 0
    for mod in encoder_modules:
        for p in mod.parameters():
            p.requires_grad = not freeze
            n += 1
    logger.info("%s %d encoder params (pattern_encoder + enc1..4 + bottleneck)",
                "Froze" if freeze else "Unfroze", n)


def load_pretrained(model: VanillaUNet, ckpt_path: Path) -> None:
    state = torch.load(ckpt_path, map_location="cpu", weights_only=False)
    if isinstance(state, dict) and "model_state_dict" in state:
        state = state["model_state_dict"]
    result = model.load_state_dict(state, strict=False)
    logger.info("Loaded pretrained from %s — missing=%d unexpected=%d",
                ckpt_path, len(result.missing_keys), len(result.unexpected_keys))
    if result.missing_keys:
        logger.warning("  Missing: %s", result.missing_keys[:5])
    if result.unexpected_keys:
        logger.warning("  Unexpected: %s", result.unexpected_keys[:5])


# ---------------------------------------------------------------------------
# Train loop
# ---------------------------------------------------------------------------

def fine_tune(
    model: VanillaUNet,
    train_loader: DataLoader,
    *,
    epochs: int,
    lr: float,
    momentum: float,
    weight_decay: float,
    device: str,
    save_dir: Path,
    freeze_encoder_epochs: int,
    save_at_epochs: list[int],
    grad_clip: float,
    use_amp: bool,
    wandb_run=None,
) -> dict:
    save_dir.mkdir(parents=True, exist_ok=True)
    history = {"epoch": [], "loss": [], "iou": [], "dice": [], "f1": [], "lr": []}

    model = model.to(device)
    criterion = DiceLoss()
    optimizer = SGD(filter(lambda p: p.requires_grad, model.parameters()),
                    lr=lr, momentum=momentum, weight_decay=weight_decay)
    scheduler = CosineAnnealingLR(optimizer, T_max=max(1, epochs))
    scaler = torch.amp.GradScaler("cuda", enabled=use_amp and device == "cuda")

    global_step = 0

    if freeze_encoder_epochs > 0:
        freeze_encoder(model, freeze=True)

    for epoch in range(1, epochs + 1):
        if epoch == freeze_encoder_epochs + 1 and freeze_encoder_epochs > 0:
            freeze_encoder(model, freeze=False)
            # Re-build optimizer to include unfrozen params
            optimizer = SGD(filter(lambda p: p.requires_grad, model.parameters()),
                            lr=lr, momentum=momentum, weight_decay=weight_decay)
            # Restart cosine schedule for the remaining epochs
            scheduler = CosineAnnealingLR(optimizer, T_max=max(1, epochs - freeze_encoder_epochs))

        model.train()
        tot_loss = tot_iou = tot_dice = tot_f1 = 0.0
        n = 0
        pbar = tqdm(train_loader, desc=f"Epoch {epoch}/{epochs}", leave=False, unit="batch")
        for images, patterns, masks in pbar:
            images = images.to(device, non_blocking=True)
            patterns = patterns.to(device, non_blocking=True)
            masks = masks.to(device, non_blocking=True)

            optimizer.zero_grad(set_to_none=True)
            with torch.amp.autocast(device_type="cuda" if device == "cuda" else "cpu",
                                     enabled=use_amp):
                logits = model(images, patterns)
                loss = criterion(logits, masks)

            if scaler.is_enabled():
                scaler.scale(loss).backward()
                scaler.unscale_(optimizer)
                torch.nn.utils.clip_grad_norm_(model.parameters(), grad_clip)
                scaler.step(optimizer)
                scaler.update()
            else:
                loss.backward()
                torch.nn.utils.clip_grad_norm_(model.parameters(), grad_clip)
                optimizer.step()

            with torch.no_grad():
                _, _, f1 = precision_recall_f1(logits.detach(), masks)
                batch_iou = iou_score(logits.detach(), masks)
                batch_dice = dice_score(logits.detach(), masks)
                tot_iou += batch_iou
                tot_dice += batch_dice
                tot_f1 += f1
            tot_loss += loss.item()
            n += 1
            global_step += 1
            pbar.set_postfix(loss=f"{loss.item():.4f}",
                             iou=f"{tot_iou / n:.3f}", f1=f"{tot_f1 / n:.3f}")

            if wandb_run is not None and global_step % 10 == 0:
                wandb_run.log({
                    "train/batch_loss": loss.item(),
                    "train/batch_iou": batch_iou,
                    "train/batch_dice": batch_dice,
                    "train/batch_f1": f1,
                    "global_step": global_step,
                }, step=global_step)

        scheduler.step()
        cur_lr = optimizer.param_groups[0]["lr"]
        avg = {k: v / max(1, n) for k, v in
               [("loss", tot_loss), ("iou", tot_iou),
                ("dice", tot_dice), ("f1", tot_f1)]}
        history["epoch"].append(epoch)
        history["loss"].append(avg["loss"])
        history["iou"].append(avg["iou"])
        history["dice"].append(avg["dice"])
        history["f1"].append(avg["f1"])
        history["lr"].append(cur_lr)

        logger.info(
            "Epoch %d/%d  lr=%.2e  loss=%.4f  iou=%.4f  dice=%.4f  f1=%.4f  "
            "(encoder %s)",
            epoch, epochs, cur_lr, avg["loss"], avg["iou"], avg["dice"], avg["f1"],
            "frozen" if epoch <= freeze_encoder_epochs else "trainable",
        )

        if wandb_run is not None:
            wandb_run.log({
                "train/epoch_loss": avg["loss"],
                "train/epoch_iou": avg["iou"],
                "train/epoch_dice": avg["dice"],
                "train/epoch_f1": avg["f1"],
                "train/lr": cur_lr,
                "epoch": epoch,
                "encoder_frozen": int(epoch <= freeze_encoder_epochs),
            }, step=global_step)

        if epoch in save_at_epochs:
            ckpt_path = save_dir / f"epoch{epoch}.pt"
            torch.save(model.state_dict(), ckpt_path)
            logger.info("  Saved %s", ckpt_path)

    final_path = save_dir / "final.pt"
    torch.save(model.state_dict(), final_path)
    with open(save_dir / "history.json", "w") as f:
        json.dump(history, f, indent=2)
    logger.info("Saved final checkpoint and history to %s", save_dir)
    return history


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def _pick_device() -> str:
    if torch.cuda.is_available():
        return "cuda"
    if torch.backends.mps.is_available():
        return "mps"
    return "cpu"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pretrained", type=Path, default=None,
                        help="Path to pretrained checkpoint (omit + use --random-init for scratch)")
    parser.add_argument("--random-init", action="store_true",
                        help="Train from scratch (no --pretrained). Sets seed for reproducibility.")
    parser.add_argument("--finetune-maps", nargs="+", required=True,
                        help="Map stems to use for fine-tuning (e.g. AR_StJoe AK_Dillingham)")

    parser.add_argument("--usgs-dir", type=Path, default=Path("usgs"))
    parser.add_argument("--dataset", default="validation",
                        choices=["validation", "evaluation"])
    parser.add_argument("--work-dir", type=Path,
                        default=Path("C:/Users/piljo/AppData/Local/Temp/usgs_eval"))

    parser.add_argument("--save-dir", type=Path, required=True,
                        help="Where to write checkpoints + history")

    # Training knobs
    parser.add_argument("--epochs", type=int, default=20)
    parser.add_argument("--save-at-epochs", nargs="+", type=int, default=[5, 10, 20])
    parser.add_argument("--lr", type=float, default=1e-6,
                        help="Low LR for fine-tuning (1e-6 default per TODO 1A)")
    parser.add_argument("--momentum", type=float, default=0.999)
    parser.add_argument("--weight-decay", type=float, default=1e-8)
    parser.add_argument("--freeze-encoder-epochs", type=int, default=3,
                        help="Epochs to freeze encoder for (0 = never freeze)")

    parser.add_argument("--batch-size", type=int, default=4)
    parser.add_argument("--num-workers", type=int, default=0)
    parser.add_argument("--crop-size", type=int, default=512)
    parser.add_argument("--crops-per-feature", type=int, default=64)
    parser.add_argument("--positive-ratio", type=float, default=0.7)

    parser.add_argument("--device", default=_pick_device())
    parser.add_argument("--grad-clip", type=float, default=1.0)
    parser.add_argument("--no-amp", action="store_true")
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--no-wandb", action="store_true",
                        help="Disable W&B even if WANDB_API_KEY is set")
    parser.add_argument("--wandb-project", default="spatially-zone-segmentation",
                        help="W&B project name")
    parser.add_argument("--wandb-run-name", default=None,
                        help="W&B run name (auto-generated if omitted)")
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO,
                        format="%(asctime)s %(levelname)s %(message)s",
                        datefmt="%H:%M:%S",
                        stream=sys.stdout)

    # Reproducibility
    random.seed(args.seed)
    np.random.seed(args.seed)
    torch.manual_seed(args.seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(args.seed)

    # Sanity: must specify exactly one of --pretrained / --random-init
    if not args.pretrained and not args.random_init:
        parser.error("Must specify either --pretrained PATH or --random-init")
    if args.pretrained and args.random_init:
        parser.error("Cannot specify both --pretrained and --random-init")

    # Set up W&B if a key is available + not disabled
    wandb_run = None
    has_key = bool(os.environ.get("WANDB_API_KEY"))
    use_wandb = (not args.no_wandb) and has_key
    if use_wandb:
        try:
            import wandb
            from datetime import datetime as _dt
            init_tag = "pretrained" if args.pretrained else "scratch"
            run_name = args.wandb_run_name or (
                f"finetune-{init_tag}-e{args.epochs}-lr{args.lr:g}-"
                f"{_dt.now().strftime('%Y%m%d-%H%M%S')}"
            )
            wandb_run = wandb.init(
                project=args.wandb_project,
                name=run_name,
                config={
                    "task": "finetune_usgs",
                    "init": init_tag,
                    "pretrained_path": str(args.pretrained) if args.pretrained else None,
                    "finetune_maps": args.finetune_maps,
                    "epochs": args.epochs,
                    "save_at_epochs": args.save_at_epochs,
                    "lr": args.lr,
                    "momentum": args.momentum,
                    "weight_decay": args.weight_decay,
                    "freeze_encoder_epochs": args.freeze_encoder_epochs,
                    "crop_size": args.crop_size,
                    "crops_per_feature": args.crops_per_feature,
                    "positive_ratio": args.positive_ratio,
                    "batch_size": args.batch_size,
                    "seed": args.seed,
                    "model": "VanillaUNet",
                },
            )
            logger.info("W&B run: %s (project=%s)", wandb_run.name, args.wandb_project)
        except ImportError:
            logger.warning("wandb not installed — falling back to file-only logging")
            use_wandb = False
        except Exception as exc:
            logger.warning("wandb init failed (%s) — file-only logging", exc)
            use_wandb = False
    elif args.no_wandb:
        logger.info("W&B disabled by --no-wandb")
    else:
        logger.info("WANDB_API_KEY not set — file-only logging")

    print("=" * 80)
    print("USGS Fine-Tuning Experiment (TODO 1A)")
    print("=" * 80)
    print(f"  Init:               {'pretrained ' + str(args.pretrained) if args.pretrained else 'random (from scratch)'}")
    print(f"  Fine-tune maps:     {args.finetune_maps}")
    print(f"  Epochs:             {args.epochs}")
    print(f"  Save at:            {args.save_at_epochs}")
    print(f"  LR / momentum / WD: {args.lr} / {args.momentum} / {args.weight_decay}")
    print(f"  Freeze encoder:     {args.freeze_encoder_epochs} epochs")
    print(f"  Crop size:          {args.crop_size}")
    print(f"  Crops/feature:      {args.crops_per_feature}")
    print(f"  Batch size:         {args.batch_size}")
    print(f"  Device:             {args.device}")
    print(f"  Save dir:           {args.save_dir}")
    print("=" * 80)

    # 1. Extract USGS data
    map_dir, json_dir, gt_dir = extract_dataset(args.usgs_dir, args.dataset, args.work_dir)

    # 2. Load only the fine-tune maps + their features
    map_arrays: dict[str, np.ndarray] = {}
    feature_records: list[dict] = []
    for stem in args.finetune_maps:
        tif = map_dir / f"{stem}.tif"
        jsn = json_dir / f"{stem}.json"
        if not tif.exists() or not jsn.exists():
            logger.error("Missing %s.tif or .json — skipping", stem)
            continue
        logger.info("Loading map %s ...", stem)
        map_arrays[stem] = load_map_image(tif)
        for f in get_poly_features(jsn):
            feature_records.append({"map": stem, "label": f["label"], "bbox": f["bbox"]})

    if not feature_records:
        logger.error("No features loaded — aborting")
        sys.exit(1)
    logger.info("Loaded %d features across %d maps",
                len(feature_records), len(map_arrays))

    # 3. Build dataset + loader
    ds = USGSFinetuneDataset(
        feature_records=feature_records,
        map_arrays=map_arrays,
        gt_dir=gt_dir,
        crop_size=args.crop_size,
        crops_per_feature=args.crops_per_feature,
        positive_ratio=args.positive_ratio,
        clean_pattern=True,
        seed=args.seed,
    )
    if len(ds) == 0:
        logger.error("Empty dataset (all features filtered) — aborting")
        sys.exit(1)
    loader = DataLoader(ds, batch_size=args.batch_size, shuffle=True,
                        num_workers=args.num_workers, pin_memory=True, drop_last=True)
    logger.info("Dataset: %d effective samples / epoch (%d features × %d crops)",
                len(ds), len(ds.feature_records), args.crops_per_feature)

    # 4. Build model
    model = VanillaUNet()
    if args.pretrained:
        load_pretrained(model, args.pretrained)
    n_params = sum(p.numel() for p in model.parameters()) / 1e6
    logger.info("Model: VanillaUNet (%.1fM params, init=%s)",
                n_params, "pretrained" if args.pretrained else "random")

    # 5. Fine-tune
    fine_tune(
        model, loader,
        epochs=args.epochs, lr=args.lr,
        momentum=args.momentum, weight_decay=args.weight_decay,
        device=args.device, save_dir=args.save_dir,
        freeze_encoder_epochs=args.freeze_encoder_epochs,
        save_at_epochs=args.save_at_epochs,
        grad_clip=args.grad_clip, use_amp=not args.no_amp,
        wandb_run=wandb_run,
    )

    if wandb_run is not None:
        wandb_run.finish()

    print("\n" + "=" * 80)
    print(f"Fine-tune complete. Checkpoints in {args.save_dir}")
    print("Next: evaluate with eval_usgs.py + --exclude-maps "
          + " ".join(args.finetune_maps))
    print("=" * 80)


if __name__ == "__main__":
    main()
