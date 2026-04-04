"""Pattern-conditioned U-Net for zone segmentation.

Architecture:
    - Encoder: ResNet-34 pretrained (first conv modified for 6-channel input)
    - Conditioning: pattern thumbnail → embedding → FiLM modulation at each decoder level
    - Decoder: U-Net decoder with skip connections
    - Output: 1-channel sigmoid (binary mask)

Input:
    - image: (B, 3, H, W) — rendered map
    - pattern: (B, 3, 32, 32) — zone pattern thumbnail

Output:
    - mask: (B, 1, H, W) — binary segmentation mask
"""

import torch
import torch.nn as nn
import torch.nn.functional as F
from torchvision import models


class PatternEncoder(nn.Module):
    """Encode a 32x32 pattern thumbnail into a conditioning vector."""

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
        """(B, 3, 32, 32) → (B, embed_dim)"""
        return self.net(pattern)


class FiLM(nn.Module):
    """Feature-wise Linear Modulation — conditions decoder features on pattern."""

    def __init__(self, n_channels: int, embed_dim: int = 256):
        super().__init__()
        self.gamma = nn.Linear(embed_dim, n_channels)
        self.beta = nn.Linear(embed_dim, n_channels)

    def forward(self, x: torch.Tensor, cond: torch.Tensor) -> torch.Tensor:
        """x: (B, C, H, W), cond: (B, embed_dim) → (B, C, H, W)"""
        gamma = self.gamma(cond).unsqueeze(-1).unsqueeze(-1)  # (B, C, 1, 1)
        beta = self.beta(cond).unsqueeze(-1).unsqueeze(-1)
        return gamma * x + beta


class DecoderBlock(nn.Module):
    """U-Net decoder block: upsample + concat skip + conv + FiLM conditioning."""

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
        # Handle size mismatch from odd dimensions
        if x.shape != skip.shape:
            x = F.interpolate(x, size=skip.shape[2:], mode="bilinear", align_corners=False)
        x = torch.cat([x, skip], dim=1)
        x = self.conv(x)
        x = self.film(x, cond)
        return x


class PatternConditionedUNet(nn.Module):
    """U-Net with pattern-conditioned FiLM modulation.

    Encoder: ResNet-34 pretrained backbone.
    Decoder: 4-level upsampling with skip connections and FiLM conditioning.
    """

    def __init__(self, embed_dim: int = 256, pretrained: bool = True):
        super().__init__()
        self.embed_dim = embed_dim

        # Pattern encoder
        self.pattern_encoder = PatternEncoder(embed_dim)

        # Image encoder (ResNet-34)
        resnet = models.resnet34(weights=models.ResNet34_Weights.DEFAULT if pretrained else None)

        self.enc0 = nn.Sequential(resnet.conv1, resnet.bn1, resnet.relu)  # /2, 64
        self.pool0 = resnet.maxpool                                        # /4
        self.enc1 = resnet.layer1  # /4,  64
        self.enc2 = resnet.layer2  # /8,  128
        self.enc3 = resnet.layer3  # /16, 256
        self.enc4 = resnet.layer4  # /32, 512

        # Decoder
        self.dec4 = DecoderBlock(512, 256, 256, embed_dim)  # /16
        self.dec3 = DecoderBlock(256, 128, 128, embed_dim)  # /8
        self.dec2 = DecoderBlock(128, 64, 64, embed_dim)    # /4
        self.dec1 = DecoderBlock(64, 64, 32, embed_dim)     # /2

        # Final upsample to full resolution
        self.final_up = nn.ConvTranspose2d(32, 32, 2, stride=2)  # /1
        self.final_conv = nn.Sequential(
            nn.Conv2d(32, 16, 3, padding=1),
            nn.ReLU(inplace=True),
            nn.Conv2d(16, 1, 1),
        )

    def forward(self, image: torch.Tensor, pattern: torch.Tensor) -> torch.Tensor:
        """
        Args:
            image: (B, 3, H, W) — map image
            pattern: (B, 3, 32, 32) — pattern thumbnail

        Returns:
            (B, 1, H, W) — binary mask logits (pre-sigmoid)
        """
        # Encode pattern
        cond = self.pattern_encoder(pattern)  # (B, embed_dim)

        # Encode image
        e0 = self.enc0(image)     # (B, 64, H/2, W/2)
        e0p = self.pool0(e0)      # (B, 64, H/4, W/4)
        e1 = self.enc1(e0p)       # (B, 64, H/4, W/4)
        e2 = self.enc2(e1)        # (B, 128, H/8, W/8)
        e3 = self.enc3(e2)        # (B, 256, H/16, W/16)
        e4 = self.enc4(e3)        # (B, 512, H/32, W/32)

        # Decode with FiLM conditioning
        d4 = self.dec4(e4, e3, cond)  # (B, 256, H/16, W/16)
        d3 = self.dec3(d4, e2, cond)  # (B, 128, H/8, W/8)
        d2 = self.dec2(d3, e1, cond)  # (B, 64, H/4, W/4)
        d1 = self.dec1(d2, e0, cond)  # (B, 32, H/2, W/2)

        # Final output
        out = self.final_up(d1)    # (B, 32, H, W)
        if out.shape[2:] != image.shape[2:]:
            out = F.interpolate(out, size=image.shape[2:], mode="bilinear", align_corners=False)
        out = self.final_conv(out)  # (B, 1, H, W)

        return out
