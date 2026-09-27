"""Multivariate return periods (Salvadori, De Michele & Durante 2011).

All periods are in years. With daily monsoon data, mu = 1 / (days per season) years is
the mean inter-arrival time between observations. Daily values are serially dependent, so
treat these as indicative hazard levels, not exact recurrence intervals.
"""
from __future__ import annotations

import numpy as np


def p_and(u, v, C) -> np.ndarray:
    """P(U > u and V > v) = 1 - u - v + C(u, v)."""
    return 1.0 - np.asarray(u) - np.asarray(v) + C(np.column_stack([u, v]))


def p_or(u, v, C) -> np.ndarray:
    """P(U > u or V > v) = 1 - C(u, v)."""
    return 1.0 - C(np.column_stack([u, v]))


def kendall_function(C, sample: np.ndarray):
    """K_C(t) = P(C(U, V) <= t), estimated from a large sample of the copula."""
    w = np.sort(C(sample))

    def K(t):
        return np.searchsorted(w, np.asarray(t), side="right") / len(w)
    return K


def return_periods(u, v, C, sample: np.ndarray, mu_years: float) -> dict:
    u, v = np.asarray(u, float), np.asarray(v, float)
    K = kendall_function(C, sample)
    t = C(np.column_stack([u, v]))
    eps = 1.0 / len(sample)  # resolution floor of the simulated Kendall function
    return {
        "T_and": mu_years / np.maximum(p_and(u, v, C), 1e-12),
        "T_or": mu_years / np.maximum(p_or(u, v, C), 1e-12),
        "T_kendall": mu_years / np.maximum(1.0 - K(t), eps),
        "T_u": mu_years / (1.0 - u),
        "T_v": mu_years / (1.0 - v),
    }
