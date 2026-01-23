#!/usr/bin/env python3
"""Extract Denver zoning map codes from GeoJSON and download PDFs."""

import json
import urllib.request
from pathlib import Path

# Read the GeoJSON file
geojson_path = Path("/Users/hunkim/Github/spatial_ml/data/maps/CO/denver/original/ODC_INDX_SRVQTRSECTION_A_-4335986555762631488.geojson")
output_dir = Path("/Users/hunkim/Github/spatial_ml/data/maps/CO/denver/images")
output_dir.mkdir(parents=True, exist_ok=True)

with open(geojson_path) as f:
    data = json.load(f)

# Extract unique QTRSEC_NUMBER values
qtrsec_numbers = set()
for feature in data['features']:
    props = feature['properties']
    if 'QTRSEC_NUMBER' in props and props['QTRSEC_NUMBER']:
        qtrsec_numbers.add(props['QTRSEC_NUMBER'])

print(f"Found {len(qtrsec_numbers)} unique QTRSEC_NUMBER values")
print("Sample values:", sorted(qtrsec_numbers)[:10])
print()

# Download PDFs
base_url = "https://www.denvergov.org/media/gis/WebDocs/CPD/Zoning/ZoningMaps"

for code in sorted(qtrsec_numbers):
    url = f"{base_url}/zoning_{code}.pdf"
    output_path = output_dir / f"zoning_{code}.pdf"

    if output_path.exists():
        print(f"Already exists: {output_path.name}")
        continue

    try:
        urllib.request.urlretrieve(url, output_path)
        print(f"Downloaded: {output_path.name}")
    except Exception as e:
        print(f"Failed {code}: {e}")

print("\nDone!")
