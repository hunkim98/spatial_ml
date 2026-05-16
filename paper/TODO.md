# SIGSPATIAL 2026 — Road to Acceptance

## Current Status

- Synthetic pipeline: DONE (219 GeoJSONs, 8 rendering dimensions, ~27K triplets)
- FiLM-conditioned U-Net: DONE (best val IoU = 0.574)
- USGS zero-shot evaluation: DONE (median F1 = 0.016, mean = 0.091, top feature = 0.93)
- Paper draft: DONE (needs reframing + new experiments)

## Critical Deficiency

The paper claims synthetic pretraining is useful for cross-domain map segmentation, but
the aggregate results (median F1 = 0.016) do not support this claim. The missing
experiment — fine-tuning on a few real maps — is the single most important thing
needed to make this publishable.

---

## Priority 1: Non-Negotiable Experiments (without these, reject guaranteed)

### 1A. Fine-tuning experiment (THE critical experiment)

**Goal:** Prove that synthetic pretraining provides useful initialization for
downstream map segmentation tasks with minimal real annotation.

**Protocol:**
1. Hold out 2 USGS validation maps as "pseudo-training" data (pick maps with
   diverse feature types — one with many color-distinctive units, one harder).
2. Fine-tune the pretrained model on those 2 maps for 5, 10, 20 epochs.
3. Evaluate on the remaining 12 maps.
4. Compare against:
   - (a) Random init + fine-tune on same 2 maps (same epochs, same LR schedule)
   - (b) Zero-shot transfer (current result, median F1 = 0.016)
   - (c) LOAM's reported numbers (median F1 = 0.809 on testing set)
5. Report:
   - Convergence speed (loss curve: pretrained vs scratch)
   - Final F1 at each epoch checkpoint
   - Per-feature breakdown for both

**Expected outcome:** Pretrained model converges faster and achieves higher F1
than random init with the same amount of real data. Even if final F1 is 0.3–0.5,
this proves the value proposition: "synthetic pretraining reduces annotation
requirements by N×."

**Implementation notes:**
- Create `model/zone_segmentation/scripts/finetune_usgs.py`
- Freeze encoder for first 2-3 epochs, then unfreeze (prevents catastrophic
  forgetting of synthetic features)
- Use lower LR than pretraining (1e-6 or 5e-7)
- Log per-feature F1 at each checkpoint

**Execution status (updated 2026-05-10):**
- Pretrained fine-tune: **DONE** (20 epochs, training F1 0.696)
  - Checkpoints: `checkpoints/finetune_pretrained/{epoch5,10,20,final}.pt`
  - W&B: `eval-pretrained-e20-heldout22` and the training run `05rggedk`
- Scratch fine-tune (matched LR=1e-6): **DONE** (20 epochs, training F1 0.295)
  - Checkpoints: `checkpoints/finetune_scratch/{epoch5,10,20,final}.pt`
  - W&B: training run `tq6jera9`
- Held-out evals: scoped down to **best checkpoint (e20) only** to fit deadline.
  - Original chain spec evaluated e5/e10/e20 (6 evals, est. 60-100h on this box)
  - Reduced to e20-only (2 evals, est. 20-34h): pretrained_e20, scratch_e20
  - Currently running pretrained_e20 (started 20:06, AK_Hughes in progress)
  - Backfill follow-up: see "1A.0" below if convergence subplot needed
- First held-out signal (pretrained_e5 on AK_Hughes only — partial e5 run):
  mean F1 0.086 vs zero-shot 0.065 (+31%). One map; full picture pending.

### 1A.0. (Optional backfill) Convergence subplots: e5/e10 evals (added 2026-05-10)

**Why:** The current run only evaluates the e20 (best) checkpoint to fit the
deadline. If we want a "F1 vs epoch" subplot in the paper to show convergence
behavior on held-out data, we need the e5 and e10 evals too. The checkpoints
are already saved at `checkpoints/finetune_{pretrained,scratch}/epoch{5,10}.pt`.

**Trigger:** Only if (1) e20 results are paper-worthy AND (2) we have remaining
compute time. Skip if the headline claim doesn't need a convergence plot.

**Cost:** 4 additional evals × ~10-17h each = 40-68h on this box.

**How:** Edit `scripts/run_1a_chain.ps1` line `$Epochs = @(20)` back to
`$Epochs = @(20, 10, 5)`, re-run. The chain is idempotent — already-completed
e20 evals are skipped via the `summary.txt` existence check.

### 1A.1. Fairer scratch baseline at higher LR (added 2026-05-10)

**Why:** The first 1A run uses LR=1e-6 for both pretrained and scratch (per
"same LR schedule" in 1A protocol step 4a). Empirically, scratch at LR=1e-6
shows essentially zero learning across epochs 1-4 — the random encoder needs
much more aggressive updates to escape its initialization. A reviewer can
fairly object: "you didn't really try with scratch; the LR is mismatched to
the regime." To pre-empt that, add a second scratch run with a higher LR.

**Trigger:** Run AFTER the first 1A held-out evals land. If pretrained's
held-out F1 > scratch's by ≥2× under matched-LR, this fairer baseline is
needed for paper credibility. If they're already close, skip.

**Protocol:**
1. Re-run scratch fine-tune on the same 2 maps with **LR=1e-4** (100× higher).
2. Same 20 epochs, same save-at-epochs (5, 10, 20).
3. Same 22-map held-out eval.
4. Save to `checkpoints/finetune_scratch_lr1e-4/` and
   `results/finetune_eval_scratch_lr1e-4_e{5,10,20}/`.
5. Report both scratch baselines in the comparison table:
   - "scratch @ LR=1e-6 (matched)"
   - "scratch @ LR=1e-4 (fair)"

**Expected outcome:** Even at higher LR, scratch should still under-perform
pretrained — but by a smaller margin. The honest paper claim becomes "X×
gap under matched LR, Y× gap under each baseline's best LR."

**Command (for later):**
```powershell
.\.venv\Scripts\python.exe -m model.zone_segmentation.scripts.finetune_usgs `
    --random-init --finetune-maps AR_StJoe AK_Dillingham `
    --epochs 20 --save-at-epochs 5 10 20 --crops-per-feature 64 `
    --batch-size 4 --num-workers 0 --lr 1e-4 --freeze-encoder-epochs 0 `
    --save-dir checkpoints/finetune_scratch_lr1e-4
```
Note: `--freeze-encoder-epochs 0` because freezing a random encoder at LR=1e-4
makes no sense — let the whole network train from step 1.

### 1A.2. Composition ablation: hard-map fine-tune set (added 2026-05-10)

**Why:** First 1A run uses AR_StJoe (mean delta-E 10.8, easy) + AK_Dillingham
(mean delta-E 6.2, typical). The model never sees the *hard* color-confusion
regime during fine-tune. First held-out result (AK_Hughes, mean delta-E 2.5,
hardest map after DC_Frederick) showed only +31% over zero-shot — possibly
because no fine-tune exposure to that regime. This ablation tests whether
fine-tune set *composition* matters as much as *count*.

**Trigger:** Run AFTER 1A held-out evals land. If 1A's held-out per-map F1
is well-correlated with each map's mean delta-E (i.e., we do well only on
easy maps), this ablation is needed.

**Protocol:**
1. Re-run pretrained fine-tune on **AK_Hughes + AR_StJoe** (one hard, one easy).
   - Same hyperparameters as 1A (LR=1e-6, 20 epochs, freeze 3, batch 4, etc.)
2. Eval on the remaining 22 maps (now 22 again because AK_Hughes is in fine-tune).
3. Compare per-map F1 between this run and original 1A.
4. Save to `checkpoints/finetune_pretrained_hardset/` and
   `results/finetune_eval_pretrained_hardset_e{5,10,20}/`.

**Expected outcome:** If composition matters: per-map F1 on remaining hard maps
(AZ_PrescottNF, DC_Frederick, CO_Alamosa, CO_Clifton) improves significantly
in the hardset run vs the original 1A. If composition doesn't matter: numbers
look similar to 1A. Either is a paper-worthy table.

**Command:**
```powershell
.\.venv\Scripts\python.exe -m model.zone_segmentation.scripts.finetune_usgs `
    --pretrained checkpoints/zone_seg_loam_vanilla_v2/best.pt `
    --finetune-maps AR_StJoe AK_Hughes `
    --epochs 20 --save-at-epochs 5 10 20 --crops-per-feature 64 `
    --batch-size 4 --num-workers 0 --lr 1e-6 --freeze-encoder-epochs 3 `
    --save-dir checkpoints/finetune_pretrained_hardset
```
Then eval with `--exclude-maps AR_StJoe AK_Hughes` (note AK_Dillingham is now
NOT excluded since it's no longer in the fine-tune set).

### 1A.3. Annotation efficiency curve: scaling sweep (added 2026-05-10)

**Why:** "We use 2 maps" is more striking than "we use 5 maps" — but reviewers
will ask "would more annotation help?" An efficiency curve answering
**F1 vs N fine-tune maps** is a much stronger paper figure than a single
data point. Becomes Table 5 / a key paper plot.

**Trigger:** Run regardless of 1A outcome. If 1A is strong, this validates
the "annotation efficiency" framing. If 1A is weak, this is the paper's main
contribution figure.

**Protocol:**
1. Define a 4-point sweep: N = 1, 2, 5, 10 fine-tune maps.
   - N=1: AR_StJoe only
   - N=2: AR_StJoe + AK_Dillingham (= the original 1A)
   - N=5: AR_StJoe + AK_Dillingham + AK_Hughes + CA_Elsinore + AZ_GrandCanyon
     (cover easy/hard/medium of delta-E spectrum, geographic diversity)
   - N=10: above + CA_MarbleCanyon + AZ_PipeSpring + NV_HiddenHills + NM_Sunshine + OR_Camas
   - (Picks above are stratified by delta-E from the failure analysis to be
     representative; can revisit selection.)
2. For each N, run BOTH pretrained init and random init (TODO 1A.1 LR for scratch).
3. Eval each on the remaining (24 - N) maps.
4. Build the curve: x = N fine-tune maps, y = held-out median F1, two lines
   (pretrained vs scratch).

**Expected outcome:** Pretrained line starts well above scratch at N=1 and
both rise with N — gap narrows but doesn't close. The shape of the curve
tells the annotation-efficiency story.

**Compute estimate:** 4 train pairs (8 fine-tune runs) × ~2.5h + 12 evals
× ~2h = ~44 hours total. Don't queue without confirming the 1A result first
— if 1A is fully informative, the N=1 and N=10 runs can be enough (skip
N=5 if compute-constrained).

**Implementation note:** Generalize finetune chain to take N as a parameter,
keep the same orchestration pattern as `scripts/run_1a_chain.ps1`.

### 1B. Quantitative failure analysis

**Goal:** Explain WHY the model succeeds or fails on specific features, turning
"it mostly fails" into "it succeeds predictably under condition X."

**Compute for each of 626 features:**
- Delta-E (CIEDE2000) between the legend swatch and its nearest-neighbor swatch
  in the same map's legend. This measures color distinctiveness.
- Polygon area fraction (target feature area / total map area in pixels).
- Number of legend entries in the map (proxy for task difficulty).
- Translucency flag: does the feature use a translucent overlay on topography?

**Produce:**
- Scatter plot: F1 vs delta-E (expect strong positive correlation)
- Scatter plot: F1 vs area fraction (expect positive correlation)
- Box plot: F1 distribution grouped by number of legend entries
- Table: mean F1 for features with delta-E > 30 vs delta-E < 15

**Implementation notes:**
- Create `model/zone_segmentation/scripts/failure_analysis.py`
- Use `colormath` library for CIEDE2000 (or implement from the formula)
- Load legend swatches from USGS JSON annotations, compute pairwise delta-E
- Correlations should be reported as Pearson/Spearman r with p-values

### 1C. Tiled vs whole-map comparison (table, not just one number)

**Goal:** Quantify whether the current poor results are due to resolution loss
or genuine domain gap.

You already have tiled results (mean F1 = 0.091). Run both modes on the same
maps and report per-map F1 for both. If tiled is consistently better, the model
has spatial discrimination ability being discarded by downsampling. If tiled is
not better, the problem is the domain gap itself (more important finding).

---

## Priority 2: High-Impact Improvements (workshop → main conference)

### 2A. Second target domain

**Goal:** Demonstrate cross-domain generalization beyond one target.

**Options (in order of feasibility):**
- Historical cadastral/land-use maps (closest to zoning — should transfer best)
- USDA soil survey maps (color-coded, similar to zoning)
- European geological surveys (different symbology than USGS)

**Minimum viable:** 3–5 maps with manual ground truth polygons. Even a small
evaluation strengthens the "cross-domain" claim from anecdote to evidence.

### 2B. Color-distinctiveness-aware conditioning

**Goal:** Address the core failure mode (confusing similar colors) at the
model level.

**Approach:** Instead of encoding the target swatch in isolation, encode ALL
swatches for the map and compute a distinctiveness-weighted conditioning vector.
The ContextUNet (legend grid encoder) is a crude version of this — replace it
with explicit pairwise swatch comparison:

1. Encode all N legend swatches → N vectors
2. Compute cosine similarity matrix
3. For the target swatch, identify its k nearest neighbors
4. Produce a "confusion-aware" conditioning that tells the decoder:
   "find this color, but NOT these similar colors"

This is architecturally more principled than the grid-of-thumbnails approach
and directly addresses the dominant failure mode.

### 2C. Expand synthetic rendering toward geological appearance

**Goal:** Narrow the domain gap through domain-informed augmentation (NOT
domain-specific preprocessing — keeps the "zero annotation" story).

**Add to `processor/map_renderer/`:**
- Translucent overlay simulation (alpha-blend zone fills over a base layer)
- Stipple/dot patterns (common in geological symbology)
- Variable-width hand-drawn boundary simulation
- Force similar colors between adjacent zones (trains discriminability)
- Topographic line overlays beneath zone fills

These are rendering options, not preprocessing channels. The pipeline stays
generic; the augmentation distribution moves closer to geological maps.

---

## Priority 3: Paper Structure Changes

### Reframe the narrative

**Current framing (weak):** "We trained on synthetic maps and tested on
geological maps. Results: median F1 = 0.016. Future work: fine-tuning."

**Better framing (strong):** "Annotation is the bottleneck for digitizing
geospatial archives. We present a synthetic pretraining approach that
eliminates annotation for the pretraining phase. When combined with minimal
fine-tuning (2 maps), it achieves X% of supervised performance at 1/7th the
annotation cost. The synthetic pipeline is domain-agnostic and extensible."

### Suggested title

"Zero-Annotation Map Segmentation via Synthetic Pretraining and Minimal Fine-Tuning"

### Key tables to add

| Table | Content |
|-------|---------|
| Table 1 | Synthetic val results (existing — source-aware vs naive) |
| Table 2 | Fine-tuning experiment (pretrained vs scratch, 1/2/5 maps) |
| Table 3 | Failure analysis: F1 vs delta-E bins |
| Table 4 | Cross-domain results per map (tiled + whole-map) |
| Table 5 | Second target domain (if completed) |

### What to remove or reduce

- The "Conditioned Segmentation" related work subsection is too long for a
  FiLM citation. Two sentences suffice.
- The CCS XML block can be shortened.
- The architecture section needs no change — it's appropriately brief.

---

## Timeline Recommendation

SIGSPATIAL 2026 submission deadline is typically June. Working backward:

1. Fine-tuning experiment (Priority 1A) — do FIRST
2. Failure analysis (Priority 1B) — can run in parallel with 1A
3. Tiled comparison table (Priority 1C) — quick, data already exists
4. Rewrite paper with new results
5. Second domain (Priority 2A) — if time allows
6. Architecture improvements (Priority 2B/2C) — only if 1A shows pretraining helps

---

## What NOT to Do

- Do NOT add model complexity (transformers, diffusion, ViT) before running 1A.
  If fine-tuning doesn't help, no architecture change will save the paper.
- Do NOT try to beat LOAM on aggregate numbers. Your contribution is zero
  annotation cost, not SOTA accuracy.
- Do NOT spend time on the frontend, collector, or other non-paper components.
- Do NOT write "future work: fine-tuning" — DO the fine-tuning.
