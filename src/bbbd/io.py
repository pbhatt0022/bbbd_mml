"""Find and read BBBD files (BIDS layout).

What we know (Handoff, Dataset Inventory): BIDS format; EEG/ECG/EOG/respiration in BDF;
non-EEG raw files are headerless .tsv.gz with column names in a JSON sidecar.
What is UNVERIFIED until notebook 00 runs on the real files: exact file-name entities
(task/run/acq labels), the sampling rate of the released raw files, and the quiz file layout.
So everything here searches by pattern and reads the sidecar instead of hard-coding names.
Update this module, and the Dataset Inventory, once notebook 00 has been run.
"""
from __future__ import annotations

import json
from pathlib import Path

import pandas as pd


def experiment_root(raw_root: str | Path, experiment: int) -> Path:
    """Folder of one unzipped experiment. Tries common names; edit once confirmed."""
    raw_root = Path(raw_root)
    for name in (f"experiment{experiment}", f"Experiment{experiment}", f"exp{experiment}",
                 f"Experiment_{experiment}", f"experiment_{experiment}"):
        if (raw_root / name).exists():
            return raw_root / name
    raise FileNotFoundError(f"No folder for experiment {experiment} under {raw_root}")


def subjects(exp_root: Path) -> list[str]:
    return sorted(p.name for p in Path(exp_root).glob("sub-*") if p.is_dir())


def find(exp_root: Path, pattern: str) -> list[Path]:
    """Recursive glob, e.g. find(root, '*_eeg.bdf') or find(root, '*eyetrack*.tsv.gz')."""
    return sorted(Path(exp_root).rglob(pattern))


def read_sidecar(data_file: Path) -> dict:
    """JSON sidecar next to a BIDS data file (same stem, .json)."""
    stem = data_file.name
    for ext in (".tsv.gz", ".tsv", ".bdf", ".edf"):
        if stem.endswith(ext):
            stem = stem[: -len(ext)]
            break
    side = data_file.with_name(stem + ".json")
    if not side.exists():
        raise FileNotFoundError(f"No sidecar for {data_file}")
    with open(side, encoding="utf-8") as f:
        return json.load(f)


def read_physio_tsv(data_file: Path) -> tuple[pd.DataFrame, dict]:
    """Headerless BIDS physio/eye .tsv.gz -> DataFrame with sidecar 'Columns' as names.

    Returns (data, sidecar). sidecar['SamplingFrequency'] and sidecar.get('StartTime')
    give the time base. Always log the sampling rate you find (Dataset Inventory).
    """
    meta = read_sidecar(data_file)
    cols = meta.get("Columns")
    df = pd.read_csv(data_file, sep="\t", header=None, names=cols, na_values=["n/a", "NaN"])
    return df, meta


def read_participants(exp_root: Path) -> pd.DataFrame:
    p = Path(exp_root) / "participants.tsv"
    return pd.read_csv(p, sep="\t") if p.exists() else pd.DataFrame()


def phenotype_files(exp_root: Path) -> list[Path]:
    """Quiz, engagement and questionnaire tables (BIDS 'phenotype/' folder)."""
    return sorted((Path(exp_root) / "phenotype").glob("*.tsv"))


def inventory(exp_root: Path) -> pd.DataFrame:
    """One row per data file: subject, file, suffix, sampling rate, n columns. For notebook 00."""
    rows = []
    for f in sorted(Path(exp_root).rglob("sub-*/**/*")):
        if not f.is_file() or f.suffix == ".json":
            continue
        try:
            meta = read_sidecar(f)
        except FileNotFoundError:
            meta = {}
        rows.append({
            "subject": next((p for p in f.parts if p.startswith("sub-")), ""),
            "file": str(f.relative_to(exp_root)),
            "size_mb": round(f.stat().st_size / 1e6, 2),
            "sfreq": meta.get("SamplingFrequency"),
            "columns": ",".join(meta.get("Columns", [])) if meta.get("Columns") else "",
        })
    return pd.DataFrame(rows)
