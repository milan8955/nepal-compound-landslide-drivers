"""Synthetic raw files with a KNOWN answer, used only by the tests.

Landslide probability depends on rainfall AND wet antecedent soil, so a correct pipeline
must find (i) positive dependence and (ii) higher skill for the compound rule.
Never mix these files with real data.
"""
from __future__ import annotations

import json
from datetime import date, timedelta
from pathlib import Path

import numpy as np
import pandas as pd


def write_synthetic(root: Path, n_units: int = 6, years=range(2011, 2026), seed: int = 1) -> None:
    rng = np.random.default_rng(seed)
    raw = root / "data" / "raw"
    raw.mkdir(parents=True, exist_ok=True)
    feats, units = [], [f"D{i}" for i in range(n_units)]
    for i, u in enumerate(units):
        x0 = 82 + i
        poly = [[x0, 27.5], [x0 + 0.9, 27.5], [x0 + 0.9, 28.4], [x0, 28.4], [x0, 27.5]]
        feats.append({"type": "Feature", "properties": {"adm2_name": u},
                      "geometry": {"type": "Polygon", "coordinates": [poly]}})
    (raw / "npl_adm2.geojson").write_text(json.dumps({"type": "FeatureCollection",
                                                      "features": feats}))
    rows, ls = [], []
    for y in years:
        d0, d1 = date(y, 5, 22), date(y, 9, 30)
        n = (d1 - d0).days + 1
        dates = [d0 + timedelta(days=k) for k in range(n)]
        for i, u in enumerate(units):
            wet = rng.random(n) < 0.6
            P = np.where(wet, rng.gamma(0.8, 18 + 4 * i, n), 0.0)
            sm = np.empty(n)
            s = 0.25
            for k in range(n):  # bucket model: soil wets with rain, dries slowly
                s = min(0.55, 0.9 * s + 0.0012 * P[k] + 0.02)
                sm[k] = s
            P3 = pd.Series(P).rolling(3, min_periods=1).sum().to_numpy()
            sm_lag = np.r_[sm[0], sm[:-1]]
            logit = -8.0 + 0.03 * P3 + 25.0 * (sm_lag - 0.32)
            prob = 1 / (1 + np.exp(-logit))
            for k, dd in enumerate(dates):
                rows.append({"unit": u, "date": dd.isoformat(), "P_era5l": P[k] * 1.1,
                             "sm1": sm[k], "sm_rz": sm[k]})
                if dd.month >= 6 and rng.random() < prob[k]:
                    ls.append({"bipad_id": len(ls), "hazard": "landslide",
                               "date_local": dd.isoformat(), "lon": 82 + i + 0.45,
                               "lat": 27.95, "peopleDeathCount": int(rng.random() < 0.2)})
    f = pd.DataFrame(rows)
    f.to_csv(raw / "forcing_era5l.csv", index=False)
    f.assign(P_imerg=f["P_era5l"] / 1.1)[["unit", "date", "P_imerg"]] \
        .to_csv(raw / "forcing_imerg.csv", index=False)
    pd.DataFrame(ls).to_csv(raw / "bipad_landslide.csv", index=False)
