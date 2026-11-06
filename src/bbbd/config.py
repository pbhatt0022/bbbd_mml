"""Load config.yaml and resolve the {data_root} placeholders in paths."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

import yaml

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_CONFIG = REPO_ROOT / "config.yaml"


def load_config(path: str | Path | None = None, **overrides: Any) -> dict:
    """Read the YAML config. `overrides` replace top-level keys, e.g. data_root='/my/path'.

    Example:
        cfg = load_config(data_root="D:/MML_BBBD")
        cfg["paths"]["raw"]  # -> 'D:/MML_BBBD/01_data_raw'
    """
    path = Path(path) if path else DEFAULT_CONFIG
    with open(path, "r", encoding="utf-8") as f:
        cfg = yaml.safe_load(f)
    if "data_root" in overrides:
        cfg["paths"]["data_root"] = overrides.pop("data_root")
    cfg.update(overrides)
    root = cfg["paths"]["data_root"]
    for key, val in cfg["paths"].items():
        if isinstance(val, str):
            cfg["paths"][key] = val.replace("{data_root}", root)
    return cfg


def path(cfg: dict, key: str) -> Path:
    """Return a configured path as a Path. Repo-relative paths are resolved from the repo root."""
    p = Path(cfg["paths"][key])
    return p if p.is_absolute() else REPO_ROOT / p


def config_hash(cfg: dict) -> str:
    """Short, stable hash of the whole config, recorded with every run."""
    blob = json.dumps(cfg, sort_keys=True, default=str).encode()
    return hashlib.sha256(blob).hexdigest()[:10]
