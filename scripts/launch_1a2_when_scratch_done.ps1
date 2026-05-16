$ErrorActionPreference = "Continue"
Write-Host "1A.2 watcher started — waiting for scratch_e20 eval to finish (results/finetune_eval_scratch_e20/summary.txt)..."
while (-not (Test-Path "results/finetune_eval_scratch_e20/summary.txt")) {
    Start-Sleep -Seconds 60
}
Write-Host ""
Write-Host "scratch_e20 done — launching 1A.2 chain..."
& .\scripts\run_1a2_chain.ps1 2>&1 | Tee-Object -FilePath logs/1a2_chain.log
