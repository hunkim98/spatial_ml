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

    def __init__(self, checkpoint: str, device: str = "cuda", image_size: int = 512):
        self.device = device
        self.image_size = image_size

        self.model = PatternConditionedUNet(pretrained=False)
        self.model.load_state_dict(torch.load(checkpoint, map_location=device))
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


def masks_to_polygons(mask: np.ndarray, simplify_tolerance: float = 2.0):
    """Convert a binary mask to polygon coordinates.

    Uses OpenCV contour detection + Douglas-Peucker simplification.

    Args:
        mask: (H, W) uint8 binary mask
        simplify_tolerance: polygon simplification tolerance in pixels

    Returns:
        List of polygon coordinate arrays, each (N, 2).
    """
    import cv2

    contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    polygons = []
    for contour in contours:
        if len(contour) < 3:
            continue
        # Simplify
        epsilon = simplify_tolerance
        approx = cv2.approxPolyDP(contour, epsilon, True)
        if len(approx) >= 3:
            polygons.append(approx.squeeze().tolist())

    return polygons


def masks_to_geojson(
    masks: dict[str, np.ndarray],
    extent: tuple[float, float, float, float],
    image_width: int,
    image_height: int,
) -> dict:
    """Convert predicted masks to GeoJSON.

    Args:
        masks: {zone_name: binary_mask} from predict_all_zones
        extent: (xmin, ymin, xmax, ymax) geographic extent
        image_width, image_height: pixel dimensions

    Returns:
        GeoJSON FeatureCollection dict.
    """
    xmin, ymin, xmax, ymax = extent
    px_to_x = lambda px: xmin + (px / image_width) * (xmax - xmin)
    px_to_y = lambda py: ymax - (py / image_height) * (ymax - ymin)  # y-flip

    features = []
    for zone_name, mask in masks.items():
        polygons = masks_to_polygons(mask)
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
