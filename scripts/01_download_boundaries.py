"""Download Nepal district (ADM2, 77 districts) boundaries: OCHA COD-AB via HDX (CC BY-IGO).

Source: Survey Department of Nepal / OCHA, https://data.humdata.org/dataset/cod-ab-npl
(geoBoundaries gbOpen NPL ADM2 was dropped: 75 units with wrong names, e.g. Parsa and
Siraha labelled Bara and Saptari; gbAuthoritative files are no longer served.)

Output: data/raw/npl_adm2.geojson
Run:    python scripts/01_download_boundaries.py
"""
from __future__ import annotations

import io
import sys
import zipfile
from pathlib import Path

import requests

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from compound.config import load_config, p  # noqa: E402

TIMEOUT = 300
SIMPLIFY_DEG = 0.002  # ~200 m; plenty for ~10 km forcing grids, keeps Earth Engine requests small


def main() -> None:
    import geopandas as gpd

    cfg = load_config()
    out = p(cfg["units"]["boundaries_file"])
    src = cfg["sources"]["boundaries"]
    r = requests.get(src["url"], timeout=TIMEOUT)
    r.raise_for_status()
    with zipfile.ZipFile(io.BytesIO(r.content)) as z:
        gdf = gpd.read_file(io.BytesIO(z.read(src["member"])))

    name = cfg["units"]["name_field"]
    gdf = gdf[[name, "adm2_pcode", "adm1_name", "valid_on", "version", "geometry"]].to_crs("EPSG:4326")
    gdf["geometry"] = gdf.geometry.simplify(SIMPLIFY_DEG, preserve_topology=True)
    out.parent.mkdir(parents=True, exist_ok=True)
    gdf.to_file(out, driver="GeoJSON")

    print(f"COD-AB {gdf['version'].iloc[0]} valid_on={gdf['valid_on'].iloc[0]}")
    print(f"Saved {len(gdf)} districts to {out}")
    if len(gdf) != 77 or gdf[name].nunique() != 77:
        print("WARNING: expected 77 uniquely named districts (post-2015 federal structure).")


if __name__ == "__main__":
    main()
