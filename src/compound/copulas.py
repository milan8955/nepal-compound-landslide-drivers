"""Bivariate copula fitting, goodness of fit and tail dependence (via pyvinecopulib)."""
from __future__ import annotations

import numpy as np
import pyvinecopulib as pv
from scipy import stats

FAMILIES = {
    "gaussian": pv.BicopFamily.gaussian, "student": pv.BicopFamily.student,
    "clayton": pv.BicopFamily.clayton, "gumbel": pv.BicopFamily.gumbel,
    "frank": pv.BicopFamily.frank, "joe": pv.BicopFamily.joe, "indep": pv.BicopFamily.indep,
}


def pseudo_obs(x: np.ndarray) -> np.ndarray:
    """Column-wise ranks / (n + 1)."""
    x = np.asarray(x, float)
    return np.column_stack([stats.rankdata(c) / (len(c) + 1) for c in x.T])


def fit_all(u: np.ndarray, families: list[str]) -> list[dict]:
    """Fit each family (all rotations) separately; return rows sorted by AIC."""
    rows = []
    for name in families:
        ctl = pv.FitControlsBicop(family_set=[FAMILIES[name]], selection_criterion="aic")
        b = pv.Bicop.from_data(u, controls=ctl)
        rows.append({"family": name, "rotation": int(b.rotation),
                     "params": np.ravel(b.parameters).round(4).tolist(),
                     "tau": float(b.tau), "aic": float(b.aic(u)), "loglik": float(b.loglik(u)),
                     "model": b})
    return sorted(rows, key=lambda r: r["aic"])


def empirical_copula(u: np.ndarray, pts: np.ndarray) -> np.ndarray:
    """C_n(a, b) = share of observations with U <= a and V <= b."""
    return np.array([np.mean((u[:, 0] <= a) & (u[:, 1] <= b)) for a, b in pts])


def cvm_statistic(u: np.ndarray, model: pv.Bicop) -> float:
    """Cramér–von Mises distance between empirical and fitted copula at the data points."""
    return float(np.sum((empirical_copula(u, u) - model.cdf(u)) ** 2))


def cvm_gof(u: np.ndarray, model: pv.Bicop, n_boot: int = 100, seed: int = 0,
            max_n: int = 1500) -> dict:
    """Parametric-bootstrap p-value for the CvM statistic (Genest et al. 2009).

    Each replicate: simulate from the fitted copula, re-fit the same family, recompute CvM.
    For speed, large samples are subsampled to `max_n` points (reported in the output).
    """
    rng = np.random.default_rng(seed)
    if len(u) > max_n:
        u = u[rng.choice(len(u), max_n, replace=False)]
        u = pseudo_obs(u)
    fam = model.family
    s_obs = cvm_statistic(u, model)
    ctl = pv.FitControlsBicop(family_set=[fam], selection_criterion="aic")
    s_boot = []
    for _ in range(n_boot):
        sim = pseudo_obs(model.sample(len(u), seeds=[int(rng.integers(1e9))]))
        m = pv.Bicop.from_data(sim, controls=ctl)
        s_boot.append(cvm_statistic(sim, m))
    pval = (1 + np.sum(np.array(s_boot) >= s_obs)) / (n_boot + 1)
    return {"cvm": s_obs, "p_value": float(pval), "n_used": int(len(u)), "n_boot": n_boot}


def upper_tail_curve(u: np.ndarray, model: pv.Bicop | None, qs: np.ndarray) -> dict:
    """Finite-level upper tail dependence lambda(q) = P(V > q | U > q), empirical vs model."""
    emp = np.array([np.mean((u[:, 0] > q) & (u[:, 1] > q)) / np.mean(u[:, 0] > q) for q in qs])
    out = {"q": qs.tolist(), "empirical": emp.tolist()}
    if model is not None:
        c = model.cdf(np.column_stack([qs, qs]))
        out["model"] = ((1 - 2 * qs + c) / (1 - qs)).tolist()
    return out
