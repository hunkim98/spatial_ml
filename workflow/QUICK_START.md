# Quick Start Guide

## Prerequisites

1. Set up environment variables (add to your `~/.bashrc` or `~/.zshrc`):

```bash
export GCP_PROJECT="your-gcp-project-id"
export GCP_REGION="us-central1"
export GCS_BUCKET_NAME="spatially-data"
export GCS_SERVICE_ACCOUNT="your-service-account@your-project.iam.gserviceaccount.com"
export GOOGLE_APPLICATION_CREDENTIALS="/path/to/service-account-key.json"
export GCS_PACKAGE_URI="gs://spatially-data/packages"  # Optional
```

2. Authenticate with GCP:

```bash
gcloud auth login
gcloud config set project $GCP_PROJECT
gcloud auth application-default login
```

## Step 1: Build and Push Docker Images

```bash
cd /Users/devraj/Documents/Development/spatial_ml/workflow

# Build and push all images
python registry/run.py --images all

# Or build specific images
python registry/run.py --images collector
python registry/run.py --images processor
```

This will:
- Create the `spatial-ml-workflows` repository in GCP Artifact Registry (if it doesn't exist)
- Build the collector image (with Selenium)
- Build the processor image (with MarkItDown)
- Push both images to GCP Artifact Registry

## Step 2: Test Single State (Rhode Island)

```bash
# Run pipeline for Rhode Island
python cli.py --pipeline municode-ordinance --state rhode-island
```

**Expected output:**
```
Running municode-ordinance for rhode-island...
Pipeline job submitted: projects/.../pipelineJobs/...
Submitted successfully! Job: spatial-ml-municode-ordinance-rhode-island-abc12345
```

**What happens:**
1. Scraper collects DOCX files from Municode for RI
2. Files saved to `gs://spatially-data/zoning_ordinance/rhode-island/*/`
3. Converter converts DOCX → Markdown
4. MD files saved to `gs://spatially-data/zoning_ordinance_markdown/rhode-island/*/`

**Duration:** ~30 minutes to 2 hours (depends on number of municipalities)

## Step 3: Monitor Pipeline

1. **Via GCP Console:**
   - Go to Vertex AI → Pipelines
   - Find your pipeline run
   - Monitor progress and logs

2. **Via CLI:**
   ```bash
   gcloud ai pipelines list --region=$GCP_REGION
   ```

## Step 4: Verify Results

```bash
# Check DOCX files were uploaded
gsutil ls gs://spatially-data/zoning_ordinance/rhode-island/

# Check Markdown files were created
gsutil ls gs://spatially-data/zoning_ordinance_markdown/rhode-island/

# Count files
echo "DOCX files:"
gsutil ls -r gs://spatially-data/zoning_ordinance/rhode-island/**/*.docx | wc -l

echo "Markdown files:"
gsutil ls -r gs://spatially-data/zoning_ordinance_markdown/rhode-island/**/*.md | wc -l

# Preview a Markdown file
gsutil cat gs://spatially-data/zoning_ordinance_markdown/rhode-island/[municipality]/[file].md | head -50
```

## Step 5: Test Multiple States

```bash
# Run for 3 states in parallel
python cli.py --pipeline municode-ordinance-parallel --states rhode-island,delaware,vermont
```

**Duration:** ~1-2 hours (limited by slowest state)

## Step 6: Production - All 50 States

⚠️ **WARNING:** This will process all 50 states in parallel. Make sure you have:
- Sufficient GCP quota
- Verified single-state test works correctly
- Budget alerts configured

```bash
# Run for ALL states (50 states + DC = 51 total)
python cli.py --pipeline municode-ordinance-parallel
```

**Duration:** ~2-4 hours total

**Cost estimate:** Variable based on:
- Vertex AI pipeline execution time
- GCS storage (GB-months)
- Network egress

## Troubleshooting

### Error: "Repository not found"

```bash
# Create the repository manually
gcloud artifacts repositories create spatial-ml-workflows \
  --repository-format=docker \
  --location=$GCP_REGION \
  --description="Docker images for Spatial ML workflows"
```

### Error: "Permission denied"

Check service account has these roles:
- `roles/aiplatform.user` - Vertex AI User
- `roles/storage.admin` - Storage Admin
- `roles/artifactregistry.writer` - Artifact Registry Writer

```bash
# Grant roles to service account
gcloud projects add-iam-policy-binding $GCP_PROJECT \
  --member="serviceAccount:$GCS_SERVICE_ACCOUNT" \
  --role="roles/aiplatform.user"

gcloud projects add-iam-policy-binding $GCP_PROJECT \
  --member="serviceAccount:$GCS_SERVICE_ACCOUNT" \
  --role="roles/storage.admin"

gcloud projects add-iam-policy-binding $GCP_PROJECT \
  --member="serviceAccount:$GCS_SERVICE_ACCOUNT" \
  --role="roles/artifactregistry.writer"
```

### Error: "Docker build failed"

Check:
1. Docker daemon is running: `docker ps`
2. Sufficient disk space: `df -h`
3. You're in the workflow directory

### Pipeline Fails Immediately

Check Vertex AI logs:
1. Go to GCP Console → Vertex AI → Pipelines
2. Click on the failed run
3. Check component logs for error messages

### No DOCX Files Collected

Possible causes:
1. Municode website structure changed
2. Rate limiting/blocking
3. State has no municipalities on Municode

Check collector logs in Vertex AI pipeline execution.

## Common Commands

```bash
# List all pipelines
python cli.py --help

# Check pipeline status
gcloud ai pipelines list --region=$GCP_REGION

# View logs for a specific pipeline run
gcloud ai pipelines describe PIPELINE_RUN_ID --region=$GCP_REGION

# Delete old pipeline runs
gcloud ai pipelines delete PIPELINE_RUN_ID --region=$GCP_REGION

# List images in Artifact Registry
gcloud artifacts docker images list \
  $GCP_REGION-docker.pkg.dev/$GCP_PROJECT/spatial-ml-workflows
```

## Tips

1. **Start Small**: Test with Rhode Island first (smallest state)
2. **Monitor Costs**: Set up budget alerts in GCP Console
3. **Check Logs**: Always check Vertex AI logs if pipeline fails
4. **Incremental Processing**: The converter skips already-processed files, so you can re-run safely
5. **Resource Limits**: Adjust CPU/memory in pipeline component definitions if needed

## Success Indicators

✅ Docker images successfully built and pushed
✅ Single-state pipeline completes without errors
✅ DOCX files appear in GCS
✅ Markdown files appear in GCS
✅ File counts match (DOCX count ≈ MD count)
✅ Markdown content is readable

## Next Steps After Testing

1. **Optimize Resource Allocation**: Adjust CPU/memory based on actual usage
2. **Add Monitoring**: Set up Cloud Monitoring alerts
3. **Cost Analysis**: Review actual costs and optimize
4. **Error Handling**: Add retry logic for transient failures
5. **Notifications**: Add Pub/Sub notifications for pipeline completion
