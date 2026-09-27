"""Re-run scripts 05 + 06 under alternative settings and tabulate the headline numbers.

Each variant is the base config/study.yaml with a few keys changed. Its config, table,
figures and results go to results/robustness/<name>/, so the main results are untouched.

Output  results/robustness/summary.md (+ summary.csv)
Run     python scripts/07_robustness.py [--quick] [--only NAME ...]
"""
from __future__ import annotations

import argparse
import copy
import json
import os
import subprocess
import sys
from pathlib import Path

import pandas as pd
import yaml

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from compound.config import ROOT, load_config, p  # noqa: E402

# name -> (changes as {dotted.key: value}, 05 label source)
VARIANTS = {
    "base":           ({}, "bipad"),
    "sm_surface":     ({"forcing.sm_variable": "sm1"}, "bipad"),
    "sm_lag2":        ({"forcing.sm_lag_days": 2}, "bipad"),
    # Surface layer at t-2: tests whether the sm1 gain is same-day rain leaking into t-1.
    "sm_surface_lag2": ({"forcing.sm_variable": "sm1", "forcing.sm_lag_days": 2}, "bipad"),
    "rain_P7":        ({"analysis.primary_pair": ["P7", "SM"]}, "bipad"),
    "rain_P1":        ({"analysis.primary_pair": ["P1", "SM"]}, "bipad"),
    "rain_era5l":     ({"forcing.precip_primary": "era5l"}, "bipad"),
    # COOLR has no labels after 2018, so train on 2011-2015 and test on 2016-2018.
    "labels_coolr":   ({"split.train_years": list(range(2011, 2016)),
                        "split.test_years": [2016, 2017, 2018]}, "coolr"),
}


def set_key(cfg: dict, dotted: str, value) -> None:
    *path, last = dotted.split(".")
    for k in path:
        cfg = cfg[k]
    cfg[last] = value


def run(name: str, changes: dict, labels: str, quick: bool) -> dict:
    cfg = copy.deepcopy(load_config(ROOT / "config" / "study.yaml"))
    for k, v in changes.items():
        set_key(cfg, k, v)
    outdir = f"results/robustness/{name}"
    cfg_path = p(f"{outdir}/config.yaml")
    cfg_path.write_text(yaml.safe_dump(cfg, sort_keys=False))
    env = {**os.environ, "COMPOUND_CONFIG": str(cfg_path)}
    table = f"{outdir}/unit_day.parquet"
    py = sys.executable
    for cmd in ([py, "scripts/05_build_table.py", "--labels", labels, "--out", table],
                [py, "scripts/06_run_analysis.py", "--table", table, "--outdir", outdir]
                + (["--quick"] if quick else [])):
        r = subprocess.run(cmd, cwd=ROOT, env=env, capture_output=True, text=True)
        if r.returncode:
            sys.exit(f"{name}: {' '.join(cmd[1:2])} failed\n{r.stdout}\n{r.stderr}")
    return json.loads(p(f"{outdir}/results/summary.json").read_text())


def row(name: str, R: dict) -> dict:
    cp, auc, auw = R["conditional_probability"], R["auc_test"], R["auc_test_within_year"]
    return {
        "variant": name,
        "pair": "/".join(R["variables"]),
        "rain": R["precip_source"],
        "labels": R["label_source"],
        "n_events": R["n_landslide_days"],
        "tau": R["copula_all_days"]["kendall_tau_empirical"],
        "copula": R["copula_all_days"]["best"],
        "cvm_p": R["copula_all_days"]["gof"]["p_value"],
        "LR_U90": cp["P_given_U>0.9"] / cp["base_rate"],
        "LR_U90_wet": cp["P_given_U>0.9_V>0.9"] / cp["base_rate"],
        "LR_U90_dry": cp["P_given_U>0.9_V<=0.5"] / cp["base_rate"],
        "AUC_rain": auc["rain_only_logistic"],
        "AUC_rain_soil": auc["rain_plus_soil_logistic"],
        "AUC_gain": auc["gain"],
        "gain_lo": auc["gain_90ci"][0],
        "gain_hi": auc["gain_90ci"][1],
        "AUCyr_rain": auw["rain_only_logistic"],
        "AUCyr_rain_soil": auw["rain_plus_soil_logistic"],
        "AUCyr_gain_min": min(auw["gain_by_year"].values()),
        "AUCyr_gain_max": max(auw["gain_by_year"].values()),
        "soil_q_in_rule": R["tuned_rules"]["bivariate_q"][1],
    }


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--quick", action="store_true")
    ap.add_argument("--only", nargs="*", help="run only these variants")
    args = ap.parse_args()
    rows = []
    for name, (changes, labels) in VARIANTS.items():
        if args.only and name not in args.only:
            continue
        print(f"running {name} ...", flush=True)
        rows.append(row(name, run(name, changes, labels, args.quick)))
    out = pd.DataFrame(rows).round(4)
    out.to_csv(p("results/robustness/summary.csv"), index=False)
    md = ["# Robustness of the headline numbers", "",
          "LR = P(landslide | condition) / base rate, train years. U90 = rainfall above its 90th",
          "percentile; wet = SM above 90th, dry = SM at or below 50th. AUC on test years;",
          "AUCyr = mean AUC within each test year (min/max = range of per-year gains).",
          "Gain CI: 90% year-block bootstrap.", "",
          out.to_markdown(index=False)]
    p("results/robustness/summary.md").write_text("\n".join(md) + "\n")
    print("\n".join(md))


if __name__ == "__main__":
    main()
