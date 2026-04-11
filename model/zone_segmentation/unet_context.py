"""Context-aware vanilla U-Net for zone segmentation.

Adds a "legend encoder" that processes ALL patterns for a map together,
giving the model context about inter-pattern relationships (e.g., "3 other
patterns look similar to the target", "there are 20 total zones").

Architecture:
    - Image encoder: vanilla U-Net (same as unet_vanilla.py)
    - Target pattern: 32×32 → PatternEncoder → 256-dim
    - Legend image: 128×128 grid of ALL patterns → LegendEncoder → 256-dim
    - Conditioning: target embedding + legend embedding → FiLM at each decoder level
"""

import math

import torch
import torch.nn as nn
import torch.nn.functional as F
from PIL import Image
from torchvision import transforms


# ---------------------------------------------------------------------------
# Legend image construction (used by dataset, importable)
# ---------------------------------------------------------------------------

def build_legend_image(
    pattern_paths: list[str],
    canvas_size: int = 128,
) -> Image.Image:
    """Arrange all pattern thumbnails into a fixed-size grid image.

    Args:
        pattern_paths: paths to all pattern PNGs for this map
        canvas_size: output image size (square)

    Returns:
        PIL Image (RGB, canvas_size × canvas_size)
    """
    n = len(pattern_paths)
    if n == 0:
        return Image.new("RGB", (canvas_size, canvas_size), (0, 0, 0))

    # Grid dimensions
    cols = math.ceil(math.sqrt(n))
    rows = math.ceil(n / cols)
    tile_size = canvas_size // max(cols, rows)
    tile_size = max(tile_size, 1)

    canvas = Image.new("RGB", (canvas_size, canvas_size), (0, 0, 0))
    for i, path in enumerate(pattern_paths):
        r, c = divmod(i, cols)
        pat = Image.open(path).convert("RGB").resize(
            (tile_size, tile_size), Image.BILINEAR,
        )
        canvas.paste(pat, (c * tile_size, r * tile_size))

    return canvas


# ---------------------------------------------------------------------------
# Model components
# ---------------------------------------------------------------------------

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
            nn.AdaptiveAvgPool2d(1),
            nn.Flatten(),
            nn.Linear(256, embed_dim),
        )

    def forward(self, pattern: torch.Tensor) -> torch.Tensor:
        return self.net(pattern)


class LegendEncoder(nn.Module):
    """Encode a 128×128 legend grid (all patterns) into a context vector."""

    def __init__(self, embed_dim: int = 256):
        super().__init__()
        self.net = nn.Sequential(
            nn.Conv2d(3, 64, 3, stride=2, padding=1),    # 128→64
            nn.BatchNorm2d(64),
            nn.ReLU(inplace=True),
            nn.Conv2d(64, 128, 3, stride=2, padding=1),   # 64→32
            nn.BatchNorm2d(128),
            nn.ReLU(inplace=True),
            nn.Conv2d(128, 256, 3, stride=2, padding=1),  # 32→16
            nn.BatchNorm2d(256),
            nn.ReLU(inplace=True),
            nn.Conv2d(256, 256, 3, stride=2, padding=1),  # 16→8
            nn.BatchNorm2d(256),
            nn.ReLU(inplace=True),
            nn.AdaptiveAvgPool2d(1),
            nn.Flatten(),
            nn.Linear(256, embed_dim),
        )

    def forward(self, legend: torch.Tensor) -> torch.Tensor:
        return self.net(legend)


class FiLM(nn.Module):
    """Feature-wise Linear Modulation — conditions on combined embedding."""

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
        features = self.conv(x)
        pooled = self.pool(features)
        return pooled, features


class DecoderBlock(nn.Module):
    """Decoder block: upsample + concat skip + 2× conv + FiLM."""

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


class ContextUNet(nn.Module):
    """Vanilla U-Net conditioned on target pattern + legend context.

    The conditioning vector is the sum of:
        - target pattern embedding (what to find)
        - legend context embedding (what else exists on the map)

    This lets the model learn: "find this pattern, knowing that these
    other patterns also exist" — crucial for disambiguating similar-looking
    zones.
    """

    def __init__(self, embed_dim: int = 256):
        super().__init__()
        self.embed_dim = embed_dim

        # Pattern encoders
        self.pattern_encoder = PatternEncoder(embed_dim)
        self.legend_encoder = LegendEncoder(embed_dim)

        # Fusion: combine target + legend embeddings
        self.fuse = nn.Sequential(
            nn.Linear(embed_dim * 2, embed_dim),
            nn.ReLU(inplace=True),
        )

        # Encoder path
        self.enc1 = EncoderBlock(3, 64)
        self.enc2 = EncoderBlock(64, 128)
        self.enc3 = EncoderBlock(128, 256)
        self.enc4 = EncoderBlock(256, 512)

        # Bottleneck
        self.bottleneck = nn.Sequential(
            nn.Conv2d(512, 1024, 3, padding=1),
            nn.BatchNorm2d(1024),
            nn.ReLU(inplace=True),
            nn.Conv2d(1024, 1024, 3, padding=1),
            nn.BatchNorm2d(1024),
            nn.ReLU(inplace=True),
        )

        # Decoder path
        self.dec4 = DecoderBlock(1024, 512, 512, embed_dim)
        self.dec3 = DecoderBlock(512, 256, 256, embed_dim)
        self.dec2 = DecoderBlock(256, 128, 128, embed_dim)
        self.dec1 = DecoderBlock(128, 64, 64, embed_dim)

        # Output
        self.final_conv = nn.Sequential(
            nn.Conv2d(64, 64, 3, padding=1),
            nn.ReLU(inplace=True),
            nn.Conv2d(64, 1, 1),
        )

    def forward(
        self,
        image: torch.Tensor,
        pattern: torch.Tensor,
        legend: torch.Tensor,
    ) -> torch.Tensor:
        """
        Args:
            image:   (B, 3, H, W) — map image
            pattern: (B, 3, 32, 32) — target pattern thumbnail
            legend:  (B, 3, 128, 128) — grid of ALL patterns for this map

        Returns:
            (B, 1, H, W) — binary mask logits (pre-sigmoid)
        """
        # Encode pattern + legend, fuse into single conditioning vector
        pat_emb = self.pattern_encoder(pattern)   # (B, 256)
        leg_emb = self.legend_encoder(legend)      # (B, 256)
        cond = self.fuse(torch.cat([pat_emb, leg_emb], dim=1))  # (B, 256)

        # Encoder
        x, s1 = self.enc1(image)
        x, s2 = self.enc2(x)
        x, s3 = self.enc3(x)
        x, s4 = self.enc4(x)

        # Bottleneck
        x = self.bottleneck(x)

        # Decoder with FiLM conditioning
        x = self.dec4(x, s4, cond)
        x = self.dec3(x, s3, cond)
        x = self.dec2(x, s2, cond)
        x = self.dec1(x, s1, cond)

        # Output
        out = self.final_conv(x)
        return out
