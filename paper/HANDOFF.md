# HANDOFF: SIGSPATIAL Short Paper — Plan 2 Playbook

> **Written by:** claude (session of 2026-05-15) for a future claude session (or human)
> picking up this work cold. Read top-to-bottom before doing anything.

---

## 0. WHAT IS THIS PROJECT? (read this first if cold)

### 0.1 The big-picture goal

The `spatial_ml` repository is a research codebase for building **machine
learning models that extract zoning data from US city maps and ordinances**.
The user (Hun Kim at Harvard) is a data scientist/researcher working on
**legend-driven map segmentation** — given a raster map and a small "legend
swatch" (e.g., a colored square indicating a zone type), the model should
output a binary mask of all pixels matching that zone.

The codebase has several components (see `CLAUDE.md` at the repo root):
- **`collector/`** — scrapers for zoning ordinances
- **`processor/`** — data processing pipelines including a **synthetic map
  renderer** that converts real-world GeoJSON files into rendered training
  images
- **`model/zone_segmentation/`** — the actual ML model (a pattern-conditioned
  U-Net). This is what the paper is about.
- **`frontend/`** — a Next.js web app (unrelated to the paper)

### 0.2 The specific paper this handoff is about

The paper studies the **zone-segmentation model's ability to transfer**
from its training domain (rendered synthetic municipal zoning maps) to a
different test domain (real USGS geological maps from the DARPA Critical
Mineral Assessment benchmark). It's a short paper aiming at SIGSPATIAL
2026's GeoAI workshop.

Two findings the paper reports:
1. **Diagnostic** — the DARPA CMA benchmark is structurally hard because
   98% of its legend swatches have a near-twin (CIEDE2000 < 15) in the
   same map. This bounds what any color-only method can achieve.
2. **Ablation** — synthetic pretraining + fine-tune on 2 USGS maps beats
   training from scratch on the same 2 maps. The gain is small in absolute
   terms (mean F1 0.126 vs 0.083) but is statistically tight and consistent
   across all 22 held-out maps.

Plan 2 (the current strategy) adds a scaling curve at N=1, 5, 10
fine-tune maps to strengthen the transferability claim.

### 0.3 What you (the future Claude session) should know

- The user is moving fast and has a deadline (paper to submit within days).
- The user prefers terse, honest updates — not optimistic spin.
- The user has previously asked for "Soviet-style" harsh critiques and values them.
- The user accepts that the absolute numbers are unimpressive and frames
  the paper around the diagnostic + the controlled ablation, not "we beat SOTA."
- The user has explicitly said the venue is GeoAI workshop, not main conference.

### 0.4 Resources to read before doing anything substantive

In order of priority, read these before making decisions:

| # | File | What you'll learn | Time |
|---|---|---|---|
| 1 | `CLAUDE.md` (repo root) | Project-wide context, codebase structure | 5 min |
| 2 | This file (`paper/HANDOFF.md`) end-to-end | What's been done, what's in flight, what to do next | 15 min |
| 3 | `paper/sigspatial_zone_segmentation.tex` | The current paper draft (the thing you're shipping) | 10 min |
| 4 | `paper/HARSH_CRITIQUE.md` | Every reviewer attack and its defuse — re-read before claiming the paper is ready | 10 min |
| 5 | `paper/RELATED_WORK_SURVEY.md` | Survey of LOAM, ICM, DIGMAPPER, Sterzinger '25, Arzoumanidis '25 (the concurrent work landscape) | 10 min |
| 6 | `model/zone_segmentation/NOTES.md` | Research notes on the model/task. Especially the "Key Prior Work: LOAM" section and our "Approach" section | 10 min |
| 7 | `paper/TODO.md` | Original paper priorities (1A, 1B, 1C) and the 1A.1, 1A.2, 1A.3 follow-ups | 5 min |
| 8 | `model/zone_segmentation/reports/failure_analysis/analysis.md` | The diagnostic finding details + correlations | 5 min |
| 9 | `model/zone_segmentation/reports/finetune_results/paper_summary.md` | Auto-generated current numbers with bootstrap CIs | 5 min |
| 10 | `paper/PAPER_OUTLINE.md` | The structural plan (slightly out of date but still useful) | 5 min |
| 11 | `paper/ABSTRACT_DRAFT.md` | Drafts A and B with the abstract evolution + reasoning | 5 min |
| 12 | `paper/sigspatial_zone_segmentation_long_v1.tex` | The original full-length draft preserved for reference | skim only |

Code files worth reading if you'll modify the pipeline:

| File | When to read |
|---|---|
| `model/zone_segmentation/scripts/eval_usgs.py` | Before touching eval logic; has tiled inference + per-map resume |
| `model/zone_segmentation/scripts/finetune_usgs.py` | Before touching the fine-tune protocol |
| `model/zone_segmentation/scripts/analyze_finetune_results.py` | Before changing how tables are auto-generated |
| `model/zone_segmentation/scripts/failure_analysis.py` | If re-running the diagnostic analysis |
| `model/zone_segmentation/unet_vanilla.py` | The actual model architecture (38M-param FiLM U-Net) |
| `model/zone_segmentation/dataset.py` | How the synthetic training data is loaded |
| `scripts/run_scaling_curve.ps1` | The Plan 2 chain (current work in flight) |

### 0.5 Data resources on disk

The user's local machine has several large data resources NOT in the repo:

| Path | What | Approx. size |
|---|---|---|
| `data/training/zoning_segmentation/` | Synthetic training data (4380 rendered maps, 27K triplets) | several GB |
| `usgs/validation.tar.gz` | Source of USGS validation maps (24 maps with GT) | 6.2 GB |
| `usgs/validation_answer_key.tar.gz` | Ground-truth raster masks | 107 MB |
| `usgs/evaluation.tar.gz` | USGS held-out evaluation set (not used in this paper) | 3.2 GB |
| `$env:TEMP/usgs_eval/` | Working dir where USGS data is extracted (82 maps, 1317 GT rasters) | several GB |
| `checkpoints/zone_seg_loam_vanilla_v2/` | The pretrained base model (38M params) | ~150 MB |
| `wandb/` | Local Weights & Biases run cache | several MB |

The wandb project is hosted at
`https://wandb.ai/hunkim98-harvard/spatially-zone-segmentation` — all
training runs are synced there for the record.

### 0.6 External resources / prior work to reference

The paper's bibliography (`paper/references.bib`) cites these. If you need
context on any of them:

| Citation key | What it is | Where it's online |
|---|---|---|
| `lin2023loam` | LOAM paper (the prior 7-channel preprocessing baseline) | https://doi.org/10.1145/3589132.3625659 ; PDF at `usgs/polygon_metadata_oldmaps.pdf` locally |
| `luo2023icm` | ICM team's earlier 6-channel U-Net (winner of DARPA CMA 2022 polygon track) | IEEE LGRS https://doi.org/10.1109/LGRS.2023.3310915 |
| `duan2025digmapper` | DIGMAPPER (newest USGS pipeline, also uses synthetic data) | arXiv:2506.16006 |
| `sterzinger2025fewshot` | Few-shot historical-map segmentation via foundation-model linear probing | arXiv:2506.21826 |
| `arzoumanidis2025synthetic` | Synthetic-data bootstrapping for historical maps with degradation modeling | arXiv:2511.15875 |
| `chiang2014survey` | Canonical map-processing survey | ACM Computing Surveys |
| `goldman2023cma` | The DARPA CMA dataset release | USGS data release, DOI 10.5066/P9FXSPT1 |
| `perez2018film` | FiLM (Feature-wise Linear Modulation), our conditioning mechanism | AAAI 2018 |
| `ronneberger2015unet` | U-Net (our base architecture family) | MICCAI 2015 |
| `kirillov2023sam` | Segment Anything Model | ICCV 2023 |

### 0.7 Things the user has explicitly decided

- **Tiled inference, always.** Every USGS eval uses `--tile-size 512 --tile-overlap 128`, never `--no-tile`. The user reiterated this.
- **GeoAI workshop is the target.** Not main short paper track.
- **De-emphasize LOAM.** "LOAM is a reference not a benchmark." Cite once, don't frame as "vs LOAM."
- **Plan 2 (scaling curve) is in flight.** N=1, 5, 10 fine-tune + eval. Not yet launched as of this writing — the user wanted the handoff doc finalized first.
- **The synthetic data is NOT being regenerated.** The user explicitly rejected regenerating with confusable colors (would take 3-5 days; out of scope).
- **No additional experiments beyond Plan 2.** Don't propose more without asking.

---

## 1. TL;DR — what you're picking up

The user is writing a short paper for SIGSPATIAL 2026 (target: GeoAI
workshop or main conference short track) on **synthetic pretraining +
minimal fine-tune for legend-keyed map segmentation on the DARPA CMA
benchmark**.

**Plan 2** is the current strategy: add a scaling curve (pretrained model
fine-tuned at N=1, 5, 10 USGS maps) to the existing results, then write up
under a "transferability has two components: prior + ceiling" framing.

What you most likely need to do (in order):

1. **Read this entire doc** (~10 min)
2. **Check chain status** (Section 4) — is it running, paused, or never started?
3. **If never started:** launch it (Section 5)
4. **If running:** wait for completion, surface per-step updates (Section 6)
5. **When data lands:** build scaling figure + table, patch paper (Section 7)
6. **Help user compile + submit** (Section 8)

---

## 2. What is already DONE (frozen, do not re-run)

### 2.1 Models on disk

| Path | What |
|---|---|
| `checkpoints/zone_seg_loam_vanilla_v2/best.pt` | **Base model.** 38M-param VanillaUNet (4-level encoder, FiLM-conditioned decoder), pretrained 40 epochs on synthetic zoning maps. Val IoU 0.574, val F1 0.615. **This is the starting point for every fine-tune.** Don't overwrite. |
| `checkpoints/finetune_pretrained/` | 1A. Pretrained + 2-map fine-tune (AR_StJoe + AK_Dillingham), LR=1e-6, 20 epochs. |
| `checkpoints/finetune_scratch/` | 1A. Random-init + same 2-map fine-tune, matched LR=1e-6. |
| `checkpoints/finetune_scratch_lr1e-4/` | 1A.1. Random-init + 2-map fine-tune at LR=1e-4 (fair LR for random init). |
| `checkpoints/finetune_pretrained_hardset/` | 1A.2. Pretrained + 2-map fine-tune with AK_Hughes instead of AK_Dillingham. |

### 2.2 Eval results on disk

| Path | What | Mean F1 |
|---|---|---:|
| `results/usgs_eval_vanilla_v2_tiled/results.json` | Zero-shot (base model, no fine-tune) on all 24 maps | 0.086 |
| `results/finetune_eval_pretrained_e20/` | 1A pretrained_e20 on 22 held-out | **0.126** |
| `results/finetune_eval_scratch_e20/` | 1A scratch matched-LR on 22 held-out | 0.017 |
| `results/finetune_eval_scratch_lr1e-4_e20/` | 1A.1 scratch fair-LR on 22 held-out | **0.083** |
| `results/finetune_eval_pretrained_hardset_e20/` | 1A.2 composition on 22 (different 22) | 0.120 |

### 2.3 Analysis artifacts on disk

| Path | What |
|---|---|
| `model/zone_segmentation/reports/failure_analysis/` | Diagnostic: 98% confusable, ΔE/area correlations, per-feature CSV |
| `model/zone_segmentation/reports/finetune_results/paper_summary.md` | Auto-generated markdown summary with bootstrap CIs |
| `model/zone_segmentation/reports/finetune_results/per_map.csv` | 22-row per-map table |
| `paper/tables/headline_table.tex` | Auto-generated LaTeX table for the paper |

---

## 3. What needs to be PRODUCED (Plan 2)

Three fine-tune runs and three evals, plus a figure and a table:

| Output | Produced by | Estimated time on RTX 3060 |
|---|---|---:|
| `checkpoints/finetune_pretrained_N1/final.pt` | N=1 fine-tune on `AR_StJoe` | ~2.5h |
| `results/finetune_eval_pretrained_N1_e20/results.json` | N=1 eval on 23 held-out maps | ~13h |
| `checkpoints/finetune_pretrained_N5/final.pt` | N=5 fine-tune | ~2.5h |
| `results/finetune_eval_pretrained_N5_e20/results.json` | N=5 eval on 19 held-out maps | ~12h |
| `checkpoints/finetune_pretrained_N10/final.pt` | N=10 fine-tune | ~2.5h |
| `results/finetune_eval_pretrained_N10_e20/results.json` | N=10 eval on 14 held-out maps | ~9h |
| `paper/figures/scaling_curve.png` | `scripts/build_scaling_figure.py` | ~5s |
| `paper/tables/scaling_table.tex` | same script | ~5s |

Total compute: ~41h sequential. The chain script handles all of it.

### 3.1 The map sets (stratified by mean ΔE)

| N | Fine-tune set | Held-out (excluded from eval) |
|---:|---|---|
| 0 | (none, zero-shot) | 0 excluded — all 22 evaluated maps + AK_Dillingham + AR_StJoe |
| 1 | `AR_StJoe` | exclude `AR_StJoe` → 23 maps with GT |
| 2 | `AR_StJoe`, `AK_Dillingham` (this is 1A, already done) | 22 maps |
| 5 | + `AK_Hughes`, `CA_Elsinore`, `AZ_GrandCanyon` | 19 maps |
| 10 | + `CA_MarbleCanyon`, `AZ_PipeSpring`, `NV_HiddenHills`, `NM_Sunshine`, `OR_Camas` | 14 maps |

These are stratified by failure-analysis ΔE so each new N adds a typical/hard
representative.

---

## 4. Check what state we are in right now

Run these and interpret:

### 4.1 Is the chain running?

```powershell
Get-CimInstance Win32_Process -Filter "Name='python.exe'" | Select-Object ProcessId, CreationDate, CommandLine
```

- **Output shows `eval_usgs.py` or `finetune_usgs.py`**: chain is running. Skip to Section 6.
- **No python.exe**: chain is not running. Could be done, or never started.

### 4.2 Has any Plan 2 output already been produced?

```powershell
ls checkpoints/finetune_pretrained_N1, checkpoints/finetune_pretrained_N5, checkpoints/finetune_pretrained_N10 -ErrorAction SilentlyContinue
ls results/finetune_eval_pretrained_N1_e20, results/finetune_eval_pretrained_N5_e20, results/finetune_eval_pretrained_N10_e20 -ErrorAction SilentlyContinue
```

- **None of these exist**: chain has never run. Go to Section 5.
- **Some exist**: chain partially completed. Go to Section 5 — relaunching
  the chain is idempotent and will skip completed steps.
- **All summary.txt files exist**: chain finished. Skip to Section 7.

### 4.3 Check git log for auto-commits

```bash
git log --oneline | head -10
```

Look for commits with messages like `auto: scaling curve N=1 complete (N1-done)`
or `auto: scaling curve N=5 complete (N5-done)`. These tell you where the
chain got to.

### 4.4 Check the chain log

```bash
tail -50 logs/scaling_curve.log 2>/dev/null
```

If the log is full of `Tiles: XX%` lines, an eval is running. If it shows
`STEP X/6:` banners, the chain is between steps.

---

## 5. Launch the chain (if not running)

### 5.1 Prerequisites — verify these BEFORE launching

```powershell
# 1. The base model checkpoint exists
Test-Path checkpoints/zone_seg_loam_vanilla_v2/best.pt
# Should print True. If False, STOP — we can't fine-tune without the base.

# 2. The USGS data is extracted with all TIFs
$wd = "$env:TEMP/usgs_eval/validation"
(Get-ChildItem $wd -Filter "*.tif").Count
# Should print 82. If less, see Section 9 (TIF re-extraction).

# 3. WANDB_API_KEY is loadable
Test-Path secrets/teampspatially-project.env
# Should print True. The chain loads it automatically.

# 4. Python venv works
.\.venv\Scripts\python.exe -c "import torch; print(torch.cuda.is_available())"
# Should print True (GPU available).
```

If ALL four are True, launch:

```powershell
.\scripts\run_scaling_curve.ps1 2>&1 | Tee-Object -FilePath logs/scaling_curve.log
```

The chain is idempotent — safe to relaunch if it dies.

### 5.2 Launch in background

If you want to free the terminal while the chain runs:

```powershell
# As a Claude background task (recommended — you can monitor it):
# Use the PowerShell tool with run_in_background: true
# Output goes to a Claude task output file.

# Or as a Windows job:
Start-Job -ScriptBlock {
  Set-Location C:\Users\piljo\Github\spatial_ml
  .\scripts\run_scaling_curve.ps1 2>&1 | Tee-Object -FilePath logs/scaling_curve.log
}
```

### 5.3 Verify it actually started

After 30 seconds, check:

```powershell
Get-CimInstance Win32_Process -Filter "Name='python.exe'" | Select-Object ProcessId, CreationDate
```

You should see a Python process with a recent CreationDate. If not, the chain
failed at launch — check `logs/scaling_curve.log` for the error.

---

## 6. Monitor the chain while it runs

### 6.1 How long should it take?

| Step | Expected | Cumulative |
|---|---:|---:|
| N=1 fine-tune | 2.5h | 2.5h |
| N=1 eval | 13h | 15.5h |
| N=5 fine-tune | 2.5h | 18h |
| N=5 eval | 12h | 30h |
| N=10 fine-tune | 2.5h | 32.5h |
| N=10 eval | 9h | 41.5h |

Eval times scale with map size and feature count. The "Map TIF not found"
warnings during eval are expected for maps without ground truth — they're
skipped automatically.

### 6.2 Per-epoch progress during a fine-tune

Tail the active fine-tune log:

```bash
tail -f logs/finetune_pretrained_N1.log 2>/dev/null | grep "INFO Epoch"
```

Each line tells you the loss, IoU, F1 for that epoch. Training F1 typically
climbs from ~0.4 at epoch 1 to ~0.7 at epoch 20.

### 6.3 Per-map progress during an eval

```bash
tail -f logs/eval_pretrained_N1_e20.log 2>/dev/null | grep -E "INFO Processing|INFO Saved incremental"
```

You'll see "Processing X" when a map starts and "Saved incremental results
(N features so far)" when each map's features are added to `results.json`.

### 6.4 What the user wants surfaced

The user appreciates concise, factual progress updates: "N=1 eval done on
9/23 maps, mean F1 so far 0.085." NOT a full numbers dump every epoch.

Suggested update cadence: every 1-2 hours, or when a map completes (every
map is a notable milestone).

### 6.5 Auto-commits

The chain auto-commits + pushes after each eval completes, with messages like:
- `auto: scaling curve N=1 complete (N1-done)`
- `auto: scaling curve N=5 complete (N5-done)`
- `auto: scaling curve N=10 complete (N10-done)`

This means an external observer (the user, or a remote check) can see
progress in GitHub even if local logs are unreachable.

---

## 7. After the chain finishes — patch the paper

### 7.1 Confirm the chain is done

```powershell
# All three summary.txt files should exist
Test-Path results/finetune_eval_pretrained_N1_e20/summary.txt
Test-Path results/finetune_eval_pretrained_N5_e20/summary.txt
Test-Path results/finetune_eval_pretrained_N10_e20/summary.txt
# All three should print True
```

### 7.2 Build the scaling figure + table

```powershell
.\.venv\Scripts\python.exe scripts/build_scaling_figure.py
```

This produces:
- `paper/figures/scaling_curve.png` — the annotation-efficiency plot
- `paper/tables/scaling_table.tex` — a LaTeX table with all 5 N points

The script handles missing data gracefully — it'll only plot the N values
whose results.json exists.

### 7.3 Refresh the headline table

```powershell
.\.venv\Scripts\python.exe -m model.zone_segmentation.scripts.analyze_finetune_results
```

This refreshes `paper/tables/headline_table.tex` with the latest data. The
table includes:
- Zero-shot, Pretrained+ft, Scratch matched-LR, Scratch fair-LR rows
- Paired bootstrap CIs

### 7.4 Patch the paper

Add the scaling figure and table to `paper/sigspatial_zone_segmentation.tex`,
just after the per-map figure in Section 5. Search the file for the string
`label{fig:per_map}` to find the right location. Add this block AFTER the
closing `\end{figure}`:

```latex
\input{tables/scaling_table}

\begin{figure}[t]
\centering
\includegraphics[width=\columnwidth]{figures/scaling_curve.png}
\caption{Annotation-efficiency curve on DARPA CMA validation. Pretrained
$+$ fine-tune at $N=0, 1, 2, 5, 10$ USGS maps. Error bars are bootstrap
95\% CIs over per-feature F1. Each $N$ value uses a different held-out
set of (24$-N$) maps; sizes shown in Table~\ref{tab:scaling}.}
\label{fig:scaling}
\end{figure}
```

Then add a paragraph just before/after to interpret the curve. Suggested
template (fill in numbers from the figure):

```latex
\subsection{Annotation-Efficiency Curve}

Figure~\ref{fig:scaling} traces held-out mean F1 as a function of $N$, the
number of USGS maps used for fine-tuning. With $N{=}0$ (zero-shot) the
synthetic-pretrained model achieves mean F1 [X.XXX]; with $N{=}1$
([X.XXX]), $N{=}2$ ([X.XXX]), $N{=}5$ ([X.XXX]), and $N{=}10$ ([X.XXX]),
the prior's gain over zero-shot scales monotonically but with diminishing
slope per added map. This is the empirical anchor for the
\emph{transferable prior} component of our framing: the prior's benefit
is real at every $N$ but does not, alone, escape the structural ceiling
identified in \S\ref{sec:diagnostic}.
```

### 7.5 Update the abstract scaling-curve sentence

The abstract currently says:

> "We further trace the prior's gain across $N{=}1, 2, 5, 10$ fine-tune
> maps, producing an annotation-efficiency curve that anchors the
> transferability claim empirically."

Update this to mention the *shape* of the curve once you've seen it:

```
We further trace the prior's gain across $N{=}1, 2, 5, 10$ fine-tune
maps. Mean F1 grows monotonically from $0.086$ at $N{=}0$ to [X.XXX] at
$N{=}10$ but with diminishing returns, suggesting the benchmark's
structural ceiling is reached well below supervised SOTA.
```

(Adjust language to match what the curve actually shows. If it's NOT
monotonically growing, say so honestly — that's also a finding.)

### 7.6 Sanity-check all numbers in the paper

Open `model/zone_segmentation/reports/finetune_results/paper_summary.md`
and verify the body text of `paper/sigspatial_zone_segmentation.tex`
uses the same numbers. Common drifts:

- "0.086" vs "0.085" (zero-shot mean — both are correct depending on
  whether maps in the fine-tune set are excluded)
- "0.014" vs "0.017" (matched-LR scratch — earlier text used 0.014, the
  final auto-table uses 0.017)
- "7.5×" vs "7.55×"
- "1.4×" vs "1.52×" (fair-LR scratch ratio)

Use the values from `paper/tables/headline_table.tex` as the source of truth.

### 7.7 Commit + push

```bash
git add paper/sigspatial_zone_segmentation.tex paper/figures/scaling_curve.png paper/tables/
git commit -m "Final paper draft with scaling curve N=0..10 complete"
git push
```

---

## 8. The submission step (user does most of this)

### 8.1 Compile

The user compiles in Overleaf (or local LaTeX). You don't have pdflatex
locally. If they hit compile errors, common fixes:

| Error | Fix |
|---|---|
| `File 'figures/scaling_curve.png' not found` | Run Section 7.2 to generate it |
| `File 'tables/headline_table.tex' not found` | Run Section 7.3 to refresh it |
| `Undefined control sequence \cite{XXX}` | Check `paper/references.bib` has the key |
| Page count > 4 | See Section 8.2 for trim targets |
| Citation key mismatch | All citations are listed in `paper/references.bib` |

### 8.2 If the paper is over 4 pages

Trim, in this order (lowest-risk cuts first):
1. The training-curves figure can be moved to appendix or dropped
2. The "Concurrent work" paragraph in Discussion can be compressed to 1 sentence
3. The Per-Map Consistency subsection can lose the per-map figure (the
   numerical claim survives)
4. The "What this paper does/does not claim" paragraph in Discussion can
   be compressed
5. The composition robustness paragraph (1A.2 result) can become a footnote

If the paper is over 5 pages, you have a bigger problem; reconsider whether
to drop a section entirely.

### 8.3 Author info

Currently stubbed as "Hun Kim, Harvard University, donghunkim@mde.harvard.edu".
User should confirm or update before submission. Look for `\author{Hun Kim}`
in the LaTeX.

### 8.4 Acknowledgments

The paper currently has no acknowledgments section. If the user wants to add
funding/advisor acknowledgments, insert before `\bibliographystyle`:

```latex
\begin{acks}
[Add acknowledgments here.]
\end{acks}
```

### 8.5 Where to submit

Recommended venue: **SIGSPATIAL GeoAI workshop** (a regular satellite of
SIGSPATIAL main conference). Higher acceptance probability than main short
papers for work like this (diagnostic + small-effect ablation).

Look up the current year's GeoAI CFP at https://sigspatial2026.sigspatial.org
or the workshop's own site. Submission portal varies year-to-year.

---

## 9. Troubleshooting

### 9.1 "Map TIF not found" warnings during eval

The USGS validation data directory at `$env:TEMP/usgs_eval/validation/`
should have 82 .tif files. If it has fewer, some maps were lost during
earlier debugging.

Fix: extract missing TIFs from the source tar:

```powershell
$workDir = "$env:TEMP\usgs_eval"
$tarPath = "C:\Users\piljo\Github\spatial_ml\usgs\validation.tar.gz"
$missing = @("AK_Kechumstuk", "AR_Maumee", "CA_AZ_Needles", "CO_Clifton",
             "DC_Frederick", "NH_Hartland", "NM_Sunshine", "NV_HiddenHills",
             "OR_Camas", "OR_Carlton")  # adjust to whichever are actually missing
Push-Location $workDir
foreach ($m in $missing) {
    & tar -xzf $tarPath "validation/$m.tif" 2>&1 | Out-Null
}
Pop-Location
```

### 9.2 Chain stops with PowerShell `NativeCommandError`

Don't put `$ErrorActionPreference = "Stop"` at the top of any chain script.
Python tools (wandb, tqdm) write to stderr on success, which PowerShell
mis-classifies as a fatal error under "Stop". The current scripts use
`$LASTEXITCODE` checks instead.

### 9.3 Resume an interrupted eval

`eval_usgs.py` has per-map resume built in. If an eval crashes mid-way:

```powershell
# Just re-run the same eval command — it'll skip maps already in results.json
.\scripts\run_scaling_curve.ps1
```

The chain script's idempotency takes care of this automatically.

### 9.4 Chain killed mid-fine-tune

The fine-tune script has NO per-epoch resume. If a fine-tune dies at epoch 12
of 20, you lose epochs 12-20 and have to restart from scratch. Cost: ~2h
per fine-tune that has to restart. Mitigation: just don't kill them.

### 9.5 GPU OOM

If the batch fails with CUDA OOM:
- Reduce `--batch-size 4` to `--batch-size 2` in `run_scaling_curve.ps1`
- Reduce `--crops-per-feature 64` to `--crops-per-feature 32`

Both reduce memory at the cost of slower training. Reflect changes in the
paper's Method section if you make them.

### 9.6 Watcher / monitor processes are stuck

If old background tasks from previous sessions are visible:

```powershell
Get-CimInstance Win32_Process -Filter "Name='powershell.exe'" |
  Where-Object {$_.CommandLine -match "run_scaling|launch_1a|finish_evals"}
# Kill any that are no longer needed:
# Stop-Process -Id <ProcessId> -Force
```

---

## 10. Files index

### Code

| Path | Purpose |
|---|---|
| `scripts/run_scaling_curve.ps1` | **The Plan 2 chain.** Idempotent, sequential N=1, 5, 10 fine-tune + eval. Auto-commits after each eval. |
| `scripts/build_scaling_figure.py` | Builds `paper/figures/scaling_curve.png` and `paper/tables/scaling_table.tex`. Run after each new N completes (or manually any time). |
| `model/zone_segmentation/scripts/finetune_usgs.py` | Fine-tune entry point. Used by chain. |
| `model/zone_segmentation/scripts/eval_usgs.py` | Eval entry point. Tiled inference + per-map resume support. |
| `model/zone_segmentation/scripts/analyze_finetune_results.py` | Builds bootstrap CIs and `paper/tables/headline_table.tex`. |
| `model/zone_segmentation/scripts/plot_training_curves.py` | Builds `paper/figures/training_curves.png`. |
| `model/zone_segmentation/scripts/failure_analysis.py` | The diagnostic analysis (already run). |

### Paper files

| Path | Purpose |
|---|---|
| `paper/sigspatial_zone_segmentation.tex` | **The paper.** Edit this. |
| `paper/sigspatial_zone_segmentation_long_v1.tex` | Old full-length draft. Reference only. Don't edit. |
| `paper/references.bib` | Bibliography. Add new entries here if you cite new papers. |
| `paper/tables/headline_table.tex` | Auto-generated by `analyze_finetune_results.py`. Used via `\input{tables/headline_table}`. |
| `paper/tables/scaling_table.tex` | Auto-generated by `build_scaling_figure.py`. To be added to paper after Section 7. |
| `paper/figures/*.png` | Figures referenced from the LaTeX. |
| `paper/HANDOFF.md` | This file. |
| `paper/HARSH_CRITIQUE.md` | Reviewer-2 pre-mortem with every attack and its defuse. Re-read before claiming done. |
| `paper/RELATED_WORK_SURVEY.md` | Survey of LOAM, ICM, DIGMAPPER, Sterzinger '25, Arzoumanidis '25. Reference. |
| `paper/PAPER_OUTLINE.md` | The structural plan (slightly out of date, but useful for context). |
| `paper/ABSTRACT_DRAFT.md` | Drafts A and B with the abstract evolution. |
| `paper/TODO.md` | The original paper TODO with priorities 1A, 1B, 1C and the 1A.1, 1A.2, 1A.3 follow-ups. |

### Logs

| Path | What |
|---|---|
| `logs/scaling_curve.log` | The Plan 2 chain's stdout |
| `logs/finetune_pretrained_N{1,5,10}.log` | Individual fine-tune outputs |
| `logs/eval_pretrained_N{1,5,10}_e20.log` | Individual eval outputs |
| `logs/analyze_*.log` | Analysis kit runs |
| `logs/scaling_figure_*.log` | Figure-build script runs |

---

## 11. Decision log

| Date | Decision | Why |
|---|---|---|
| 2026-05-09 | Pivoted from LOAM-replication to TODO 1A fine-tuning | User redirected to paper-aligned work |
| 2026-05-10 | Cut e5/e10 eval, ran e20 only | Fit ~36h timeline; e20 is best checkpoint anyway |
| 2026-05-12 | Added 1A.1 (fair-LR scratch) | Defuse "wrong-LR strawman" reviewer critique |
| 2026-05-13 | Added 1A.2 (composition ablation) | Test fine-tune-set composition robustness |
| 2026-05-14 | All 1A/1A.1/1A.2 evals complete, bootstrap CIs added | Foundation for paper writing |
| 2026-05-15 | Plan 2 chosen: add scaling curve N=1, 5, 10 | Strongest single addition for transferability framing |
| 2026-05-15 | De-emphasize LOAM throughout | User: "LOAM is a reference not a benchmark" |
| 2026-05-15 | Target GeoAI workshop, not main short paper track | Realistic given absolute numbers |

---

## 12. Quick command cheat-sheet

```powershell
# === LAUNCH THE PLAN 2 CHAIN (idempotent) ===
.\scripts\run_scaling_curve.ps1 2>&1 | Tee-Object -FilePath logs/scaling_curve.log

# === CHECK WHAT'S RUNNING ===
Get-CimInstance Win32_Process -Filter "Name='python.exe'" | Select-Object ProcessId, CommandLine

# === BUILD SCALING FIGURE + TABLE (run after each new N completes) ===
.\.venv\Scripts\python.exe scripts/build_scaling_figure.py

# === REFRESH HEADLINE TABLE FROM CURRENT EVAL DATA ===
.\.venv\Scripts\python.exe -m model.zone_segmentation.scripts.analyze_finetune_results

# === BUILD TRAINING-CURVES FIGURE ===
.\.venv\Scripts\python.exe -m model.zone_segmentation.scripts.plot_training_curves

# === RE-EXTRACT MISSING USGS TIFS (see Section 9.1) ===
# (only if eval logs show "Map TIF not found" warnings)

# === FORCE-KILL THE CHAIN (last resort) ===
Stop-Process -Name python -Force
Get-CimInstance Win32_Process -Filter "Name='powershell.exe'" |
  Where-Object {$_.CommandLine -match "run_scaling_curve"} |
  ForEach-Object {Stop-Process -Id $_.ProcessId -Force}

# === LOOK AT RECENT GIT ACTIVITY ===
git log --oneline -10
git status

# === MANUAL COMMIT + PUSH ===
git add paper/ model/zone_segmentation/reports/finetune_results/
git commit -m "Final paper draft after scaling curve"
git push
```

---

## 13. If you only have 5 minutes

1. The user is shipping a SIGSPATIAL short paper.
2. The scaling-curve chain (`scripts/run_scaling_curve.ps1`) needs to run to completion.
3. When done, run `scripts/build_scaling_figure.py` and patch the paper per Section 7.4.
4. The paper is at `paper/sigspatial_zone_segmentation.tex`, compilable via Overleaf.
5. Re-read this doc fully when you have more time.

You've got this. Good luck.
