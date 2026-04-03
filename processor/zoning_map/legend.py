"""Randomized legend placement for zoning map PDF exports.

Legend parameters (position, font, title, alignment) are randomized to match
the distribution observed across 150+ real-world zoning map PDFs.
"""

import random

_STRIP_POSITION_WEIGHTS = {
    "bottom": 55,
    "right": 20,
    "top": 15,
    "left": 10,
}

# Alignment within the strip:
# top/bottom strips: "left", "center", "right"
# left/right strips: "top", "middle", "bottom"
_H_ALIGN_WEIGHTS = {"left": 30, "center": 50, "right": 20}
_V_ALIGN_WEIGHTS = {"top": 50, "middle": 30, "bottom": 20}

_TITLE_WEIGHTS = {
    "Legend": 60,
    "Zoning Districts": 37,
    "Zoning Area": 2,
    "Land Use": 1,
}

_FONT_WEIGHTS = {
    "Arial": 50,
    "Arial Narrow": 15,
    "Segoe UI": 10,
    "Tahoma": 5,
    "Calibri": 5,
    "Gill Sans MT": 3,
    "Verdana": 3,
    "Corbel": 3,
    "Times New Roman": 3,
    "Bookman Old Style": 2,
    "Garamond": 1,
}

_TITLE_SIZE_RANGE = (8, 14)
_LABEL_SIZE_RANGE = (6, 10)
_STRIP_SIZE_RANGE = (0.15, 0.28)


def _weighted_choice(weights: dict) -> str:
    keys = list(weights.keys())
    vals = list(weights.values())
    return random.choices(keys, weights=vals, k=1)[0]


class LegendConfig:
    """Randomized legend configuration for a single training sample."""

    def __init__(self):
        self.strip_position = _weighted_choice(_STRIP_POSITION_WEIGHTS)
        self.title = _weighted_choice(_TITLE_WEIGHTS)
        self.font_family = _weighted_choice(_FONT_WEIGHTS)
        self.title_size = random.uniform(*_TITLE_SIZE_RANGE)
        self.label_size = random.uniform(*_LABEL_SIZE_RANGE)
        self.show_title = random.random() < 0.85
        self.strip_fraction = random.uniform(*_STRIP_SIZE_RANGE)

        # Alignment depends on strip orientation
        if self.strip_position in ("top", "bottom"):
            self.alignment = _weighted_choice(_H_ALIGN_WEIGHTS)
        else:
            self.alignment = _weighted_choice(_V_ALIGN_WEIGHTS)

        # Column count: None = auto-determine based on available space
        self.column_count = None

    def to_dict(self) -> dict:
        """Serialize config for the sidecar JSON."""
        return {
            "strip_position": self.strip_position,
            "alignment": self.alignment,
            "title": self.title,
            "font_family": self.font_family,
            "title_size": round(self.title_size, 1),
            "label_size": round(self.label_size, 1),
            "show_title": self.show_title,
            "strip_fraction": round(self.strip_fraction, 3),
        }
