#!/bin/bash
#
# Launch GCP VM Training for Zoning Code Extraction
#
# This script creates a GCP VM, runs training on it, and automatically shuts down
# the VM when training completes. Models are uploaded to GCS automatically.
#
# Usage:
#   bash launch_gcp_training.sh --states california texas --n-cities 50
#   bash launch_gcp_training.sh --all-states
#

set -e  # Exit on error

# ============================================================================
# Configuration
# ============================================================================

PROJECT_ID="${GCP_PROJECT:-teamspatially}"
ZONE="${GCP_ZONE:-us-central1-a}"
MACHINE_TYPE="${GCP_MACHINE_TYPE:-n1-highmem-8}"
BOOT_DISK_SIZE="${GCP_BOOT_DISK_SIZE:-100GB}"
IMAGE_FAMILY="pytorch-latest-cpu"
IMAGE_PROJECT="deeplearning-platform-release"

# Generate unique instance name with timestamp
TIMESTAMP=$(date +%Y%m%d-%H%M%S)
INSTANCE_NAME="zoning-training-${TIMESTAMP}"

# Default training parameters
STATES=""
N_CITIES=""
ALL_STATES=false

# ============================================================================
# Parse Command Line Arguments
# ============================================================================

while [[ $# -gt 0 ]]; do
    case $1 in
        --states)
            shift
            # Collect all state names until next flag
            while [[ $# -gt 0 ]] && [[ ! $1 =~ ^-- ]]; do
                STATES="$STATES $1"
                shift
            done
            ;;
        --n-cities)
            N_CITIES="$2"
            shift 2
            ;;
        --all-states)
            ALL_STATES=true
            shift
            ;;
        --project)
            PROJECT_ID="$2"
            shift 2
            ;;
        --zone)
            ZONE="$2"
            shift 2
            ;;
        --machine-type)
            MACHINE_TYPE="$2"
            shift 2
            ;;
        --preemptible)
            PREEMPTIBLE="--preemptible"
            shift
            ;;
        -h|--help)
            echo "Launch GCP VM Training for Zoning Code Extraction"
            echo ""
            echo "Usage:"
            echo "  bash launch_gcp_training.sh [OPTIONS]"
            echo ""
            echo "Options:"
            echo "  --states <states...>    List of states to train on (e.g., california texas)"
            echo "  --n-cities <num>        Number of cities per state (optional)"
            echo "  --all-states            Train on all US states"
            echo "  --project <id>          GCP project ID (default: teamspatially)"
            echo "  --zone <zone>           GCP zone (default: us-central1-a)"
            echo "  --machine-type <type>   VM machine type (default: n1-highmem-8)"
            echo "  --preemptible           Use preemptible VM (70% cost savings)"
            echo "  -h, --help              Show this help message"
            echo ""
            echo "Examples:"
            echo "  # Train on California and Texas with 50 cities each"
            echo "  bash launch_gcp_training.sh --states california texas --n-cities 50"
            echo ""
            echo "  # Train on all US states"
            echo "  bash launch_gcp_training.sh --all-states"
            echo ""
            echo "  # Use preemptible VM for cost savings"
            echo "  bash launch_gcp_training.sh --states california --preemptible"
            exit 0
            ;;
        *)
            echo "Unknown option: $1"
            echo "Run with --help for usage information"
            exit 1
            ;;
    esac
done

# ============================================================================
# Validate Arguments
# ============================================================================

if [ "$ALL_STATES" = false ] && [ -z "$STATES" ]; then
    echo "Error: Must specify either --states or --all-states"
    echo "Run with --help for usage information"
    exit 1
fi

# ============================================================================
# Prepare Startup Script
# ============================================================================

echo "=========================================="
echo "Launching GCP Training VM"
echo "=========================================="
echo "Instance name: $INSTANCE_NAME"
echo "Machine type:  $MACHINE_TYPE"
echo "Zone:          $ZONE"
echo "Project:       $PROJECT_ID"
if [ -n "$PREEMPTIBLE" ]; then
    echo "Preemptible:   Yes (70% cost savings)"
fi
echo "=========================================="

# Read startup script
STARTUP_SCRIPT_PATH="$(dirname "$0")/gcp_vm_startup.sh"
if [ ! -f "$STARTUP_SCRIPT_PATH" ]; then
    echo "Error: Startup script not found: $STARTUP_SCRIPT_PATH"
    exit 1
fi

# Create training command
TRAINING_CMD="cd /home/\$USER/spatial_ml/model/zoning_codes_extract/training && "

if [ "$ALL_STATES" = true ]; then
    TRAINING_CMD+="bash scripts/run_pipeline.sh --all-states"
else
    TRAINING_CMD+="bash scripts/run_pipeline.sh --states $STATES"
    if [ -n "$N_CITIES" ]; then
        TRAINING_CMD+=" --n-cities $N_CITIES"
    fi
fi

# Add auto-shutdown after training
TRAINING_CMD+=" && echo 'Training complete! Shutting down VM...' && sudo shutdown -h now"

# ============================================================================
# Prepare GCP Credentials and Environment
# ============================================================================

SECRETS_DIR="$(dirname "$0")/../../../../secrets"
CREDENTIALS_FILE="$SECRETS_DIR/teamspatially-storage-accessor-keys.json"
ENV_FILE="$SECRETS_DIR/teamspatially-project.env"

# Read credentials if they exist
if [ -f "$CREDENTIALS_FILE" ]; then
    CREDENTIALS_CONTENT=$(cat "$CREDENTIALS_FILE" | base64)
    echo "✓ Found GCP credentials"
else
    echo "⚠ Warning: GCP credentials not found at $CREDENTIALS_FILE"
    echo "  The VM will need manual credential configuration"
    CREDENTIALS_CONTENT=""
fi

# Read environment variables if they exist
if [ -f "$ENV_FILE" ]; then
    ENV_CONTENT=$(cat "$ENV_FILE")
    # Ensure UPLOAD_TO_GCS is enabled
    if ! echo "$ENV_CONTENT" | grep -q "UPLOAD_TO_GCS=1"; then
        ENV_CONTENT="${ENV_CONTENT}
UPLOAD_TO_GCS=1"
    fi
    echo "✓ Found environment configuration"
else
    # Create default env content
    ENV_CONTENT="GCP_PROJECT=$PROJECT_ID
GCS_DATA_BUCKET=spatially-data
GCS_MODEL_BUCKET=spatially-models
WANDB_PROJECT=zoning-code-extraction
WANDB_ENTITY=spatially
UPLOAD_TO_GCS=1"
    echo "✓ Using default environment configuration"
fi

# ============================================================================
# Create GCP VM Instance
# ============================================================================

echo ""
echo "Creating GCP VM instance..."

gcloud compute instances create "$INSTANCE_NAME" \
    --project="$PROJECT_ID" \
    --zone="$ZONE" \
    --machine-type="$MACHINE_TYPE" \
    --image-family="$IMAGE_FAMILY" \
    --image-project="$IMAGE_PROJECT" \
    --boot-disk-size="$BOOT_DISK_SIZE" \
    --boot-disk-type=pd-standard \
    --metadata-from-file=startup-script="$STARTUP_SCRIPT_PATH" \
    --metadata="env-vars=$ENV_CONTENT,training-command=$TRAINING_CMD" \
    --scopes=https://www.googleapis.com/auth/cloud-platform \
    $PREEMPTIBLE

echo "✓ VM instance created"

# ============================================================================
# Wait for Startup Script to Complete
# ============================================================================

echo ""
echo "Waiting for startup script to complete..."
echo "(This may take 2-3 minutes)"

sleep 30  # Give VM time to start

# Poll until startup script completes
MAX_WAIT=300  # 5 minutes
ELAPSED=0
while [ $ELAPSED -lt $MAX_WAIT ]; do
    # Check if startup script has finished
    STATUS=$(gcloud compute instances get-serial-port-output "$INSTANCE_NAME" \
        --project="$PROJECT_ID" \
        --zone="$ZONE" 2>/dev/null | grep "GCP VM Setup Complete" || echo "")

    if [ -n "$STATUS" ]; then
        echo "✓ Startup script completed"
        break
    fi

    sleep 10
    ELAPSED=$((ELAPSED + 10))
    echo "  Still waiting... (${ELAPSED}s)"
done

if [ $ELAPSED -ge $MAX_WAIT ]; then
    echo "⚠ Startup script taking longer than expected"
    echo "  You can monitor progress with:"
    echo "  gcloud compute ssh $INSTANCE_NAME --project=$PROJECT_ID --zone=$ZONE"
fi

# ============================================================================
# Start Training
# ============================================================================

echo ""
echo "Starting training on VM..."

gcloud compute ssh "$INSTANCE_NAME" \
    --project="$PROJECT_ID" \
    --zone="$ZONE" \
    --command="$TRAINING_CMD" || true

echo ""
echo "=========================================="
echo "Training Complete!"
echo "=========================================="
echo ""
echo "VM will shut down automatically in a few moments."
echo ""
echo "Trained models have been uploaded to:"
echo "  gs://spatially-models/models/"
echo ""
echo "To view training logs:"
echo "  gcloud compute instances get-serial-port-output $INSTANCE_NAME --project=$PROJECT_ID --zone=$ZONE"
echo ""
echo "To manually access the VM (if still running):"
echo "  gcloud compute ssh $INSTANCE_NAME --project=$PROJECT_ID --zone=$ZONE"
echo ""
echo "To delete the VM manually (if not auto-deleted):"
echo "  gcloud compute instances delete $INSTANCE_NAME --project=$PROJECT_ID --zone=$ZONE"
echo ""
