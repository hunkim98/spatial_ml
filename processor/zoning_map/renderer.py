"""ArcPy-based map renderer. The ONLY module that imports arcpy.

Takes a MapConfig → produces a cropped map frame image + metadata.
"""

import logging
from pathlib import Path

import arcpy
import geopandas as gpd

from .config import MapConfig, RenderResult
from .legend import LegendConfig

logger = logging.getLogger(__name__)

_sample_counter = 0

_DEFAULT_APRX = (
    "C:/Program Files/ArcGIS/Pro/Resources/ArcToolBox/"
    "Services/routingservices/data/Blank.aprx"
)



# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _ingest_to_feature_class(gdf: gpd.GeoDataFrame, output_dir: Path) -> str:
    global _sample_counter
    output_dir = output_dir.resolve()
    temp_gdb = str(output_dir / "scratch.gdb")
    fc_name = f"zones_{_sample_counter}"
    _sample_counter += 1

    if not arcpy.Exists(temp_gdb):
        arcpy.management.CreateFileGDB(str(output_dir), "scratch.gdb")

    fc_path = f"{temp_gdb}/{fc_name}"
    if arcpy.Exists(fc_path):
        arcpy.management.Delete(fc_path)

    temp_shp = output_dir / "temp_zones.shp"
    export_gdf = gdf.drop(columns=["zone_color"], errors="ignore")
    export_gdf.to_file(temp_shp, driver="ESRI Shapefile")
    arcpy.conversion.FeatureClassToFeatureClass(str(temp_shp), temp_gdb, fc_name)

    for ext in [".shp", ".shx", ".dbf", ".prj", ".cpg"]:
        p = temp_shp.with_suffix(ext)
        if p.exists():
            p.unlink()
    return fc_path


# Map our style names to ArcGIS gallery names
HATCH_STYLES = [
    # Line patterns — varying spacing: tight, medium, loose
    {"name": "diagonal", "gallery": "Hatched Fill with Background"},
    {"name": "horizontal", "gallery": "Horizontal Hatch Fill"},
    {"name": "vertical", "gallery": "Vertical Hatch Fill"},
    {"name": "crosshatch_tight", "gallery": "Crosshatch Fill, Tight"},
    {"name": "crosshatch_medium", "gallery": "Crosshatch Fill, Medium"},
    {"name": "crosshatch_loose", "gallery": "Crosshatch Fill, Loose"},
    {"name": "crosshatch_10pct", "gallery": "10% Crosshatch"},
    {"name": "hatch_10pct", "gallery": "10% Simple hatch"},
    {"name": "striped", "gallery": "Striped Fill"},
    # Point/dot patterns
    {"name": "dots_medium", "gallery": "Dot Fill 2"},
    {"name": "dots_dense", "gallery": "Dot Fill 3"},
    {"name": "stipple", "gallery": "10% Ordered Stipple"},
    {"name": "diamond", "gallery": "Diamond Pattern Fill"},
]


def _apply_symbology(
    lyr, zone_field: str, color_map: dict[str, list[int]],
    hatch_zones: dict[str, str] | None = None,
):
    """Apply unique value renderer with zone colors and optional hatching.

    Uses applySymbolFromGallery for hatched zones (Esri's native approach).

    Args:
        hatch_zones: {zone_name: hatch_style_name} for zones that should
            have hatched fills. None = all solid.
    """
    gallery_lookup = {s["name"]: s["gallery"] for s in HATCH_STYLES}

    shp_field = zone_field[:10]
    sym = lyr.symbology
    if not hasattr(sym, "updateRenderer"):
        return
    sym.updateRenderer("UniqueValueRenderer")
    sym.renderer.fields = [shp_field]
    for grp in sym.renderer.groups:
        for item in grp.items:
            zone_val = item.values[0][0]
            if zone_val in color_map:
                r, g, b = color_map[zone_val]
                # Apply hatch style from gallery if this zone is hatched
                if hatch_zones and zone_val in hatch_zones:
                    style_name = hatch_zones[zone_val]
                    gallery_name = gallery_lookup.get(style_name, HATCH_STYLES[0]["gallery"])
                    item.symbol.applySymbolFromGallery(gallery_name)
                item.symbol.color = {"RGB": [r, g, b, 100]}
                item.symbol.outlineColor = {"RGB": [80, 80, 80, 100]}
                item.symbol.outlineWidth = 0.5
    lyr.symbology = sym


def _pad_extent(extent, factor: float):
    w = extent.XMax - extent.XMin
    h = extent.YMax - extent.YMin
    dx = w * (factor - 1) / 2
    dy = h * (factor - 1) / 2
    extent.XMin -= dx
    extent.XMax += dx
    extent.YMin -= dy
    extent.YMax += dy
    return extent


def _compute_layout_regions(legend_config, pdf_width, pdf_height, margin):
    """Compute map frame rect and legend position/anchor based on alignment."""
    strip = legend_config.strip_fraction
    align = legend_config.alignment
    gap = 0.1
    usable_w = pdf_width - 2 * margin
    usable_h = pdf_height - 2 * margin

    if legend_config.strip_position == "bottom":
        sh = pdf_height * strip
        strip_top = margin + sh
        if align == "left":
            lx, anchor = margin + gap, "TOP_LEFT_CORNER"
        elif align == "right":
            lx, anchor = pdf_width - margin - gap, "TOP_RIGHT_CORNER"
        else:
            lx, anchor = pdf_width / 2, "TOP_MID_POINT"
        return {
            "map_rect": (margin, strip_top, pdf_width - margin, pdf_height - margin),
            "legend_pos": (lx, strip_top - gap),
            "legend_anchor": anchor,
            "legend_max_w": usable_w - 0.2,
            "legend_max_h": sh - 0.2,
        }
    elif legend_config.strip_position == "top":
        sh = pdf_height * strip
        strip_bottom = pdf_height - margin - sh
        if align == "left":
            lx, anchor = margin + gap, "TOP_LEFT_CORNER"
        elif align == "right":
            lx, anchor = pdf_width - margin - gap, "TOP_RIGHT_CORNER"
        else:
            lx, anchor = pdf_width / 2, "TOP_MID_POINT"
        return {
            "map_rect": (margin, margin, pdf_width - margin, strip_bottom),
            "legend_pos": (lx, pdf_height - margin - gap),
            "legend_anchor": anchor,
            "legend_max_w": usable_w - 0.2,
            "legend_max_h": sh - 0.2,
        }
    elif legend_config.strip_position == "right":
        sw = pdf_width * strip
        strip_left = pdf_width - margin - sw
        if align == "top":
            ly, anchor = pdf_height - margin - gap, "TOP_LEFT_CORNER"
        elif align == "bottom":
            ly, anchor = margin + gap, "BOTTOM_LEFT_CORNER"
        else:
            ly, anchor = pdf_height / 2, "LEFT_MID_POINT"
        return {
            "map_rect": (margin, margin, strip_left, pdf_height - margin),
            "legend_pos": (strip_left + gap, ly),
            "legend_anchor": anchor,
            "legend_max_w": sw - 0.2,
            "legend_max_h": usable_h - 0.2,
        }
    else:  # left
        sw = pdf_width * strip
        strip_right = margin + sw
        if align == "top":
            ly, anchor = pdf_height - margin - gap, "TOP_LEFT_CORNER"
        elif align == "bottom":
            ly, anchor = margin + gap, "BOTTOM_LEFT_CORNER"
        else:
            ly, anchor = pdf_height / 2, "LEFT_MID_POINT"
        return {
            "map_rect": (strip_right, margin, pdf_width - margin, pdf_height - margin),
            "legend_pos": (margin + gap, ly),
            "legend_anchor": anchor,
            "legend_max_w": sw - 0.2,
            "legend_max_h": usable_h - 0.2,
        }


def _map_frame_to_pixels(map_rect, pdf_width, pdf_height, img_w, img_h):
    mx0, my0, mx1, my1 = map_rect
    sx = img_w / pdf_width
    sy = img_h / pdf_height
    return (
        int(mx0 * sx),
        int((pdf_height - my1) * sy),
        int(mx1 * sx),
        int((pdf_height - my0) * sy),
    )



# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

class MapRenderer:
    """Renders a MapConfig to a cropped map frame image using ArcGIS Pro.

    This is the only class that depends on arcpy.
    """

    def __init__(self, aprx_template: str | None = None):
        self._aprx_template = aprx_template

    def render(self, config: MapConfig, work_dir: Path) -> RenderResult:
        """Render a map to a PNG image, cropped to the map frame.

        Args:
            config: MapConfig with all rendering parameters.
            work_dir: directory for temporary files (PDF, GDB).

        Returns:
            RenderResult with the image path, dimensions, extent, etc.
        """
        work_dir = work_dir.resolve()
        work_dir.mkdir(parents=True, exist_ok=True)

        gdf = config.gdf
        zone_field = config.zone_field
        color_map = config.color_map
        pdf_width = config.page_width
        pdf_height = config.page_height

        fc_path = _ingest_to_feature_class(gdf, work_dir)

        aprx_path = self._aprx_template or _DEFAULT_APRX
        aprx = arcpy.mp.ArcGISProject(aprx_path)
        m = aprx.listMaps()[0]

        for lyr in m.listLayers():
            m.removeLayer(lyr)

        if config.basemap:
            try:
                m.addBasemap(config.basemap)
            except Exception:
                logger.warning(f"Failed to add basemap '{config.basemap}'")

        lyr = m.addDataFromPath(fc_path)
        lyr.name = "Zoning"

        if zone_field and zone_field in gdf.columns:
            _apply_symbology(lyr, zone_field, color_map, config.hatch_zones or None)

        # Zone layer transparency (config.opacity: 1.0=opaque, 0.0=transparent)
        transparency = int((1.0 - config.opacity) * 100)
        if transparency > 0:
            lyr_cim = lyr.getDefinition("V3")
            lyr_cim.transparency = transparency
            lyr.setDefinition(lyr_cim)

        # Native arcpy labeling — zone codes on each polygon
        if config.show_labels and zone_field:
            self._add_labels(lyr, zone_field, color_map)

        # --- Layout ---
        layout = aprx.createLayout(pdf_width, pdf_height, "INCH")
        margin = 0.4

        if config.legend:
            regions = _compute_layout_regions(config.legend, pdf_width, pdf_height, margin)
            map_rect = regions["map_rect"]
        else:
            map_rect = (margin, margin, pdf_width - margin, pdf_height - margin)
            regions = None
        mx0, my0, mx1, my1 = map_rect

        mf = layout.createMapFrame(
            arcpy.Geometry("polygon", arcpy.Array([
                arcpy.Point(mx0, my0), arcpy.Point(mx1, my0),
                arcpy.Point(mx1, my1), arcpy.Point(mx0, my1),
            ])),
            m,
        )
        ext = mf.getLayerExtent(lyr, True)
        mf.camera.setExtent(_pad_extent(ext, config.extent_padding))

        # Read back the ACTUAL extent arcpy is using (it adjusts for aspect ratio)
        actual_ext = mf.camera.getExtent()
        actual_geo_extent = (
            actual_ext.XMin, actual_ext.YMin,
            actual_ext.XMax, actual_ext.YMax,
        )

        # --- Legend (if configured) ---
        if config.legend and regions:
            self._add_legend(aprx, layout, mf, config, regions)

        # --- Scale bar inside map frame ---
        # --- Export PDF ---
        pdf_path = work_dir / "render.pdf"
        layout.exportToPDF(str(pdf_path), resolution=config.dpi * 2)

        # --- Crop to map frame ---
        import fitz
        doc = fitz.open(str(pdf_path))
        page = doc[0]
        full_pix = page.get_pixmap(dpi=config.dpi)
        full_w, full_h = full_pix.width, full_pix.height

        crop_box = _map_frame_to_pixels(
            map_rect, pdf_width, pdf_height, full_w, full_h
        )

        from PIL import Image
        img = Image.frombytes("RGB", (full_w, full_h), full_pix.samples)
        img = img.crop(crop_box)
        doc.close()

        # Unique filename per render to avoid overwrites when rendering twice
        import uuid
        image_path = work_dir / f"map_frame_{uuid.uuid4().hex[:8]}.png"
        img.save(str(image_path))
        img_w, img_h = img.size

        # Cleanup
        pdf_path.unlink(missing_ok=True)
        del mf, layout, lyr, m, aprx

        return RenderResult(
            image_path=image_path,
            width=img_w,
            height=img_h,
            extent=actual_geo_extent,
            color_map=color_map,
            zone_field=zone_field,
            gdf=gdf,
        )

    def _add_legend(self, aprx, layout, mf, config: MapConfig, regions: dict):
        """Add legend using built-in ArcGIS style."""
        legend_config = config.legend

        legend_style = aprx.listStyleItems("ArcGIS 2D", "LEGEND", "Legend 1")[0]
        lx, ly = regions["legend_pos"]
        legend = layout.createMapSurroundElement(
            arcpy.Point(lx, ly), "LEGEND", mf, legend_style, "ZoningLegend"
        )
        legend.title = legend_config.title
        legend.showTitle = legend_config.show_title
        legend.fittingStrategy = "AdjustColumns"

        max_w = regions["legend_max_w"]
        max_h = regions["legend_max_h"]
        legend.elementWidth = max_w

        pos = legend_config.strip_position
        if pos in ("left", "right"):
            import math
            n_items = len(config.color_map) or 10
            auto_cols = max(1, round(max_w / 1.0))
            if auto_cols > 1:
                items_per_col = math.ceil(n_items / auto_cols)
                forced_h = items_per_col * 0.25 + 0.5
                legend.elementHeight = min(forced_h, max_h)
            else:
                legend.elementHeight = max_h
        else:
            legend.elementHeight = max_h
            if legend_config.column_count:
                legend.columnCount = legend_config.column_count
            else:
                legend.columnCount = max(2, round(max_w / 1.3))

        # Suppress layer metadata
        cim = legend.getDefinition("V3")
        if cim.defaultLegendItem:
            cim.defaultLegendItem.showLayerName = False
            cim.defaultLegendItem.showHeading = False
            cim.defaultLegendItem.showDescription = False
            cim.defaultLegendItem.showGroupLayerName = False
        if cim.items:
            for item in cim.items:
                item.showLayerName = False
                item.showHeading = False
                item.showDescription = False
                item.showGroupLayerName = False
        if cim.titleSymbol and cim.titleSymbol.symbol:
            cim.titleSymbol.symbol.fontFamilyName = legend_config.font_family
            cim.titleSymbol.symbol.height = legend_config.title_size
        if cim.defaultLegendItem and cim.defaultLegendItem.labelSymbol:
            if cim.defaultLegendItem.labelSymbol.symbol:
                cim.defaultLegendItem.labelSymbol.symbol.fontFamilyName = (
                    legend_config.font_family
                )
                cim.defaultLegendItem.labelSymbol.symbol.height = (
                    legend_config.label_size
                )
        legend.setDefinition(cim)

        if legend.elementWidth > max_w:
            legend.elementWidth = max_w
        if legend.elementHeight > max_h:
            legend.elementHeight = max_h

        legend.setAnchor(regions["legend_anchor"])
        legend.elementPositionX = lx
        legend.elementPositionY = ly

    def _add_labels(self, lyr, zone_field, color_map):
        """Add zone code labels with per-zone random font, size, opacity, style.

        Uses the full Arcade text formatting vocabulary:
        FNT (name, size, scale), BOL, ITA, UND, SCP, CLR (with alpha), CHR (spacing)
        """
        import random as _rng

        lyr.showLabels = True
        shp_field = zone_field[:10]

        fonts = ["Arial", "Arial Narrow", "Tahoma", "Times New Roman",
                 "Calibri", "Verdana", "Corbel", "Gill Sans MT",
                 "Georgia", "Garamond", "Bookman Old Style"]

        # Per-zone formatting via Arcade When()
        zone_names = list(color_map.keys())
        cases = []
        for z in zone_names:
            # Random font per zone (or shared — 50/50)
            font = _rng.choice(fonts)
            size = _rng.randint(7, 20)
            scale = _rng.choice([100, 100, 100, 110, 120, 80, 90])  # mostly 100%

            # Random text style
            style = _rng.choice([
                "regular", "regular", "bold", "bold",
                "italic", "bold_italic", "underline",
                "smallcaps", "bold_underline",
            ])
            style_open = ""
            style_close = ""
            if "bold" in style and "italic" in style:
                style_open += "<BOL><ITA>"
                style_close = "</ITA></BOL>" + style_close
            elif "bold" in style and "underline" in style:
                style_open += "<BOL><UND>"
                style_close = "</UND></BOL>" + style_close
            elif "bold" in style:
                style_open += "<BOL>"
                style_close = "</BOL>" + style_close
            elif "italic" in style:
                style_open += "<ITA>"
                style_close = "</ITA>" + style_close
            elif "underline" in style:
                style_open += "<UND>"
                style_close = "</UND>" + style_close
            elif "smallcaps" in style:
                style_open += "<SCP>"
                style_close = "</SCP>" + style_close

            # Random color and opacity
            alpha = _rng.randint(40, 100)
            if _rng.random() < 0.7:
                # Dark text (most common)
                r = _rng.randint(0, 50)
                g = _rng.randint(0, 50)
                b = _rng.randint(0, 50)
            elif _rng.random() < 0.5:
                # White text (for dark zones)
                r = _rng.randint(200, 255)
                g = _rng.randint(200, 255)
                b = _rng.randint(200, 255)
            else:
                # Colored text (red, blue, brown — like real maps)
                r = _rng.randint(80, 200)
                g = _rng.randint(0, 80)
                b = _rng.randint(0, 80)

            # Random character spacing (occasionally)
            spacing = ""
            spacing_close = ""
            if _rng.random() < 0.15:
                sp = _rng.choice([80, 120, 150, 200])
                spacing = f"<CHR spacing='{sp}'>"
                spacing_close = "</CHR>"

            tag = (
                f"{spacing}"
                f"<FNT name='{font}' size='{size}' scale='{scale}'>"
                f"<CLR red='{r}' green='{g}' blue='{b}' alpha='{alpha}'>"
                f"{style_open}"
            )
            tag_close = f"{style_close}</CLR></FNT>{spacing_close}"

            escaped_z = z.replace("'", "\\'")
            cases.append(
                f'$feature.{shp_field} == \'{escaped_z}\', '
                f'"{tag}" + $feature.{shp_field} + "{tag_close}"'
            )

        fallback_size = _rng.randint(8, 14)
        fallback = f'"<FNT size=\'{fallback_size}\'>" + $feature.{shp_field} + "</FNT>"'

        expr = f"When({', '.join(cases)}, {fallback})"

        for lc in lyr.listLabelClasses():
            lc.expression = expr
            lc.visible = True

