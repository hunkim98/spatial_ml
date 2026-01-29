#!/bin/bash
# Updates the DVC manifest hash file after data changes.
# Run this after: dvc add data/
#
# Usage: ./scripts/update-manifest-hash.sh

set -e

DVC_FILE="data.dvc"

if [ ! -f "$DVC_FILE" ]; then
  echo "Error: $DVC_FILE not found"
  exit 1
fi

# Extract hash from data.dvc (format: "md5: aca543f303438b3df1f6e174c47af627.dir")
HASH=$(grep "md5:" "$DVC_FILE" | head -1 | sed 's/.*md5: //' | sed 's/\.dir$//')

if [ -z "$HASH" ]; then
  echo "Error: Could not extract hash from $DVC_FILE"
  exit 1
fi

# Update the hash file
HASH_FILE="frontend/dvc-manifest-hash.txt"
echo "$HASH" > "$HASH_FILE"

echo "Updated $HASH_FILE with hash: $HASH"
