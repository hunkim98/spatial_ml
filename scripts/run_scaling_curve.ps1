# =========================================================================
#  Plan 2 — Annotation-efficiency scaling curve (TODO 1A.3 partial)
#
#  Runs N=1 and N=5 pretrained fine-tunes + evals on the remaining held-out
#  maps. Combined with the existing N=2 (1A) and N=0 (zero-shot) data, this
#  gives 4 points on an "F1 vs # fine-tune maps" curve for the paper.
#
#  Map selections (stratified by mean delta-E from failure analysis):
#    N=1  → AR_StJoe (mean ΔE 10.8, easy)
#    N=2  → AR_StJoe + AK_Dillingham (already done as 1A)
#    N=5  → AR_StJoe + AK_Dillingham + AK_Hughes + CA_Elsinore + AZ_GrandCanyon
#           (covers easy/typical/hard regimes)
#    N=10 → N=5 set + CA_MarbleCanyon + AZ_PipeSpring + NV_HiddenHills
#           + NM_Sunshine + OR_Camas
#           (close to LOAM's 14-map training setup — comparable scale)
#
#  Estimated compute: ~42h sequential on RTX 3060
#    N=1  fine-tune ~2.5h + eval (~13h on 23 maps) = ~15.5h
#    N=5  fine-tune ~2.5h + eval (~12h on 19 maps) = ~14.5h
#    N=10 fine-tune ~2.5h + eval (~9h  on 14 maps) = ~11.5h
#
#  Idempotent. Skips any step whose output already exists.
#  Safe to re-launch after interruption.
#
#  Usage:
#    .\scripts\run_scaling_curve.ps1
# =========================================================================

# Load WANDB_API_KEY
$envFile = "secrets/teampspatially-project.env"
if (Test-Path $envFile) {
    Get-Content $envFile | ForEach-Object {
        if ($_ -match '^\s*([^#=][^=]*?)\s*=\s*(.+?)\s*$') {
            [Environment]::SetEnvironmentVariable($matches[1], $matches[2], 'Process')
        }
    }
    if ($env:WANDB_API_KEY) { Write-Host "Loaded WANDB_API_KEY" -ForegroundColor Green }
}

$EvalWorkDir = "$env:TEMP/usgs_eval"

# Map sets stratified by failure-analysis delta-E
$MAPS_N1  = @("AR_StJoe")
$MAPS_N5  = @("AR_StJoe", "AK_Dillingham", "AK_Hughes", "CA_Elsinore", "AZ_GrandCanyon")
$MAPS_N10 = @("AR_StJoe", "AK_Dillingham", "AK_Hughes", "CA_Elsinore", "AZ_GrandCanyon",
              "CA_MarbleCanyon", "AZ_PipeSpring", "NV_HiddenHills", "NM_Sunshine", "OR_Camas")

function Step([string]$msg) {
    Write-Host ""
    Write-Host ("=" * 80) -ForegroundColor Cyan
    Write-Host "  $msg" -ForegroundColor Cyan
    Write-Host ("=" * 80) -ForegroundColor Cyan
}

# Helper: commit + push artifacts so remote agents / future sessions see state
function Commit-Push([string]$tag, [string]$msg) {
    & .\.venv\Scripts\python.exe -m model.zone_segmentation.scripts.analyze_finetune_results 2>&1 |
        Tee-Object -FilePath "logs/analyze_$tag.log" | Out-Null
    # Also build/refresh the scaling-curve figure if the script exists
    if (Test-Path scripts/build_scaling_figure.py) {
        & .\.venv\Scripts\python.exe scripts/build_scaling_figure.py 2>&1 |
            Tee-Object -FilePath "logs/scaling_figure_$tag.log" | Out-Null
    }
    & git add paper/tables/headline_table.tex paper/figures/scaling_curve.png `
              model/zone_segmentation/reports/finetune_results/ 2>&1 | Out-Null
    & git commit -m "auto: $msg ($tag)" 2>&1 | Out-Null
    if ($LASTEXITCODE -eq 0) {
        & git push 2>&1 | Out-Null
        Write-Host "  committed + pushed ($tag)" -ForegroundColor Green
    }
}

# -------------------------------------------------------------------------
# 1) N=1 fine-tune
# -------------------------------------------------------------------------
$N1Dir = "checkpoints/finetune_pretrained_N1"
if (Test-Path "$N1Dir/final.pt") {
    Step "SKIP N=1 fine-tune (already exists at $N1Dir/final.pt)"
} else {
    Step "STEP 1/4: pretrained fine-tune on N=1 map [$($MAPS_N1 -join ', ')]"
    .\.venv\Scripts\python.exe -m model.zone_segmentation.scripts.finetune_usgs `
        --pretrained checkpoints/zone_seg_loam_vanilla_v2/best.pt `
        --finetune-maps $MAPS_N1 `
        --epochs 20 --save-at-epochs 5 10 20 `
        --crops-per-feature 64 --batch-size 4 --num-workers 0 `
        --lr 1e-6 --freeze-encoder-epochs 3 `
        --save-dir $N1Dir 2>&1 | Tee-Object -FilePath "logs/finetune_pretrained_N1.log"
    if ($LASTEXITCODE -ne 0) {
        Write-Host "ERROR N=1 fine-tune exit $LASTEXITCODE" -ForegroundColor Red
        exit $LASTEXITCODE
    }
}

# -------------------------------------------------------------------------
# 2) N=1 eval (excludes AR_StJoe only — 23 maps with GT)
# -------------------------------------------------------------------------
$N1OutDir = "results/finetune_eval_pretrained_N1_e20"
if (Test-Path "$N1OutDir/summary.txt") {
    Step "SKIP N=1 eval (summary already exists at $N1OutDir)"
} else {
    Step "STEP 2/4: EVAL pretrained_N1_e20 on 23 held-out maps"
    New-Item -ItemType Directory -Force -Path $N1OutDir | Out-Null
    & .\.venv\Scripts\python.exe -m model.zone_segmentation.scripts.eval_usgs `
        --checkpoint "$N1Dir/epoch20.pt" `
        --usgs-dir usgs --dataset validation `
        --work-dir $EvalWorkDir --output-dir $N1OutDir `
        --tile-size 512 --tile-overlap 128 --batch-size 4 `
        --threshold 0.5 --device cuda --model-type vanilla `
        --skip-no-gt --save-viz `
        --wandb-run-name "eval-pretrained-N1-e20-heldout23" `
        --exclude-maps $MAPS_N1 2>&1 |
        Tee-Object -FilePath "logs/eval_pretrained_N1_e20.log"
    if ($LASTEXITCODE -ne 0) { Write-Host "WARN N=1 eval exit $LASTEXITCODE" -ForegroundColor Yellow }
    Commit-Push -tag "N1-done" -msg "scaling curve N=1 complete"
}

# -------------------------------------------------------------------------
# 3) N=5 fine-tune
# -------------------------------------------------------------------------
$N5Dir = "checkpoints/finetune_pretrained_N5"
if (Test-Path "$N5Dir/final.pt") {
    Step "SKIP N=5 fine-tune (already exists at $N5Dir/final.pt)"
} else {
    Step "STEP 3/4: pretrained fine-tune on N=5 maps [$($MAPS_N5 -join ', ')]"
    .\.venv\Scripts\python.exe -m model.zone_segmentation.scripts.finetune_usgs `
        --pretrained checkpoints/zone_seg_loam_vanilla_v2/best.pt `
        --finetune-maps $MAPS_N5 `
        --epochs 20 --save-at-epochs 5 10 20 `
        --crops-per-feature 64 --batch-size 4 --num-workers 0 `
        --lr 1e-6 --freeze-encoder-epochs 3 `
        --save-dir $N5Dir 2>&1 | Tee-Object -FilePath "logs/finetune_pretrained_N5.log"
    if ($LASTEXITCODE -ne 0) {
        Write-Host "ERROR N=5 fine-tune exit $LASTEXITCODE" -ForegroundColor Red
        exit $LASTEXITCODE
    }
}

# -------------------------------------------------------------------------
# 4) N=5 eval (excludes 5 maps — 19 maps with GT)
# -------------------------------------------------------------------------
$N5OutDir = "results/finetune_eval_pretrained_N5_e20"
if (Test-Path "$N5OutDir/summary.txt") {
    Step "SKIP N=5 eval (summary already exists at $N5OutDir)"
} else {
    Step "STEP 4/4: EVAL pretrained_N5_e20 on 19 held-out maps"
    New-Item -ItemType Directory -Force -Path $N5OutDir | Out-Null
    & .\.venv\Scripts\python.exe -m model.zone_segmentation.scripts.eval_usgs `
        --checkpoint "$N5Dir/epoch20.pt" `
        --usgs-dir usgs --dataset validation `
        --work-dir $EvalWorkDir --output-dir $N5OutDir `
        --tile-size 512 --tile-overlap 128 --batch-size 4 `
        --threshold 0.5 --device cuda --model-type vanilla `
        --skip-no-gt --save-viz `
        --wandb-run-name "eval-pretrained-N5-e20-heldout19" `
        --exclude-maps $MAPS_N5 2>&1 |
        Tee-Object -FilePath "logs/eval_pretrained_N5_e20.log"
    if ($LASTEXITCODE -ne 0) { Write-Host "WARN N=5 eval exit $LASTEXITCODE" -ForegroundColor Yellow }
    Commit-Push -tag "N5-done" -msg "scaling curve N=5 complete — full curve N=0,1,2,5"
}

# -------------------------------------------------------------------------
# 5) N=10 fine-tune
# -------------------------------------------------------------------------
$N10Dir = "checkpoints/finetune_pretrained_N10"
if (Test-Path "$N10Dir/final.pt") {
    Step "SKIP N=10 fine-tune (already exists at $N10Dir/final.pt)"
} else {
    Step "STEP 5/6: pretrained fine-tune on N=10 maps"
    .\.venv\Scripts\python.exe -m model.zone_segmentation.scripts.finetune_usgs `
        --pretrained checkpoints/zone_seg_loam_vanilla_v2/best.pt `
        --finetune-maps $MAPS_N10 `
        --epochs 20 --save-at-epochs 5 10 20 `
        --crops-per-feature 64 --batch-size 4 --num-workers 0 `
        --lr 1e-6 --freeze-encoder-epochs 3 `
        --save-dir $N10Dir 2>&1 | Tee-Object -FilePath "logs/finetune_pretrained_N10.log"
    if ($LASTEXITCODE -ne 0) {
        Write-Host "ERROR N=10 fine-tune exit $LASTEXITCODE" -ForegroundColor Red
        exit $LASTEXITCODE
    }
}

# -------------------------------------------------------------------------
# 6) N=10 eval (excludes 10 maps — 14 maps with GT, comparable to LOAM scale)
# -------------------------------------------------------------------------
$N10OutDir = "results/finetune_eval_pretrained_N10_e20"
if (Test-Path "$N10OutDir/summary.txt") {
    Step "SKIP N=10 eval (summary already exists at $N10OutDir)"
} else {
    Step "STEP 6/6: EVAL pretrained_N10_e20 on 14 held-out maps"
    New-Item -ItemType Directory -Force -Path $N10OutDir | Out-Null
    & .\.venv\Scripts\python.exe -m model.zone_segmentation.scripts.eval_usgs `
        --checkpoint "$N10Dir/epoch20.pt" `
        --usgs-dir usgs --dataset validation `
        --work-dir $EvalWorkDir --output-dir $N10OutDir `
        --tile-size 512 --tile-overlap 128 --batch-size 4 `
        --threshold 0.5 --device cuda --model-type vanilla `
        --skip-no-gt --save-viz `
        --wandb-run-name "eval-pretrained-N10-e20-heldout14" `
        --exclude-maps $MAPS_N10 2>&1 |
        Tee-Object -FilePath "logs/eval_pretrained_N10_e20.log"
    if ($LASTEXITCODE -ne 0) { Write-Host "WARN N=10 eval exit $LASTEXITCODE" -ForegroundColor Yellow }
    Commit-Push -tag "N10-done" -msg "scaling curve N=10 complete — full curve N=0,1,2,5,10"
}

Step "SCALING CURVE COMPLETE — 5 data points (N=0, 1, 2, 5, 10)"
Write-Host "  N=0  (zero-shot):     results/usgs_eval_vanilla_v2_tiled/"
Write-Host "  N=1  AR_StJoe:        results/finetune_eval_pretrained_N1_e20/"
Write-Host "  N=2  (original 1A):   results/finetune_eval_pretrained_e20/"
Write-Host "  N=5  (stratified):    results/finetune_eval_pretrained_N5_e20/"
Write-Host "  N=10 (LOAM-scale):    results/finetune_eval_pretrained_N10_e20/"
Write-Host ""
Write-Host "Next: review paper/figures/scaling_curve.png and patch the paper text."
