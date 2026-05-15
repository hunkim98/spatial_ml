# Harsh Critique — pre-mortem for the SIGSPATIAL submission

**Written**: 2026-05-12. Author: claude, in the "hostile Reviewer 2" voice, at user request.
**Purpose**: catalogue every attack the paper can expect, so we can defuse each before submission.
Keep this doc in the repo. Future iterations should re-read and check whether their changes resolve or worsen each item.

---

## Headline attacks (the ones that decide accept/reject)

### A1. The numbers are objectively bad

- Mean F1 = 0.126 on held-out. LOAM = 0.809. We are **6.4× worse than the supervised baseline.**
- "+47% over zero-shot" sounds impressive until you notice zero-shot was 0.086 and the trivial baseline is somewhere around 0.05–0.08 depending on map.
- We moved from "barely above trivial" to "still barely above trivial."
- **Defuse**: don't claim "competitive with LOAM." Frame as "controlled isolation of the pretraining contribution."

### A2. The scratch baseline is a strawman

- Scratch held-out F1 = 0.014. That is *below* trivial. A randomly-initialized CNN trained at LR=1e-6 for 20 epochs on 2 maps trivially can't learn.
- The "8.7× pretrained/scratch ratio" is therefore inflated by a degenerate baseline.
- TODO 1A.1 (high-LR scratch at LR=1e-4) is queued — **must run and report before submission.**
- **Defuse**: report both the matched-LR ratio (1A) AND the fair-LR ratio (1A.1). Lead with whichever framing is more honest. If 1A.1 still shows pretrained winning, the contribution survives.

### A3. The "cross-domain" framing is a stretch

- Synthetic zoning maps and real geological maps are both colored-polygon maps with legend keys. The actual abstraction — "find pixels matching a swatch" — is the same.
- Calling this "cross-domain" invites attacks from foundation-model / domain-adaptation reviewers.
- **Defuse**: replace "cross-domain transfer" with "transfer across map aesthetic distributions" or "from synthetic municipal-zoning renderings to real USGS geological maps." Be precise.

### A4. We are no longer first to synthetic data

- DIGMAPPER (Duan '25, same USC group, same dataset) uses synthetic data.
- Arzoumanidis '25 uses synthetic data for historical maps.
- Sterzinger '25 does few-shot foundation-model probing for historical maps.
- **Defuse**: sharpen the contribution to three precise differentiators —
  (1) cross-domain (zoning→geology) where others train+test on same map type;
  (2) legend-key-conditioned task framing where Sterzinger and Arzoumanidis do generic seg;
  (3) controlled pretrained-vs-scratch ablation that none of the concurrent works run.

---

## Methodological attacks

### B1. No statistical significance reporting

- We claimed "+47%" and "8.7×" without confidence intervals or significance tests.
- **Resolved** (2026-05-12): paired bootstrap added to `analyze_finetune_results.py`.
  - Pretrained vs Zero-shot paired Δ = +0.040, 95% CI [+0.031, +0.050], P(pre>zs) = 1.000.
  - Pretrained vs Scratch (matched-LR) paired Δ = +0.111, 95% CI [+0.095, +0.127], P(pre>sc) = 1.000.
  - Ratio 8.8× with 95% CI [7.5, 10.6].
- **Defuse**: Table 1 and Table 2 must include CIs.

### B2. One random seed, no seed-variance analysis

- All fine-tune + eval runs use seed=42.
- A reviewer can ask "would another seed flip the conclusion?"
- **Risk**: real but probably small — paired Δ between pretrained and scratch is so large (0.111) that seed noise is unlikely to flip it.
- **Defuse (cheap)**: re-run pretrained fine-tune with seeds 41 and 43 (3 × 2.5h = ~8h). If results agree, append to a footnote. If unaffordable, acknowledge as future work in the limitations section.

### B3. 2 fine-tune maps is arbitrary

- Why 2? Because the paper TODO said so. Reviewer: "Could be cherry-picked."
- TODO 1A.3 (scaling curve N=1,2,5,10) addresses this but is 44h compute.
- **Defuse (cheap path)**: run N=1 (5h) and N=5 (12h) at minimum, plot a 3-point curve. Says enough about scaling without committing to 44h.
- **Or**: report that 2 was chosen *before* seeing held-out results (it was — it's in our TODO from 2026-05-10), and lock the protocol in supplement.

### B4. Composition: fine-tune maps were not chosen by held-out criteria

- AR_StJoe + AK_Dillingham were picked for stratified ΔE coverage. Fair, but a reviewer might say "you picked an easy map plus a typical map; what if you'd picked two hard maps?"
- TODO 1A.2 (composition ablation) addresses this — already queued to launch after scratch_e20 finishes.
- **Defuse**: run 1A.2, report as supplementary table.

### B5. No qualitative failure analysis on the fine-tuned model

- We did failure analysis on zero-shot only. We don't know if fine-tune fixes the same failures or different ones.
- **Defuse**: re-run `failure_analysis.py` style correlation on pretrained_e20 results. Cheap. Adds one paragraph to the paper.

---

## Architectural / novelty attacks

### C1. The model itself isn't novel

- VanillaUNet + FiLM, 38M params, BCE+Dice. Off-the-shelf.
- **Defuse**: don't claim model novelty. The novelty is in the synthetic-data pipeline + evaluation protocol. Make that explicit in the abstract.

### C2. The synthetic-data pipeline isn't sufficiently described

- 219 GeoJSONs + 8 randomization dimensions is a small contribution presented as a big one.
- A reviewer can say "this is just data augmentation on existing GIS data."
- **Defuse**: present the pipeline as a *methodology pattern* (annotation-free pretraining via real-vector-source rendering) rather than as a specific dataset.

### C3. We don't compare to ICM (Luo 2023)

- The closest architectural prior — 6-channel U-Net with legend-key prompt + OCR — and we don't replicate or compare.
- **Hard to fix in remaining time**. Their code is not public.
- **Defuse**: cite as the closest architectural prior; note that direct replication was infeasible in our time budget; argue that the LOAM (which beat ICM by 4.5%) is sufficient comparison.

---

## Framing / writing attacks

### D1. "Annotation efficiency" framing assumes reader values it

- SIGSPATIAL reviewers from the geosciences community may value correct extraction over fewer annotations.
- They want SOTA on the task, not a story about pretraining.
- **Defuse**: don't put "annotation efficiency" in the abstract's opening sentence. Lead with the diagnostic finding (98% confusable colors structural problem) and the controlled ablation. Annotation efficiency is a consequence, not the headline.

### D2. The failure analysis is descriptive, not prescriptive

- We diagnosed a problem (color confusability) and proposed no solution.
- **Defuse**: acknowledge as limitation; point to "color-distinctiveness-aware conditioning" (TODO 2B) as the natural next step. Limitations sections that acknowledge specific futures look thoughtful, not weak.

### D3. The 98% confusable colors finding is trivially predictable

- "Maps with many similar colors are hard." Of course.
- **Defuse**: the contribution isn't the prediction; it's the *quantification* (CIEDE2000 + per-feature correlation analysis on a 1141-feature benchmark). Reviewers respect quantification of folk knowledge.

---

## What to actually do before submitting

In priority order:

1. **Run TODO 1A.1** (high-LR scratch baseline). [queued, will fire after 1A.2]
2. **Add CIs to every reported number**. [DONE — analyze_finetune_results.py]
3. **Drop LOAM-parity language** from abstract Draft A. [pending]
4. **Sharpen contribution paragraph** to the three precise differentiators (see this doc §A4 defuse). [pending]
5. **Run failure analysis on pretrained_e20 results**. [easy, ~10 min]
6. **Run 1A.2** (composition ablation). [auto-queued]
7. **(Stretch)** Run N=1 and N=5 fine-tunes for partial scaling curve.
8. **(Stretch)** Re-run pretrained fine-tune with seeds 41, 43.

If only the first 5 land before deadline: workshop submission is solid.
If all 8 land: short main-conference paper is plausible.

---

## Index of related claims and where they're defended

| Claim | Where in the paper | Strongest attack | Where defused |
|---|---|---|---|
| "+47% over zero-shot" | Abstract, Sec 4 | Significance? | Bootstrap CI in Table 1 |
| "8.7× over scratch" | Abstract, Sec 4 | Fair LR? | 1A.1 high-LR scratch run + footnote |
| "All 22 maps improve" | Sec 4 results | None — strong claim | n/a |
| "Cross-domain transfer" | Title, Abstract | Stretch framing | Replace with "across aesthetic distributions" |
| "Synthetic data novel" | Intro, Related Work | DIGMAPPER, Arzoumanidis '25 | Three-axis differentiation in §A4 defuse |
| "Annotation efficient" | Abstract | "Why not just use 14 maps?" | Limitations: yes; reframe as "isolating pretrain contribution" |

---

This document should be re-read by anyone working on the paper, including future claude sessions, before claiming the work is ready. Each item has a defuse path; the work is to execute them.
