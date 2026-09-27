"""Marginal distributions: rank transforms and extreme-value fits (GPD / GEV)."""
from __future__ import annotations

import numpy as np
import pandas as pd
from scipy import stats


def ecdf_transform(train: np.ndarray, x: np.ndarray) -> np.ndarray:
    """Pseudo-observations in (0, 1) for x using the empirical CDF of `train`.

    Uses mid-ranks for ties (common for zero rainfall) and the n+1 denominator so no value
    reaches 0 or 1. Fitting on train only keeps test years out of the marginal model.
    """
    t = np.sort(np.asarray(train, float)[~np.isnan(train)])
    x = np.asarray(x, float)
    lo = np.searchsorted(t, x, side="left")
    hi = np.searchsorted(t, x, side="right")
    u = (lo + hi) / 2.0 + 0.5
    u = u / (len(t) + 1)
    u[np.isnan(x)] = np.nan
    return np.clip(u, 0.5 / (len(t) + 1), 1 - 0.5 / (len(t) + 1))


def per_unit_uniform(df: pd.DataFrame, col: str, train_mask: pd.Series) -> pd.Series:
    """Transform `col` to uniforms separately within each unit (removes climatology)."""
    out = pd.Series(np.nan, index=df.index)
    for _, idx in df.groupby("unit").groups.items():
        sub = df.loc[idx]
        tr = sub.loc[train_mask.loc[idx], col].to_numpy()
        if np.isfinite(tr).sum() < 30:
            continue
        out.loc[idx] = ecdf_transform(tr, sub[col].to_numpy())
    return out


def fit_gpd(x: np.ndarray, q: float = 0.9) -> dict:
    """Peaks-over-threshold GPD fit (location fixed at 0 on exceedances)."""
    x = np.asarray(x, float)
    x = x[np.isfinite(x)]
    u = np.quantile(x, q)
    exc = x[x > u] - u
    c, _, scale = stats.genpareto.fit(exc, floc=0)
    return {"threshold": float(u), "shape": float(c), "scale": float(scale),
            "n_exc": int(len(exc)), "zeta": len(exc) / len(x)}


def gpd_return_level(fit: dict, T_years: np.ndarray, obs_per_year: float) -> np.ndarray:
    """Return level exceeded on average once every T years (Coles 2001, eq. 4.13)."""
    m = np.asarray(T_years, float) * obs_per_year * fit["zeta"]
    xi, s, u = fit["shape"], fit["scale"], fit["threshold"]
    if abs(xi) < 1e-6:
        return u + s * np.log(m)
    return u + s / xi * (m ** xi - 1)


def mean_residual_life(x: np.ndarray, thresholds: np.ndarray) -> pd.DataFrame:
    x = np.asarray(x, float)
    x = x[np.isfinite(x)]
    rows = []
    for u in thresholds:
        e = x[x > u] - u
        if len(e) > 10:
            rows.append({"u": u, "mean_excess": e.mean(),
                         "ci": 1.96 * e.std(ddof=1) / np.sqrt(len(e)), "n": len(e)})
    return pd.DataFrame(rows)


def parameter_stability(x: np.ndarray, quantiles: np.ndarray) -> pd.DataFrame:
    rows = []
    for q in quantiles:
        f = fit_gpd(x, q)
        # modified scale sigma* = sigma - xi * u is constant above a valid threshold
        rows.append({"q": q, "u": f["threshold"], "shape": f["shape"],
                     "mod_scale": f["scale"] - f["shape"] * f["threshold"], "n": f["n_exc"]})
    return pd.DataFrame(rows)


def fit_gev(block_maxima: np.ndarray) -> dict:
    c, loc, scale = stats.genextreme.fit(np.asarray(block_maxima, float))
    # scipy's c has the opposite sign to the usual xi
    return {"shape_xi": float(-c), "loc": float(loc), "scale": float(scale)}
