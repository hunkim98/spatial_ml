"""Base class for post-processing effects."""

from abc import ABC, abstractmethod

from PIL import Image


class BaseEffect(ABC):
    """Abstract base for all post-processing effects.

    Each effect takes a PIL Image and returns (processed_image, annotations_dict).
    The annotations dict records what was applied for reproducibility.
    """

    @abstractmethod
    def apply(self, img: Image.Image) -> tuple[Image.Image, dict]:
        """Apply the effect to an image.

        Returns:
            (processed_image, annotations_dict)
        """
