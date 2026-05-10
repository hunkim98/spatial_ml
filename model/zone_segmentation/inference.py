"""Inference — given a map image and pattern thumbnails, produce binary masks.

Also includes vectorization: mask → polygon → GeoJSON.
"""

import json
from pathlib import Path

import numpy as np
import torch
from PIL import Image
from torchvision import transforms

from .unet import PatternConditionedUNet


class ZoneSegmenter:
    """Run inference on a map image with pattern queries."""

    def __init__(
        self,
        checkpoint: str,
        device: str = "cuda",
        image_size: int = 512,
        model_type: str = "resnet",
    ):
        self.device = device
        self.image_size = image_size

        if model_type == "vanilla":
            from .unet_vanilla import VanillaUNet
            self.model = VanillaUNet()
        else:
            self.model = PatternConditionedUNet(pretrained=False)

        self.model.load_state_dict(
            torch.load(checkpoint, map_location=device, weights_only=True)
        )
        self.model.to(device)
        self.model.eval()

        self.image_transform = transforms.Compose([
            transforms.Resize((image_size, image_size)),
            transforms.ToTensor(),
            transforms.Normalize(mean=[0.485, 0.456, 0.406],
                                 std=[0.229, 0.224, 0.225]),
        ])

        self.pattern_transform = transforms.Compose([
            transforms.Resize((32, 32)),
            transforms.ToTensor(),
            transforms.Normalize(mean=[0.485, 0.456, 0.406],
                                 std=[0.229, 0.224, 0.225]),
        ])

    @torch.no_grad()
    def predict_mask(
        self, image: Image.Image, pattern: Image.Image, threshold: float = 0.5,
    ) -> np.ndarray:
        """Predict binary mask for one pattern query.

        Args:
            image: map image (any size)
            pattern: 32x32 pattern thumbnail

        Returns:
            Binary mask at original image resolution (H, W) uint8.
        """
        orig_w, orig_h = image.size

        img_t = self.image_transform(image).unsqueeze(0).to(self.device)
        pat_t = self.pattern_transform(pattern).unsqueeze(0).to(self.device)

        logits = self.model(img_t, pat_t)  # (1, 1, H, W)
        prob = torch.sigmoid(logits).squeeze().cpu().numpy()

        # Resize back to original resolution
        prob_img = Image.fromarray((prob * 255).astype(np.uint8))
        prob_img = prob_img.resize((orig_w, orig_h), Image.BILINEAR)
        mask = np.array(prob_img) > (threshold * 255)

        return mask.astype(np.uint8) * 255

    def predict_all_zones(
        self, image: Image.Image, pattern_dir: str, threshold: float = 0.5,
    ) -> dict[str, np.ndarray]:
        """Predict masks for all patterns in a directory.

        Args:
            image: map image
            pattern_dir: directory containing zone_XX/pattern.png files

        Returns:
            {zone_name: binary_mask} dict
        """
        results = {}
        pattern_path = Path(pattern_dir)

        for zone_dir in sorted(pattern_path.iterdir()):
            if not zone_dir.is_dir():
                continue
            pattern_file = zone_dir / "pattern.png"
            if not pattern_file.exists():
                continue

            pattern = Image.open(pattern_file).convert("RGB")
            mask = self.predict_mask(image, pattern, threshold)
            results[zone_dir.name] = mask

        return results


def masks_to_polygons(
    mask: np.ndarray,
    simplify_tolerance: float = 2.0,
    min_area: float = 100.0,
):
    """Convert a binary mask to polygon coordinates.

    Uses OpenCV contour detection + Douglas-Peucker simplification.

    Args:
        mask: (H, W) uint8 binary mask
        simplify_tolerance: Douglas-Peucker epsilon in pixels
        min_area: minimum contour area in pixels to keep (filters noise)

    Returns:
        List of polygon coordinate arrays, each (N, 2).
    """
    import cv2

    contours, _ = cv2.findContours(
        mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE
    )

    polygons = []
    for contour in contours:
        if len(contour) < 3:
            continue
        if cv2.contourArea(contour) < min_area:
            continue
        approx = cv2.approxPolyDP(contour, simplify_tolerance, True)
        if len(approx) >= 3:
            polygons.append(approx.squeeze().tolist())

    return polygons


def _align_shared_boundaries(
    masks: dict[str, np.ndarray],
    simplify_tolerance: float = 2.0,
    min_area: float = 100.0,
    snap_distance: float = 4.0,
) -> dict[str, list]:
    """Vectorize all masks and snap shared boundaries so adjacent zones align.

    For each pair of zones that share a border (adjacent pixels in their masks),
    vertices from one polygon that are within snap_distance of an edge in the
    other polygon get snapped to the nearest point on that edge, and vice versa.

    Args:
        masks: {zone_name: binary_mask}
        simplify_tolerance: Douglas-Peucker epsilon in pixels
        min_area: minimum contour area to keep
        snap_distance: max pixel distance to snap vertices between zones

    Returns:
        {zone_name: list_of_polygon_coords} with aligned boundaries.
    """
    import cv2

    zone_names = list(masks.keys())

    # Step 1: vectorize each mask independently
    zone_polygons: dict[str, list] = {}
    for name in zone_names:
        zone_polygons[name] = masks_to_polygons(
            masks[name], simplify_tolerance, min_area
        )

    if len(zone_names) < 2:
        return zone_polygons

    # Step 2: find which zone pairs share a border (dilate each mask and check overlap)
    adjacent_pairs: list[tuple[str, str]] = []
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (3, 3))
    for i in range(len(zone_names)):
        dilated_i = cv2.dilate(masks[zone_names[i]], kernel, iterations=1)
        for j in range(i + 1, len(zone_names)):
            overlap = cv2.bitwise_and(dilated_i, masks[zone_names[j]])
            if np.any(overlap):
                adjacent_pairs.append((zone_names[i], zone_names[j]))

    if not adjacent_pairs:
        return zone_polygons

    # Step 3: for each adjacent pair, snap vertices to shared edges
    def _snap_point_to_segment(
        px: float, py: float, ax: float, ay: float, bx: float, by: float
    ) -> tuple[float, float, float]:
        """Project point P onto segment AB. Returns (snapped_x, snapped_y, dist)."""
        dx, dy = bx - ax, by - ay
        length_sq = dx * dx + dy * dy
        if length_sq == 0:
            return ax, ay, ((px - ax) ** 2 + (py - ay) ** 2) ** 0.5
        t = max(0.0, min(1.0, ((px - ax) * dx + (py - ay) * dy) / length_sq))
        sx, sy = ax + t * dx, ay + t * dy
        dist = ((px - sx) ** 2 + (py - sy) ** 2) ** 0.5
        return sx, sy, dist

    def _snap_polygons_to_edges(
        polys_to_snap: list, reference_polys: list, snap_dist: float
    ) -> list:
        """Snap vertices in polys_to_snap to nearby edges in reference_polys."""
        # Collect all reference edges
        ref_edges: list[tuple[float, float, float, float]] = []
        for poly in reference_polys:
            for k in range(len(poly)):
                ax, ay = poly[k]
                bx, by = poly[(k + 1) % len(poly)]
                ref_edges.append((ax, ay, bx, by))

        result = []
        for poly in polys_to_snap:
            new_poly = []
            for px, py in poly:
                best_sx, best_sy, best_dist = px, py, float("inf")
                for ax, ay, bx, by in ref_edges:
                    sx, sy, d = _snap_point_to_segment(px, py, ax, ay, bx, by)
                    if d < best_dist:
                        best_sx, best_sy, best_dist = sx, sy, d
                if best_dist <= snap_dist:
                    new_poly.append([round(best_sx, 6), round(best_sy, 6)])
                else:
                    new_poly.append([px, py])
            result.append(new_poly)
        return result

    for name_a, name_b in adjacent_pairs:
        # Snap A's vertices to B's edges, then B's vertices to A's edges
        zone_polygons[name_a] = _snap_polygons_to_edges(
            zone_polygons[name_a], zone_polygons[name_b], snap_distance
        )
        zone_polygons[name_b] = _snap_polygons_to_edges(
            zone_polygons[name_b], zone_polygons[name_a], snap_distance
        )

    return zone_polygons


def masks_to_geojson(
    masks: dict[str, np.ndarray],
    extent: tuple[float, float, float, float],
    image_width: int,
    image_height: int,
    simplify_tolerance: float = 2.0,
    min_area: float = 100.0,
    snap_distance: float = 4.0,
) -> dict:
    """Convert predicted masks to GeoJSON with aligned boundaries.

    Args:
        masks: {zone_name: binary_mask} from predict_all_zones
        extent: (xmin, ymin, xmax, ymax) geographic extent
        image_width, image_height: pixel dimensions
        simplify_tolerance: Douglas-Peucker epsilon in pixels
        min_area: minimum polygon area in pixels to keep
        snap_distance: max pixel distance to snap shared boundaries

    Returns:
        GeoJSON FeatureCollection dict.
    """
    xmin, ymin, xmax, ymax = extent
    px_to_x = lambda px: xmin + (px / image_width) * (xmax - xmin)
    px_to_y = lambda py: ymax - (py / image_height) * (ymax - ymin)  # y-flip

    # Vectorize with boundary alignment
    zone_polygons = _align_shared_boundaries(
        masks, simplify_tolerance, min_area, snap_distance
    )

    features = []
    for zone_name, polygons in zone_polygons.items():
        for poly_coords in polygons:
            # Convert pixel coords to geographic
            geo_coords = [[px_to_x(x), px_to_y(y)] for x, y in poly_coords]
            geo_coords.append(geo_coords[0])  # close the ring

            feature = {
                "type": "Feature",
                "properties": {"zone": zone_name},
                "geometry": {
                    "type": "Polygon",
                    "coordinates": [geo_coords],
                },
            }
            features.append(feature)

    return {
        "type": "FeatureCollection",
        "features": features,
    }
