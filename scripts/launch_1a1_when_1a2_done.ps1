$ErrorActionPreference = "Continue"
Write-Host "1A.1 watcher started — waiting for 1A.2 eval to finish (results/finetune_eval_pretrained_hardset_e20/summary.txt)..."
while (-not (Test-Path "results/finetune_eval_pretrained_hardset_e20/summary.txt")) {
    Start-Sleep -Seconds 60
}
Write-Host ""
Write-Host "1A.2 done — launching 1A.1 chain (fair-LR scratch baseline)..."
& .\scripts\run_1a1_chain.ps1 2>&1 | Tee-Object -FilePath logs/1a1_chain.log
