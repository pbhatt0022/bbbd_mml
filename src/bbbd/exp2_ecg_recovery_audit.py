"""Register the D-33 audit of recovered attentive Experiment 2 ECG tables."""
import argparse
import csv
import hashlib
import io
import math
import tarfile
from collections import Counter
from pathlib import Path

from . import runlog
from .config import load_config

FOLDER = "MML_BBBD/04_results/ecg_full_diagnostic/"
KEYS = ("experiment", "subject", "video", "session", "variant")
ARCHIVE_SHA256 = "767f2d6be2c8933309ab14f5e01e71436a0adfed9754b0e510d379a5c95cf50a"


def classify(qc, validation, minimum_recall):
    if qc["status"] != "processed":
        return "unevaluable", "processing_failed", None, None
    if qc["reference_available"].lower() != "true":
        return "unevaluable", "missing_reference", None, None
    try:
        tp, ref, detected = (int(float(validation[k])) for k in ("tp", "n_ref", "n_ours"))
        if any(float(validation[k]) != n for k, n in zip(("tp", "n_ref", "n_ours"), (tp, ref, detected))):
            raise ValueError("Noninteger beat count")
        if not 0 <= tp <= min(ref, detected) or ref <= 0:
            raise ValueError("Invalid denominator or counts")
        recall, f1 = tp / ref, 2 * tp / (ref + detected)
        if not all(math.isclose(float(validation[k]), v, abs_tol=1e-12)
                   for k, v in (("recall", recall), ("f1", f1))):
            raise ValueError("Inconsistent saved metrics")
    except (ValueError, OverflowError, TypeError):
        return "unevaluable", "unusable_reference_or_metrics", None, None
    if recall < minimum_recall:
        return "excluded", "below_reference_recall_threshold", recall, f1
    return "eligible", "", recall, f1


def table(bundle, name):
    member = bundle.getmember(FOLDER + name)
    if not member.isfile():
        raise ValueError(f"Expected regular file: {name}")
    rows = list(csv.DictReader(io.TextIOWrapper(bundle.extractfile(member), encoding="utf-8-sig")))
    index = {tuple(row[k] for k in KEYS): row for row in rows}
    if len(index) != len(rows) or not rows or any(key[0] != "2" for key in index):
        raise ValueError(f"Unexpected experiment or duplicate keys: {name}")
    return index


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("archive", type=Path)
    args = parser.parse_args()
    with args.archive.open("rb") as f:
        digest = hashlib.file_digest(f, "sha256").hexdigest()
    if digest != ARCHIVE_SHA256:
        raise ValueError("Recovery archive SHA-256 mismatch")
    cfg = load_config()
    limits = cfg["exclusions"]["ecg_min_detected_beat_frac"]
    f1_cutoff = cfg["ecg"]["match_f1_threshold"]
    if cfg["ecg"]["match_tolerance_ms"] != 50:
        raise ValueError("Expected archived 50 ms matching tolerance")
    with tarfile.open(args.archive, "r:gz") as bundle:
        qc, validation = [table(bundle, n) for n in ("ecg_qc.csv", "ecg_validation.csv")]
    if qc.keys() != validation.keys():
        raise ValueError("QC and validation keys differ")
    rows = []
    for key, row in qc.items():
        if row["session"] != "ses-01":
            continue
        status, reason, recall, f1 = classify(row, validation[key], limits)
        rows.append({**dict(zip(KEYS, key)), "recording": row["recording"],
                     "processing_status": row["status"], "reference_available": row["reference_available"],
                     "eligibility": status, "reason": reason,
                     "tp": validation[key]["tp"], "n_ref": validation[key]["n_ref"],
                     "n_ours": validation[key]["n_ours"], "recall": recall, "f1": f1,
                     "h0a_f1_threshold_met": None if f1 is None else f1 >= f1_cutoff})
    if not rows:
        raise ValueError("No attentive recordings in recovery tables")
    run = runlog.start_run(cfg, "exp2_ecg_recovery_audit", "exp2_ecg_recovery_audit", member="A")
    with (run.output_dir / "ecg_eligibility.csv").open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["run_id", *rows[0]])
        writer.writeheader()
        writer.writerows({"run_id": run.run_id, **row} for row in rows)
    summary = dict(archive_sha256=digest, experiment=2, session="ses-01",
                   source="Recovered diagnostic QC and beat-validation tables",
                   decision="D-33 Proposed", deviation="DV-04",
                   raw_ecg_reprocessed=False, n_recordings=len(rows),
                   eligibility=dict(Counter(r["eligibility"] for r in rows)),
                   unevaluable_reasons=dict(Counter(r["reason"] for r in rows if r["eligibility"]=="unevaluable")),
                   n_f1_threshold_met=sum(r["h0a_f1_threshold_met"] is True for r in rows),
                   minimum_recall=limits, f1_threshold=f1_cutoff)
    runlog.save_json(run, summary, "ecg_recovery_audit.json")
    runlog.finish_run(run, note="D-33/DV-04 retrospective recovered ECG table audit; no raw detector rerun.")
    print(summary)


if __name__ == "__main__":
    main()
