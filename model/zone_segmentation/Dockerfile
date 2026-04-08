# Zone Segmentation trainer image
#
# Single image that runs on both GPU and CPU hosts:
#   - GPU: docker compose run --rm --gpus all zone_segmentation_trainer ...
#   - CPU: docker compose run --rm              zone_segmentation_trainer ...
#
# The PyTorch CUDA base image already has matching cuDNN; we install only the
# extra Python deps via uv. Mirrors the ac215_Spatially NER trainer Dockerfile.
FROM pytorch/pytorch:2.5.1-cuda12.4-cudnn9-runtime

ENV LANG=C.UTF-8 \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

# Minimal system deps:
#  - libgl1 / libglib2.0-0 are needed by opencv-python-headless and matplotlib
#  - git is handy for pip installs from VCS
RUN apt-get update && apt-get install -y --no-install-recommends \
        git \
        libgl1 \
        libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

# uv for fast Python dependency installs
RUN pip install --no-cache-dir uv

# Install only the trainer's extra deps (torch / torchvision come from the base image).
COPY model/zone_segmentation/pyproject.toml /app/pyproject.toml
RUN uv pip install --system --no-cache -r /app/pyproject.toml

# Copy the model package. The bind mount in docker-compose will overlay this
# during local development; the COPY makes the image self-contained for CI / GCP.
COPY model /app/model

# Stable mount points for data, checkpoints, secrets
RUN mkdir -p /data /app/checkpoints /secrets

# Make `from model.zone_segmentation...` importable
ENV PYTHONPATH=/app

# Default: drop into bash. Override with `python -m model.zone_segmentation.train ...`
CMD ["bash"]
