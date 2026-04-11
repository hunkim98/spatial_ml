#!/bin/bash
#SBATCH --job-name=zone_seg_loam
#SBATCH --partition=gpu
#SBATCH --gres=gpu:1
#SBATCH --cpus-per-task=4
#SBATCH --mem=32G
#SBATCH --time=12:00:00
#SBATCH --output=slurm-%j.out
#SBATCH --error=slurm-%j.err

module load python/3.12.11-fasrc02
module load cuda

source .venv/bin/activate

bash model/zone_segmentation/train_loam.sh "$@"
