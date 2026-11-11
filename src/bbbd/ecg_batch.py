"""Experiment 2 ECG batch processing.

Uses the frozen ECG detector and thresholds.
Missing reference annotations are not treated as failed detection.
No exclusion decision is inferred from an undefined denominator.
"""

from pathlib import Path
import argparse
import json

import numpy as np
import pandas as pd

from bbbd import ecg
from bbbd.config import load_config


def process_recording(path, root, cfg):
    """Process one ECG recording and return validation, QC and features."""

    relative = path.relative_to(root)
    subject, session = relative.parts[:2]

    base = path.name.removesuffix(
        "_recording-ecg_physio.tsv.gz"
    )

    video = base.split("_task-")[-1]

    metadata_path = path.with_name(
        base + "_recording-ecg_physio.json"
    )

    reference_path = (
        root / "derivatives" / subject / session / "beh"
        / f"{base}_desc-rpeak_timestamps.tsv.gz"
    )

    keys = {
        "experiment": 2,
        "subject": subject,
        "video": video,
        "session": session,
        "variant": "V1",
    }

    qc = {
        **keys,
        "recording": base,
        "reference_available": reference_path.exists(),
        "status": "error",
        "error": "",
        "ecg_exclusion_status": "undetermined",
    }

    validation = dict(keys)
    features = dict(keys)

    try:
        with open(metadata_path) as f:
            metadata = json.load(f)

        assert metadata["Columns"] == ["rawECG"], (
            f"Unexpected columns: {metadata['Columns']}"
        )

        sfreq = float(metadata["SamplingFrequency"])
        assert sfreq > 0

        signal = pd.read_csv(
            path,
            sep="\t",
            header=None,
        ).iloc[:, 0].to_numpy(dtype=float)

        assert len(signal) > 0, "Empty ECG signal"
        assert np.all(np.isfinite(signal)), (
            "Non-finite values in ECG"
        )

        duration = len(signal) / sfreq

        peaks = ecg.detect_rpeaks(
            signal,
            sfreq,
            method=cfg["ecg"]["method"],
        )

        peaks = np.asarray(peaks, dtype=int)

        assert np.all(np.diff(peaks) > 0), (
            "Detected peaks are not strictly increasing"
        )
        assert np.all((peaks >= 0) & (peaks < len(signal)))

        rr_ms, _ = ecg.clean_rr(
            peaks,
            sfreq,
            rr_min_ms=cfg["ecg"]["rr_min_ms"],
            rr_max_ms=cfg["ecg"]["rr_max_ms"],
        )

        cardiac = ecg.hr_features(rr_ms)

        qc.update({
            "status": "processed",
            "sfreq": sfreq,
            "duration_s": duration,
            "n_samples": len(signal),
            "n_detected_peaks": len(peaks),
            "n_rr": len(rr_ms),
            "valid_rr_frac": (
                float(np.isfinite(rr_ms).mean())
                if len(rr_ms) else np.nan
            ),
        })

        features.update(cardiac)

        if reference_path.exists():
            reference_df = pd.read_csv(
                reference_path,
                sep="\t",
            )

            assert "timestamp" in reference_df.columns

            reference_times = reference_df[
                "timestamp"
            ].to_numpy(dtype=float)

            assert len(reference_times) > 0
            assert np.all(np.isfinite(reference_times))
            assert np.all(np.diff(reference_times) > 0)
            assert reference_times.min() >= 0
            assert reference_times.max() <= duration

            reference_samples = reference_times * sfreq

            metrics = ecg.match_beats(
                peaks,
                reference_samples,
                sfreq,
                tol_ms=cfg["ecg"]["match_tolerance_ms"],
            )

            validation.update(metrics)

            validation["f1_threshold_met"] = bool(
                metrics["f1"] >=
                cfg["ecg"]["match_f1_threshold"]
            )

            validation["reference_recall"] = metrics["recall"]

            # Diagnostic only. Do not equate this with the
            # preregistered ECG exclusion decision.
            validation["reference_recall_ge_80pct"] = bool(
                metrics["recall"] >= 0.80
            )

        else:
            validation.update({
                "n_ours": len(peaks),
                "n_ref": np.nan,
                "tp": np.nan,
                "precision": np.nan,
                "recall": np.nan,
                "f1": np.nan,
                "median_error_ms": np.nan,
                "f1_threshold_met": pd.NA,
                "reference_recall": np.nan,
                "reference_recall_ge_80pct": pd.NA,
            })

        return qc, validation, features

    except Exception as exc:
        qc["status"] = "error"
        qc["error"] = f"{type(exc).__name__}: {exc}"

        return qc, validation, features


def main():
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--data-root",
        default=str(Path.home() / "MML_BBBD"),
    )

    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Process only the first N recordings for diagnostics",
    )

    parser.add_argument(
        "--output",
        default=None,
        help="Directory for diagnostic output CSV files",
    )

    args = parser.parse_args()

    cfg = load_config(data_root=args.data_root)
    root = Path(cfg["paths"]["raw"])

    paths = sorted(
        p for p in root.rglob(
            "*recording-ecg_physio.tsv.gz"
        )
        if "derivatives" not in p.parts
    )

    total = len(paths)

    if args.limit is not None:
        assert args.limit > 0
        paths = paths[:args.limit]

    assert paths, "No raw ECG recordings found"

    qc_rows = []
    validation_rows = []
    feature_rows = []

    for index, path in enumerate(paths, 1):
        qc, validation, features = process_recording(
            path, root, cfg
        )

        qc_rows.append(qc)
        validation_rows.append(validation)
        feature_rows.append(features)

        print(
            f"[{index}/{len(paths)}] "
            f"{qc['recording']} "
            f"{qc['status']}",
            flush=True,
        )

    qc_df = pd.DataFrame(qc_rows)
    validation_df = pd.DataFrame(validation_rows)
    feature_df = pd.DataFrame(feature_rows)

    print("\n========== SUMMARY ==========")
    print("Total dataset recordings:", total)
    print("Attempted:", len(paths))
    print(
        "Processed:",
        int((qc_df["status"] == "processed").sum())
    )
    print(
        "Errors:",
        int((qc_df["status"] == "error").sum())
    )
    print(
        "Reference available:",
        int(qc_df["reference_available"].sum())
    )

    if "f1" in validation_df:
        print(
            "Median F1:",
            validation_df["f1"].median()
        )

        print(
            "F1 >= threshold:",
            int(
                validation_df["f1_threshold_met"]
                .fillna(False)
                .astype(bool)
                .sum()
            ),
        )

    if args.output:
        output = Path(args.output)
        output.mkdir(parents=True, exist_ok=True)

        qc_df.to_csv(
            output / "ecg_qc.csv",
            index=False,
        )

        validation_df.to_csv(
            output / "ecg_validation.csv",
            index=False,
        )

        feature_df.to_csv(
            output / "ecg_features.csv",
            index=False,
        )

        print("\nDiagnostic files saved to:", output)

    if (qc_df["status"] == "error").any():
        print("\n========== ERRORS ==========")
        print(
            qc_df.loc[
                qc_df["status"] == "error",
                ["recording", "error"]
            ].head(20).to_string(index=False)
        )


if __name__ == "__main__":
    main()
