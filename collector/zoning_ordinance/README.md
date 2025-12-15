# Zoning Ordinance Data Collectors

This directory contains automated web scrapers for collecting zoning ordinance data from multiple cities.

## Available Cities

### Boston
- **Source:** https://library.municode.com/ma/boston/codes/redevelopment_authority
- **Format:** Excel (.xlsx) files for each zoning article
- **File Count:** ~140 articles
- **Runtime:** ~10 minutes
- **Collector:** `boston.py` → `BostonCollector`

### Chicago
- **Source:** https://codelibrary.amlegal.com/codes/chicago/latest/overview
- **Format:** Single PDF file
- **Runtime:** ~10 minutes (includes server file preparation)
- **Collector:** `chicago.py` → `ChicagoZoningCollector`

## Usage

### Basic Usage

From the `/data` directory:

```bash
# Collect Boston zoning data
python collector/zoning_ordinance/run.py --city boston --headless true

# Collect Chicago zoning data
python collector/zoning_ordinance/run.py --city chicago --headless true
```

### Options

- `--city`: Which city to collect data for (required: `boston` or `chicago`)
- `--headless`: Run browser in headless mode (default: `true`)
- `--download_dir`: Custom download directory (optional)

### Examples

```bash
# Run with visible browser window
python collector/zoning_ordinance/run.py --city boston --headless false

# Run with custom download directory
python collector/zoning_ordinance/run.py --city chicago --download_dir /path/to/output

# Interactive mode (will prompt for options)
python collector/zoning_ordinance/run.py
```

## Output

Downloaded files are saved to:
- Boston: `data/downloads/zoning_ordinance/boston/`
- Chicago: `data/downloads/zoning_ordinance/chicago/`


## Files

- `base.py`: Base class for zoning ordinance collectors
- `boston.py`: Boston zoning code collector implementation
- `chicago.py`: Chicago municipal code collector implementation
- `run.py`: CLI entry point for running either collector
- `__init__.py`: Module exports
- `README.md`: This file


## Technical Details

Both collectors:
- Extend `BaseCollector` abstract class
- Use Selenium WebDriver with Chrome
- Support both headless and visible browser modes
- Include download completion detection
- Validate downloaded files

### Boston Collector

- Downloads individual Excel files for each zoning article
- Excludes certain sections (maps, comparative tables, etc.)
- Handles Angular-based dynamic content rendering
- Optimized for performance (O(n) complexity)

### Chicago Collector

- Multi-step modal interaction workflow
- Waits for server-side PDF generation
- Handles format selection (PDF/Word/etc.)
- Clicks "OPEN" button after file preparation

## Adding New Cities

To add a new city collector:

1. Create `{city}.py` with a collector class extending `BaseCollector`
2. Implement `collect()` and `validate()` methods
3. Update `__init__.py` to export the new collector
4. Update `run.py` to handle the new city option
5. Update this README with the new city details


## Requirements

See `/data/pyproject.toml` for full dependencies


