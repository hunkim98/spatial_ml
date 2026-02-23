# Municode Ordinance Scraper - Vertex AI Pipeline

This workflow provides a Vertex AI pipeline for scraping Municode ordinances and converting them to Markdown format.

## Overview

The pipeline consists of two main components:

1. **Collector**: Scrapes DOCX files from Municode for a given state and uploads to GCS
2. **Processor**: Converts DOCX files to Markdown and saves to GCS

## Architecture

```
MunicodeOrdinanceCollectorComponent(state_slug)
    ↓ Downloads DOCX files
    ↓ Saves to: gs://spatially-data/zoning_ordinance/{state}/{municipality}/*.docx

DocxToMarkdownConverterComponent(state_slug)
    ↓ Reads DOCX from GCS
    ↓ Converts to Markdown
    ↓ Saves to: gs://spatially-data/zoning_ordinance_markdown/{state}/{municipality}/*.md
```

## Setup

### Prerequisites

1. GCP Project with Vertex AI enabled
2. Service account with necessary permissions
3. Docker installed
4. Environment variables set:
   - `GCP_PROJECT`: Your GCP project ID
   - `GCP_REGION`: Your GCP region (e.g., `us-central1`)
   - `GCS_BUCKET_NAME`: GCS bucket name (e.g., `spatially-data`)
   - `GCS_SERVICE_ACCOUNT`: Service account email for Vertex AI
   - `GOOGLE_APPLICATION_CREDENTIALS`: Path to service account key file

### Building Docker Images

1. Build and push images to GCP Artifact Registry:

```bash
cd workflow
python registry/run.py --images all
```

Or build specific images:

```bash
python registry/run.py --images collector
python registry/run.py --images processor
```

## Usage

### Single State Pipeline

Run the pipeline for a single state:

```bash
python cli.py --pipeline municode-ordinance --state rhode-island
```

### Parallel Pipeline (All 50 States)

Run the pipeline for all US states in parallel:

```bash
python cli.py --pipeline municode-ordinance-parallel
```

### Parallel Pipeline (Subset of States)

Run the pipeline for specific states:

```bash
python cli.py --pipeline municode-ordinance-parallel --states rhode-island,delaware,vermont
```

## Pipeline Components

### MunicodeOrdinanceCollectorComponent

- **Input**: State slug (e.g., "rhode-island")
- **Output**: DOCX files in `gs://spatially-data/zoning_ordinance/{state}/{municipality}/*.docx`
- **Resources**: 2 CPU, 8GB RAM

### DocxToMarkdownConverterComponent

- **Input**: State slug (e.g., "rhode-island")
- **Output**: Markdown files in `gs://spatially-data/zoning_ordinance_markdown/{state}/{municipality}/*.md`
- **Resources**: 2 CPU, 4GB RAM

## File Structure

```
workflow/
├── cli.py                          # CLI for running pipelines
├── Dockerfile                      # Main workflow container
├── docker-entrypoint.sh           # Container entrypoint
├── pyproject.toml                 # Python dependencies
├── collector/
│   ├── Dockerfile                 # Collector container with Selenium
│   └── municode_ordinance/
│       └── run.py                 # Entry point for collector
├── processor/
│   ├── Dockerfile                 # Processor container
│   └── municode_converter/
│       ├── run.py                 # Entry point for converter
│       └── converter.py           # DOCX→Markdown conversion logic
├── pipelines/
│   ├── base_component.py          # Base class for components
│   ├── base_pipeline.py           # Base class for pipelines
│   ├── collector/
│   │   └── municode_ordinance.py  # Collector component
│   ├── processor/
│   │   └── municode_converter.py  # Converter component
│   ├── municode_ordinance.py      # Single-state pipeline
│   └── municode_ordinance_parallel.py  # Parallel pipeline
└── registry/
    ├── config.py                  # Docker image configuration
    └── run.py                     # Build and push images
```

## Verification

After running the pipeline, verify the results:

1. **Check DOCX files:**
   ```bash
   gsutil ls gs://spatially-data/zoning_ordinance/rhode-island/
   ```

2. **Check Markdown files:**
   ```bash
   gsutil ls gs://spatially-data/zoning_ordinance_markdown/rhode-island/
   ```

3. **Verify file counts match:**
   ```bash
   gsutil ls -r gs://spatially-data/zoning_ordinance/rhode-island/**/*.docx | wc -l
   gsutil ls -r gs://spatially-data/zoning_ordinance_markdown/rhode-island/**/*.md | wc -l
   ```

4. **Preview Markdown content:**
   ```bash
   gsutil cat gs://spatially-data/zoning_ordinance_markdown/rhode-island/{city}/{file}.md | head -50
   ```

## Performance

- **Sequential (one state at a time)**: ~30 hours per state
- **Parallel (all 50 states)**: ~30 hours total (limited by slowest state)
- **Speedup**: 50x when running all states in parallel

## Troubleshooting

### Image Build Failures

If Docker image build fails:

1. Check that you're in the workflow directory
2. Verify all required files exist
3. Check Docker daemon is running
4. Ensure sufficient disk space

### Pipeline Failures

If pipeline fails:

1. Check Vertex AI logs in GCP Console
2. Verify environment variables are set correctly
3. Check service account permissions
4. Verify GCS bucket exists and is accessible

### Authentication Issues

If authentication fails:

1. Verify `GOOGLE_APPLICATION_CREDENTIALS` points to valid service account key
2. Check service account has necessary roles:
   - Vertex AI User
   - Storage Admin
   - Artifact Registry Writer

## State Slugs

All 51 US states/territories are supported:

```
alabama, alaska, arizona, arkansas, california, colorado, connecticut,
delaware, district-of-columbia, florida, georgia, hawaii, idaho,
illinois, indiana, iowa, kansas, kentucky, louisiana, maine, maryland,
massachusetts, michigan, minnesota, mississippi, missouri, montana,
nebraska, nevada, new-hampshire, new-jersey, new-mexico, new-york,
north-carolina, north-dakota, ohio, oklahoma, oregon, pennsylvania,
rhode-island, south-carolina, south-dakota, tennessee, texas, utah,
vermont, virginia, washington, west-virginia, wisconsin, wyoming
```
