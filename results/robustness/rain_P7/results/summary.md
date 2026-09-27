# Results summary

- Unit-days: 140,910 across 77 units; landslide unit-days: 3,226 (base rate 0.0229)
- Rainfall: P_imerg; labels: bipad
- Best copula (all train days): **gaussian**, Kendall τ = 0.374, CvM p = 0.010
- P(landslide | U>0.9) = 0.04929; with wet soil (V>0.9) = 0.06279; with dry soil (V<=0.5) = 0.036; base rate 0.0162
- AUC on test years: rain only 0.69683, rain + soil 0.69334; gain -0.00349 (90% year-bootstrap CI [-0.01092, 0.00505]); within-year mean AUC 0.69589 vs 0.69743

| Rule (test years) | Hit rate | False alarm rate | TSS | TSS 90% CI |
|---|---|---|---|---|
| Dahal–Hasegawa ID | 0.11586 | 0.02377 | 0.09208 | [0.01718, 0.15014] |
| P7 ≥ q0.69 | 0.5945 | 0.32885 | 0.26565 | [0.20772, 0.3243] |
| P7 ≥ q0.69 & SM ≥ q0.00 | 0.58865 | 0.32355 | 0.2651 | [0.2014, 0.32529] |
| Logistic (rain+soil), same alarm rate | 0.56758 | 0.31769 | 0.24989 | [0.18097, 0.3147] |
