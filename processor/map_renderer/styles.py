"""Pools of visual options to sample from during randomized rendering.

Every list/dict here is a pool the renderer samples from.
Add entries to increase diversity; the renderer picks randomly.
"""

# ------------------------------------------------------------------
# Backgrounds — name or basemap provider dict
# ------------------------------------------------------------------

BACKGROUNDS = [
    "white",
    "off_white",
    "light_gray",
    "warm_gray",
    "cool_gray",
    "parchment",
    "cream",
    "blueprint",
    "pale_blue",
    "pale_green",
    "pale_yellow",
]

# background name -> callable that returns (R, G, B) floats 0-1
# Callables so each sample is slightly different
import random as _random

BACKGROUND_COLORS = {
    "white":       lambda: (1.0, 1.0, 1.0),
    "off_white":   lambda: (_random.uniform(0.95, 1.0), _random.uniform(0.93, 0.98), _random.uniform(0.90, 0.96)),
    "light_gray":  lambda: tuple([_random.uniform(0.88, 0.95)] * 3),
    "warm_gray":   lambda: (_random.uniform(0.90, 0.95), _random.uniform(0.88, 0.93), _random.uniform(0.85, 0.90)),
    "cool_gray":   lambda: (_random.uniform(0.85, 0.90), _random.uniform(0.87, 0.93), _random.uniform(0.90, 0.95)),
    "parchment":   lambda: (_random.uniform(0.90, 0.96), _random.uniform(0.87, 0.93), _random.uniform(0.78, 0.86)),
    "cream":       lambda: (_random.uniform(0.96, 1.0), _random.uniform(0.95, 0.99), _random.uniform(0.88, 0.93)),
    "blueprint":   lambda: (_random.uniform(0.03, 0.07), _random.uniform(0.06, 0.10), _random.uniform(0.20, 0.30)),
    "pale_blue":   lambda: (_random.uniform(0.90, 0.95), _random.uniform(0.93, 0.97), _random.uniform(0.96, 1.0)),
    "pale_green":  lambda: (_random.uniform(0.91, 0.96), _random.uniform(0.96, 1.0), _random.uniform(0.91, 0.96)),
    "pale_yellow": lambda: (_random.uniform(0.97, 1.0), _random.uniform(0.97, 1.0), _random.uniform(0.88, 0.93)),
}

# ------------------------------------------------------------------
# Boundaries — weight is relative (0.0-1.0), renderer scales to figure
# ------------------------------------------------------------------

BOUNDARY_PRESETS = [
    # Solid lines
    {"color": "black",   "line_weight": 0.3,  "line_style": "-"},
    {"color": "black",   "line_weight": 0.5,  "line_style": "-"},
    {"color": "black",   "line_weight": 0.7,  "line_style": "-"},
    {"color": "#333333", "line_weight": 0.2,  "line_style": "-"},
    {"color": "#333333", "line_weight": 0.4,  "line_style": "-"},
    {"color": "#555555", "line_weight": 0.3,  "line_style": "-"},
    {"color": "#666666", "line_weight": 0.5,  "line_style": "-"},
    {"color": "#888888", "line_weight": 0.2,  "line_style": "-"},
    # Dashed
    {"color": "black",   "line_weight": 0.3,  "line_style": "--"},
    {"color": "#333333", "line_weight": 0.4,  "line_style": "--"},
    {"color": "#555555", "line_weight": 0.3,  "line_style": "--"},
    # Dotted
    {"color": "black",   "line_weight": 0.3,  "line_style": ":"},
    {"color": "#444444", "line_weight": 0.4,  "line_style": ":"},
    # Dash-dot
    {"color": "black",   "line_weight": 0.3,  "line_style": "-."},
    {"color": "#555555", "line_weight": 0.4,  "line_style": "-."},
    # No boundary
    {"color": "none",    "line_weight": 0.0,  "line_style": "-"},
    # Dark colored boundaries (for lighter zone fills)
    {"color": "#8B0000", "line_weight": 0.3,  "line_style": "-"},
    {"color": "#00008B", "line_weight": 0.3,  "line_style": "-"},
    {"color": "#006400", "line_weight": 0.3,  "line_style": "-"},
    {"color": "#4B0082", "line_weight": 0.2,  "line_style": "-"},
]

# ------------------------------------------------------------------
# Hatch patterns — matplotlib notation
# ------------------------------------------------------------------

HATCH_PATTERNS = {
    # Diagonal
    "diagonal":            "///",
    "diagonal_dense":      "//////",
    "back_diagonal":       "\\\\\\",
    "back_diagonal_dense": "\\\\\\\\\\\\",
    # Straight
    "horizontal":          "---",
    "horizontal_dense":    "------",
    "vertical":            "|||",
    "vertical_dense":      "||||||",
    # Grid
    "crosshatch":          "+++",
    "crosshatch_dense":    "++++++",
    "x_hatch":             "xxx",
    "x_hatch_dense":       "xxxxxx",
    # Point
    "dots":                "...",
    "dots_dense":          "......",
    "circles":             "ooo",
    "circles_dense":       "oooooo",
    "stars":               "***",
    # Combined
    "diagonal_dots":       "//..",
    "cross_dots":          "++..",
    "vert_dots":           "||..",
}

# ------------------------------------------------------------------
# Label fonts
# ------------------------------------------------------------------

LABEL_FONTS = [
    "DejaVu Sans",
    "DejaVu Serif",
    "DejaVu Sans Mono",
    "sans-serif",
    "serif",
    "monospace",
]
