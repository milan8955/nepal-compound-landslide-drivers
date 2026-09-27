# Results summary

- Unit-days: 140,910 across 77 units; landslide unit-days: 3,226 (base rate 0.0229)
- Rainfall: P_imerg; labels: bipad
- Best copula (all train days): **gaussian**, Kendall τ = 0.400, CvM p = 0.030
- P(landslide | U>0.9) = 0.05621; with wet soil (V>0.9) = 0.07284; with dry soil (V<=0.5) = 0.03701; base rate 0.0162
- AUC on test years: rain only 0.71607, rain + soil 0.72195; gain 0.00588 (90% year-bootstrap CI [0.00251, 0.00936]); within-year mean AUC 0.71504 vs 0.72344

| Rule (test years) | Hit rate | False alarm rate | TSS | TSS 90% CI |
|---|---|---|---|---|
| Dahal–Hasegawa ID | 0.11586 | 0.02377 | 0.09208 | [0.01718, 0.15014] |
| P3 ≥ q0.67 | 0.64833 | 0.33508 | 0.31325 | [0.26968, 0.3456] |
| P3 ≥ q0.67 & SM ≥ q0.00 | 0.64833 | 0.33508 | 0.31325 | [0.26864, 0.3461] |
| Logistic (rain+soil), same alarm rate | 0.63019 | 0.3216 | 0.30859 | [0.25868, 0.35686] |
