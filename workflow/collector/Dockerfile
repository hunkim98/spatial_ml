FROM infologistix/docker-selenium-python:3.10-bullseye

ARG DEBIAN_PACKAGES="build-essential gdal-bin libgdal-dev libproj-dev libgeos-dev"

# Prevent apt from showing prompts
ENV DEBIAN_FRONTEND=noninteractive

# Python wants UTF-8 locale
ENV LANG=C.UTF-8

# Tell Python to disable buffering so we don't lose any logs.
ENV PYTHONUNBUFFERED=1

# Set PYTHONPATH to allow imports from /app/collector
ENV PYTHONPATH=/app/collector

# Tell uv where to create the virtual environment
ENV UV_PROJECT_ENVIRONMENT=/home/app/.venv

# Install system dependencies (Chrome already included in base image)
RUN set -ex; \
    for i in $(seq 1 8); do mkdir -p "/usr/share/man/man${i}"; done && \
    apt-get update && \
    apt-get upgrade -y && \
    apt-get install -y --no-install-recommends $DEBIAN_PACKAGES && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/* && \
    pip install --no-cache-dir --upgrade pip && \
    pip install uv && \
    useradd -ms /bin/bash app -d /home/app -u 1000 && \
    mkdir -p /app && \
    chown app:app /app

# Switch to the new user
USER app
WORKDIR /app

# Copy the entire collector directory from spatial_ml root
COPY --chown=app:app collector /app/collector

# Copy run.py into zoning_ordinance directory where imports work
COPY --chown=app:app workflow/collector/municode_ordinance/run.py /app/collector/zoning_ordinance/run_pipeline.py

# Install collector dependencies
WORKDIR /app/collector
RUN uv sync

# Set working directory back to app
WORKDIR /app

# Entry point will be overridden by pipeline
CMD ["bash", "-c", "source /home/app/.venv/bin/activate && exec bash"]
