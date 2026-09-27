"""Load the study configuration and resolve paths relative to the repo root."""
from __future__ import annotations

import os
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[2]


def load_config(path: str | Path | None = None) -> dict:
    # COMPOUND_CONFIG lets robustness runs swap the config without editing this file.
    path = Path(path or os.environ.get("COMPOUND_CONFIG") or ROOT / "config" / "study.yaml")
    with open(path, encoding="utf-8") as f:
        return yaml.safe_load(f)


def p(rel: str) -> Path:
    """Absolute path for a repo-relative path, creating the parent folder."""
    out = ROOT / rel
    out.parent.mkdir(parents=True, exist_ok=True)
    return out
