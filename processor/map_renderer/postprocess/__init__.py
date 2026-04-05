"""Post-processing effects for rendered map images."""

from .base import BaseEffect
from .noise import GaussianNoise, SaltPepperNoise, ScanLineNoise
from .color import ColorJitter, PaperYellowing
from .degradation import Vignette, FoldLines, Blur, BoundaryBlur, ResolutionVariation
from .pipeline import OldMapStyle, PostProcessPipeline

__all__ = [
    "BaseEffect",
    "GaussianNoise",
    "SaltPepperNoise",
    "ScanLineNoise",
    "ColorJitter",
    "PaperYellowing",
    "Vignette",
    "FoldLines",
    "Blur",
    "BoundaryBlur",
    "ResolutionVariation",
    "OldMapStyle",
    "PostProcessPipeline",
]
