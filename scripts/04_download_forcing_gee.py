"""District-average daily rainfall and soil moisture from Google Earth Engine.

Everything is reduced to district means on Earth Engine's servers, so you download a
small CSV (~77 districts x ~1,300 days) instead of gigabytes of NetCDF.

Products
  era5l  : ECMWF/ERA5_LAND/DAILY_AGGR  -> P_era5l (mm/day), sm1 (0-7 cm), sm_rz (0-100 cm)
           Days are UTC days (05:45-05:45 Nepal time); documented as a known misalignment.
  imerg  : NASA/GPM_L3/IMERG_V07 (half-hourly, mm/hr) -> P_imerg summed over the Nepal
           calendar day (00:00-24:00 NPT) to match BIPAD incident dates.
  chirps : UCSB-CHG/CHIRPS/DAILY -> P_chirps (mm/day), robustness check only.

Setup (once):
  pip install earthengine-api
  earthengine authenticate
  # a Google Cloud project registered for non-commercial Earth Engine use
Run:
  python scripts/04_download_forcing_gee.py --project YOUR_GCP_PROJECT --product era5l
  python scripts/04_download_forcing_gee.py --project YOUR_GCP_PROJECT --product imerg
  python scripts/04_download_forcing_gee.py --project YOUR_GCP_PROJECT --product chirps

Output: data/raw/forcing_<product>.csv  (resumable: finished chunks are skipped)
"""
from __future__ import annotations

import argparse
import sys
import time
from datetime import date, timedelta
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from compound.config import load_config, p  # noqa: E402

SCALE = {"era5l": 11132, "imerg": 11132, "chirps": 5566}
# IMERG sums 48 half-hourly images per day, so smaller requests avoid "Too many concurrent aggregations".
CHUNK_DAYS = {"era5l": 15, "imerg": 5, "chirps": 15}
LEAD_DAYS = 10  # extra days before the season so 7-day antecedent sums exist on 1 June


def district_fc(ee, cfg):
    import geopandas as gpd
    gdf = gpd.read_file(p(cfg["units"]["boundaries_file"]))
    name = cfg["units"]["name_field"]
    gdf["geometry"] = gdf.geometry.simplify(0.005, preserve_topology=True)
    feats = [ee.Feature(ee.Geometry(row.geometry.__geo_interface__), {"unit": row[name]})
             for _, row in gdf.iterrows()]
    return ee.FeatureCollection(feats)


def daily_image(ee, product: str, day):
    """Return an ee.Image for one calendar day with the product's output bands."""
    d0 = ee.Date(day)
    if product == "era5l":
        img = ee.ImageCollection("ECMWF/ERA5_LAND/DAILY_AGGR").filterDate(d0, d0.advance(1, "day")).first()
        p_mm = img.select("total_precipitation_sum").multiply(1000).rename("P_era5l")
        l1 = img.select("volumetric_soil_water_layer_1")
        l2 = img.select("volumetric_soil_water_layer_2")
        l3 = img.select("volumetric_soil_water_layer_3")
        # Layer thicknesses 7, 21, 72 cm -> depth-weighted 0-100 cm root-zone moisture.
        rz = l1.multiply(7).add(l2.multiply(21)).add(l3.multiply(72)).divide(100).rename("sm_rz")
        return p_mm.addBands(l1.rename("sm1")).addBands(rz)
    if product == "imerg":
        # Nepal calendar day: 00:00 NPT = 18:15 UTC on the previous day.
        start = ee.Date(ee.String(d0.format("YYYY-MM-dd")).cat("T00:00:00"), "Asia/Kathmandu")
        col = ee.ImageCollection("NASA/GPM_L3/IMERG_V07").filterDate(start, start.advance(1, "day"))
        return col.select("precipitation").sum().multiply(0.5).rename("P_imerg")  # mm/hr x 0.5 h
    if product == "chirps":
        return (ee.ImageCollection("UCSB-CHG/CHIRPS/DAILY").filterDate(d0, d0.advance(1, "day"))
                .first().select("precipitation").rename("P_chirps"))
    raise ValueError(product)


def reduce_chunk(ee, product, fc, days: list[date]) -> pd.DataFrame:
    def per_day(ds):
        img = daily_image(ee, product, ds)
        stats = img.reduceRegions(collection=fc, reducer=ee.Reducer.mean(), scale=SCALE[product])
        return stats.map(lambda f: ee.Feature(None, f.toDictionary()).set("date", ds))

    fcs = ee.FeatureCollection(ee.List([d.isoformat() for d in days]).map(per_day)).flatten()
    info = fcs.getInfo()["features"]
    df = pd.DataFrame([f["properties"] for f in info])
    # reduceRegions names a single-band result after the reducer ("mean"), not the band.
    return df.rename(columns={"mean": f"P_{product}"})


def season_days(cfg) -> list[date]:
    y0 = int(cfg["period"]["start"][:4])
    y1 = int(cfg["period"]["end"][:4])
    months = cfg["period"]["season_months"]
    days = []
    for y in range(y0, y1 + 1):
        d = date(y, min(months), 1) - timedelta(days=LEAD_DAYS)
        end = (date(y, max(months) + 1, 1) - timedelta(days=1)) if max(months) < 12 else date(y, 12, 31)
        while d <= end:
            days.append(d)
            d += timedelta(days=1)
    return days


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--project", required=True, help="Google Cloud project registered for Earth Engine")
    ap.add_argument("--product", choices=["era5l", "imerg", "chirps"], required=True)
    args = ap.parse_args()

    import ee
    ee.Initialize(project=args.project)
    cfg = load_config()
    fc = district_fc(ee, cfg)
    out = p(f"data/raw/forcing_{args.product}.csv")
    done = set(pd.read_csv(out, usecols=["date"])["date"].unique()) if out.exists() else set()

    days = [d for d in season_days(cfg) if d.isoformat() not in done]
    print(f"{args.product}: {len(days)} days to fetch ({len(done)} already on disk)")
    for i in range(0, len(days), CHUNK_DAYS[args.product]):
        chunk = days[i:i + CHUNK_DAYS[args.product]]
        for attempt in range(8):
            try:
                df = reduce_chunk(ee, args.product, fc, chunk)
                break
            except Exception as exc:  # EE quota / timeout: back off and retry
                print(f"  {chunk[0]}: {exc}; retrying")
                time.sleep(30 * (attempt + 1))
        else:
            sys.exit(f"Giving up at {chunk[0]}; rerun to resume.")
        df.to_csv(out, mode="a", header=not out.exists(), index=False)
        print(f"  {chunk[0]} to {chunk[-1]}: {len(df)} rows")
    print(f"Done -> {out}")


if __name__ == "__main__":
    main()
