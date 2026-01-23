#!/bin/bash
# Download Denver zoning PDFs

OUTPUT_DIR="/Users/hunkim/Github/spatial_ml/data/maps/CO/denver/images"
mkdir -p "$OUTPUT_DIR"
cd "$OUTPUT_DIR"

BASE_URL="https://www.denvergov.org/media/gis/WebDocs/CPD/Zoning/ZoningMaps"

# Try all direction/number combinations
for dir in NW NE SW SE; do
  for num in $(seq -f "%03g" 1 50); do
    url="${BASE_URL}/zoning_${dir}_${num}.pdf"
    code=$(curl -s -o /dev/null -w "%{http_code}" "$url")
    if [ "$code" = "200" ]; then
      curl -sL -o "zoning_${dir}_${num}.pdf" "$url"
      echo "Downloaded zoning_${dir}_${num}.pdf"
    fi
  done
done

echo "Done!"
