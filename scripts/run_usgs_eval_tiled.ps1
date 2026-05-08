# =========================================================================
#  Run USGS AI4CMA tiled evaluation on Windows (PowerShell)
#  Usage: .\run_usgs_eval_tiled.ps1 [-Device cuda] [-MaxMaps 0]
# =========================================================================

param(
    [string]$Device = "cuda",
    [int]$MaxMaps = 0,
    [int]$BatchSize = 16,
    [switch]$NoTile,
    [switch]$NoViz
)

# --- Configuration -------------------------------------------------------
$Checkpoint = "checkpoints\zone_seg_loam_vanilla_v2\best.pt"
$UsgsDir    = "usgs"
$Dataset    = "validation"
$WorkDir    = "$env:TEMP\usgs_eval"
$OutputDir  = $(if ($NoTile) { "results\usgs_eval_vanilla_v2_notile" } else { "results\usgs_eval_vanilla_v2_tiled" })
$TileSize   = 512
$TileOverlap = 128
$Threshold  = 0.5
$ModelType  = "vanilla"

# --- Banner ---------------------------------------------------------------
Write-Host "=========================================================================" -ForegroundColor Cyan
Write-Host "  USGS AI4CMA Evaluation" -ForegroundColor Cyan
Write-Host "=========================================================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "  Checkpoint:  $Checkpoint"
Write-Host "  USGS data:   $UsgsDir"
Write-Host "  Dataset:     $Dataset"
Write-Host "  Device:      $Device"
Write-Host "  Tile mode:   $(if ($NoTile) { 'whole-map (fast, lower quality)' } else { "tiled ${TileSize}x${TileSize}, overlap $TileOverlap, batch $BatchSize" })"
Write-Host "  Model type:  $ModelType"
Write-Host "  Max maps:    $(if ($MaxMaps -eq 0) { 'all' } else { $MaxMaps })"
Write-Host "  Output dir:  $OutputDir"
Write-Host ""

# --- Checks ---------------------------------------------------------------
if (-not (Test-Path $Checkpoint)) {
    Write-Host "ERROR: Checkpoint not found at $Checkpoint" -ForegroundColor Red
    exit 1
}
if (-not (Test-Path $UsgsDir)) {
    Write-Host "ERROR: USGS data directory not found at $UsgsDir" -ForegroundColor Red
    exit 1
}
if (-not (Test-Path "$UsgsDir\validation.tar.gz")) {
    Write-Host "ERROR: validation.tar.gz not found in $UsgsDir" -ForegroundColor Red
    exit 1
}

# Create output directory
New-Item -ItemType Directory -Path $OutputDir -Force | Out-Null

# --- Build command ---------------------------------------------------------
$pyArgs = @(
    "-m", "model.zone_segmentation.scripts.eval_usgs",
    "--checkpoint", $Checkpoint,
    "--usgs-dir", $UsgsDir,
    "--dataset", $Dataset,
    "--work-dir", $WorkDir,
    "--output-dir", $OutputDir,
    "--tile-size", $TileSize,
    "--tile-overlap", $TileOverlap,
    "--threshold", $Threshold,
    "--device", $Device,
    "--model-type", $ModelType,
    "--skip-no-gt"
)

if ($NoTile) {
    $pyArgs += "--no-tile"
}
if (-not $NoViz) {
    $pyArgs += "--save-viz"
}
if ($MaxMaps -gt 0) {
    $pyArgs += @("--max-maps", $MaxMaps)
}

# --- Run -------------------------------------------------------------------
Write-Host "Starting evaluation..." -ForegroundColor Green
if (-not $NoTile) {
    Write-Host "NOTE: Tiled evaluation is slow (~1 min/feature on GPU, ~18 hours total)." -ForegroundColor Yellow
    Write-Host "      Use -NoTile for fast preliminary results." -ForegroundColor Yellow
    Write-Host "      Use -MaxMaps N to limit to first N maps." -ForegroundColor Yellow
}
Write-Host ""

$stopwatch = [System.Diagnostics.Stopwatch]::StartNew()

& python @pyArgs

$exitCode = $LASTEXITCODE
$stopwatch.Stop()
$elapsed = $stopwatch.Elapsed

Write-Host ""
if ($exitCode -eq 0) {
    Write-Host "=========================================================================" -ForegroundColor Green
    Write-Host "  Evaluation complete! (elapsed: $($elapsed.ToString('hh\:mm\:ss')))" -ForegroundColor Green
    Write-Host "  Results: $OutputDir\results.json" -ForegroundColor Green
    Write-Host "  Summary: $OutputDir\summary.txt" -ForegroundColor Green
    if (-not $NoViz) {
        Write-Host "  Viz:     $OutputDir\viz\" -ForegroundColor Green
    }
    Write-Host "=========================================================================" -ForegroundColor Green
} else {
    Write-Host "ERROR: Evaluation failed (exit code $exitCode, elapsed: $($elapsed.ToString('hh\:mm\:ss')))" -ForegroundColor Red
    exit $exitCode
}
