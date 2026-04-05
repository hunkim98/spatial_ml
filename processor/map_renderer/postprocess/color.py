"""Color effects: jitter and paper yellowing."""

import random

import numpy as np
from PIL import Image, ImageEnhance

from .base import BaseEffect


class ColorJitter(BaseEffect):
    """Random brightness, contrast, and saturation perturbation."""

    def __init__(
        self,
        brightness: float | None = None,
        contrast: float | None = None,
        saturation: float | None = None,
    ):
        self.brightness = brightness
        self.contrast = contrast
        self.saturation = saturation

    def apply(self, img: Image.Image) -> tuple[Image.Image, dict]:
        if self.brightness is None:
            self.brightness = random.uniform(-0.3, 0.3)
        if self.contrast is None:
            self.contrast = random.uniform(-0.3, 0.3)
        if self.saturation is None:
            self.saturation = random.uniform(-0.3, 0.3)

        if self.brightness != 0:
            img = ImageEnhance.Brightness(img).enhance(1.0 + self.brightness)
        if self.contrast != 0:
            img = ImageEnhance.Contrast(img).enhance(1.0 + self.contrast)
        if self.saturation != 0:
            img = ImageEnhance.Color(img).enhance(1.0 + self.saturation)

        return img, {
            "color_jitter_brightness": round(self.brightness, 4),
            "color_jitter_contrast": round(self.contrast, 4),
            "color_jitter_saturation": round(self.saturation, 4),
        }


class PaperYellowing(BaseEffect):
    """Warm tint simulating aged paper (R+30, G+15, B-20 per strength unit)."""

    def __init__(self, strength: float | None = None):
        self.strength = strength

    def apply(self, img: Image.Image) -> tuple[Image.Image, dict]:
        if self.strength is None:
            self.strength = random.uniform(0.1, 0.6)
        arr = np.array(img, dtype=np.float32)
        arr[:, :, 0] = np.clip(arr[:, :, 0] + 30 * self.strength, 0, 255)
        arr[:, :, 1] = np.clip(arr[:, :, 1] + 15 * self.strength, 0, 255)
        arr[:, :, 2] = np.clip(arr[:, :, 2] - 20 * self.strength, 0, 255)
        return Image.fromarray(arr.astype(np.uint8)), {
            "paper_yellowing_strength": round(self.strength, 4),
        }
