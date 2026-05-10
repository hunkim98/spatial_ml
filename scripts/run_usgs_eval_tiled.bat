@echo off
REM =========================================================================
REM  Run USGS AI4CMA tiled evaluation on Windows
REM  Usage: run_usgs_eval_tiled.bat [device] [max_maps]
REM    device:   cuda (default), cpu
REM    max_maps: 0 = all (default 2 for quick sanity check)
REM =========================================================================

setlocal

REM --- Configuration (edit these paths if needed) --------------------------
set CHECKPOINT=checkpoints\zone_seg_loam_vanilla_v2\best.pt
set USGS_DIR=usgs
set DATASET=validation
set WORK_DIR=%TEMP%\usgs_eval
set OUTPUT_DIR=results\usgs_eval_vanilla_v2_tiled
set TILE_SIZE=512
set TILE_OVERLAP=128
set BATCH_SIZE=4
set THRESHOLD=0.5
set MODEL_TYPE=vanilla

REM --- Device selection ----------------------------------------------------
set DEVICE=%1
if "%DEVICE%"=="" set DEVICE=cuda

REM --- Max maps (sanity-check default = 2; pass 0 for all) -----------------
set MAX_MAPS=%2
if "%MAX_MAPS%"=="" set MAX_MAPS=2

REM --- Check prerequisites -------------------------------------------------
echo =========================================================================
echo  USGS AI4CMA Tiled Evaluation
echo =========================================================================
echo.
echo  Checkpoint:  %CHECKPOINT%
echo  USGS data:   %USGS_DIR%
echo  Dataset:     %DATASET%
echo  Device:      %DEVICE%
echo  Tile size:   %TILE_SIZE% (overlap %TILE_OVERLAP%)
echo  Batch size:  %BATCH_SIZE%
echo  Max maps:    %MAX_MAPS% (0 = all)
echo  Model type:  %MODEL_TYPE%
echo  Output dir:  %OUTPUT_DIR%
echo  Work dir:    %WORK_DIR%
echo.

REM Check checkpoint exists
if not exist "%CHECKPOINT%" (
    echo ERROR: Checkpoint not found at %CHECKPOINT%
    echo Please ensure the checkpoint file exists.
    exit /b 1
)

REM Check USGS data directory exists
if not exist "%USGS_DIR%" (
    echo ERROR: USGS data directory not found at %USGS_DIR%
    exit /b 1
)

REM Check validation archive exists
if not exist "%USGS_DIR%\validation.tar.gz" (
    echo ERROR: validation.tar.gz not found in %USGS_DIR%
    exit /b 1
)

REM Create output directory
if not exist "%OUTPUT_DIR%" mkdir "%OUTPUT_DIR%"

echo Starting tiled evaluation...
echo This will take a long time (~18 hours for full validation set on GPU).
echo Results will be saved to %OUTPUT_DIR%
echo.
echo Press Ctrl+C to abort.
echo.

REM --- Run evaluation -------------------------------------------------------
python -m model.zone_segmentation.scripts.eval_usgs ^
    --checkpoint "%CHECKPOINT%" ^
    --usgs-dir "%USGS_DIR%" ^
    --dataset %DATASET% ^
    --work-dir "%WORK_DIR%" ^
    --output-dir "%OUTPUT_DIR%" ^
    --tile-size %TILE_SIZE% ^
    --tile-overlap %TILE_OVERLAP% ^
    --batch-size %BATCH_SIZE% ^
    --max-maps %MAX_MAPS% ^
    --threshold %THRESHOLD% ^
    --device %DEVICE% ^
    --model-type %MODEL_TYPE% ^
    --skip-no-gt ^
    --save-viz

if %ERRORLEVEL% NEQ 0 (
    echo.
    echo ERROR: Evaluation failed with exit code %ERRORLEVEL%
    exit /b %ERRORLEVEL%
)

echo.
echo =========================================================================
echo  Evaluation complete! Results saved to:
echo    - %OUTPUT_DIR%\results.json   (detailed per-feature results)
echo    - %OUTPUT_DIR%\summary.txt    (aggregate summary)
echo    - %OUTPUT_DIR%\viz\           (visualization panels)
echo =========================================================================

endlocal
