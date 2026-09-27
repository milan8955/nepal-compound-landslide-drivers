# Results summary

- Unit-days: 140,910 across 77 units; landslide unit-days: 315 (base rate 0.0022)
- Rainfall: P_imerg; labels: coolr
- Best copula (all train days): **student**, Kendall τ = 0.298, CvM p = 0.050
- P(landslide | U>0.9) = 0.01469; with wet soil (V>0.9) = 0.01382; with dry soil (V<=0.5) = 0.019; base rate 0.0040
- AUC on test years: rain only 0.69648, rain + soil 0.69813; gain 0.00165 (90% year-bootstrap CI [0.00085, 0.00403]); within-year mean AUC 0.71571 vs 0.71846

| Rule (test years) | Hit rate | False alarm rate | TSS | TSS 90% CI |
|---|---|---|---|---|
| Dahal–Hasegawa ID | 0.064 | 0.02556 | 0.03844 | [0.02252, 0.07341] |
| P3 ≥ q0.80 | 0.488 | 0.23392 | 0.25408 | [0.1949, 0.37559] |
| P3 ≥ q0.80 & SM ≥ q0.00 | 0.488 | 0.23392 | 0.25408 | [0.1949, 0.37559] |
| Logistic (rain+soil), same alarm rate | 0.496 | 0.23541 | 0.26059 | [0.20481, 0.3746] |
