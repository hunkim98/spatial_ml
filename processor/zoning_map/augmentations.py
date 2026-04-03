"""Post-processing augmentations for rendered map images.

Applied AFTER arcpy rendering, BEFORE saving to the dataset.
Pure PIL/numpy — no arcpy dependency.
"""

import random

import numpy as np
from PIL import Image, ImageEnhance, ImageFilter

from .config import ColorJitterConfig, NoiseConfig


def apply_noise(img: Image.Image, config: NoiseConfig) -> Image.Image:
    """Apply noise to simulate scanned or degraded maps."""
    if config.type == "none" or config.strength <= 0:
        return img

    arr = np.array(img, dtype=np.float32)

    if config.type == "gaussian":
        sigma = config.strength * 50
        noise = np.random.normal(0, sigma, arr.shape)
        arr = np.clip(arr + noise, 0, 255)

    elif config.type == "salt_pepper":
        mask = np.random.random(arr.shape[:2])
        salt = mask < config.strength / 2
        pepper = mask > (1 - config.strength / 2)
        arr[salt] = 255
        arr[pepper] = 0

    elif config.type == "scan_lines":
        h = arr.shape[0]
        n_lines = max(1, int(h * config.strength * 0.1))
        line_rows = np.random.choice(h, n_lines, replace=False)
        for row in line_rows:
            darken = np.random.uniform(0.6, 0.9)
            arr[row, :] = arr[row, :] * darken

    return Image.fromarray(arr.astype(np.uint8))


def apply_color_jitter(img: Image.Image, config: ColorJitterConfig) -> Image.Image:
    """Apply brightness, contrast, and saturation perturbations."""
    if config.brightness != 0:
        enhancer = ImageEnhance.Brightness(img)
        img = enhancer.enhance(1.0 + config.brightness)

    if config.contrast != 0:
        enhancer = ImageEnhance.Contrast(img)
        img = enhancer.enhance(1.0 + config.contrast)

    if config.saturation != 0:
        enhancer = ImageEnhance.Color(img)
        img = enhancer.enhance(1.0 + config.saturation)

    return img


def apply_blur(img: Image.Image, radius: float = 0) -> Image.Image:
    """Apply Gaussian blur to simulate low-quality scans."""
    if radius <= 0:
        return img
    return img.filter(ImageFilter.GaussianBlur(radius=radius))


def apply_paper_yellowing(img: Image.Image, strength: float = 0.3) -> Image.Image:
    """Tint the image warm to simulate aged paper."""
    if strength <= 0:
        return img
    arr = np.array(img, dtype=np.float32)
    arr[:, :, 0] = np.clip(arr[:, :, 0] + 30 * strength, 0, 255)
    arr[:, :, 1] = np.clip(arr[:, :, 1] + 15 * strength, 0, 255)
    arr[:, :, 2] = np.clip(arr[:, :, 2] - 20 * strength, 0, 255)
    return Image.fromarray(arr.astype(np.uint8))


def apply_vignette(img: Image.Image, strength: float = 0.3) -> Image.Image:
    """Darken edges to simulate uneven scanner lighting."""
    if strength <= 0:
        return img
    arr = np.array(img, dtype=np.float32)
    h, w = arr.shape[:2]
    y, x = np.ogrid[:h, :w]
    cy, cx = h / 2, w / 2
    r = np.sqrt((x - cx) ** 2 + (y - cy) ** 2)
    r_max = np.sqrt(cx ** 2 + cy ** 2)
    mask = 1.0 - strength * (r / r_max) ** 2
    mask = np.clip(mask, 0.3, 1.0)
    arr = arr * mask[:, :, np.newaxis]
    return Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8))


def apply_fold_lines(img: Image.Image, n_folds: int = 2) -> Image.Image:
    """Add dark crease lines to simulate folded paper maps."""
    if n_folds <= 0:
        return img
    arr = np.array(img, dtype=np.float32)
    h, w = arr.shape[:2]
    for _ in range(n_folds):
        if random.random() < 0.5:
            row = random.randint(int(h * 0.2), int(h * 0.8))
            thickness = random.randint(1, 3)
            arr[row:row + thickness, :] *= random.uniform(0.5, 0.8)
        else:
            col = random.randint(int(w * 0.2), int(w * 0.8))
            thickness = random.randint(1, 3)
            arr[:, col:col + thickness] *= random.uniform(0.5, 0.8)
    return Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8))


def apply_boundary_blur(img: Image.Image, strength: float = 0.5) -> Image.Image:
    """Blur polygon boundaries to simulate scan-quality anti-aliasing.

    Applies a slight blur then re-sharpens the interior to keep zone fills
    crisp while softening edges — mimicking how printed maps look when scanned.
    """
    if strength <= 0:
        return img
    radius = 0.3 + strength * 0.7  # 0.3 to 1.0
    blurred = img.filter(ImageFilter.GaussianBlur(radius=radius))
    # Blend: mostly original, with blurred edges
    blend = random.uniform(0.15, 0.4) * strength
    return Image.blend(img, blurred, blend)


def apply_resolution_variation(img: Image.Image) -> Image.Image:
    """Simulate different scan/download resolutions by downscaling then upscaling.

    Real maps come at 72 DPI (web), 150 DPI (standard scan), 300+ DPI (archival).
    This simulates the lower-resolution sources.
    """
    w, h = img.size

    # Random scale factor: 0.3 = very low res (72 DPI feel), 1.0 = no change
    scale = random.choices(
        [0.35, 0.5, 0.65, 0.8, 1.0],
        weights=[10, 20, 30, 25, 15],
    )[0]

    if scale >= 1.0:
        return img

    # Downscale then upscale back to original size
    small_w = max(100, int(w * scale))
    small_h = max(100, int(h * scale))
    small = img.resize((small_w, small_h), Image.LANCZOS)
    return small.resize((w, h), Image.LANCZOS)


def apply_old_map_style(img: Image.Image, intensity: float = 0.5) -> Image.Image:
    """Composite effect simulating an old scanned paper map."""
    if intensity <= 0:
        return img

    enhancer = ImageEnhance.Color(img)
    img = enhancer.enhance(1.0 - 0.5 * intensity)

    enhancer = ImageEnhance.Contrast(img)
    img = enhancer.enhance(1.0 - 0.2 * intensity)

    enhancer = ImageEnhance.Brightness(img)
    img = enhancer.enhance(1.0 + 0.1 * intensity)

    img = apply_paper_yellowing(img, strength=0.6 * intensity)
    img = apply_blur(img, radius=0.5 * intensity)
    img = apply_vignette(img, strength=0.3 * intensity)

    if intensity > 0.3 and random.random() < intensity:
        n_folds = random.randint(1, max(1, int(3 * intensity)))
        img = apply_fold_lines(img, n_folds)

    img = apply_noise(img, NoiseConfig(type="gaussian", strength=0.015 * intensity))

    return img


def augment(
    img: Image.Image,
    noise: NoiseConfig,
    jitter: ColorJitterConfig,
    old_map_intensity: float = 0.0,
) -> Image.Image:
    """Apply all augmentations in sequence."""
    if old_map_intensity > 0:
        img = apply_old_map_style(img, old_map_intensity)
    else:
        img = apply_color_jitter(img, jitter)
        img = apply_noise(img, noise)

    # Always apply these (with random probability)
    # Note: text labels are handled by arcpy's native labeling in the renderer,
    # not here. PIL text overlay is available as apply_text_overlay() but not
    # used in the default pipeline.

    # Boundary blur: 30% chance
    if random.random() < 0.3:
        img = apply_boundary_blur(img, random.uniform(0.3, 0.8))

    # Resolution variation: 25% chance
    if random.random() < 0.25:
        img = apply_resolution_variation(img)

    return img
