"""Geopandas + Matplotlib renderer — no arcpy dependency.

Renders maps covering a wide range of styles from modern digital to
old scanned maps. Fully controllable hatching, patterns, labels,
boundaries, backgrounds, and post-processing.

Targets: zoning maps, geological maps, USGS topo maps, land use maps.
"""

import logging
import random
from pathlib import Path

import geopandas as gpd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import matplotlib.patheffects as pe
from matplotlib.colors import to_rgba
import numpy as np
from PIL import Image, ImageEnhance, ImageFilter

from processor.zoning_map.config import MapConfig, RenderResult

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Hatch patterns — matplotlib notation
# ---------------------------------------------------------------------------
HATCH_PATTERNS = [
    # Diagonal lines
    {"name": "diagonal", "hatch": "///"},
    {"name": "diagonal_dense", "hatch": "//////"},
    {"name": "back_diagonal", "hatch": "\\\\\\"},
    {"name": "back_diagonal_dense", "hatch": "\\\\\\\\\\\\"},
    # Straight lines
    {"name": "horizontal", "hatch": "---"},
    {"name": "horizontal_dense", "hatch": "------"},
    {"name": "vertical", "hatch": "|||"},
    {"name": "vertical_dense", "hatch": "||||||"},
    # Grids
    {"name": "crosshatch", "hatch": "+++"},
    {"name": "crosshatch_dense", "hatch": "++++++"},
    {"name": "x_hatch", "hatch": "xxx"},
    {"name": "x_hatch_dense", "hatch": "xxxxxx"},
    # Point patterns
    {"name": "dots", "hatch": "..."},
    {"name": "dots_dense", "hatch": "......"},
    {"name": "circles", "hatch": "ooo"},
    {"name": "circles_dense", "hatch": "oooooo"},
    {"name": "stars", "hatch": "***"},
    # Combined patterns (realistic for geological maps)
    {"name": "diagonal_dots", "hatch": "//.."},
    {"name": "cross_dots", "hatch": "++.."},
    {"name": "vert_dots", "hatch": "||.."},
]

# Background styles
BACKGROUND_STYLES = [
    "white",
    "off_white",      # slightly warm
    "light_gray",
    "parchment",       # old paper
    "blueprint",       # dark blue bg, white lines
]

# Boundary styles
BOUNDARY_STYLES = [
    {"name": "thin_gray", "color": (0.3, 0.3, 0.3), "width": 0.3, "style": "-"},
    {"name": "thin_black", "color": (0, 0, 0), "width": 0.5, "style": "-"},
    {"name": "medium_black", "color": (0, 0, 0), "width": 1.0, "style": "-"},
    {"name": "thick_black", "color": (0, 0, 0), "width": 1.5, "style": "-"},
    {"name": "dashed", "color": (0.2, 0.2, 0.2), "width": 0.5, "style": "--"},
    {"name": "dotted", "color": (0.2, 0.2, 0.2), "width": 0.5, "style": ":"},
    {"name": "none", "color": "none", "width": 0, "style": "-"},
    {"name": "colored", "color": None, "width": 0.8, "style": "-"},  # uses zone color
]

# Label styles
LABEL_FONTS = ["DejaVu Sans", "DejaVu Serif", "DejaVu Sans Mono",
               "Arial", "Times New Roman", "Courier New", "sans-serif", "serif", "monospace"]


def _color_to_mpl(rgb: list[int]) -> tuple[float, float, float]:
    return (rgb[0] / 255, rgb[1] / 255, rgb[2] / 255)


def _darken(color, amount=0.25):
    return tuple(max(0, c - amount) for c in color)


def _lighten(color, amount=0.25):
    return tuple(min(1, c + amount) for c in color)


def _random_bg_color(style: str) -> str | tuple:
    if style == "white":
        return "white"
    elif style == "off_white":
        r = random.uniform(0.95, 1.0)
        g = random.uniform(0.93, 0.98)
        b = random.uniform(0.88, 0.95)
        return (r, g, b)
    elif style == "light_gray":
        v = random.uniform(0.88, 0.95)
        return (v, v, v)
    elif style == "parchment":
        return (random.uniform(0.9, 0.96), random.uniform(0.87, 0.93), random.uniform(0.78, 0.86))
    elif style == "blueprint":
        return (0.05, 0.08, 0.25)
    return "white"


# ---------------------------------------------------------------------------
# Map rendering
# ---------------------------------------------------------------------------

def render_map(
    config: MapConfig,
    output_path: Path,
    dpi: int = 200,
    figsize: tuple[float, float] | None = None,
    background: str | None = None,
    boundary_style: str | None = None,
    hatch_color_mode: str = "dark",
    grid_lines: bool | None = None,
    contour_lines: bool | None = None,
    basemap_provider=None,
) -> RenderResult:
    """Render a map with full style control.

    Args:
        config: MapConfig with polygons, colors, etc.
        output_path: output PNG path.
        dpi: resolution.
        figsize: figure size in inches.
        background: background style name or None=random.
        boundary_style: boundary style name or None=random.
        hatch_color_mode: "dark" (darken fill), "black", "white", "colored".
        grid_lines: draw coordinate grid. None=random (20% chance).
        contour_lines: draw fake contour lines. None=random (15% chance).
    """
    zone_field = config.zone_field
    color_map = config.color_map
    hatch_zones = config.hatch_zones or {}

    # If basemap tiles are needed, reproject to EPSG:3857 inside the renderer
    if basemap_provider is not None:
        gdf = config.gdf.to_crs(epsg=3857)
    else:
        gdf = config.gdf

    # 1. Compute extent FIRST so we can size the figure correctly
    bounds = gdf.total_bounds
    xmin, ymin, xmax, ymax = bounds
    pad = config.extent_padding
    dx = (xmax - xmin) * (pad - 1) / 2
    dy = (ymax - ymin) * (pad - 1) / 2
    extent_w = (xmax + dx) - (xmin - dx)
    extent_h = (ymax + dy) - (ymin - dy)

    # 2. Set figure size to match data aspect ratio
    if figsize is None:
        fig_w = config.page_width
    else:
        fig_w = figsize[0]
    if extent_w > 0 and extent_h > 0:
        aspect = extent_h / extent_w
        fig_h = fig_w * aspect
    else:
        fig_h = fig_w * 0.75

    fig, ax = plt.subplots(1, 1, figsize=(fig_w, fig_h), dpi=dpi)

    # 3. Set extent immediately so everything is centered
    ax.set_xlim(xmin - dx, xmax + dx)
    ax.set_ylim(ymin - dy, ymax + dy)

    # Background
    if background is None:
        background = random.choice(BACKGROUND_STYLES)
    bg_color = _random_bg_color(background)
    ax.set_facecolor(bg_color)
    fig.patch.set_facecolor(bg_color)

    is_blueprint = background == "blueprint"
    has_basemap = basemap_provider is not None

    # When a basemap is present, reduce opacity so basemap shows through
    if has_basemap:
        config_opacity = min(config.opacity, random.uniform(0.55, 0.85))
    else:
        config_opacity = config.opacity

    # Boundary style
    if boundary_style is None:
        boundary_style = random.choice(BOUNDARY_STYLES)
    else:
        boundary_style = next((b for b in BOUNDARY_STYLES if b["name"] == boundary_style),
                               BOUNDARY_STYLES[0])

    hatch_lookup = {h["name"]: h["hatch"] for h in HATCH_PATTERNS}

    # Plot zones
    if zone_field and zone_field in gdf.columns:
        for zone_name, rgb in color_map.items():
            zone_gdf = gdf[gdf[zone_field] == zone_name]
            if zone_gdf.empty:
                continue

            fill_color = _color_to_mpl(rgb)
            alpha = config_opacity

            # Blueprint: invert to light colors on dark bg
            if is_blueprint:
                fill_color = _lighten(fill_color, 0.3)
                alpha = min(1.0, alpha + 0.1)

            # Hatch
            hatch = None
            if zone_name in hatch_zones:
                hatch = hatch_lookup.get(hatch_zones[zone_name], "///")

            # Boundary edge
            if isinstance(boundary_style, dict):
                edge_color = boundary_style["color"]
                edge_width = boundary_style["width"]
                edge_style = boundary_style["style"]
                if edge_color == "none" or edge_width == 0:
                    edge_color = "none"
                    edge_width = 0
                elif edge_color is None:  # "colored" mode
                    edge_color = _darken(fill_color, 0.3)
                if is_blueprint and edge_color != "none":
                    edge_color = (0.7, 0.8, 1.0)
            else:
                edge_color = (0.3, 0.3, 0.3)
                edge_width = 0.5
                edge_style = "-"

            zone_gdf.plot(
                ax=ax,
                color=fill_color,
                alpha=alpha,
                edgecolor=edge_color,
                linewidth=edge_width,
                linestyle=edge_style,
                hatch=hatch,
            )

            # Set hatch edge color
            if hatch:
                if hatch_color_mode == "dark":
                    hc = _darken(fill_color, 0.3)
                elif hatch_color_mode == "black":
                    hc = (0, 0, 0)
                elif hatch_color_mode == "white":
                    hc = (1, 1, 1)
                else:
                    hc = _darken(fill_color, 0.15)
                plt.rcParams['hatch.color'] = hc
    else:
        gdf.plot(ax=ax, color="lightblue", edgecolor="gray", linewidth=0.5)

    # Grid lines (coordinate grid overlay)
    if grid_lines is None:
        grid_lines = random.random() < 0.20
    if grid_lines:
        ax.grid(True, linewidth=0.3, alpha=0.4,
                color=(0.8, 0.8, 1.0) if is_blueprint else (0.5, 0.5, 0.5))

    # Fake contour lines (simulate topographic underlayer)
    # Skip on dark basemaps where they look unrealistic
    has_dark_bg = is_blueprint or (basemap_provider and "Dark" in str(basemap_provider.get("name", "")))
    if contour_lines is None:
        contour_lines = random.random() < 0.15 and not has_dark_bg
    if contour_lines and not has_dark_bg:
        bounds = gdf.total_bounds
        xmin, ymin, xmax, ymax = bounds
        n_lines = random.randint(5, 15)
        contour_color = (0.55, 0.35, 0.15, 0.15)  # subtle brown, low alpha
        for _ in range(n_lines):
            x_start = random.uniform(xmin, xmax)
            x_pts = np.linspace(x_start - (xmax-xmin)*0.5, x_start + (xmax-xmin)*0.5, 80)
            y_base = random.uniform(ymin, ymax)
            amplitude = (ymax - ymin) * random.uniform(0.01, 0.08)
            freq = random.uniform(2, 8)
            y_pts = y_base + amplitude * np.sin(freq * np.linspace(0, 2*np.pi, 80))
            ax.plot(x_pts, y_pts, color=contour_color, linewidth=random.uniform(0.15, 0.4))

    # Labels — only label 1-3 of the largest polygons per zone type
    if config.show_labels and zone_field and zone_field in gdf.columns:
        # Shared style per zone but varied across zones
        zone_font = random.choice(LABEL_FONTS)
        zone_weight = random.choice(["normal", "normal", "bold"])
        zone_style = random.choice(["normal", "normal", "italic"])

        for zone_name in color_map:
            zone_gdf = gdf[gdf[zone_field] == zone_name].copy()
            if zone_gdf.empty:
                continue

            # Sort by area, label only the 1-3 largest polygons
            zone_gdf["_area"] = zone_gdf.geometry.area
            zone_gdf = zone_gdf.sort_values("_area", ascending=False)
            n_to_label = random.randint(1, min(3, len(zone_gdf)))
            to_label = zone_gdf.head(n_to_label)

            fontsize = random.uniform(6, 16)
            alpha = random.uniform(0.5, 1.0)

            if is_blueprint:
                txt_color = (0.8, 0.85, 1.0)
            else:
                txt_color = (random.uniform(0, 0.25),) * 3

            for _, row in to_label.iterrows():
                centroid = row.geometry.centroid
                rotation = random.choice([0, 0, 0, 0, random.uniform(-15, 15)])

                text = ax.text(
                    centroid.x, centroid.y, zone_name,
                    fontsize=fontsize,
                    fontstyle=zone_style,
                    fontweight=zone_weight,
                    color=txt_color,
                    alpha=alpha,
                    ha="center", va="center",
                    fontfamily=zone_font,
                    rotation=rotation,
                )

                # Text outline/halo (50% chance)
                if random.random() < 0.5:
                    halo_color = "white" if not is_blueprint else (0.05, 0.08, 0.25)
                    text.set_path_effects([
                        pe.withStroke(linewidth=random.uniform(1, 3), foreground=halo_color),
                    ])

    # Basemap tiles (extent already set at top, so tiles fill correctly)
    if basemap_provider is not None:
        try:
            import contextily as cx
            cx.add_basemap(ax, source=basemap_provider, zoom="auto", zorder=0)
        except Exception as e:
            logger.warning(f"Failed to add basemap: {e}")

    # Re-enforce extent (basemap may have shifted it)
    ax.set_xlim(xmin - dx, xmax + dx)
    ax.set_ylim(ymin - dy, ymax + dy)
    ax.set_axis_off()

    # Remove all margins so the axes fill the entire figure
    ax.set_position([0, 0, 1, 1])

    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(str(output_path), dpi=dpi,
                facecolor=fig.get_facecolor())
    plt.close(fig)

    img = Image.open(output_path)

    # Post-processing: old map effects
    if config.old_map_intensity > 0:
        img = _apply_old_map(img, config.old_map_intensity)
        img.save(str(output_path))

    img_w, img_h = img.size
    extent = (xmin - dx, ymin - dy, xmax + dx, ymax + dy)

    return RenderResult(
        image_path=output_path,
        width=img_w,
        height=img_h,
        extent=extent,
        color_map=color_map,
        zone_field=zone_field,
        gdf=gdf,
    )


def _apply_old_map(img: Image.Image, intensity: float) -> Image.Image:
    """Apply old/scanned map effects: yellowing, noise, blur, vignette, folds."""
    # Desaturate
    enhancer = ImageEnhance.Color(img)
    img = enhancer.enhance(1.0 - 0.5 * intensity)

    # Reduce contrast
    enhancer = ImageEnhance.Contrast(img)
    img = enhancer.enhance(1.0 - 0.2 * intensity)

    # Brighten (faded)
    enhancer = ImageEnhance.Brightness(img)
    img = enhancer.enhance(1.0 + 0.1 * intensity)

    # Yellowing
    arr = np.array(img, dtype=np.float32)
    arr[:, :, 0] = np.clip(arr[:, :, 0] + 30 * intensity, 0, 255)
    arr[:, :, 1] = np.clip(arr[:, :, 1] + 15 * intensity, 0, 255)
    arr[:, :, 2] = np.clip(arr[:, :, 2] - 20 * intensity, 0, 255)

    # Vignette
    h, w = arr.shape[:2]
    y, x = np.ogrid[:h, :w]
    cy, cx = h / 2, w / 2
    r = np.sqrt((x - cx) ** 2 + (y - cy) ** 2)
    r_max = np.sqrt(cx ** 2 + cy ** 2)
    mask = 1.0 - 0.3 * intensity * (r / r_max) ** 2
    mask = np.clip(mask, 0.3, 1.0)
    arr = arr * mask[:, :, np.newaxis]

    # Gaussian noise
    noise = np.random.normal(0, intensity * 8, arr.shape)
    arr = np.clip(arr + noise, 0, 255)

    img = Image.fromarray(arr.astype(np.uint8))

    # Slight blur
    if intensity > 0.3:
        img = img.filter(ImageFilter.GaussianBlur(radius=0.5 * intensity))

    # Fold lines
    if intensity > 0.3 and random.random() < intensity:
        arr = np.array(img, dtype=np.float32)
        n_folds = random.randint(1, max(1, int(3 * intensity)))
        for _ in range(n_folds):
            if random.random() < 0.5:
                row = random.randint(int(h * 0.2), int(h * 0.8))
                thickness = random.randint(1, 3)
                arr[row:row + thickness, :] *= random.uniform(0.5, 0.8)
            else:
                col = random.randint(int(w * 0.2), int(w * 0.8))
                thickness = random.randint(1, 3)
                arr[:, col:col + thickness] *= random.uniform(0.5, 0.8)
        img = Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8))

    return img


# ---------------------------------------------------------------------------
# Pattern swatches
# ---------------------------------------------------------------------------

def render_pattern_swatch(
    color: list[int],
    pattern_type: str = "solid",
    size: int = 32,
    dpi: int = 100,
) -> Image.Image:
    """Render a clean pattern swatch with full hatching control."""
    hatch_lookup = {h["name"]: h["hatch"] for h in HATCH_PATTERNS}
    hatch = hatch_lookup.get(pattern_type, None)

    fig_size = size / dpi
    fig, ax = plt.subplots(1, 1, figsize=(fig_size, fig_size), dpi=dpi)

    mpl_color = _color_to_mpl(color)
    hatch_color = _darken(mpl_color, 0.25) if hatch else None

    rect = mpatches.Rectangle(
        (0, 0), 1, 1,
        facecolor=mpl_color,
        edgecolor=hatch_color or "none",
        hatch=hatch,
        linewidth=0,
    )
    ax.add_patch(rect)
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.set_axis_off()
    plt.tight_layout(pad=0)

    fig.canvas.draw()
    buf = fig.canvas.buffer_rgba()
    arr = np.asarray(buf)
    plt.close(fig)

    img = Image.fromarray(arr[:, :, :3])
    img = img.resize((size, size), Image.LANCZOS)
    return img
