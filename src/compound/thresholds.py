"""Warning rules and skill scores: rainfall threshold vs compound (rainfall + soil moisture)."""
from __future__ import annotations

import numpy as np
import pandas as pd
from sklearn.metrics import roc_auc_score

# Dahal & Hasegawa (2008, Geomorphology 100:429-443): I = 73.90 * D^-0.79, I in mm/h, D in h.
DH_ALPHA, DH_BETA = 73.90, -0.79


def dahal_hasegawa_exceed(df: pd.DataFrame, windows=(1, 3, 7)) -> np.ndarray:
    """True if mean intensity over any D-day window exceeds the ID threshold."""
    hit = np.zeros(len(df), bool)
    for k in windows:
        D = 24.0 * k
        intensity = df[f"P{k}"].to_numpy() / D
        hit |= intensity >= DH_ALPHA * D ** DH_BETA
    return hit


def contingency(pred: np.ndarray, obs: np.ndarray) -> dict:
    pred, obs = np.asarray(pred, bool), np.asarray(obs, bool)
    tp = int(np.sum(pred & obs)); fp = int(np.sum(pred & ~obs))
    fn = int(np.sum(~pred & obs)); tn = int(np.sum(~pred & ~obs))
    hr = tp / (tp + fn) if tp + fn else np.nan          # hit rate (probability of detection)
    pofd = fp / (fp + tn) if fp + tn else np.nan        # false alarm rate
    far = fp / (tp + fp) if tp + fp else np.nan         # false alarm ratio
    return {"TP": tp, "FP": fp, "FN": fn, "TN": tn, "hit_rate": hr,
            "false_alarm_rate": pofd, "false_alarm_ratio": far, "TSS": hr - pofd,
            "alarm_share": (tp + fp) / len(obs)}


def tune_univariate(score: np.ndarray, obs: np.ndarray, grid=None) -> float:
    """Threshold on a single score that maximises TSS (train data only)."""
    grid = np.linspace(0.5, 0.995, 100) if grid is None else grid
    tss = [contingency(score >= g, obs)["TSS"] for g in grid]
    return float(grid[int(np.nanargmax(tss))])


def tune_bivariate(u: np.ndarray, v: np.ndarray, obs: np.ndarray, grid=None) -> tuple[float, float]:
    """Joint rule U >= a AND V >= b maximising TSS (train data only)."""
    grid = np.linspace(0.5, 0.99, 50) if grid is None else grid
    best, arg = -np.inf, (np.nan, np.nan)
    for a in grid:
        for b in np.r_[0.0, grid]:
            t = contingency((u >= a) & (v >= b), obs)["TSS"]
            if t > best:
                best, arg = t, (float(a), float(b))
    return arg


def auc(score: np.ndarray, obs: np.ndarray) -> float:
    ok = np.isfinite(score)
    if len(np.unique(obs[ok])) < 2:
        return np.nan
    return float(roc_auc_score(obs[ok], score[ok]))


def conditional_surface(u: np.ndarray, v: np.ndarray, obs: np.ndarray, grid: np.ndarray,
                        n_boot: int = 0, seed: int = 0) -> dict:
    """P(L = 1 | U > a, V > b) on a grid, with optional bootstrap 90% intervals."""
    def surf(uu, vv, oo):
        z = np.full((len(grid), len(grid)), np.nan)
        for i, a in enumerate(grid):
            for j, b in enumerate(grid):
                m = (uu > a) & (vv > b)
                if m.sum() >= 20:
                    z[j, i] = oo[m].mean()
        return z
    base = surf(u, v, obs)
    out = {"grid": grid.tolist(), "p": base, "base_rate": float(obs.mean())}
    if n_boot:
        rng = np.random.default_rng(seed)
        boots = []
        for _ in range(n_boot):
            k = rng.integers(0, len(u), len(u))
            boots.append(surf(u[k], v[k], obs[k]))
        b = np.array(boots)
        out["lo"] = np.nanpercentile(b, 5, axis=0)
        out["hi"] = np.nanpercentile(b, 95, axis=0)
    return out
