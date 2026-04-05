"""Degradation effects: vignette, folds, blur, boundary blur, resolution variation."""

import random

import numpy as np
from PIL import Image, ImageFilter

from .base import BaseEffect


class Vignette(BaseEffect):
    """Circular radial darkening simulating uneven scanner lighting."""

    def __init__(self, strength: float | None = None):
        self.strength = strength

    def apply(self, img: Image.Image) -> tuple[Image.Image, dict]:
        if self.strength is None:
            self.strength = random.uniform(0.1, 0.5)
        arr = np.array(img, dtype=np.float32)
        h, w = arr.shape[:2]
        y, x = np.ogrid[:h, :w]
        cy, cx = h / 2, w / 2
        r = np.sqrt((x - cx) ** 2 + (y - cy) ** 2)
        r_max = np.sqrt(cx ** 2 + cy ** 2)
        mask = 1.0 - self.strength * (r / r_max) ** 2
        mask = np.clip(mask, 0.3, 1.0)
        arr = arr * mask[:, :, np.newaxis]
        return Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8)), {
            "vignette_strength": round(self.strength, 4),
        }


class FoldLines(BaseEffect):
    """Dark crease lines simulating folded paper maps."""

    def __init__(self, n_folds: int | None = None):
        self.n_folds = n_folds

    def apply(self, img: Image.Image) -> tuple[Image.Image, dict]:
        if self.n_folds is None:
            self.n_folds = random.randint(1, 4)
        arr = np.array(img, dtype=np.float32)
        h, w = arr.shape[:2]
        for _ in range(self.n_folds):
            if random.random() < 0.5:
                row = random.randint(int(h * 0.2), int(h * 0.8))
                thickness = random.randint(1, 3)
                arr[row:row + thickness, :] *= random.uniform(0.5, 0.8)
            else:
                col = random.randint(int(w * 0.2), int(w * 0.8))
                thickness = random.randint(1, 3)
                arr[:, col:col + thickness] *= random.uniform(0.5, 0.8)
        return Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8)), {
            "fold_lines": self.n_folds,
        }


class Blur(BaseEffect):
    """Gaussian blur simulating low-quality scans."""

    def __init__(self, radius: float | None = None):
        self.radius = radius

    def apply(self, img: Image.Image) -> tuple[Image.Image, dict]:
        if self.radius is None:
            self.radius = random.uniform(0.3, 1.5)
        img = img.filter(ImageFilter.GaussianBlur(radius=self.radius))
        return img, {
            "blur_radius": round(self.radius, 4),
        }


class BoundaryBlur(BaseEffect):
    """Blend original + blurred to soften polygon edges like scanned maps."""

    def __init__(self, strength: float | None = None):
        self.strength = strength
        self._blend = None

    def apply(self, img: Image.Image) -> tuple[Image.Image, dict]:
        if self.strength is None:
            self.strength = random.uniform(0.3, 0.8)
        if self._blend is None:
            self._blend = random.uniform(0.15, 0.4) * self.strength
        radius = 0.3 + self.strength * 0.7
        blurred = img.filter(ImageFilter.GaussianBlur(radius=radius))
        img = Image.blend(img, blurred, self._blend)
        return img, {
            "boundary_blur_strength": round(self.strength, 4),
        }


class ResolutionVariation(BaseEffect):
    """Downscale + upscale to simulate different scan/download resolutions."""

    def __init__(self):
        self._scale = None

    def apply(self, img: Image.Image) -> tuple[Image.Image, dict]:
        if self._scale is None:
            self._scale = random.choices(
                [0.35, 0.5, 0.65, 0.8, 1.0],
                weights=[10, 20, 30, 25, 15],
            )[0]

        if self._scale >= 1.0:
            return img, {"resolution_scale": 1.0}

        w, h = img.size
        small_w = max(100, int(w * self._scale))
        small_h = max(100, int(h * self._scale))
        small = img.resize((small_w, small_h), Image.LANCZOS)
        img = small.resize((w, h), Image.LANCZOS)
        return img, {
            "resolution_scale": round(self._scale, 4),
        }
