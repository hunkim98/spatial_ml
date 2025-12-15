# Playwright-based Dockerfile for web scraping tasks that require
# better compatibility with Next.js and bot-protected sites
FROM mcr.microsoft.com/playwright/python:v1.55.0-jammy

ARG DEBIAN_PACKAGES="build-essential gdal-bin libgdal-dev libproj-dev libgeos-dev"

# Prevent apt from showing prompts
ENV DEBIAN_FRONTEND=noninteractive

# Python wants UTF-8 locale
ENV LANG=C.UTF-8

# Tell Python to disable buffering so we don't lose any logs.
ENV PYTHONUNBUFFERED=1

# Set PYTHONPATH to allow imports from /app
ENV PYTHONPATH=/app

# Tell uv to copy packages from the wheel into the site-packages
ENV UV_LINK_MODE=copy
ENV UV_PROJECT_ENVIRONMENT=/home/pwuser/.venv

# Install system dependencies
USER root
RUN set -ex; \
    for i in $(seq 1 8); do mkdir -p "/usr/share/man/man${i}"; done && \
    apt-get update && \
    apt-get upgrade -y && \
    apt-get install -y --no-install-recommends $DEBIAN_PACKAGES && \
    # Clean up and install Python tools
    apt-get clean && \
    rm -rf /var/lib/apt/lists/* && \
    pip install --no-cache-dir --upgrade pip && \
    pip install uv && \
    mkdir -p /app && \
    chown pwuser:pwuser /app

# Switch to the playwright user (pwuser exists in the base image)
USER pwuser
WORKDIR /app

# Copy the entire data directory to match docker-compose structure
COPY --chown=pwuser:pwuser . ./

# Use the Playwright-specific pyproject.toml
RUN rm -f uv.lock && uv sync

# Playwright browsers are already installed in the base image (Chromium, Firefox, WebKit)

# Set up entrypoint to activate virtual environment
# Entry point
ENTRYPOINT ["/bin/bash"]
# Run setup on startup, then drop into bash
CMD ["-c", "source /home/pwuser/.venv/bin/activate && exec bash"]
