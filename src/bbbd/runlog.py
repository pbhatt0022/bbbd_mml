"""Run logging: every result gets a run ID tied to the code version, config and seed.

Usage in a notebook:

    from bbbd.config import load_config
    from bbbd import runlog
    cfg = load_config()
    run = runlog.start_run(cfg, name="ridge_eye_only", notebook="60_classical_models", seed=2026)
    ...  # compute metrics
    runlog.save_json(run, {"spearman": 0.21, "ci": [0.05, 0.36]}, "metrics.json")
    runlog.finish_run(run, note="RQ1 eye-only, V1 preprocessing")

A number may appear in the report only if it has a run ID (README rule 3).
"""
from __future__ import annotations

import csv
import json
import os
import random
import subprocess
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

from .config import REPO_ROOT, config_hash, path

REGISTRY_FIELDS = [
    "run_id", "started_utc", "finished_utc", "name", "notebook", "member",
    "git_hash", "git_dirty", "config_hash", "seed", "output_dir", "note",
]


def set_seed(seed: int) -> None:
    """Seed Python, NumPy and (if installed) PyTorch."""
    random.seed(seed)
    np.random.seed(seed)
    os.environ["PYTHONHASHSEED"] = str(seed)
    try:
        import torch
        torch.manual_seed(seed)
        torch.cuda.manual_seed_all(seed)
    except ImportError:
        pass


def git_info() -> tuple[str, bool]:
    """(short commit hash, whether there are uncommitted changes). 'nogit' outside a repo."""
    try:
        h = subprocess.check_output(["git", "rev-parse", "--short", "HEAD"], cwd=REPO_ROOT,
                                    stderr=subprocess.DEVNULL, text=True).strip()
        dirty = bool(subprocess.check_output(["git", "status", "--porcelain"], cwd=REPO_ROOT,
                                             stderr=subprocess.DEVNULL, text=True).strip())
        return h, dirty
    except (subprocess.CalledProcessError, FileNotFoundError):
        return "nogit", True


@dataclass
class Run:
    run_id: str
    name: str
    notebook: str
    member: str
    seed: int
    cfg: dict
    output_dir: Path
    started_utc: str
    git_hash: str
    git_dirty: bool
    meta: dict = field(default_factory=dict)


def _next_run_id(registry: Path) -> str:
    n = 0
    if registry.exists():
        with open(registry, newline="", encoding="utf-8") as f:
            for row in csv.DictReader(f):
                try:
                    n = max(n, int(row["run_id"].split("-")[1]))
                except (KeyError, IndexError, ValueError):
                    continue
    return f"R-{n + 1:03d}"


def start_run(cfg: dict, name: str, notebook: str, seed: int | None = None,
              member: str = "", large_outputs: bool = False) -> Run:
    """Create a run: set the seed, make an output folder, record code + config versions.

    Small outputs go to results/<run_id>_<name>/ (versioned in git).
    large_outputs=True puts them on Drive (04_results) instead, e.g. checkpoints or embeddings.
    """
    seed = cfg["seeds"]["global"] if seed is None else seed
    set_seed(seed)
    registry = path(cfg, "run_registry")
    run_id = _next_run_id(registry)
    base = path(cfg, "results_drive") if large_outputs else path(cfg, "results_repo")
    out = Path(base) / f"{run_id}_{name}"
    out.mkdir(parents=True, exist_ok=True)
    h, dirty = git_info()
    if dirty:
        print(f"[runlog] warning: uncommitted changes; {run_id} is not exactly reproducible from {h}.")
    run = Run(run_id, name, notebook, member, seed, cfg, out,
              datetime.now(timezone.utc).isoformat(timespec="seconds"), h, dirty)
    with open(out / "run_meta.json", "w", encoding="utf-8") as f:
        json.dump({"run_id": run_id, "name": name, "notebook": notebook, "member": member,
                   "seed": seed, "git_hash": h, "git_dirty": dirty,
                   "config_hash": config_hash(cfg), "started_utc": run.started_utc,
                   "config": cfg}, f, indent=2, default=str)
    print(f"[runlog] {run_id} '{name}' started; outputs -> {out}")
    return run


def save_json(run: Run, obj: dict, filename: str) -> Path:
    """Save a result dict stamped with the run ID."""
    p = run.output_dir / filename
    payload = {"run_id": run.run_id, "git_hash": run.git_hash, **obj}
    with open(p, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2, default=_to_builtin)
    return p


def save_table(run: Run, df, filename: str) -> Path:
    """Save a pandas DataFrame (CSV, or Parquet if the name ends .parquet) with a run_id column."""
    df = df.copy()
    df.insert(0, "run_id", run.run_id)
    p = run.output_dir / filename
    df.to_parquet(p, index=False) if filename.endswith(".parquet") else df.to_csv(p, index=False)
    return p


def save_figure(run: Run, fig, filename: str, dpi: int = 200) -> Path:
    """Save a matplotlib figure; the run ID is written in the corner."""
    fig.text(0.995, 0.005, run.run_id, ha="right", va="bottom", fontsize=6, color="0.5")
    p = run.output_dir / filename
    fig.savefig(p, dpi=dpi, bbox_inches="tight")
    return p


def finish_run(run: Run, note: str = "") -> None:
    """Write the run to docs/run_registry.csv, replacing any earlier row for this run ID.

    Re-running the save cell in a notebook calls this again with the same Run, so a
    plain append would leave several rows claiming the same run ID. One row per run ID
    keeps the registry usable as the index the report cites (README rule 3).
    """
    registry = path(run.cfg, "run_registry")
    registry.parent.mkdir(parents=True, exist_ok=True)

    existing = []
    if registry.exists() and registry.stat().st_size:
        with open(registry, newline="", encoding="utf-8") as f:
            existing = [r for r in csv.DictReader(f) if r.get("run_id") != run.run_id]

    with open(registry, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=REGISTRY_FIELDS)
        w.writeheader()
        for r in existing:
            w.writerow({k: r.get(k, "") for k in REGISTRY_FIELDS})
        w.writerow({
            "run_id": run.run_id, "started_utc": run.started_utc,
            "finished_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "name": run.name, "notebook": run.notebook, "member": run.member,
            "git_hash": run.git_hash, "git_dirty": run.git_dirty,
            "config_hash": config_hash(run.cfg), "seed": run.seed,
            "output_dir": str(run.output_dir.relative_to(REPO_ROOT)
                              if run.output_dir.is_relative_to(REPO_ROOT) else run.output_dir),
            "note": note,
        })
    print(f"[runlog] {run.run_id} finished and registered. Log any conclusion in docs/inference_log.md.")


def _to_builtin(o):
    if isinstance(o, (np.integer,)):
        return int(o)
    if isinstance(o, (np.floating,)):
        return float(o)
    if isinstance(o, np.ndarray):
        return o.tolist()
    return str(o)
