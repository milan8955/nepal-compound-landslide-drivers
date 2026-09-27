# Results summary

- Unit-days: 140,910 across 77 units; landslide unit-days: 3,226 (base rate 0.0229)
- Rainfall: P_imerg; labels: bipad
- Best copula (all train days): **gaussian**, Kendall τ = 0.291, CvM p = 0.050
- P(landslide | U>0.9) = 0.05621; with wet soil (V>0.9) = 0.06992; with dry soil (V<=0.5) = 0.03912; base rate 0.0162
- AUC on test years: rain only 0.71607, rain + soil 0.71621; gain 0.00013 (90% year-bootstrap CI [-0.00724, 0.00637]); within-year mean AUC 0.71504 vs 0.71955

| Rule (test years) | Hit rate | False alarm rate | TSS | TSS 90% CI |
|---|---|---|---|---|
| Dahal–Hasegawa ID | 0.11586 | 0.02377 | 0.09208 | [0.01718, 0.15014] |
| P3 ≥ q0.67 | 0.64833 | 0.33508 | 0.31325 | [0.26968, 0.3456] |
| P3 ≥ q0.67 & SM ≥ q0.00 | 0.64833 | 0.33508 | 0.31325 | [0.26864, 0.3461] |
| Logistic (rain+soil), same alarm rate | 0.63078 | 0.33276 | 0.29802 | [0.24584, 0.34301] |
