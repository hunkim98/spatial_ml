#!/bin/bash
#SBATCH --job-name=dvc_pull
#SBATCH --partition=serial_requeue
#SBATCH --cpus-per-task=4
#SBATCH --mem=16G
#SBATCH --time=04:00:00
#SBATCH --output=slurm-dvc-pull-%j.out
#SBATCH --error=slurm-dvc-pull-%j.err

module load python/3.12.11-fasrc02

source .venv/bin/activate

dvc pull -v
