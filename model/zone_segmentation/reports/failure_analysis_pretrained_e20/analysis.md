# USGS Failure Analysis (Priority 1B)

**Source**: `results/usgs_eval_vanilla_v2_tiled/results.json`
**Total features evaluated**: 1083
**Features used in analysis** (with delta-E + F1): 1083

## Headline correlations

| Predictor | Pearson | Spearman |
|---|---|---|
| Delta-E to nearest swatch | r=0.245, p=2.68e-16 | r=0.286, p=7.80e-22 |
| log10(area fraction) | r=0.606, p=2.21e-109 | r=0.796, p=3.03e-238 |

## Distinctiveness gating

| Subset | n | Mean F1 | Median F1 |
|---|---:|---:|---:|
| Delta-E < 15 (confusable) | 1066 | 0.1255 | 0.0326 |
| Delta-E > 30 (distinctive) | 1 | 0.0117 | 0.0117 |

## Top 10 features by F1

| map | label | F1 | delta-E | area_frac | n_keys |
|---|---|---:|---:|---:|---:|
| CO_Clifton | Qac_poly | 0.966 | 4.5 | 0.1493 | 19 |
| CA_MarbleCanyon | QTs_poly | 0.957 | 8.9 | 0.0233 | 14 |
| NM_Sunshine | Qao3_poly | 0.949 | 10.1 | 0.0135 | 20 |
| NM_Sunshine | QTsf_poly | 0.917 | 10.8 | 0.0103 | 20 |
| MN | Mbv_poly | 0.903 | 7.1 | 0.0026 | 100 |
| CA_NV_DeathValley | Qay_poly | 0.879 | 5.8 | 0.0959 | 13 |
| AZ_PipeSpring | Qd_poly | 0.876 | 6.3 | 0.0359 | 33 |
| CA_AZ_Needles | Qc2fp_poly | 0.873 | 5.3 | 0.0897 | 34 |
| MN | Psq_poly | 0.867 | 4.9 | 0.0168 | 100 |
| KY_WestFranklin | Qlt_poly | 0.852 | 8.2 | 0.0128 | 9 |

## Bottom 10 features by F1 (excluding F1=0)

| map | label | F1 | delta-E | area_frac | n_keys |
|---|---|---:|---:|---:|---:|
| DC_Frederick | Dp_poly | 0.000 | 4.1 | 0.0000 | 267 |
| DC_Frederick | Dg_poly | 0.000 | 2.6 | 0.0000 | 267 |
| DC_Frederick | CZmt_poly | 0.000 | 4.0 | 0.0000 | 267 |
| DC_Frederick | Ocla_poly | 0.000 | 3.0 | 0.0000 | 267 |
| AZ_PrescottNF | Ywcb_poly | 0.000 | 2.9 | 0.0000 | 180 |
| AZ_PrescottNF | TKr_poly | 0.000 | 1.3 | 0.0000 | 180 |
| OR_Camas | Qbph-pattern_poly | 0.000 | 0.6 | 0.0012 | 27 |
| DC_Frederick | CZscf_poly | 0.000 | 1.7 | 0.0000 | 267 |
| DC_Frederick | Dl_poly | 0.000 | 2.7 | 0.0000 | 267 |
| CA_Elsinore | Tcg_poly | 0.000 | 8.6 | 0.0000 | 29 |

## Plots

- `plots/f1_vs_deltaE.png`
- `plots/f1_vs_area.png`
- `plots/f1_by_n_keys.png`
- `plots/f1_by_deltaE_bin.png`

## Per-feature CSV

`per_feature.csv` has all rows for paper-ready tables.