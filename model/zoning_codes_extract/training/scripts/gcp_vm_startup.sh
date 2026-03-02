#!/bin/bash
#
# GCP VM Startup Script for Zoning Code Extraction Training
#
# This script initializes a GCP VM for training the zoning code extraction models.
# It installs dependencies, clones the repo, sets up credentials, and prepares
# the environment for training.
#
# Usage:
#   This script is automatically executed when the VM starts up.
#   It can also be run manually: bash gcp_vm_startup.sh
#

set -e  # Exit on error

echo "=========================================="
echo "GCP VM Startup - Zoning Code Extraction"
echo "=========================================="

# Update system packages
echo "Updating system packages..."
sudo apt-get update -qq
sudo apt-get install -y git python3-pip python3-venv

# Install Python dependencies
echo "Installing Python dependencies..."
pip3 install --upgrade pip setuptools wheel

# Install required packages
pip3 install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cpu
pip3 install transformers datasets seqeval scikit-learn pandas numpy
pip3 install wandb google-cloud-storage python-dotenv flask

# Create working directory
WORK_DIR="/home/$USER/spatial_ml"
echo "Setting up working directory: $WORK_DIR"

# Check if repo exists, clone if not
if [ ! -d "$WORK_DIR" ]; then
    echo "Cloning repository..."
    git clone https://github.com/yourusername/spatial_ml.git "$WORK_DIR"
else
    echo "Repository already exists, pulling latest changes..."
    cd "$WORK_DIR"
    git pull origin main
fi

cd "$WORK_DIR"

# Setup GCP credentials
echo "Setting up GCP credentials..."
SECRETS_DIR="$WORK_DIR/secrets"
mkdir -p "$SECRETS_DIR"

# Check if credentials are provided via metadata
CREDENTIALS_JSON=$(curl -s "http://metadata.google.internal/computeMetadata/v1/instance/attributes/gcp-credentials" -H "Metadata-Flavor: Google" 2>/dev/null || echo "")

if [ -n "$CREDENTIALS_JSON" ]; then
    echo "$CREDENTIALS_JSON" > "$SECRETS_DIR/teamspatially-storage-accessor-keys.json"
    echo "✓ GCP credentials configured from metadata"
else
    echo "⚠ No credentials found in metadata. Make sure to provide them manually."
fi

# Setup environment file
echo "Setting up environment file..."
ENV_FILE="$SECRETS_DIR/teamspatially-project.env"

# Check if env vars are provided via metadata
ENV_VARS=$(curl -s "http://metadata.google.internal/computeMetadata/v1/instance/attributes/env-vars" -H "Metadata-Flavor: Google" 2>/dev/null || echo "")

if [ -n "$ENV_VARS" ]; then
    echo "$ENV_VARS" > "$ENV_FILE"
    echo "✓ Environment variables configured from metadata"
else
    # Create default env file
    cat > "$ENV_FILE" <<EOF
# GCP Configuration
GCP_PROJECT=teamspatially
GCS_DATA_BUCKET=spatially-data
GCS_MODEL_BUCKET=spatially-models

# W&B Configuration
WANDB_PROJECT=zoning-code-extraction
WANDB_ENTITY=spatially

# Training Configuration
UPLOAD_TO_GCS=1
USE_GCS_MODELS=0
EOF
    echo "✓ Default environment file created"
fi

# Install training dependencies
echo "Installing training dependencies..."
cd "$WORK_DIR/model/zoning_codes_extract/training"

# Setup .env file for training
cp "$ENV_FILE" .env.training 2>/dev/null || true

echo ""
echo "=========================================="
echo "GCP VM Setup Complete!"
echo "=========================================="
echo ""
echo "Working directory: $WORK_DIR"
echo ""
echo "To start training, run:"
echo "  cd $WORK_DIR/model/zoning_codes_extract/training"
echo "  bash scripts/run_pipeline.sh --states california texas --n-cities 50"
echo ""
echo "Environment variables:"
echo "  UPLOAD_TO_GCS=1       (models will upload to GCS)"
echo "  GCS_MODEL_BUCKET=spatially-models"
echo ""
