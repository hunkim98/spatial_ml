"""Noise effects: Gaussian, salt-and-pepper, scan lines."""

import random

import numpy as np
from PIL import Image

from .base import BaseEffect


class GaussianNoise(BaseEffect):
    """Additive Gaussian noise to simulate sensor/scanner noise."""

    def __init__(self, strength: float | None = None):
        self.strength = strength

    def apply(self, img: Image.Image) -> tuple[Image.Image, dict]:
        if self.strength is None:
            self.strength = random.uniform(0.01, 0.15)
        sigma = self.strength * 50
        arr = np.array(img, dtype=np.float32)
        noise = np.random.normal(0, sigma, arr.shape)
        arr = np.clip(arr + noise, 0, 255)
        return Image.fromarray(arr.astype(np.uint8)), {
            "noise_type": "gaussian",
            "noise_strength": round(self.strength, 4),
        }


class SaltPepperNoise(BaseEffect):
    """Salt-and-pepper noise to simulate scan defects."""

    def __init__(self, strength: float | None = None):
        self.strength = strength

    def apply(self, img: Image.Image) -> tuple[Image.Image, dict]:
        if self.strength is None:
            self.strength = random.uniform(0.005, 0.05)
        arr = np.array(img, dtype=np.float32)
        mask = np.random.random(arr.shape[:2])
        salt = mask < self.strength / 2
        pepper = mask > (1 - self.strength / 2)
        arr[salt] = 255
        arr[pepper] = 0
        return Image.fromarray(arr.astype(np.uint8)), {
            "noise_type": "salt_pepper",
            "noise_strength": round(self.strength, 4),
        }


class ScanLineNoise(BaseEffect):
    """Horizontal scan-line darkening to simulate scanner artifacts."""

    def __init__(self, strength: float | None = None):
        self.strength = strength

    def apply(self, img: Image.Image) -> tuple[Image.Image, dict]:
        if self.strength is None:
            self.strength = random.uniform(0.02, 0.15)
        arr = np.array(img, dtype=np.float32)
        h = arr.shape[0]
        n_lines = max(1, int(h * self.strength * 0.1))
        line_rows = np.random.choice(h, n_lines, replace=False)
        for row in line_rows:
            darken = np.random.uniform(0.6, 0.9)
            arr[row, :] = arr[row, :] * darken
        return Image.fromarray(arr.astype(np.uint8)), {
            "noise_type": "scan_lines",
            "noise_strength": round(self.strength, 4),
        }
