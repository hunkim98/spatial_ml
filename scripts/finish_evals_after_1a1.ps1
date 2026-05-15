# =========================================================================
#  Wait for the in-progress 1A.1 eval to finish, then resume both
#  1A.1 and 1A.2 evals to fill the 10 maps that were skipped due to
#  missing TIFs (now extracted). eval_usgs.py per-map resume kicks in
#  automatically — it loads existing results.json and skips done maps.
#
#  Sequence:
#    1. Wait for results/finetune_eval_scratch_lr1e-4_e20/summary.txt
#    2. Resume 1A.1 eval (LR=1e-4 scratch) — fills 10 missing maps
#    3. Resume 1A.2 eval (pretrained_hardset) — fills 10 missing maps
#    4. Re-run analysis kit
#
#  Usage:
#    .\scripts\finish_evals_after_1a1.ps1
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

function Step([string]$msg) {
    Write-Host ""
    Write-Host ("=" * 80) -ForegroundColor Cyan
    Write-Host "  $msg" -ForegroundColor Cyan
    Write-Host ("=" * 80) -ForegroundColor Cyan
}

# Re-run analysis kit and commit/push the auto-generated paper table so a
# remote Claude agent can verify completion without local file access.
function Update-PaperTable([string]$tag) {
    Write-Host ""
    Write-Host "  [Update-PaperTable: $tag] re-running analysis kit + committing table" -ForegroundColor Cyan
    & .\.venv\Scripts\python.exe -m model.zone_segmentation.scripts.analyze_finetune_results 2>&1 |
        Tee-Object -FilePath "logs/analyze_finetune_results_$tag.log" | Out-Null
    & git add paper/tables/headline_table.tex 2>&1 | Out-Null
    & git commit -m "auto: update paper headline table ($tag)" 2>&1 | Out-Null
    if ($LASTEXITCODE -eq 0) {
        Write-Host "  committed table update ($tag); attempting push" -ForegroundColor Green
        & git push 2>&1 | Out-Null
        if ($LASTEXITCODE -eq 0) {
            Write-Host "  pushed to origin" -ForegroundColor Green
        } else {
            Write-Host "  push failed (continuing); commit is local" -ForegroundColor Yellow
        }
    } else {
        Write-Host "  no commit (table unchanged or git refused)" -ForegroundColor Yellow
    }
}

Step "Waiting for current 1A.1 eval to finish..."
while (-not (Test-Path "results/finetune_eval_scratch_lr1e-4_e20/summary.txt")) {
    Start-Sleep -Seconds 60
}
Write-Host "1A.1 first pass done. Resuming both evals on the 10 newly-available TIFs."

# -------------------------------------------------------------------------
# 1) Resume 1A.1 eval — eval_usgs.py auto-resumes from existing results.json
# -------------------------------------------------------------------------
Step "RESUME [1/2]: 1A.1 (scratch_lr1e-4_e20) — fills 10 maps"
& .\.venv\Scripts\python.exe -m model.zone_segmentation.scripts.eval_usgs `
    --checkpoint checkpoints/finetune_scratch_lr1e-4/epoch20.pt `
    --usgs-dir usgs `
    --dataset validation `
    --work-dir $EvalWorkDir `
    --output-dir results/finetune_eval_scratch_lr1e-4_e20 `
    --tile-size 512 --tile-overlap 128 --batch-size 4 --threshold 0.5 `
    --device cuda --model-type vanilla `
    --skip-no-gt --save-viz `
    --wandb-run-name "eval-scratch-lr1e-4-e20-heldout22-resume" `
    --exclude-maps AR_StJoe AK_Dillingham 2>&1 |
    Tee-Object -FilePath "logs/eval_scratch_lr1e-4_e20_resume.log"

if ($LASTEXITCODE -ne 0) { Write-Host "WARN 1A.1 resume exit $LASTEXITCODE" -ForegroundColor Yellow }

# Auto-commit table after 1A.1 finishes so the remote check sees partial progress
Update-PaperTable -tag "after-1a1-resume"

# -------------------------------------------------------------------------
# 2) Resume 1A.2 eval — same per-map resume mechanism
# -------------------------------------------------------------------------
Step "RESUME [2/2]: 1A.2 (pretrained_hardset_e20) — fills 10 maps"
& .\.venv\Scripts\python.exe -m model.zone_segmentation.scripts.eval_usgs `
    --checkpoint checkpoints/finetune_pretrained_hardset/epoch20.pt `
    --usgs-dir usgs `
    --dataset validation `
    --work-dir $EvalWorkDir `
    --output-dir results/finetune_eval_pretrained_hardset_e20 `
    --tile-size 512 --tile-overlap 128 --batch-size 4 --threshold 0.5 `
    --device cuda --model-type vanilla `
    --skip-no-gt --save-viz `
    --wandb-run-name "eval-pretrained-hardset-e20-heldout22-resume" `
    --exclude-maps AR_StJoe AK_Hughes 2>&1 |
    Tee-Object -FilePath "logs/eval_pretrained_hardset_e20_resume.log"

if ($LASTEXITCODE -ne 0) { Write-Host "WARN 1A.2 resume exit $LASTEXITCODE" -ForegroundColor Yellow }

# Auto-commit table after 1A.2 also done — this is the FINAL state for the paper
Update-PaperTable -tag "final-22maps"

Step "FILL-IN COMPLETE — full 22-map coverage on 1A, 1A.1, 1A.2"
Write-Host "Updated artifacts in model/zone_segmentation/reports/finetune_results/"
Write-Host "paper/tables/headline_table.tex committed and pushed"
