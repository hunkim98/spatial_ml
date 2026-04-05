"""Geopandas-only zoning map renderer — no arcpy dependency.

Use this for:
  - Hatching / custom pattern generation
  - Environments without ArcGIS Pro
  - Fast rendering (no PDF intermediate)
  - Linux / Docker / CI compatibility
"""

from .renderer import HATCH_PATTERNS, render_map, render_pattern_swatch, render_text_layer
