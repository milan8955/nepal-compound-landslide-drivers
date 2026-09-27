"""Antecedent rainfall and lagged soil-moisture features on a complete unit-day grid."""
from __future__ import annotations

import pandas as pd


def complete_grid(forcing: pd.DataFrame) -> pd.DataFrame:
    """Reindex every unit onto every date so rolling windows never skip a missing day."""
    forcing = forcing.copy()
    forcing["date"] = pd.to_datetime(forcing["date"])
    dates = pd.Index(sorted(forcing["date"].unique()), name="date")
    units = pd.Index(sorted(forcing["unit"].unique()), name="unit")
    idx = pd.MultiIndex.from_product([units, dates])
    return (forcing.groupby(["unit", "date"]).mean(numeric_only=True)
                   .reindex(idx).reset_index())


def add_antecedent(df: pd.DataFrame, precip_col: str, windows: list[int],
                   sm_col: str, sm_lag: int) -> pd.DataFrame:
    """P{k}: k-day rainfall ending on day t (inclusive). SM: soil moisture on day t - sm_lag.

    Windows only count as valid if every day in the window is present and consecutive,
    so values never straddle the gap between two monsoon seasons.
    """
    df = df.sort_values(["unit", "date"]).copy()
    g = df.groupby("unit", group_keys=False)
    gap = g["date"].diff().dt.days.ne(1)  # True at the first day of each block
    df["_block"] = gap.groupby(df["unit"]).cumsum()
    gb = df.groupby(["unit", "_block"], group_keys=False)
    for k in windows:
        df[f"P{k}"] = gb[precip_col].transform(lambda s, k=k: s.rolling(k, min_periods=k).sum())
    df["SM"] = gb[sm_col].shift(sm_lag)
    return df.drop(columns="_block")


def in_season(df: pd.DataFrame, months: list[int], start: str, end: str) -> pd.DataFrame:
    m = df["date"].dt.month.isin(months) & df["date"].between(start, end)
    return df.loc[m].copy()
