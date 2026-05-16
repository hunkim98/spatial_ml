# =========================================================================
#  TODO 1A.2 — Composition ablation
#  Re-run the fine-tune experiment with HARDER fine-tune set composition:
#    fine-tune maps = AR_StJoe (easy, ΔE 10.8) + AK_Hughes (hard, ΔE 2.5)
#  vs the original 1A which used AR_StJoe + AK_Dillingham.
#
#  Tests whether fine-tune-set composition matters as much as count: does
#  including a hard-color-confusion map during fine-tune improve held-out
#  performance on the OTHER hard maps (AZ_PrescottNF, DC_Frederick, etc.)?
#
#  Idempotent: skips already-completed steps. Safe to re-run.
#
#  Usage:
#    .\scripts\run_1a2_chain.ps1
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

$FinetuneMaps = @("AR_StJoe", "AK_Hughes")    # NEW: AK_Hughes instead of AK_Dillingham
$EvalWorkDir = "$env:TEMP/usgs_eval"

function Step-Banner([string]$msg) {
    Write-Host ""
    Write-Host ("=" * 80) -ForegroundColor Cyan
    Write-Host "  $msg" -ForegroundColor Cyan
    Write-Host ("=" * 80) -ForegroundColor Cyan
}

# -------------------------------------------------------------------------
# 1) Pretrained fine-tune on AR_StJoe + AK_Hughes (skip if already done)
# -------------------------------------------------------------------------
$PretrainedDir = "checkpoints/finetune_pretrained_hardset"
if (Test-Path "$PretrainedDir/final.pt") {
    Step-Banner "SKIP: pretrained_hardset fine-tune (already exists at $PretrainedDir/final.pt)"
} else {
    Step-Banner "STEP 1/2: pretrained fine-tune on AR_StJoe + AK_Hughes"
    .\.venv\Scripts\python.exe -m model.zone_segmentation.scripts.finetune_usgs `
        --pretrained checkpoints/zone_seg_loam_vanilla_v2/best.pt `
        --finetune-maps $FinetuneMaps `
        --epochs 20 `
        --save-at-epochs 5 10 20 `
        --crops-per-feature 64 `
        --batch-size 4 `
        --num-workers 0 `
        --lr 1e-6 `
        --freeze-encoder-epochs 3 `
        --save-dir $PretrainedDir 2>&1 | Tee-Object -FilePath "logs/finetune_pretrained_hardset.log"
    if ($LASTEXITCODE -ne 0) {
        Write-Host "ERROR: pretrained_hardset fine-tune exited $LASTEXITCODE" -ForegroundColor Red
        exit $LASTEXITCODE
    }
}

# -------------------------------------------------------------------------
# 2) Eval pretrained_hardset_e20 on the 22 maps NOT in this fine-tune set
#    (excludes AR_StJoe + AK_Hughes; AK_Dillingham IS now in the eval set)
# -------------------------------------------------------------------------
$ckpt = "$PretrainedDir/epoch20.pt"
$outDir = "results/finetune_eval_pretrained_hardset_e20"

if (-not (Test-Path $ckpt)) {
    Write-Host "MISSING checkpoint: $ckpt — cannot eval" -ForegroundColor Red
    exit 1
}
if (Test-Path "$outDir/summary.txt") {
    Step-Banner "SKIP eval pretrained_hardset_e20 (summary already exists at $outDir)"
} else {
    Step-Banner "STEP 2/2: EVAL pretrained_hardset_e20 on 22 held-out maps"
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
        --wandb-run-name "eval-pretrained-hardset-e20-heldout22" `
        --exclude-maps $FinetuneMaps 2>&1 |
        Tee-Object -FilePath "logs/eval_pretrained_hardset_e20.log"

    if ($LASTEXITCODE -ne 0) {
        Write-Host "WARN: eval pretrained_hardset_e20 exited $LASTEXITCODE" -ForegroundColor Yellow
    }
}

Step-Banner "1A.2 CHAIN COMPLETE"
Write-Host "Compare to original 1A:"
Write-Host "  Original 1A held-out: results/finetune_eval_pretrained_e20/results.json"
Write-Host "  Composition 1A.2:      $outDir/results.json"
Write-Host ""
Write-Host "Look at per-map F1 — does AK_Hughes-trained model do better on"
Write-Host "the other hard maps (AZ_PrescottNF, CO_Alamosa, DC_Frederick)?"
