# Zoning Codes Collector

Collects zoning code data from various sources. Currently supports:

- **Zoneomics** (`zoneomics`) - Scrapes zoning district data from [zoneomics.com](https://www.zoneomics.com)

## Requirements

This collector uses **Playwright** for web scraping due to compatibility issues with Next.js sites in headless Chrome/Selenium. You must use the Playwright-based Docker image.

## Usage

### Local Development (Docker Compose)

```bash
# Build the Playwright collector image
docker compose build collector-playwright

# Run in test mode (first state, first city only)
docker compose run collector-playwright -c "source /home/pwuser/.venv/bin/activate && python zoning_codes/run.py --source zoneomics --test-mode"

# Run full collection (all 50 states)
docker compose run collector-playwright -c "source /home/pwuser/.venv/bin/activate && python zoning_codes/run.py --source zoneomics"
```

### Command Line Arguments

| Argument | Description |
|----------|-------------|
| `--source` | Data source to collect from (required). Options: `zoneomics` |
| `--test-mode` | Only process the first state (Alabama) for testing |

## Output

### CSV Files

Data is saved to `tmp/zoning_codes/{source}/{state}/{city}.csv` with columns:

| Column | Description |
|--------|-------------|
| `zone_code` | Zone code identifier (e.g., "R-1", "B-2") |
| `zone_subtype` | Zone name/subtype (e.g., "Single Family Residential") |
| `area_acres` | Area covered by this zone in acres |
| `description` | Full description of the zoning district |

### GCS Upload

CSV files are uploaded to `gs://{bucket}/zoning_codes/{source}/{state}/{city}.csv`

### Database

Creates a `zoning_codes` table with foreign key reference to `cities` table:

```sql
CREATE TABLE zoning_codes (
    id SERIAL PRIMARY KEY,
    city_id INTEGER NOT NULL REFERENCES cities(id) ON DELETE CASCADE,
    zone_code VARCHAR(50) NOT NULL,
    zone_subtype VARCHAR(255),
    area_acres DECIMAL(12, 2),
    description TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(city_id, zone_code)
);
```

## Vertex AI Pipeline

Use the `ZoningCodesCollectorComponent` from `workflow/pipelines/collector/zoning_codes.py`:

```python
from pipelines.collector.zoning_codes import ZoningCodesCollectorComponent

# Run full collection
component = ZoningCodesCollectorComponent(source="zoneomics")
component.run()

# Run in test mode
component = ZoningCodesCollectorComponent(source="zoneomics", test_mode=True)
component.run()
```

The pipeline uses the `data-collector-playwright` Docker image automatically.

## Environment Variables

| Variable | Description |
|----------|-------------|
| `GCS_BUCKET_NAME` | GCS bucket for storing CSV files |
| `GCP_PROJECT` | GCP project ID |
| `APP_DB_NAME` | PostgreSQL database name |
| `POSTGRE_HOST` | PostgreSQL host |
| `POSTGRE_PORT` | PostgreSQL port (default: 5432) |
| `POSTGRE_USER` | PostgreSQL username |
| `POSTGRE_PASSWORD` | PostgreSQL password |
