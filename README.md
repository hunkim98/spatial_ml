# Spatial ML

A project for training spatial ML models, including a CV model for extracting GIS data from zoning PDFs and an LLM for parsing zoning codes from ordinances.

## Getting Started

### 1. Clone and Setup

```bash
git clone <repo-url>
cd spatial_ml

# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt  # or use uv: uv sync
```

### 2. Set Up GCP Credentials

```bash
# Option A: Use gcloud CLI
gcloud auth application-default login

# Option B: Use service account key (ask team for access)
export GOOGLE_APPLICATION_CREDENTIALS=./secrets/teamspatially-storage-accessor-keys.json
```

### 3. Pull Data with DVC

We use [DVC](https://dvc.org/) to manage large data files. Data is stored in GCS bucket `gs://zoning_data`.

```bash
# Pull all data from GCS
dvc pull
```

This will download the `data/` folder with all datasets.

## DVC Workflow

### Pulling Data (when you clone or switch branches)

```bash
dvc pull
```

### Adding/Updating Data

When you add new files to `data/`:

```bash
dvc add data    # Update tracking (recalculates hash)
dvc push        # Upload to GCS
```

If you want to version your data changes (recommended):

```bash
dvc add data
git add data.dvc
git commit -m "Update data: <describe changes>"
dvc push
```

### Check Sync Status

```bash
dvc status       # Local changes
dvc status -c    # Compare with remote
```

## Project Structure

```
spatial_ml/
├── data/           # Datasets (managed by DVC, not in git)
├── model/          # Model training code
├── processor/      # Data processing code
├── scripts/        # Utility scripts
├── secrets/        # Credentials (not in git)
├── data.dvc        # DVC tracking file
└── docker-compose.yml
```

## Useful Scripts

### Download GeoJSON from ArcGIS

Download GIS data from ArcGIS map viewer URLs:

```bash
python scripts/arcgis_url_to_geojson.py "<arcgis_url>"
```

Example:
```bash
python scripts/arcgis_url_to_geojson.py "https://boston.maps.arcgis.com/apps/mapviewer/index.html?layers=fffb5de90c814daabf2cfd5538b8d22c"
```

This will:
- Download all features as GeoJSON
- Save to current directory (e.g., `Boston_Zoning_Subdistricts.geojson`)
- Generate and open a preview image

## Docker

Run the processor container:

```bash
docker-compose up processor
```

## Questions?

Reach out to the team if you need access to secrets or have any questions!
