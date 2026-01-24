FROM infologistix/docker-selenium-python:3.10-bullseye

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
ENV UV_PROJECT_ENVIRONMENT=/home/app/.venv

# Install system dependencies (Chrome already included in base image)
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
    useradd -ms /bin/bash app -d /home/app -u 1000 && \
    mkdir -p /app && \
    chown app:app /app

# Switch to the new user
USER app
WORKDIR /app
# Copy the entire data directory to match docker-compose structure
COPY --chown=app:app . ./

RUN uv sync

# Set up entrypoint to activate virtual environment
# Entry point
ENTRYPOINT ["/bin/bash"]
# Run setup on startup, then drop into bash
CMD ["-c", "source /home/app/.venv/bin/activate && exec bash"]