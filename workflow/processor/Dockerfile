FROM python:3.11-slim

# Prevent apt from showing prompts
ENV DEBIAN_FRONTEND=noninteractive

# Python wants UTF-8 locale
ENV LANG=C.UTF-8

# Tell Python to disable buffering so we don't lose any logs.
ENV PYTHONUNBUFFERED=1

# Install system dependencies
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    curl \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Install Python dependencies
RUN pip install --no-cache-dir \
    markitdown[docx] \
    google-cloud-storage

# Copy processor code (from spatial_ml root context)
COPY workflow/processor/municode_converter /app/municode_converter

# Set Python path
ENV PYTHONPATH=/app

# Entry point will be overridden by pipeline
CMD ["python", "/app/municode_converter/run.py"]
