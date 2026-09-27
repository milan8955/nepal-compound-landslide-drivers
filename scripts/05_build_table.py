"""Merge landslide labels with antecedent rainfall and soil moisture into one unit-day table.

Inputs  data/raw/npl_adm2.geojson, data/raw/bipad_landslide.csv (and/or coolr_nepal.csv),
        data/raw/forcing_era5l.csv (+ forcing_imerg.csv, forcing_chirps.csv if present)
Output  data/processed/unit_day.parquet
Run     python scripts/05_build_table.py [--labels bipad|coolr|merged]
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import geopandas as gpd
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from compound.config import load_config, p  # noqa: E402
from compound.features import add_antecedent, complete_grid, in_season  # noqa: E402
from compound.labels import assign_units, unit_day_labels  # noqa: E402


def load_labels(kind: str, units: gpd.GeoDataFrame, name_field: str) -> pd.DataFrame:
    frames = []
    if kind in ("bipad", "merged"):
        b = pd.read_csv(p("data/raw/bipad_landslide.csv"))
        frames.append(unit_day_labels(assign_units(b, units, name_field), "date_local"))
    if kind in ("coolr", "merged"):
        c = pd.read_csv(p("data/raw/coolr_nepal.csv"))
        c = c.rename(columns={"longitude": "lon", "latitude": "lat"})
        if "fatality_count" in c.columns:
            c["peopleDeathCount"] = c["fatality_count"]
        frames.append(unit_day_labels(assign_units(c, units, name_field), "date_utc"))
    lab = pd.concat(frames)
    return lab.groupby(["unit", "date"], as_index=False).agg(n_events=("n_events", "sum"),
                                                             deaths=("deaths", "sum"))


def load_forcing(cfg) -> tuple[pd.DataFrame, str]:
    era = pd.read_csv(p("data/raw/forcing_era5l.csv"))
    forcing = era[["unit", "date", "P_era5l", "sm1", "sm_rz"]]
    for prod in ("imerg", "chirps"):
        f = p(f"data/raw/forcing_{prod}.csv")
        if f.exists():
            forcing = forcing.merge(pd.read_csv(f)[["unit", "date", f"P_{prod}"]],
                                    on=["unit", "date"], how="left")
    primary = f"P_{cfg['forcing']['precip_primary']}"
    if primary not in forcing:
        print(f"{primary} not available; falling back to P_era5l")
        primary = "P_era5l"
    return forcing, primary


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--labels", default="bipad", choices=["bipad", "coolr", "merged"])
    ap.add_argument("--out", default="data/processed/unit_day.parquet")
    args = ap.parse_args()
    cfg = load_config()
    units = gpd.read_file(p(cfg["units"]["boundaries_file"]))
    name_field = cfg["units"]["name_field"]

    forcing, primary = load_forcing(cfg)
    grid = complete_grid(forcing)
    windows = cfg["forcing"]["precip_windows_days"]
    df = add_antecedent(grid, primary, windows, cfg["forcing"]["sm_variable"],
                        cfg["forcing"]["sm_lag_days"])
    # Robustness copies of the 3-day sum from the other rainfall products.
    for alt in [c for c in ("P_era5l", "P_imerg", "P_chirps") if c in grid and c != primary]:
        tmp = add_antecedent(grid, alt, [3], cfg["forcing"]["sm_variable"], 1)
        df[f"P3_{alt[2:]}"] = tmp["P3"].to_numpy()
    df = in_season(df, cfg["period"]["season_months"], cfg["period"]["start"], cfg["period"]["end"])

    lab = load_labels(args.labels, units, name_field)
    lab_season = in_season(lab, cfg["period"]["season_months"], cfg["period"]["start"],
                           cfg["period"]["end"])
    df = df.merge(lab_season, on=["unit", "date"], how="left")
    df[["n_events", "deaths"]] = df[["n_events", "deaths"]].fillna(0)
    df["L"] = (df["n_events"] > 0).astype(int)
    df["year"] = df["date"].dt.year
    df["precip_source"] = primary
    df["label_source"] = args.labels

    unmatched = set(lab_season["unit"]) - set(df["unit"])
    out = p(args.out)
    df.to_parquet(out, index=False)
    n_ev_total = int(lab["n_events"].sum())
    n_ev_season = int(lab_season["n_events"].sum())
    print(f"unit-days: {len(df):,} | units: {df['unit'].nunique()} | years: "
          f"{df['year'].min()}-{df['year'].max()}")
    print(f"landslide unit-days: {int(df['L'].sum()):,} (base rate {df['L'].mean():.4f})")
    print(f"incidents in season window: {n_ev_season:,} of {n_ev_total:,} labelled incidents")
    if unmatched:
        print(f"WARNING: label units missing from forcing: {sorted(unmatched)[:10]}")
    print(f"primary rainfall: {primary} -> {out}")


if __name__ == "__main__":
    main()
