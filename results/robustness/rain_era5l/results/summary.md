# Results summary

- Unit-days: 140,910 across 77 units; landslide unit-days: 3,226 (base rate 0.0229)
- Rainfall: P_era5l; labels: bipad
- Best copula (all train days): **student**, Kendall τ = 0.435, CvM p = 0.010
- P(landslide | U>0.9) = 0.04577; with wet soil (V>0.9) = 0.05132; with dry soil (V<=0.5) = 0.0306; base rate 0.0162
- AUC on test years: rain only 0.70537, rain + soil 0.70081; gain -0.00456 (90% year-bootstrap CI [-0.01185, 0.00271]); within-year mean AUC 0.70184 vs 0.7009

| Rule (test years) | Hit rate | False alarm rate | TSS | TSS 90% CI |
|---|---|---|---|---|
| Dahal–Hasegawa ID | 0.2206 | 0.06182 | 0.15878 | [0.07363, 0.23219] |
| P3 ≥ q0.59 | 0.67759 | 0.38439 | 0.2932 | [0.24254, 0.32678] |
| P3 ≥ q0.60 & SM ≥ q0.00 | 0.67057 | 0.37891 | 0.29165 | [0.23912, 0.32728] |
| Logistic (rain+soil), same alarm rate | 0.66764 | 0.38238 | 0.28526 | [0.24575, 0.32805] |
