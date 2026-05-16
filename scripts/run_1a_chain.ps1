# =========================================================================
#  Run the rest of TODO 1A end-to-end after pretrained fine-tune finishes.
#  - scratch fine-tune (~2.5h)
#  - 6 evals (3 checkpoints x 2 init types) on the 22 held-out maps (~12h)
#
#  Idempotent: skips any step whose output already exists.
#  Eval scripts have built-in resume from results.json, so partial evals
#  pick up where they left off if the script is restarted.
#
#  Usage:
#    .\scripts\run_1a_chain.ps1
# =========================================================================

# NOTE: do NOT set $ErrorActionPreference = "Stop". Python tools (wandb, tqdm)
# write to stderr on success, which PowerShell mis-classifies as a fatal error
# under "Stop". We rely on $LASTEXITCODE checks after each invocation instead.

# Load secrets/*.env into the process environment (WANDB_API_KEY etc.)
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
# Eval ONLY the best checkpoint (epoch 20). Convergence story (e5/e10) is a
# nice-to-have we drop to fit the few-day deadline. Just 2 evals total:
# pretrained_e20 then scratch_e20 — the headline head-to-head comparison.
$Epochs = @(20)
$EvalWorkDir = "$env:TEMP/usgs_eval"

function Step-Banner([string]$msg) {
    Write-Host ""
    Write-Host ("=" * 80) -ForegroundColor Cyan
    Write-Host "  $msg" -ForegroundColor Cyan
    Write-Host ("=" * 80) -ForegroundColor Cyan
}

# -------------------------------------------------------------------------
# 1) Scratch fine-tune (skip if final.pt exists)
# -------------------------------------------------------------------------
$ScratchDir = "checkpoints/finetune_scratch"
if (Test-Path "$ScratchDir/final.pt") {
    Step-Banner "SKIP: scratch fine-tune (already exists at $ScratchDir/final.pt)"
} else {
    Step-Banner "STEP 1/2: scratch (random-init) fine-tune"
    .\.venv\Scripts\python.exe -m model.zone_segmentation.scripts.finetune_usgs `
        --random-init `
        --finetune-maps $FinetuneMaps `
        --epochs 20 `
        --save-at-epochs 5 10 20 `
        --crops-per-feature 64 `
        --batch-size 4 `
        --num-workers 0 `
        --lr 1e-6 `
        --freeze-encoder-epochs 3 `
        --save-dir $ScratchDir 2>&1 | Tee-Object -FilePath "logs/finetune_scratch.log"
    if ($LASTEXITCODE -ne 0) {
        Write-Host "ERROR: scratch fine-tune exited $LASTEXITCODE" -ForegroundColor Red
        exit $LASTEXITCODE
    }
}

# -------------------------------------------------------------------------
# 2) Six evals — 3 epochs x 2 init types — on the held-out 22 maps
# -------------------------------------------------------------------------
$Excluded = $FinetuneMaps -join " "

foreach ($epoch in $Epochs) {
    foreach ($init in @("pretrained", "scratch")) {
        $ckpt = "checkpoints/finetune_$init/epoch$epoch.pt"
        $outDir = "results/finetune_eval_${init}_e${epoch}"

        if (-not (Test-Path $ckpt)) {
            Write-Host "MISSING checkpoint: $ckpt — skipping eval" -ForegroundColor Yellow
            continue
        }
        if (Test-Path "$outDir/summary.txt") {
            Step-Banner "SKIP eval $init e$epoch (summary already exists at $outDir)"
            continue
        }

        Step-Banner "EVAL: $init init, epoch $epoch  →  $outDir"

        New-Item -ItemType Directory -Force -Path $outDir | Out-Null

        $wandbName = "eval-${init}-e${epoch}-heldout22"

        # Note: --model-type vanilla (matches train_loam_vanilla.py)
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
            --wandb-run-name $wandbName `
            --exclude-maps $FinetuneMaps 2>&1 |
            Tee-Object -FilePath "logs/eval_${init}_e${epoch}.log"

        if ($LASTEXITCODE -ne 0) {
            Write-Host "WARN: eval $init e$epoch exited $LASTEXITCODE — continuing" -ForegroundColor Yellow
        }
    }
}

Step-Banner "1A CHAIN COMPLETE"
Write-Host "Checkpoints: checkpoints/finetune_pretrained, checkpoints/finetune_scratch"
Write-Host "Eval outputs: results/finetune_eval_{pretrained,scratch}_e{5,10,20}/"
Write-Host "Logs: logs/finetune_*.log, logs/eval_*.log"
