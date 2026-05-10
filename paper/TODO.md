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
