"""Download BIPAD (NDRRMA, Government of Nepal) incident records for selected hazards.

The BIPAD API is public but undocumented. Observed behaviour (checked Sept 2026):
  * /api/v1/incident/?hazard=<id>&limit=&offset=&ordering=  works
  * 'count' is a dummy value (2**63-1), so we page until a short page comes back
  * date-range filters are unreliable, so we filter dates locally
  * incidentOn is a local (Nepal, UTC+05:45) timestamp; we keep its calendar date

Output: data/raw/bipad_<hazard>.csv  (one row per incident)
Run:    python scripts/02_download_bipad.py            # landslides only
        python scripts/02_download_bipad.py --all      # + flood, heavy rainfall, GLOF, avalanche
"""
from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

import pandas as pd
import requests

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from compound.config import load_config, p  # noqa: E402

PAGE = 500
LOSS_FIELDS = ["peopleDeathCount", "peopleMissingCount", "peopleInjuredCount",
               "infrastructureDestroyedHouseCount", "infrastructureDestroyedRoadCount",
               "infrastructureDestroyedBridgeCount"]


def fetch_hazard(api: str, hazard_id: int, session: requests.Session) -> list[dict]:
    rows, offset = [], 0
    while True:
        params = {"format": "json", "hazard": hazard_id, "limit": PAGE, "offset": offset,
                  "ordering": "-incident_on", "expand": "loss"}
        for attempt in range(5):
            try:
                r = session.get(f"{api}/incident/", params=params, timeout=120)
                r.raise_for_status()
                break
            except requests.RequestException as exc:
                wait = 5 * (attempt + 1)
                print(f"  retry {attempt + 1} after error: {exc} (sleep {wait}s)")
                time.sleep(wait)
        else:
            raise RuntimeError(f"BIPAD request failed at offset {offset}")
        page = r.json().get("results", [])
        # Guard: if the server ignores the hazard filter we must not keep other hazards.
        page = [x for x in page if x.get("hazard") == hazard_id]
        rows.extend(page)
        print(f"  hazard {hazard_id}: offset {offset:>6} -> {len(page)} rows (total {len(rows)})")
        if len(r.json().get("results", [])) < PAGE:
            return rows
        offset += PAGE
        time.sleep(0.5)  # be polite to a government server


def flatten(rec: dict, hazard_name: str) -> dict:
    pt = (rec.get("point") or {}).get("coordinates") or [None, None]
    loss = rec.get("loss") if isinstance(rec.get("loss"), dict) else {}
    out = {
        "bipad_id": rec["id"],
        "hazard": hazard_name,
        "title": rec.get("title"),
        "date_local": (rec.get("incidentOn") or "")[:10],
        "reported_on": (rec.get("reportedOn") or "")[:10],
        "lon": pt[0],
        "lat": pt[1],
        "ward_ids": ";".join(str(w) for w in rec.get("wards") or []),
        "verified": rec.get("verified"),
        "approved": rec.get("approved"),
        "source": rec.get("source"),
        "cause": rec.get("cause"),
    }
    for f in LOSS_FIELDS:
        out[f] = loss.get(f)
    return out


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--all", action="store_true", help="also download flood, rainfall, GLOF, avalanche")
    args = ap.parse_args()
    cfg = load_config()
    api = cfg["sources"]["bipad_api"]
    hazards = cfg["sources"]["bipad_hazard_ids"]
    wanted = hazards if args.all else {"landslide": hazards["landslide"]}
    s = requests.Session()
    s.headers["User-Agent"] = "nepal-compound-landslide-drivers (research; non-commercial)"
    for name, hid in wanted.items():
        print(f"Downloading BIPAD {name} (hazard id {hid})")
        df = pd.DataFrame([flatten(r, name) for r in fetch_hazard(api, hid, s)])
        df = df.drop_duplicates("bipad_id")
        out = p(f"data/raw/bipad_{name}.csv")
        df.to_csv(out, index=False)
        print(f"Saved {len(df)} {name} incidents "
              f"({df['date_local'].min()} to {df['date_local'].max()}) -> {out}")


if __name__ == "__main__":
    main()
