# Abstract Drafts for SIGSPATIAL 2026

## Draft A — Assumes fine-tuning experiment succeeds

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
> strongly predicted by swatch color distinctiveness (Spearman r = X.XX,
> p < 0.001). When fine-tuned on just 2 annotated geological maps, the
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
> F1 scores up to 0.93 on color-distinctive units, though aggregate performance
> remains limited (median F1 = 0.016) due to the substantial domain gap. We
> find that success is strongly predicted by the target feature's color
> distinctiveness relative to other legend entries (Spearman r = X.XX): the
> model reliably segments features with delta-E > 30 from their nearest
> neighbor (mean F1 = X.XX) but fails on visually similar units. These results
> establish that legend-driven segmentation can be learned from synthetic data
> without domain expertise, and identify color distinctiveness as the key factor
> governing cross-domain transfer success. Code and synthetic data pipeline are
> publicly available.

## Key differences between drafts

- Draft A requires the fine-tuning experiment (Priority 1A) to succeed
- Draft B works with current results + failure analysis (Priority 1B) only
- Draft A is main conference strength; Draft B is workshop/short-paper strength
- Both require the failure analysis (delta-E correlation) to fill in the X.XX placeholders

## Submission target

- **If fine-tuning works:** Main conference paper (10 pages)
- **If fine-tuning is marginal:** Short paper (4 pages) or GeoAI workshop
- **Deadline:** Check https://sigspatial2026.sigspatial.org (typically June)
