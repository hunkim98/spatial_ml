"""Vanilla U-Net with FiLM conditioning for zone segmentation.

Matches LOAM's encoder architecture: 4 downsampling blocks, each with
2× (3x3 conv + BN + ReLU) + 2×2 maxpool.  No pretrained backbone.

Differences from unet.py (ResNet-34 variant):
    - No aggressive initial 4× downsampling (ResNet's 7×7 stride-2 + maxpool)
    - Gradual 2× downsampling at each level — preserves fine spatial detail
    - No pretrained weights — trained from scratch
    - Same PatternEncoder + FiLM conditioning in decoder

Architecture:
    Encoder: 3 → 64 → 128 → 256 → 512 (4 blocks, each /2)
    Bottleneck: 512 → 1024
    Decoder: 1024 → 512 → 256 → 128 → 64 (4 blocks, each ×2, with FiLM)
    Output: 64 → 1
"""

import torch
import torch.nn as nn
import torch.nn.functional as F


class PatternEncoder(nn.Module):
    """Encode a 32×32 pattern thumbnail into a conditioning vector."""

    def __init__(self, embed_dim: int = 256):
        super().__init__()
        self.net = nn.Sequential(
            nn.Conv2d(3, 64, 3, stride=2, padding=1),   # 32→16
            nn.BatchNorm2d(64),
            nn.ReLU(inplace=True),
            nn.Conv2d(64, 128, 3, stride=2, padding=1),  # 16→8
            nn.BatchNorm2d(128),
            nn.ReLU(inplace=True),
            nn.Conv2d(128, 256, 3, stride=2, padding=1),  # 8→4
            nn.BatchNorm2d(256),
            nn.ReLU(inplace=True),
            nn.AdaptiveAvgPool2d(1),                       # 4→1
            nn.Flatten(),
            nn.Linear(256, embed_dim),
        )

    def forward(self, pattern: torch.Tensor) -> torch.Tensor:
        return self.net(pattern)


class FiLM(nn.Module):
    """Feature-wise Linear Modulation."""

    def __init__(self, n_channels: int, embed_dim: int = 256):
        super().__init__()
        self.gamma = nn.Linear(embed_dim, n_channels)
        self.beta = nn.Linear(embed_dim, n_channels)

    def forward(self, x: torch.Tensor, cond: torch.Tensor) -> torch.Tensor:
        gamma = self.gamma(cond).unsqueeze(-1).unsqueeze(-1)
        beta = self.beta(cond).unsqueeze(-1).unsqueeze(-1)
        return gamma * x + beta


class EncoderBlock(nn.Module):
    """Vanilla U-Net encoder block: 2× (conv3x3 + BN + ReLU) + maxpool."""

    def __init__(self, in_ch: int, out_ch: int):
        super().__init__()
        self.conv = nn.Sequential(
            nn.Conv2d(in_ch, out_ch, 3, padding=1),
            nn.BatchNorm2d(out_ch),
            nn.ReLU(inplace=True),
            nn.Conv2d(out_ch, out_ch, 3, padding=1),
            nn.BatchNorm2d(out_ch),
            nn.ReLU(inplace=True),
        )
        self.pool = nn.MaxPool2d(2, stride=2)

    def forward(self, x: torch.Tensor) -> tuple[torch.Tensor, torch.Tensor]:
        """Returns (pooled_output, skip_connection)."""
        features = self.conv(x)
        pooled = self.pool(features)
        return pooled, features


class DecoderBlock(nn.Module):
    """Vanilla U-Net decoder block: upsample + concat skip + 2× conv + FiLM."""

    def __init__(self, in_ch: int, skip_ch: int, out_ch: int, embed_dim: int = 256):
        super().__init__()
        self.up = nn.ConvTranspose2d(in_ch, in_ch, 2, stride=2)
        self.conv = nn.Sequential(
            nn.Conv2d(in_ch + skip_ch, out_ch, 3, padding=1),
            nn.BatchNorm2d(out_ch),
            nn.ReLU(inplace=True),
            nn.Conv2d(out_ch, out_ch, 3, padding=1),
            nn.BatchNorm2d(out_ch),
            nn.ReLU(inplace=True),
        )
        self.film = FiLM(out_ch, embed_dim)

    def forward(self, x: torch.Tensor, skip: torch.Tensor, cond: torch.Tensor) -> torch.Tensor:
        x = self.up(x)
        if x.shape[2:] != skip.shape[2:]:
            x = F.interpolate(x, size=skip.shape[2:], mode="bilinear", align_corners=False)
        x = torch.cat([x, skip], dim=1)
        x = self.conv(x)
        x = self.film(x, cond)
        return x


class VanillaUNet(nn.Module):
    """Vanilla U-Net with FiLM conditioning (no pretrained backbone).

    Matches LOAM's 4-level encoder/decoder structure. Gradual 2× downsampling
    at each level preserves fine spatial detail better than ResNet's aggressive
    initial 4× downsampling.

    Channel progression:
        Encoder: 3 → 64 → 128 → 256 → 512
        Bottleneck: 512 → 1024
        Decoder: 1024 → 512 → 256 → 128 → 64
        Output: 64 → 1
    """

    def __init__(self, embed_dim: int = 256):
        super().__init__()
        self.embed_dim = embed_dim

        # Pattern encoder (same as ResNet variant)
        self.pattern_encoder = PatternEncoder(embed_dim)

        # Encoder path
        self.enc1 = EncoderBlock(3, 64)      # /2, 64
        self.enc2 = EncoderBlock(64, 128)     # /4, 128
        self.enc3 = EncoderBlock(128, 256)    # /8, 256
        self.enc4 = EncoderBlock(256, 512)    # /16, 512

        # Bottleneck
        self.bottleneck = nn.Sequential(
            nn.Conv2d(512, 1024, 3, padding=1),
            nn.BatchNorm2d(1024),
            nn.ReLU(inplace=True),
            nn.Conv2d(1024, 1024, 3, padding=1),
            nn.BatchNorm2d(1024),
            nn.ReLU(inplace=True),
        )

        # Decoder path (with FiLM at each level)
        self.dec4 = DecoderBlock(1024, 512, 512, embed_dim)  # /8
        self.dec3 = DecoderBlock(512, 256, 256, embed_dim)   # /4
        self.dec2 = DecoderBlock(256, 128, 128, embed_dim)   # /2
        self.dec1 = DecoderBlock(128, 64, 64, embed_dim)     # /1

        # Final output
        self.final_conv = nn.Sequential(
            nn.Conv2d(64, 64, 3, padding=1),
            nn.ReLU(inplace=True),
            nn.Conv2d(64, 1, 1),
        )

    def forward(self, image: torch.Tensor, pattern: torch.Tensor) -> torch.Tensor:
        """
        Args:
            image: (B, 3, H, W) — map image
            pattern: (B, 3, 32, 32) — pattern thumbnail

        Returns:
            (B, 1, H, W) — binary mask logits (pre-sigmoid)
        """
        cond = self.pattern_encoder(pattern)

        # Encoder
        x, s1 = self.enc1(image)   # x: (B, 64, H/2, W/2),   s1: (B, 64, H, W)
        x, s2 = self.enc2(x)       # x: (B, 128, H/4, W/4),  s2: (B, 128, H/2, W/2)
        x, s3 = self.enc3(x)       # x: (B, 256, H/8, W/8),  s3: (B, 256, H/4, W/4)
        x, s4 = self.enc4(x)       # x: (B, 512, H/16, W/16), s4: (B, 512, H/8, W/8)

        # Bottleneck
        x = self.bottleneck(x)     # (B, 1024, H/16, W/16)

        # Decoder with FiLM conditioning
        x = self.dec4(x, s4, cond)  # (B, 512, H/8, W/8)
        x = self.dec3(x, s3, cond)  # (B, 256, H/4, W/4)
        x = self.dec2(x, s2, cond)  # (B, 128, H/2, W/2)
        x = self.dec1(x, s1, cond)  # (B, 64, H, W)

        # Output
        out = self.final_conv(x)    # (B, 1, H, W)
        return out
