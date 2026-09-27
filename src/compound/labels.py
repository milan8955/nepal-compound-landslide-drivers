"""Turn point incident records into unit-day landslide labels."""
from __future__ import annotations

import geopandas as gpd
import pandas as pd


def assign_units(incidents: pd.DataFrame, units: gpd.GeoDataFrame, name_field: str,
                 max_snap_deg: float = 0.05) -> pd.DataFrame:
    """Attach the district containing each incident point.

    Points just outside the (simplified) boundary are snapped to the nearest district if
    within `max_snap_deg` (~5 km); points further away are dropped and counted.
    """
    df = incidents.dropna(subset=["lon", "lat"]).copy()
    pts = gpd.GeoDataFrame(df, geometry=gpd.points_from_xy(df["lon"], df["lat"]), crs="EPSG:4326")
    u = units[[name_field, "geometry"]].rename(columns={name_field: "unit"}).to_crs("EPSG:4326")
    joined = gpd.sjoin(pts, u, how="left", predicate="within").drop(columns="index_right")
    miss = joined["unit"].isna()
    if miss.any():
        near = gpd.sjoin_nearest(joined.loc[miss].drop(columns="unit"), u, how="left",
                                 max_distance=max_snap_deg, distance_col="snap_deg")
        near = near[~near.index.duplicated()]
        joined.loc[miss, "unit"] = near["unit"]
    n_drop = int(joined["unit"].isna().sum())
    if n_drop:
        print(f"assign_units: dropped {n_drop} points outside all units")
    return pd.DataFrame(joined.dropna(subset=["unit"]).drop(columns="geometry"))


def unit_day_labels(incidents: pd.DataFrame, date_col: str = "date_local") -> pd.DataFrame:
    """Count incidents (and deaths) per unit and calendar day."""
    df = incidents.copy()
    df["date"] = pd.to_datetime(df[date_col], errors="coerce")
    df = df.dropna(subset=["date"])
    deaths = df["peopleDeathCount"] if "peopleDeathCount" in df else 0
    df = df.assign(deaths=pd.to_numeric(deaths, errors="coerce").fillna(0))
    return (df.groupby(["unit", "date"])
              .agg(n_events=("unit", "size"), deaths=("deaths", "sum"))
              .reset_index())
