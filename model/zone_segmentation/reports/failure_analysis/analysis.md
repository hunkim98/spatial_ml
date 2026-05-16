# USGS Failure Analysis (Priority 1B)

**Source**: `results/usgs_eval_vanilla_v2_tiled/results.json`
**Total features evaluated**: 1141
**Features used in analysis** (with delta-E + F1): 1141

## Headline correlations

| Predictor | Pearson | Spearman |
|---|---|---|
| Delta-E to nearest swatch | r=0.253, p=3.62e-18 | r=0.209, p=1.09e-12 |
| log10(area fraction) | r=0.446, p=6.27e-57 | r=0.483, p=1.20e-67 |

## Distinctiveness gating

| Subset | n | Mean F1 | Median F1 |
|---|---:|---:|---:|
| Delta-E < 15 (confusable) | 1122 | 0.0885 | 0.0152 |
| Delta-E > 30 (distinctive) | 1 | 0.5608 | 0.5608 |

## Top 10 features by F1

| map | label | F1 | delta-E | area_frac | n_keys |
|---|---|---:|---:|---:|---:|
| MN | Psq_poly | 0.905 | 4.9 | 0.0168 | 100 |
| CO_Clifton | Qac_poly | 0.882 | 4.5 | 0.1493 | 19 |
| NV_HiddenHills | Qai_poly | 0.867 | 5.8 | 0.0742 | 14 |
| CA_AZ_Needles | sw_poly | 0.835 | 5.9 | 0.0087 | 34 |
| CA_Elsinore | Tsi_poly | 0.813 | 9.9 | 0.0042 | 29 |
| NM_Sunshine | Tsb_poly | 0.801 | 11.4 | 0.0725 | 20 |
| CA_MarbleCanyon | Pd_poly | 0.782 | 14.0 | 0.0164 | 14 |
| CA_MarbleCanyon | QTs_poly | 0.772 | 8.9 | 0.0233 | 14 |
| NM_Sunshine | QTsf_poly | 0.757 | 10.8 | 0.0103 | 20 |
| AZ_PrescottNF | Tlal_poly | 0.753 | 6.8 | 0.0030 | 180 |

## Bottom 10 features by F1 (excluding F1=0)

| map | label | F1 | delta-E | area_frac | n_keys |
|---|---|---:|---:|---:|---:|
| CA_NV_DeathValley | Qayy_poly | 0.000 | 8.1 | 0.0064 | 13 |
| CA_AZ_Needles | Qc1ch_poly | 0.000 | 5.3 | 0.0073 | 34 |
| CO_Alamosa | Xag_poly | 0.000 | 7.7 | 0.0016 | 71 |
| CO_Clifton | Qls_poly | 0.000 | 2.9 | 0.0054 | 19 |
| DC_Frederick | CZo_poly | 0.000 | 4.2 | 0.0000 | 267 |
| KY_WestFranklin | Ql_poly | 0.000 | 12.0 | 0.0946 | 9 |
| AZ_PipeSpring | Pkh_poly | 0.000 | 9.8 | 0.0266 | 33 |
| MN | Pas_poly | 0.000 | 3.9 | 0.0318 | 100 |
| CA_MarbleCanyon | Jh_poly | 0.000 | 7.4 | 0.0117 | 14 |
| DC_Frederick | CZim_poly | 0.000 | 1.8 | 0.0000 | 267 |

## Plots

- `plots/f1_vs_deltaE.png`
- `plots/f1_vs_area.png`
- `plots/f1_by_n_keys.png`
- `plots/f1_by_deltaE_bin.png`

## Per-feature CSV

`per_feature.csv` has all rows for paper-ready tables.