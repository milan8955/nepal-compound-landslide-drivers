"""End-to-end run of scripts 05 and 06 on synthetic data in a throwaway copy of the repo."""
import json
import shutil
import subprocess
import sys
from pathlib import Path

from synthetic import write_synthetic

ROOT = Path(__file__).resolve().parents[1]


def test_end_to_end(tmp_path):
    work = tmp_path / "repo"
    shutil.copytree(ROOT, work, ignore=shutil.ignore_patterns("data", "figures", "results", ".venv",
                                                              ".git", "__pycache__"))
    write_synthetic(work)
    for script in ["05_build_table.py", "06_run_analysis.py"]:
        args = [sys.executable, str(work / "scripts" / script)]
        if script.startswith("06"):
            args.append("--quick")
        r = subprocess.run(args, cwd=work, capture_output=True, text=True)
        assert r.returncode == 0, r.stdout + r.stderr
    res = json.loads((work / "results" / "summary.json").read_text())
    assert res["n_landslide_days"] > 100
    assert res["copula_all_days"]["kendall_tau_empirical"] > 0.1
    cp = res["conditional_probability"]
    # The synthetic truth: wet soil raises landslide odds at the same rainfall level.
    assert cp["P_given_U>0.9_V>0.9"] > cp["P_given_U>0.9_V<=0.5"]
    auc = res["auc_test"]
    assert auc["rain_plus_soil_logistic"] > auc["rain_only_logistic"]
    for i in range(1, 8):
        assert list((work / "figures").glob(f"fig0{i}_*.png")), f"missing fig0{i}"
