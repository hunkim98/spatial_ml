#!/bin/bash

# Load environment variables
set -a
source ../secrets/teamspatially-project.env
set +a

export GOOGLE_APPLICATION_CREDENTIALS="../secrets/teamspatially-storage-accessor-keys.json"

# Run whatever command was passed
"$@"
