"""MapRenderer — orchestrates canvas + layers into a rendered map."""

from __future__ import annotations

import io
from pathlib import Path

import geopandas as gpd
import matplotlib.pyplot as plt
from PIL import Image
from pyproj import Transformer

from .canvas import Canvas
from .config import MapConfig, RenderResult
from .layers.base import BaseLayer
from .layers.label import LabelLayer
from .postprocess.pipeline import PostProcessPipeline


class MapRenderer:
    """Renders a zoning map by drawing layers onto a canvas.

    Usage:
        renderer = MapRenderer(
            canvas=Canvas(zoom=1.0),
            layers=[
                BackgroundLayer(),
                ZoneLayer(),
                LabelLayer(),
            ],
        )
        result = renderer.render(config, "output.png")
    """

    def __init__(
        self,
        canvas: Canvas | None = None,
        layers: list[BaseLayer] | None = None,
        postprocess: PostProcessPipeline | None = None,
    ):
        self.canvas = canvas or Canvas()
        self.layers = layers or []
        self.postprocess = postprocess

    def render(self, config: MapConfig, output_path: Path) -> RenderResult:
        """Render all layers onto the canvas and save.

        Order: background + zones + grid → snapshot (no labels) →
        labels → save. Postprocessing applied to both images so the
        nolabel_image has identical effects but no text.
        """
        fig, ax, render_gdf = self.canvas.create(config.gdf)

        render_config = MapConfig(
            gdf=render_gdf,
            zone_column=config.zone_column,
            color_map=config.color_map,
        )

        annotations = {
            "rotation": self.canvas.post_rotation or self.canvas.rotation,
            "zoom": self.canvas.resolved_zoom,
        }
        label_layers = []

        # Phase 1: draw everything except labels
        for layer in self.layers:
            if isinstance(layer, LabelLayer):
                label_layers.append(layer)
                continue
            layer_ann = layer.draw(ax, render_config)
            if layer_ann:
                annotations.update(layer_ann)

        # Snapshot before labels (for pattern extraction later)
        nolabel_image = self._snapshot(fig)

        # Phase 2: draw labels on top
        for layer in label_layers:
            layer_ann = layer.draw(ax, render_config)
            if layer_ann:
                annotations.update(layer_ann)

        return self._save(fig, output_path, render_config, config.gdf, annotations, nolabel_image)

    def _snapshot(self, fig: plt.Figure) -> Image.Image:
        """Capture the current figure state as a PIL Image (in-memory)."""
        buf = io.BytesIO()
        fig.savefig(buf, format="png", dpi=self.canvas.dpi)
        buf.seek(0)
        img = Image.open(buf)
        img.load()
        buf.close()
        return img

    def _apply_rotation(self, img: Image.Image) -> Image.Image:
        """Post-render rotation + crop back to original extent.

        The canvas expanded the extent to a square covering the diagonal
        so the rotated image has no blank corners. We crop back to the
        original (pre-expansion) field of view.
        """
        img = img.rotate(self.canvas.post_rotation, resample=Image.BICUBIC, expand=False)
        w, h = img.size

        # Compute crop from actual extent geometry
        oxmin, oymin, oxmax, oymax = self.canvas.original_extent
        exmin, eymin, exmax, eymax = self.canvas.extent
        ew = exmax - exmin
        eh = eymax - eymin

        crop_left = (oxmin - exmin) / ew if ew > 0 else 0
        crop_top = (eymax - oymax) / eh if eh > 0 else 0  # y-axis is flipped in image
        crop_right = (exmax - oxmax) / ew if ew > 0 else 0
        crop_bottom = (oymin - eymin) / eh if eh > 0 else 0

        left = int(w * crop_left)
        top = int(h * crop_top)
        right = int(w * (1 - crop_right))
        bottom = int(h * (1 - crop_bottom))
        return img.crop((left, top, right, bottom))

    def _save(
        self,
        fig: plt.Figure,
        output_path: Path,
        config: MapConfig,
        original_gdf: gpd.GeoDataFrame,
        annotations: dict | None = None,
        nolabel_image: Image.Image | None = None,
    ) -> RenderResult:
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        fig.savefig(str(output_path), dpi=self.canvas.dpi)
        plt.close(fig)

        img = Image.open(output_path)
        raw_w, raw_h = img.size

        # Post-render rotation — apply to both images
        if self.canvas.post_rotation != 0:
            img = self._apply_rotation(img)
            if nolabel_image is not None:
                nolabel_image = self._apply_rotation(nolabel_image)

        # Postprocessing — nolabel image first (freezes random params),
        # then main image reuses the same frozen params
        if self.postprocess:
            if nolabel_image is not None:
                nolabel_image, _ = self.postprocess.run(nolabel_image)
            img, pp_annotations = self.postprocess.run(img)
            if annotations is None:
                annotations = {}
            annotations.update(pp_annotations)

        img.save(str(output_path))

        # Compute WGS84 corners from the original GDF (before rotation/reprojection)
        corners_wgs84 = self._extent_to_wgs84(original_gdf)
        if annotations:
            annotations["corners_wgs84"] = corners_wgs84

        return RenderResult(
            image_path=output_path,
            width=img.size[0],
            height=img.size[1],
            extent=self.canvas.extent,
            color_map=config.color_map,
            zone_column=config.zone_column,
            gdf=config.gdf,
            annotations=annotations or {},
            raw_width=raw_w,
            raw_height=raw_h,
            post_rotation=self.canvas.post_rotation,
            nolabel_image=nolabel_image,
        )

    def _extent_to_wgs84(self, original_gdf: gpd.GeoDataFrame) -> dict:
        """Convert original GDF bounds to WGS84 lat/lon corners.

        Uses the original GDF (before any rotation or reprojection) to get
        geographically correct WGS84 coordinates regardless of render transforms.
        """
        xmin, ymin, xmax, ymax = original_gdf.total_bounds
        src_crs = original_gdf.crs

        if src_crs is None or src_crs.to_epsg() == 4326:
            to_ll = lambda x, y: (x, y)
        else:
            transformer = Transformer.from_crs(src_crs, "EPSG:4326", always_xy=True)
            to_ll = transformer.transform

        return {
            "top_left": list(reversed(to_ll(xmin, ymax))),      # [lat, lon]
            "top_right": list(reversed(to_ll(xmax, ymax))),
            "bottom_left": list(reversed(to_ll(xmin, ymin))),
            "bottom_right": list(reversed(to_ll(xmax, ymin))),
        }
