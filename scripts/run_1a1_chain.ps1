# =========================================================================
#  TODO 1A.1 — Fairer scratch baseline at higher LR
#  Random init + fine-tune at LR=1e-4 (vs 1e-6 in original 1A) on the
#  SAME 2 fine-tune maps. Defuses the "you used the wrong LR for scratch"
#  reviewer critique. See paper/HARSH_CRITIQUE.md §A2 + paper/TODO.md 1A.1.
#
#  Idempotent: skips already-completed steps.
#
#  Usage:
#    .\scripts\run_1a1_chain.ps1
# =========================================================================

# Load WANDB_API_KEY from secrets file
$envFile = "secrets/teampspatially-project.env"
if (Test-Path $envFile) {
    Get-Content $envFile | ForEach-Object {
        if ($_ -match '^\s*([^#=][^=]*?)\s*=\s*(.+?)\s*$') {
            [Environment]::SetEnvironmentVariable($matches[1], $matches[2], 'Process')
        }
    }
    if ($env:WANDB_API_KEY) { Write-Host "Loaded WANDB_API_KEY (len=$($env:WANDB_API_KEY.Length))" -ForegroundColor Green }
}

$FinetuneMaps = @("AR_StJoe", "AK_Dillingham")
$EvalWorkDir  = "$env:TEMP/usgs_eval"

function Step-Banner([string]$msg) {
    Write-Host ""
    Write-Host ("=" * 80) -ForegroundColor Cyan
    Write-Host "  $msg" -ForegroundColor Cyan
    Write-Host ("=" * 80) -ForegroundColor Cyan
}

# -------------------------------------------------------------------------
# 1) Scratch fine-tune at LR=1e-4 with no encoder freeze
# -------------------------------------------------------------------------
$ScratchDir = "checkpoints/finetune_scratch_lr1e-4"
if (Test-Path "$ScratchDir/final.pt") {
    Step-Banner "SKIP: scratch_lr1e-4 fine-tune already exists at $ScratchDir/final.pt"
} else {
    Step-Banner "STEP 1/2: scratch fine-tune (random init, LR=1e-4, no freeze)"
    .\.venv\Scripts\python.exe -m model.zone_segmentation.scripts.finetune_usgs `
        --random-init `
        --finetune-maps $FinetuneMaps `
        --epochs 20 `
        --save-at-epochs 5 10 20 `
        --crops-per-feature 64 `
        --batch-size 4 `
        --num-workers 0 `
        --lr 1e-4 `
        --freeze-encoder-epochs 0 `
        --save-dir $ScratchDir 2>&1 | Tee-Object -FilePath "logs/finetune_scratch_lr1e-4.log"
    if ($LASTEXITCODE -ne 0) {
        Write-Host "ERROR: scratch_lr1e-4 fine-tune exited $LASTEXITCODE" -ForegroundColor Red
        exit $LASTEXITCODE
    }
}

# -------------------------------------------------------------------------
# 2) Eval on the same 22 held-out maps
# -------------------------------------------------------------------------
$ckpt = "$ScratchDir/epoch20.pt"
$outDir = "results/finetune_eval_scratch_lr1e-4_e20"

if (-not (Test-Path $ckpt)) {
    Write-Host "MISSING checkpoint: $ckpt — cannot eval" -ForegroundColor Red
    exit 1
}
if (Test-Path "$outDir/summary.txt") {
    Step-Banner "SKIP eval scratch_lr1e-4_e20 (summary already exists at $outDir)"
} else {
    Step-Banner "STEP 2/2: EVAL scratch_lr1e-4_e20 on 22 held-out maps"
    New-Item -ItemType Directory -Force -Path $outDir | Out-Null

    & .\.venv\Scripts\python.exe -m model.zone_segmentation.scripts.eval_usgs `
        --checkpoint $ckpt `
        --usgs-dir usgs `
        --dataset validation `
        --work-dir $EvalWorkDir `
        --output-dir $outDir `
        --tile-size 512 `
        --tile-overlap 128 `
        --batch-size 4 `
        --threshold 0.5 `
        --device cuda `
        --model-type vanilla `
        --skip-no-gt `
        --save-viz `
        --wandb-run-name "eval-scratch-lr1e-4-e20-heldout22" `
        --exclude-maps $FinetuneMaps 2>&1 |
        Tee-Object -FilePath "logs/eval_scratch_lr1e-4_e20.log"

    if ($LASTEXITCODE -ne 0) {
        Write-Host "WARN: eval scratch_lr1e-4_e20 exited $LASTEXITCODE" -ForegroundColor Yellow
    }
}

Step-Banner "1A.1 CHAIN COMPLETE — fairer scratch baseline"
Write-Host "Compare to original 1A scratch:"
Write-Host "  Original (LR=1e-6, freeze 3): results/finetune_eval_scratch_e20/results.json"
Write-Host "  Fairer (LR=1e-4, no freeze):   $outDir/results.json"
Write-Host ""
Write-Host "Re-run paper analysis to update the ratio:"
Write-Host "  python -m model.zone_segmentation.scripts.analyze_finetune_results --scratch $outDir/results.json"
