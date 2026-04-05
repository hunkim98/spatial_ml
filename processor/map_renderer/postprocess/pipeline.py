"""Pipeline orchestrator and composite effects."""

import random

from PIL import Image, ImageEnhance

from .base import BaseEffect
from .noise import GaussianNoise, SaltPepperNoise, ScanLineNoise
from .color import ColorJitter, PaperYellowing
from .degradation import Vignette, FoldLines, Blur, BoundaryBlur, ResolutionVariation


class OldMapStyle(BaseEffect):
    """Composite preset simulating an old scanned paper map.

    Applies: desaturate + lower contrast + brighten + yellowing +
    blur + vignette + fold lines + gaussian noise.
    """

    def __init__(self, intensity: float | None = None):
        self.intensity = intensity
        self._sub_effects = None

    def apply(self, img: Image.Image) -> tuple[Image.Image, dict]:
        if self.intensity is None:
            self.intensity = random.uniform(0.2, 0.7)
        # Build sub-effects on first call so they freeze their params too
        if self._sub_effects is None:
            i = self.intensity
            self._sub_effects = [
                PaperYellowing(strength=0.6 * i),
                Blur(radius=0.5 * i),
                Vignette(strength=0.3 * i),
            ]
            if i > 0.3 and random.random() < i:
                n_folds = random.randint(1, max(1, int(3 * i)))
                self._sub_effects.append(FoldLines(n_folds=n_folds))
            self._sub_effects.append(GaussianNoise(strength=0.015 * i))

        annotations = {"old_map_intensity": round(self.intensity, 4)}
        i = self.intensity

        # Desaturate
        img = ImageEnhance.Color(img).enhance(1.0 - 0.5 * i)
        # Lower contrast
        img = ImageEnhance.Contrast(img).enhance(1.0 - 0.2 * i)
        # Brighten slightly
        img = ImageEnhance.Brightness(img).enhance(1.0 + 0.1 * i)

        for effect in self._sub_effects:
            img, ann = effect.apply(img)
            annotations.update(ann)

        return img, annotations


class PostProcessPipeline:
    """Runs a list of effects in order, collecting annotations."""

    def __init__(self, effects: list[BaseEffect]):
        self.effects = effects

    def run(self, img: Image.Image) -> tuple[Image.Image, dict]:
        """Apply all effects in sequence.

        Returns:
            (processed_image, combined_annotations)
        """
        annotations = {}
        for effect in self.effects:
            img, ann = effect.apply(img)
            annotations.update(ann)
        return img, annotations

    @classmethod
    def random(cls) -> "PostProcessPipeline":
        """Build a random postprocessing pipeline.

        30% chance: OldMapStyle composite
        70% chance: ColorJitter + random noise type
        Then independently: 30% BoundaryBlur, 25% ResolutionVariation
        """
        effects: list[BaseEffect] = []

        if random.random() < 0.3:
            effects.append(OldMapStyle())
        else:
            effects.append(ColorJitter())
            # Pick a random noise type
            noise_cls = random.choice([GaussianNoise, SaltPepperNoise, ScanLineNoise])
            effects.append(noise_cls())

        if random.random() < 0.3:
            effects.append(BoundaryBlur())

        if random.random() < 0.25:
            effects.append(ResolutionVariation())

        return cls(effects)
