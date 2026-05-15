# Abstract Drafts for SIGSPATIAL 2026

## Draft A — REVISED 2026-05-12 (drops LOAM-parity language per HARSH_CRITIQUE §A1, A2, A3)

> Legend-driven polygon extraction from historical raster maps — finding all
> pixels in a map that match a queried legend swatch — has motivated several
> supervised systems on the DARPA Critical Mineral Assessment benchmark, each
> requiring 14+ hand-annotated USGS maps for training. We study what can be
> recovered from synthetic pretraining and minimal real supervision. Our pipeline
> renders unlimited (image, pattern, mask) triplets from 219 US municipal zoning
> GeoJSONs with 8 randomized rendering dimensions — producing 27,000+ triplets
> at zero annotation cost — and trains a FiLM-conditioned U-Net to perform
> legend-driven segmentation. Evaluated on the DARPA CMA validation set with
> aesthetic distribution unseen during pretraining, the zero-shot model
> achieves F1 up to 0.93 on individual features but median F1 only 0.016,
> a gap we trace to a structural property of the benchmark:
> 98% of USGS legend swatches have a CIEDE2000 distance below 15 to the
> nearest other swatch in the same map. Within this structurally adversarial
> regime, fine-tuning the pretrained model on just 2 USGS maps produces
> measurable held-out improvement on the remaining 22 maps (mean F1
> 0.126 vs 0.086 zero-shot; paired bootstrap Δ = +0.040, 95% CI
> [+0.031, +0.050], P > 0.999), with every map showing positive gain. A
> randomly initialized network trained on the same 2 maps with identical
> hyperparameters achieves only F1 = 0.014 (paired bootstrap Δ vs pretrained
> = +0.111, 95% CI [+0.095, +0.127], P > 0.999), isolating the contribution
> of the synthetic prior to the encoder representation rather than to the
> fine-tune procedure itself. We do not claim parity with the supervised
> state of the art; our contribution is a controlled isolation of synthetic
> pretraining's effect on this benchmark, together with a quantitative
> diagnosis of why the task remains hard.

## Draft A (older version, kept for diff/history)

> Extracting polygonal features from historical raster maps remains bottlenecked
> by the cost of manual annotation: existing state-of-the-art methods require
> domain-expert labeling of dozens of maps per target domain. We present a
> synthetic pretraining framework that eliminates this requirement. Our pipeline
> generates unlimited (image, pattern, mask) training triplets from 219 US city
> zoning GeoJSONs with 8 randomized rendering dimensions—including simulated
> aging, hatching, and basemap variation—producing 27,000+ triplets at zero
> annotation cost. A FiLM-conditioned U-Net trained on this synthetic data
> learns general legend-driven segmentation: given a map image and a legend
> swatch query, produce the corresponding binary mask. We evaluate cross-domain
> transfer on USGS geological maps from the DARPA Critical Mineral Assessment
> benchmark—a domain never seen during pretraining. Zero-shot transfer achieves
> F1 up to 0.93 on color-distinctive geological units, with performance
> significantly predicted by swatch color distinctiveness (Spearman r = 0.21,
> p < 1e-12) and feature area (Pearson r = 0.45 in log space, p < 1e-56).
> When fine-tuned on just 2 annotated geological maps, the
> pretrained model achieves [X.XX] median F1, matching [YY]% of LOAM's fully
> supervised performance (0.809 F1, trained on 14 annotated maps) while
> requiring 7x less real annotation. Models initialized from scratch and
> fine-tuned on the same 2 maps achieve only [Z.ZZ] F1, confirming that
> synthetic pretraining provides meaningful feature transfer. Our synthetic
> pipeline is domain-agnostic and requires no modification to target new map
> types, suggesting a path toward general-purpose map digitization with minimal
> per-domain supervision.

## Draft B — Conservative (if fine-tuning improvement is modest)

> Digitizing historical raster maps into machine-readable vector data requires
> legend-driven segmentation—identifying all pixels belonging to a queried
> legend category—which existing methods solve through domain-specific
> preprocessing and extensive manual annotation. We investigate whether this
> task can instead be learned from synthetic data alone. We present a pipeline
> that generates unlimited (image, pattern, mask) training triplets from real
> municipal zoning GeoJSONs with randomized rendering styles, and train a
> FiLM-conditioned U-Net that segments map images conditioned on a pattern
> query. Trained entirely on synthetic zoning maps, the model achieves 0.559
> IoU on held-out synthetic data. On real USGS geological maps from the DARPA
> CMA benchmark—a domain never seen during training—zero-shot transfer produces
> F1 scores up to 0.93 on individual features, though aggregate performance is
> limited (median F1 = 0.016, mean F1 = 0.091, n = 1141 features across 24
> maps) by a substantial and structural domain gap: 98% of USGS legend
> swatches have a CIEDE2000 distance below 15 to the nearest other swatch in
> the same map, and 59% have a near-duplicate (delta-E < 5). Within this
> difficult regime, per-feature F1 correlates significantly with color
> distinctiveness (Spearman r = 0.21, p < 1e-12) and with feature area
> fraction (Pearson r = 0.45 in log space, p < 1e-56); mean F1 rises from
> 0.061 in the dominant delta-E < 5 bin to 0.235 in the rare delta-E
> ∈ [15, 20] bin, a 3.9× ratio. These results establish that legend-driven
> segmentation can be learned from synthetic data without domain expertise,
> identify swatch confusability as a structural property of the USGS benchmark,
> and isolate color distinctiveness and feature area as the two factors
> governing cross-domain transfer success. Code and synthetic data pipeline
> are publicly available.

## Key differences between drafts

- Draft A requires the fine-tuning experiment (Priority 1A) to succeed
- Draft B works with current results + failure analysis (Priority 1B) only
- Draft A is main conference strength; Draft B is workshop/short-paper strength
- Both require the failure analysis (delta-E correlation) to fill in the X.XX placeholders

## Submission target

- **If fine-tuning works:** Main conference paper (10 pages)
- **If fine-tuning is marginal:** Short paper (4 pages) or GeoAI workshop
- **Deadline:** Check https://sigspatial2026.sigspatial.org (typically June)
