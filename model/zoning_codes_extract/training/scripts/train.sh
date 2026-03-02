#!/bin/bash
# Unified training script - runs data preparation and training
#
# Usage:
#   ./training/scripts/train.sh --model extractor --states california texas --config local
#   ./training/scripts/train.sh --model validator --states all --config cloud
#   ./training/scripts/train.sh --model both --states california --config local

set -e  # Exit on error

# Get project root (parent of training directory)
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

# Change to project root
cd "$PROJECT_ROOT"

# Default values
MODEL=""
STATES=""
CONFIG=""

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --model)
            MODEL="$2"
            shift 2
            ;;
        --states)
            shift
            # Collect all state arguments until next flag
            while [[ $# -gt 0 ]] && [[ ! $1 =~ ^-- ]]; do
                if [ -z "$STATES" ]; then
                    STATES="$1"
                else
                    STATES="$STATES $1"
                fi
                shift
            done
            ;;
        --config)
            CONFIG="$2"
            shift 2
            ;;
        *)
            echo "Unknown option: $1"
            exit 1
            ;;
    esac
done

# Validate required arguments
if [ -z "$MODEL" ] || [ -z "$STATES" ] || [ -z "$CONFIG" ]; then
    echo "Error: Missing required arguments"
    echo ""
    echo "Usage: $0 --model <extractor|validator|both> --states <states|all> --config <local|cloud>"
    echo ""
    echo "Examples:"
    echo "  $0 --model extractor --states california texas --config local"
    echo "  $0 --model validator --states all --config cloud"
    echo "  $0 --model both --states california --config local"
    exit 1
fi

# Validate model
if [[ ! "$MODEL" =~ ^(extractor|validator|both)$ ]]; then
    echo "Error: --model must be 'extractor', 'validator', or 'both'"
    exit 1
fi

# Validate config
if [[ ! "$CONFIG" =~ ^(local|cloud)$ ]]; then
    echo "Error: --config must be 'local' or 'cloud'"
    exit 1
fi

# Build config file path
CONFIG_FILE="training/.env.training.$CONFIG"

# Build states argument for Python CLI
if [ "$STATES" = "all" ]; then
    STATES_ARG=""
else
    STATES_ARG="--states $STATES"
fi

echo "================================================================================"
echo "TRAINING PIPELINE"
echo "================================================================================"
echo "Model(s):  $MODEL"
echo "States:    $STATES"
echo "Config:    $CONFIG ($CONFIG_FILE)"
echo "================================================================================"
echo ""

# Function to run pipeline for a single model
run_model_pipeline() {
    local model_type=$1

    echo ""
    echo "================================================================================"
    echo "PIPELINE: $model_type"
    echo "================================================================================"

    # Step 1: Prepare data
    echo ""
    echo "Step 1/2: Preparing $model_type data..."
    python -m training.train prepare $model_type $STATES_ARG

    # Step 2: Train model
    echo ""
    echo "Step 2/2: Training $model_type model..."
    python -m training.train $model_type --config $CONFIG_FILE

    echo ""
    echo "✓ $model_type pipeline complete!"
}

# Run pipeline based on model selection
if [ "$MODEL" = "both" ]; then
    run_model_pipeline "extractor"
    run_model_pipeline "validator"

    echo ""
    echo "================================================================================"
    echo "✓ FULL PIPELINE COMPLETE (Extractor + Validator)"
    echo "================================================================================"
else
    run_model_pipeline "$MODEL"
fi
