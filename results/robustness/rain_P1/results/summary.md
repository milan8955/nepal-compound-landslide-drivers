# Results summary

- Unit-days: 140,910 across 77 units; landslide unit-days: 3,226 (base rate 0.0229)
- Rainfall: P_imerg; labels: bipad
- Best copula (all train days): **gaussian**, Kendall τ = 0.179, CvM p = 0.010
- P(landslide | U>0.9) = 0.05525; with wet soil (V>0.9) = 0.09235; with dry soil (V<=0.5) = 0.03701; base rate 0.0162
- AUC on test years: rain only 0.69654, rain + soil 0.70758; gain 0.01105 (90% year-bootstrap CI [-0.00208, 0.0244]); within-year mean AUC 0.69564 vs 0.7142

| Rule (test years) | Hit rate | False alarm rate | TSS | TSS 90% CI |
|---|---|---|---|---|
| Dahal–Hasegawa ID | 0.11586 | 0.02377 | 0.09208 | [0.01718, 0.15014] |
| P1 ≥ q0.67 | 0.60913 | 0.33433 | 0.2748 | [0.23985, 0.30769] |
| P1 ≥ q0.67 & SM ≥ q0.00 | 0.60094 | 0.32975 | 0.27118 | [0.22637, 0.30069] |
| Logistic (rain+soil), same alarm rate | 0.62376 | 0.32843 | 0.29533 | [0.24948, 0.3394] |
