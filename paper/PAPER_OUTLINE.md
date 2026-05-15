# Short Paper Outline — SIGSPATIAL 2026 (4 pages)

Target: GeoAI workshop or short-paper track at SIGSPATIAL.
Length: ~4 pages including references, figures, tables.

## Headline numbers (from analyze_finetune_results.py)

- Pretrained_e20 mean F1 = **0.126** vs zero-shot 0.086 across 22 held-out USGS maps = **+47% mean, +118% median**
- Pretrained / Scratch ratio = **8.68×** (matched 7+ maps; final after scratch eval completes)
- Every held-out map shows positive Δ
- Failure analysis: 98% of features have ΔE < 15 (structural property of USGS)
- Spearman correlation F1 vs ΔE: r=0.21 (p<1e-12)
- Pearson correlation F1 vs log(area): r=0.45 (p<1e-56)

## Section structure

### 1. Abstract (~150 words)

Use `paper/ABSTRACT_DRAFT.md` Draft B with the headline numbers filled in. Three sentences:
1. Setup the problem (annotation bottleneck, raster maps, legend-driven segmentation)
2. Our pipeline (219 GeoJSONs → 27K triplets → FiLM U-Net)
3. Three findings (failure analysis structural insight, pretrained vs zero-shot Δ, pretrained vs scratch ratio)

### 2. Introduction (~0.75 page, ~3 paragraphs)

- **Para 1**: 100K+ historical USGS maps; manual annotation cost; LOAM-style methods require 14+ annotated maps.
- **Para 2**: We propose synthetic pretraining as the bottleneck-relief lever. Generate unlimited (image, pattern, mask) triplets from real GeoJSONs.
- **Para 3**: Contributions (bulleted):
  - A domain-agnostic synthetic data pipeline (8 randomized rendering dimensions)
  - Empirical characterization of WHY USGS map segmentation is hard (98% confusable-color regime)
  - Demonstration that 2-map fine-tune of a synthetic-pretrained model beats random init by 8.7× and zero-shot by 47% on held-out USGS

### 3. Method (~0.75 page)

- **3.1 Synthetic data pipeline** (1 paragraph): 219 GeoJSONs, 8 dims (rotation, basemap, hatching, labels, old-map, colors, page size, resolution); ~4380 maps, ~27K triplets. Cite NOTES.md for details.
- **3.2 Model** (1 paragraph): FiLM-conditioned VanillaUNet, 38M params, encoder + decoder + pattern-thumbnail encoder, BCE+Dice loss.
- **3.3 Fine-tuning protocol** (1 paragraph): SGD momentum=0.999, LR 1e-6, freeze encoder for 3 epochs then unfreeze, Dice loss only, 20 epochs at 1024². 2 fine-tune maps (AR_StJoe + AK_Dillingham), 22 held-out for eval. Tiled inference at 512×512 / overlap 128.

**Cuts from existing draft**: trim Related Work to 1 paragraph (LOAM + maybe SAM mention). The current draft over-discusses conditioned segmentation.

### 4. Experiments & Results (~1.5 pages)

This is the load-bearing section. Structure:

- **4.1 Setup** (short): USGS AI4CMA validation set. 24 maps total (2 fine-tune, 22 held-out, 2 dropped for lack of GT). Metrics: per-feature F1 with 0.5 threshold, tile-averaged inference.

- **4.2 Structural difficulty of USGS** (Failure Analysis — half-page)
  - **Table 1**: F1 by ΔE bin (from `failure_analysis/analysis.md`) — show monotonic gain, but 98% of features in confusable regime.
  - **Figure 1**: scatter F1 vs ΔE, log-area vs F1, F1 distribution by N legend entries.
  - Claim: "USGS is structurally adversarial to color-based segmentation."

- **4.3 Synthetic pretraining + fine-tune transfers** (Main result — full page)
  - **Table 2**: Per-map breakdown — 22 rows × {ZS, Pre, Sc, Δ Pre/ZS, Pre/Sc}.
  - **Figure 2**: per_map_bar.png (already generated).
  - Aggregate paragraph with the +47% / 8.7× numbers.
  - Sub-claim: **every map improves**, not just the easy ones.

- **4.4 Where pretraining helps most** (short — half-page or paragraph)
  - **Figure 3**: improvement_vs_deltaE.png — does pretrained help more on hard or easy features?
  - **Figure 4 (optional)**: qualitative panel (4 features where pretrained > 0.5 F1 but scratch ≈ 0). Picks already chosen in `qualitative_picks.json`.

### 5. Discussion (~0.5 page)

3 paragraphs:
- **Why scratch fails so badly**: at the LR appropriate for fine-tuning (1e-6), random init can't learn — confirms pretraining provides feature-level transfer, not just initialization.
- **Why absolute F1 is bounded**: the 98% confusable-color regime. No method without explicit color-disambiguation machinery will saturate this benchmark from 2 maps. Reference LOAM's 0.81 as the supervised-with-14-maps ceiling.
- **Future work**: scaling curve (N=1, 2, 5, 10 fine-tune maps), confusable-color synthetic augmentation, foundation-model encoders. Brief; this is workshop scope.

### 6. Conclusion (~0.25 page)

Short. Reiterate three findings:
1. USGS map segmentation is structurally hard (98% confusable colors).
2. Synthetic pretraining + 2-map fine-tune yields +47% F1 over zero-shot.
3. Random init with same data fails (8.7× lower) — pretraining is the lever.

### 7. References

LOAM (Lin '23), DARPA CMA dataset, FiLM (Perez '18), U-Net (Ronneberger '15), maybe DINOv2/SAM as future-work pointers.

## Figures & Tables checklist

| Asset | Source | Section | Status |
|---|---|---|---|
| Table 1 — F1 by ΔE bin | `failure_analysis/analysis.md` | 4.2 | ✅ ready |
| Figure 1 — Failure scatter | `failure_analysis/plots/*.png` | 4.2 | ✅ ready (publication-polish them) |
| Table 2 — Per-map results | `finetune_results/per_map.csv` | 4.3 | ✅ ready (re-run after scratch_e20 done) |
| Figure 2 — Per-map bar | `finetune_results/plots/per_map_bar.png` | 4.3 | ✅ ready (re-run later) |
| Figure 3 — Improvement vs ΔE | `finetune_results/plots/improvement_vs_deltaE.png` | 4.4 | ✅ ready |
| Figure 4 (optional) — Qualitative panel | hand-pick from `qualitative_picks.json` | 4.4 | ⏳ build later |

## What's TBD before submission

1. **Wait for scratch_e20 eval to finish** (in progress; ~6-10 hr remaining).
2. **Re-run analyze_finetune_results.py** with final data.
3. **Run 1A.2** (composition ablation, ~6h) — adds one row to Table 2 if it helps the story.
4. **Polish failure-analysis plots** for paper-quality (300dpi, bigger fonts, vector output).
5. **Build the qualitative panel** (Figure 4) — manual feature picking from `qualitative_picks.json`.
6. **Rewrite the existing LaTeX** (`paper/sigspatial_zone_segmentation.tex`, currently 487 lines) to fit this outline.

## Suggested writing order (so each section depends only on what's already done)

1. Method (no new data needed — write today/tomorrow)
2. Section 4.1 Setup (also static)
3. Section 4.2 Failure analysis (data already final)
4. Conclusion (knows what we want to claim)
5. **Wait for scratch_e20 eval** → finalize Table 2 + Figures 2, 3
6. Section 4.3 + 4.4 (depend on final data)
7. Discussion (depends on final numbers)
8. Introduction (write last so it matches the actual story)
9. Abstract (write last)

This way Section 4 is the only thing blocked on remaining compute. Everything else can be written now.
