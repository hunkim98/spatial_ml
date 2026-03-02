# Training Scripts

## Quick Start

### Single Unified Script: `train.sh`

**All training is done through ONE script with 3 required flags:**

```bash
./training/scripts/train.sh --model <MODEL> --states <STATES> --config <CONFIG>
```

### Flags

1. **`--model`** (required): Which model(s) to train
   - `extractor` - Train only the extractor model
   - `validator` - Train only the validator model
   - `both` - Train both models sequentially

2. **`--states`** (required): Which states to use for training
   - State names (space-separated): `california texas florida`
   - `all` - Use all available states (163 cities)

3. **`--config`** (required): Hardware configuration profile
   - `local` - Small batch size, subset of data (for laptop/CPU)
   - `cloud` - Large batch size, full dataset (for T4 GPU)

## Examples

### Local Development

```bash
# Train extractor on California only (local config)
./training/scripts/train.sh --model extractor --states california --config local

# Train both models on California and Texas (local config)
./training/scripts/train.sh --model both --states california texas --config local

# Train validator on all states (local config - will be slow!)
./training/scripts/train.sh --model validator --states all --config local
```

### Cloud Production

```bash
# Train extractor on all states with T4 GPU
./training/scripts/train.sh --model extractor --states all --config cloud

# Train both models on all states with T4 GPU
./training/scripts/train.sh --model both --states all --config cloud

# Train on specific states for testing
./training/scripts/train.sh --model both --states california florida --config cloud
```

## What the Script Does

For each model specified, the script runs a **complete 2-step pipeline**:

1. **Data Preparation**: Downloads data from GCS, prepares training/test splits
2. **Model Training**: Trains the model and uploads to GCS

## GCP Training

### Option 1: Launch New VM (Recommended)

```bash
# Launches a new GCP VM and starts training
./training/scripts/launch_gcp_training.sh
```

Then SSH to the VM and run:
```bash
./training/scripts/train.sh --model both --states all --config cloud
```

### Option 2: Existing VM

If you already have a VM running:

```bash
# SSH to VM
gcloud compute ssh training-vm --zone=us-central1-a

# Navigate to project
cd /path/to/spatial_ml/model/zoning_codes_extract

# Run training
./training/scripts/train.sh --model both --states all --config cloud
```

## Script Reference

| Script | Purpose | When to Use |
|--------|---------|-------------|
| **train.sh** | Unified training pipeline | All training (local or cloud) |
| launch_gcp_training.sh | Provision GCP VM | Setting up cloud training environment |
| gcp_vm_startup.sh | VM initialization | Auto-runs when VM starts (don't call directly) |

## Configuration Files

The `--config` flag loads different configuration profiles:

**Local** (`training/.env.training.local`):
- Batch size: 2
- Gradient accumulation: 8
- Effective batch: 16
- Cities: Based on states selected
- Precision: none (CPU/MPS safe)

**Cloud** (`training/.env.training.cloud`):
- Batch size: 8
- Gradient accumulation: 4
- Effective batch: 32
- Cities: Based on states selected
- Precision: fp16 (T4 GPU optimized)

## Common Workflows

### Quick Testing (5-10 minutes)
```bash
./training/scripts/train.sh --model extractor --states california --config local
```

### Development Iteration (1-2 hours)
```bash
./training/scripts/train.sh --model both --states california texas florida --config local
```

### Production Training (6-8 hours on T4)
```bash
# On GCP VM
./training/scripts/train.sh --model both --states all --config cloud
```

## Tips

- **Start local**: Test on 1-3 states locally before running full pipeline
- **Use cloud for production**: Full dataset (all states) is best on T4 GPU
- **States are downloaded once**: GCS data is cached, subsequent runs are faster
- **Models auto-upload**: Trained models automatically upload to `gs://spatially-models/`

## Troubleshooting

### "Error: Missing required arguments"
- All 3 flags are mandatory: `--model`, `--states`, `--config`

### "Error: --model must be 'extractor', 'validator', or 'both'"
- Check spelling of model name

### "Out of memory"
- Use `--config local` for local training
- Reduce number of states: `--states california` instead of `all`

### Wrong config file loaded
- Ensure you're using `local` or `cloud`, not a file path
- The script automatically builds the path: `training/.env.training.<config>`
