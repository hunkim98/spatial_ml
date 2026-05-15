# Related Work Survey — Map Feature Extraction & Historical Map Segmentation

Combines (1) LOAM's bibliography extracted from `usgs/polygon_metadata_oldmaps.pdf`, (2) web search of post-LOAM 2023 work and DARPA CMA outcomes, (3) ICDAR 2021 MapSeg context. Goal: position our paper without tunnel-vision on LOAM.

## 1. The three methods that matter most for our paper

These are the direct comparisons. The first two are head-to-head on the same DARPA CMA benchmark we use.

### 1.1 LOAM (Lin et al., SIGSPATIAL '23) — what we've been comparing against

- **Lin, F., Knoblock, C.A., Shbita, B., Vu, B., Li, Z., Chiang, Y.-Y.** (2023). "Exploiting Polygon Metadata to Understand Raster Maps - Accurate Polygonal Feature Extraction." SIGSPATIAL '23. [DOI](https://doi.org/10.1145/3589132.3625659)
- **Method**: 7-channel bitmap stack (color thresholds, color differencing, boundary detection, etc.) + auxiliary info embedding (32-d color set + 9-d metadata vectors) → U-Net with Shuffle Attention + custom modulation layer. Multi-task: polygon mask + boundary mask.
- **Training data**: 14 real USGS maps from DARPA CMA validation set (~536 keys).
- **Test results**: median F1 **0.809** (pixel-weighted, easy/hard split).
- **Affiliation**: USC ISI / UMN (Chiang group).
- **Code**: github.com/Fandel-Lin/LOAM (we cloned + ran their pretrained checkpoint in Phase 0).
- **For us**: NOT our competitor framing. LOAM is supervised on real maps. We're zero-/few-shot from synthetic data — *different problem*. Don't claim parity; cite as a "with annotations, this is what's possible."

### 1.2 ICM / Luo et al. (IEEE LGRS '23) — actual DARPA CMA polygon winner

- **Luo, S. et al.** (2023). "Critical minerals map feature extraction using deep learning." IEEE Geoscience and Remote Sensing Letters, vol. 20, pp. 1-5. [DOI](https://doi.org/10.1109/LGRS.2023.3310915)
- **LOAM cites this as ref [12]** — their direct predecessor and benchmark.
- **Method**: OCR + adaptive histogram equalization + **6-channel U-Net that takes the map key as a prompt**. Data augmentation: re-scaling, channel shuffle, RGB shift.
- **For us**: This is the most directly comparable architecture — pattern-conditioned segmentation with a small input channel stack. Worth reading their preprocessing in detail. Their data aug strategy is what we should compare to.
- **Why LOAM frames itself against ICM**: LOAM's 4.52% improvement claim is over ICM, not over LOAM itself.

### 1.3 DIGMAPPER (Duan et al., SIGSPATIAL '25) — newest geologic-map work, post-LOAM

- **Duan, W., Gerlek, M.P., Minton, S.N., Knoblock, C.A., Lin, F., Chen, T., Jang, L., Kirsanova, S., Li, Z., Lin, Y., Chiang, Y.-Y.** (2025). "DIGMAPPER: A Modular System for Automated Geologic Map Digitization." SIGSPATIAL '25. [arXiv:2506.16006](https://arxiv.org/abs/2506.16006), [DOI](https://doi.org/10.1145/3748636.3764602)
- **Method**: Modular pipeline — map layout analysis, feature extraction (polygon/line/point), georeferencing. Dockerized, deployed at USGS. Notably their abstract explicitly mentions **"synthetic data generation"** as a component technique.
- **Training data**: 100+ annotated USGS maps from DARPA-USGS dataset.
- **For us**: **Concurrent work that also uses synthetic data.** Cannot claim we are "the first to use synthetic data for USGS map extraction" — that's no longer true. Must position our contribution more precisely (see §4 below). Cite as the most current SOTA on this benchmark.

## 2. Other LOAM references that matter for our framing

From the 17-ref bibliography on pages 10-12. Grouped by what they're useful for.

### 2.1 The map-processing survey (must cite)
- **Chiang, Y.-Y. et al.** (2014). "A survey of digital map processing techniques." ACM Computing Surveys 47(1), 1-44.
  - The canonical survey. Pre-dates deep learning. Useful for general context: "Map processing has been studied for decades; we focus on the legend-driven polygon extraction subproblem."

### 2.2 Adjacent map-processing review (worth citing)
- **Liu, T. et al.** (2019). "A review of recent advances in scanned topographic map processing." Neurocomputing 328, 75-87.
  - More recent than Chiang 2014. Covers the deep learning era.

### 2.3 Foundation models cited by LOAM
- **Kirillov, A. et al.** (2023). "Segment Anything." arXiv:2304.02643.
- **Ji, W. et al.** (2023). "Segment anything is not always perfect..." arXiv:2304.05750.
  - LOAM explicitly notes SAM doesn't apply to their problem (not key-conditioned, not fully automated). We should make a similar note.

### 2.4 Generic segmentation backbones
- **Ronneberger, O. et al.** (2015). "U-Net..." MICCAI 2015.
- **He, K. et al.** (2017). "Mask R-CNN." ICCV.
- **Zhang & Yang** (2021). "SA-Net: Shuffle Attention..." ICASSP.
  - U-Net citation is mandatory. SA-Net only matters if you're replicating LOAM's attention; we're not.

### 2.5 Building / non-map polygon extraction (less central but cited)
- **Arteaga** (2013). Historical map polygon extractor — image-processing era, pre-deep-learning. SIGSPATIAL workshop.
- **Chen, W. et al.** (2022). Building detection from LiDAR. SIGSPATIAL '22.
- **Song & Jung** (2022). Building extraction from airborne LiDAR.
- **Zorzi, S. et al.** (2022). "PolyWorld: polygonal building extraction with GNNs." CVPR '22.
- **Lee, D.G. et al.** (2020). SegNet for land cover.
- **Li, Z. et al.** (2019). Topological map extraction.
- **Wang, X. et al.** (2022). "FreeSOLO: weakly supervised instance segmentation." CVPR '22.

For our paper: these are weak adjacent work. Cite at most 1-2 to acknowledge the broader "polygon extraction" space, then narrow to our specific problem.

## 3. Beyond LOAM's bibliography — what else is out there

### 3.1 DARPA CMA competition outcomes

[DARPA news release](https://www.darpa.mil/news/2022/critical-minerals-assessement-winners), [USC ISI news](https://www.isi.edu/news/53660/usc-wins-darpa-map-feature-extraction-challenge/).

- **18 teams** competed. 1st USC-UMN, 2nd "Team ICM" (UIUC), 3rd "Uncharted."
- Polygon-specific ranking: **1st ICM (Luo et al., §1.2)**, 2nd Uncharted (no publication), 3rd unknown.
- The USC group's competition submission was followed by the LOAM paper (Lin '23) as a refinement.
- For our paper: cite the dataset (Goldman et al., USGS data release, [DOI: 10.5066/P9FXSPT1](https://doi.org/10.5066/P9FXSPT1)) and acknowledge the competition.

### 3.2 ICDAR 2021 Historical Map Segmentation Competition

[ICDAR21-MapSeg site](https://icdar21-mapseg.github.io/), [Springer LNCS chapter](https://link.springer.com/chapter/10.1007/978-3-030-86337-1_46).

- **Different dataset**: Paris historical atlases (1894-1937), 1/5000 scale. Building blocks, map content, intersection points.
- **Tasks 1 (building blocks)**: won by L3IRIS team with **DenseNet-121 + weakly supervised**.
- **Tasks 2 (map content), 3 (intersection points)**: won by UWB team with **U-Net-like FCN + morphological postprocessing**.
- **Heuvel et al.** (ICDAR '21). "Vectorization of Historical Maps Using Deep Edge Filtering and Closed Shape Extraction." [Springer chapter](https://link.springer.com/chapter/10.1007/978-3-030-86337-1_34).
- **For us**: NOT the same task (building blocks vs legend-keyed polygons). But useful as a "historical map segmentation has multiple subproblems; we work on legend-driven polygon extraction" framing. Cite the competition paper.

### 3.3 Other recent work (2024-2025)

- **GCN-based semantic segmentation of historical maps** — [Self-Constructing Graph Convolutional Networks paper](https://www.tandfonline.com/doi/full/10.1080/15230406.2025.2468304) (Cartography & Geographic Information Science 2025). GCNs capture long-range dependencies; complementary to CNNs.
- **FCN-Boosted Historical Map Segmentation with Little Training Data** — Baloun, Lenc, Král (ICDAR 2023). Directly tackles the "minimal training data" angle we care about.

### 3.4 Concurrent arXiv 2025 work (THE most important new finds)

These post-date LOAM and overlap heavily with our contribution. Discovered after the initial survey via dedicated search.

#### Sterzinger et al. (ICDAR '25) — few-shot historical maps via foundation models

- **Sterzinger, R., Peer, M., Sablatnig, R.** (2025). "Few-Shot Segmentation of Historical Maps via Linear Probing of Vision Foundation Models." [arXiv:2506.21826](https://arxiv.org/abs/2506.21826).
- **Method**: linear probing of frozen vision foundation models — trains only a small classification head (~689k params, 0.21% of total) on foundation features.
- **Datasets**: Siegfried (vineyard, railway) + ICDAR 2021 (building blocks). **NOT DARPA CMA / USGS.**
- **Results**: +20% relative mIoU in 5-shot, +5–13% in 10-shot vs baselines. mean PQ 67.3% on ICDAR 2021 buildings.
- **For us**: The closest "few-shot historical map" prior. Different dataset, different task (generic seg vs legend-driven). Our differentiation: (1) we do legend-/pattern-conditioned segmentation, not generic; (2) we pretrain on synthetic, not foundation models; (3) we use a 38M-param small model, not foundation features.

#### Arzoumanidis et al. (arXiv '25) — synthetic data bootstrapping for historical maps

- **Arzoumanidis, L., Knechtel, J., Haunert, J.-H., Dehbi, Y.** (2025). "Automatic Uncertainty-Aware Synthetic Data Bootstrapping for Historical Map Segmentation." [arXiv:2511.15875](https://arxiv.org/abs/2511.15875).
- **Method**: transfer cartographic style of historical-map corpus onto modern vector data; combine a deep generative model + manual stochastic degradation. "Uncertainty-aware" = emulate aleatoric uncertainty in scanned historical documents.
- **Datasets**: un-named "homogeneous map corpus" (not DARPA CMA).
- **For us**: The most direct "synthetic data for historical maps" concurrent prior. Their angle is **degradation/noise emulation**; ours is **rendering-style randomization with legend-driven pairs**. Different problem framing (generic seg vs key-conditioned). Must acknowledge + differentiate explicitly.

## 4. Methodological landscape — sharpened after §3.4

The 2025 concurrent work means "we use synthetic data" is no longer a differentiator. Sharpened picture:

| Approach family | Example | Task framing | Data source | Our differentiator |
|---|---|---|---|---|
| Classical image processing | Arteaga '13, Comaniciu '02 | Single feature | Hand-tuned | Learning + multi-feature |
| Supervised CNN, real-map training | LOAM '23, ICM '23 | **Legend-driven** | 14+ real USGS maps | We use 2 maps + synthetic prior |
| Modular system w/ synthetic gen | **DIGMAPPER '25** | **Legend-driven** | 100+ real + synthetic | We isolate the *pretraining contribution* via ablation; they don't |
| Few-shot via foundation models | Sterzinger '25 | Generic (not key-conditioned) | ICDAR/Siegfried, frozen FM features | We are key-conditioned; we use small models; different benchmark |
| Synthetic data for historical maps | Arzoumanidis '25 | Generic (not key-conditioned) | Style-transferred synthetic | We are key-conditioned; we render from GeoJSON, not transfer existing |
| Foundation-model zero-shot | SAM '23 | Click-prompted | Frozen | No key-conditioning primitive |
| **OUR WORK** | — | **Legend-/pattern-conditioned cross-domain** | Synthetic zoning maps + 2 USGS | (combination not previously published) |

### What our paper claims, after this survey

**Old framing (now too weak)**: "Synthetic data for historical map segmentation."
→ Already done by DIGMAPPER and Arzoumanidis.

**Better framing**: Three orthogonal claims, each defensible against the concurrent work:

1. **Cross-domain pretraining works** — synthetic *zoning* maps train a model that transfers to real *geological* maps via fine-tune. Not the same domain → different problem from DIGMAPPER/Arzoumanidis (both train + test on same map type).
2. **Pattern-conditioned setup** — we condition on a 32×32 swatch (legend key), so the model is a *single* network that handles any feature class. LOAM does this; DIGMAPPER does this; Sterzinger and Arzoumanidis do generic seg without key conditioning.
3. **Clean pretrained-vs-scratch isolation** — we run the same fine-tune protocol on synthetic-pretrained AND randomly-initialized networks. The **8.7× ratio** (preliminary) on held-out USGS maps directly attributes the gain to the synthetic prior, not the fine-tune procedure. None of the concurrent works do this ablation.

Combined: *"a synthetic-pretraining + 2-map fine-tune pipeline that achieves measurable cross-domain transfer with isolated attribution of gains to the synthetic prior."*

## 5. Suggested Related Work section for our short paper (~1 paragraph, revised)

> "Polygon feature extraction from raster maps has a long history \cite{chiang2014survey, liu2019topomap}. The 2022 DARPA Critical Mineral Assessment Competition \cite{goldman2023cma} produced the first deep-learning systems for legend-keyed polygon extraction from USGS geological maps: the ICM team \cite{luo2023icm} used a 6-channel U-Net with the legend swatch as input prompt and OCR-based text matching, and the subsequent LOAM system \cite{lin2023loam} achieved median F1 0.809 by encoding seven hand-crafted preprocessing channels plus auxiliary color and metadata vectors into a shuffle-attention U-Net. Both required 14+ manually annotated USGS maps for training. The DIGMAPPER system \cite{duan2025digmapper} extends this line into a modular USGS-deployed pipeline that also incorporates synthetic data generation. Concurrent work on historical maps (a related but distinct task — not legend-keyed) explores few-shot foundation-model probing \cite{sterzinger2025fewshot} and synthetic-data bootstrapping with degradation modeling \cite{arzoumanidis2025synthetic}, both evaluated on Paris-atlas and Siegfried datasets rather than the DARPA CMA benchmark. The ICDAR 2021 Historical Map Segmentation competition \cite{chazalon2021icdarmapseg} addresses a parallel problem on Paris atlases. Foundation models for natural images such as SAM \cite{kirillov2023sam} provide strong general segmentation but lack the key-conditioned primitive these methods require. Our work differs from the prior art on three axes: (i) we evaluate **cross-domain transfer** — pretraining on synthetic zoning maps and testing on real geological maps, a setting none of the concurrent works address; (ii) we retain the legend-key-conditioned task framing (unlike \cite{sterzinger2025fewshot, arzoumanidis2025synthetic}); (iii) we isolate the *contribution* of the synthetic prior through a matched pretrained-vs-scratch ablation that, to our knowledge, has not been previously reported on this benchmark."

This positions us:
- Acknowledges the competition history (LOAM, ICM, DIGMAPPER's continuation)
- Acknowledges the concurrent few-shot + synthetic work explicitly
- Stakes three precise differentiators, each defensible against a specific concurrent paper
- Closes with SAM acknowledgement so reviewers don't ask

## 6. Concrete TODO follow-ups from this survey

1. **DIGMAPPER arxiv 2506.16006** ✅ found (see §1.3) — cite as concurrent USGS-deployed system that *also* uses synthetic data. Differentiation: they integrate as pipeline component; we isolate via pretrained-vs-scratch ablation.
2. **Sterzinger 2025 (ICDAR)** ✅ — closest few-shot prior on historical maps. Differentiation: they use foundation-model features on generic seg; we use small custom model on key-conditioned task.
3. **Arzoumanidis 2025** ✅ — closest synthetic-data prior on historical maps. Differentiation: they emulate degradation; we render from real GeoJSON sources with paired masks.
4. **Read Luo 2023 (ICM)** in detail (still pending) — closest architecture. Their data augmentation may inform our 2C "improve synthetic" follow-up.
5. **Goldman 2023 dataset citation** ✅ in bib.

Skip:
- Re-reading LOAM's bibliography of building / LiDAR / GNN papers — too tangential for a short paper.
- SAM/SAM2 deep dive — one sentence is enough.
- Older surveys beyond Chiang 2014 and Liu 2019.

## 7. Bottom-line — what this means for the next 2 days of writing

- **Differentiation paragraph (§5)** is the most important paragraph in the paper. Get it right and the rest follows.
- **Run the matched pretrained-vs-scratch ablation cleanly** — this is the one thing no concurrent paper has done. Final numbers from current chain + 1A.2 will populate Table 2.
- **Don't oversell synthetic data** — DIGMAPPER and Arzoumanidis already use it. Our specific synthetic-data pipeline (rendering from GeoJSON with 8 randomized dimensions) is a contribution, but it's a smaller one than we previously assumed.
- **The cross-domain claim (zoning → geology) is now the strongest unique angle.** Lead with it in the abstract.
