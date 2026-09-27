"""Download NASA COOLR / Global Landslide Catalog points for Nepal (independent label set).

Uses the public ArcGIS REST query endpoint (max 2,000 records per request, so we page).
Cite: Kirschbaum et al. 2010, 2015; Juang et al. 2019 (see README).

Output: data/raw/coolr_nepal.csv
Run:    python scripts/03_download_coolr.py
"""
from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd
import requests

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from compound.config import load_config, p  # noqa: E402

# Nepal bounding box, used in addition to the country field (some records lack it).
BBOX = "80.0,26.3,88.3,30.5"


def query_layer(url: str) -> pd.DataFrame:
    rows, offset = [], 0
    while True:
        params = {
            "where": "1=1",
            "geometry": BBOX, "geometryType": "esriGeometryEnvelope", "inSR": 4326,
            "spatialRel": "esriSpatialRelIntersects",
            "outFields": "*", "returnGeometry": "true", "outSR": 4326,
            "resultOffset": offset, "resultRecordCount": 2000, "f": "json",
        }
        r = requests.get(f"{url}/query", params=params, timeout=120)
        r.raise_for_status()
        js = r.json()
        if "error" in js:
            raise RuntimeError(js["error"])
        feats = js.get("features", [])
        for f in feats:
            a = dict(f["attributes"])
            g = f.get("geometry") or {}
            a.setdefault("longitude", g.get("x"))
            a.setdefault("latitude", g.get("y"))
            rows.append(a)
        if not js.get("exceededTransferLimit") and len(feats) < 2000:
            break
        offset += len(feats)
    return pd.DataFrame(rows)


def main() -> None:
    cfg = load_config()
    df, used = None, None
    for url in cfg["sources"]["coolr_layers"]:
        try:
            df = query_layer(url)
            used = url
            print(f"OK: {url} -> {len(df)} records")
            break
        except Exception as exc:
            print(f"Failed: {url} ({exc})")
    if df is None or df.empty:
        sys.exit("No COOLR layer answered. Download manually from https://landslides.nasa.gov "
                 "(Landslide Viewer > Download) and save as data/raw/coolr_nepal.csv")
    # Dates are epoch milliseconds (UTC) in ArcGIS; convert to calendar date.
    date_col = next(c for c in ["event_date", "ev_date"] if c in df.columns)
    df["date_utc"] = pd.to_datetime(df[date_col], unit="ms", errors="coerce").dt.date.astype(str)
    if "country_name" in df.columns:
        df = df[df["country_name"].fillna("Nepal").str.contains("Nepal", case=False)]
    df["layer_url"] = used
    out = p("data/raw/coolr_nepal.csv")
    df.to_csv(out, index=False)
    print(f"Saved {len(df)} Nepal records -> {out}")
    for col in ["landslide_trigger", "location_accuracy", "event_import_source"]:
        if col in df.columns:
            print(df[col].value_counts(dropna=False).head(10).to_string(), "\n")


if __name__ == "__main__":
    main()
