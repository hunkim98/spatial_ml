"""FastAPI backend for zone segmentation inference.

Loads VanillaUNet at startup, serves segmentation requests.

Usage:
    uv run uvicorn api.main:app --host 0.0.0.0 --port 8000 --reload
"""

import io
import json
import logging
from contextlib import asynccontextmanager

import torch
from fastapi import FastAPI, File, Form, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from PIL import Image

from model.zone_segmentation.inference import ZoneSegmenter, masks_to_geojson

logger = logging.getLogger(__name__)

CHECKPOINT = "checkpoints/zone_seg_loam_vanilla_v2/best.pt"
MODEL_TYPE = "vanilla"

segmenter: ZoneSegmenter | None = None


def _pick_device() -> str:
    if torch.cuda.is_available():
        return "cuda"
    if torch.backends.mps.is_available():
        return "mps"
    return "cpu"


@asynccontextmanager
async def lifespan(app: FastAPI):
    global segmenter
    device = _pick_device()
    logger.info("Loading %s model on %s from %s", MODEL_TYPE, device, CHECKPOINT)
    segmenter = ZoneSegmenter(
        checkpoint=CHECKPOINT,
        device=device,
        model_type=MODEL_TYPE,
    )
    logger.info("Model loaded successfully")
    yield


app = FastAPI(title="Zone Segmentation API", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/health")
async def health():
    return {
        "status": "ok",
        "device": segmenter.device if segmenter else "unloaded",
        "model": MODEL_TYPE,
    }


@app.post("/api/segment")
async def segment(
    image: UploadFile = File(...),
    patterns: list[UploadFile] = File(...),
    pattern_names: str = Form(...),
    extent: str = Form(...),
    threshold: float = Form(0.5),
    simplify_tolerance: float = Form(2.0),
    snap_distance: float = Form(4.0),
):
    """Run segmentation on a map image with one or more pattern queries.

    Returns a GeoJSON FeatureCollection with polygons for each detected zone.
    """
    assert segmenter is not None, "Model not loaded"

    names = json.loads(pattern_names)
    ext = json.loads(extent)
    extent_tuple = (ext["xmin"], ext["ymin"], ext["xmax"], ext["ymax"])

    # Load map image
    img_bytes = await image.read()
    map_image = Image.open(io.BytesIO(img_bytes)).convert("RGB")

    # Run inference for each pattern
    masks = {}
    for upload, name in zip(patterns, names):
        pat_bytes = await upload.read()
        pattern_img = Image.open(io.BytesIO(pat_bytes)).convert("RGB")
        mask = segmenter.predict_mask(map_image, pattern_img, threshold=threshold)
        masks[name] = mask

    # Convert to GeoJSON with simplification and boundary alignment
    geojson = masks_to_geojson(
        masks,
        extent_tuple,
        map_image.width,
        map_image.height,
        simplify_tolerance=simplify_tolerance,
        snap_distance=snap_distance,
    )
    return geojson
