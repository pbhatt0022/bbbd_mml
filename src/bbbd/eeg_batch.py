"""Experiment 2 EEG/EOG batch preprocessing and diagnostic QC."""

import argparse
import json
from pathlib import Path

import mne
import numpy as np
import pandas as pd

from bbbd import eeg, features
from bbbd import batch_runlog
from bbbd.config import load_config


def process_recording(eeg_path, cfg):
    """Process one matched EEG/EOG recording."""

    eeg_path = Path(eeg_path)
    base = eeg_path.name.removesuffix("_eeg.bdf")

    session_dir = eeg_path.parent.parent
    beh_dir = session_dir / "beh"

    events_path = eeg_path.with_name(f"{base}_events.tsv")
    eog_path = beh_dir / f"{base}_recording-eog_physio.tsv.gz"
    eog_json = beh_dir / f"{base}_recording-eog_physio.json"

    if not eog_path.exists():
        raise FileNotFoundError(f"Missing EOG: {eog_path}")

    raw = eeg.load_bdf(eeg_path)
    sfreq = float(raw.info["sfreq"])
    original_samples = raw.n_times

    if len(raw.ch_names) != 64:
        raise ValueError("Expected 64 EEG channels")

    # Verify event-defined recording interval.
    events = pd.read_csv(events_path, sep="\t")

    starts = events.loc[events["event"] == "start", "onset"]
    ends = events.loc[events["event"] == "end", "onset"]

    if len(starts) != 1 or len(ends) != 1:
        raise ValueError("Expected one start and one end event")

    if not np.isclose(float(starts.iloc[0]), 0):
        raise ValueError("Unexpected EEG start time")

    endpoint = float(ends.iloc[0]) * sfreq
    end_samples = round(endpoint)

    if not np.isclose(endpoint, end_samples, atol=1e-3):
        raise ValueError("EEG endpoint not on sample boundary")

    if not (0 < end_samples <= original_samples):
        raise ValueError("Invalid EEG endpoint")

    # Load independently stored EOG.
    with open(eog_json) as f:
        metadata = json.load(f)

    if float(metadata["SamplingFrequency"]) != sfreq:
        raise ValueError("EEG/EOG sampling rates differ")

    eog_data = pd.read_csv(
        eog_path,
        sep="\t",
        header=None,
    ).to_numpy(dtype=float)

    eog_names = metadata["Columns"]

    if len(eog_names) != 6 or eog_data.shape[1] != 6:
        raise ValueError("Expected six EOG channels")

    if eog_data.shape[0] != end_samples:
        raise ValueError("EOG length differs from event endpoint")

    if not np.isfinite(eog_data).all():
        raise ValueError("Non-finite EOG samples")

    # MNE expects EOG values in volts.
    for name in eog_names:
        units = metadata.get(name, {}).get("Units")
        if units not in ("uV", "µV"):
            raise ValueError(f"Unexpected EOG units: {name}={units}")

    # Exclude EEG samples beyond the event-defined endpoint.
    raw.crop(tmin=0, tmax=(end_samples - 1) / sfreq)

    if raw.n_times != eog_data.shape[0]:
        raise ValueError("EEG/EOG lengths differ after trimming")

    if not np.isfinite(raw.get_data(picks="eeg")).all():
        raise ValueError("Non-finite EEG samples")

    # Normalize the observed capitalization discrepancy.
    if "Afz" in raw.ch_names:
        raw.rename_channels({"Afz": "AFz"})

    # Add six correctly typed EOG channels.
    eog_info = mne.create_info(
        ch_names=[f"EOG_{name}" for name in eog_names],
        sfreq=sfreq,
        ch_types=["eog"] * 6,
    )

    eog_raw = mne.io.RawArray(
        eog_data.T * 1e-6,
        eog_info,
        verbose="ERROR",
    )

    raw.add_channels([eog_raw], force_update_info=True)

    if raw.get_channel_types().count("eeg") != 64:
        raise ValueError("Incorrect EEG channel count")

    if raw.get_channel_types().count("eog") != 6:
        raise ValueError("Incorrect EOG channel count")

    # Reuse the existing frozen V1 preprocessing pipeline.
    cleaned, qc = eeg.preprocess(
        raw,
        cfg["eeg"],
        seed=cfg["seeds"]["global"],
    )

    if qc["eye_artifact"] != "eog_regression":
        raise ValueError("EOG regression did not execute")

    bad_channel_frac = float(qc["bad_channel_frac"])
    bad_time_frac = float(qc["bad_time_frac"])

    exclude_channels = (
        bad_channel_frac >
        cfg["exclusions"]["eeg_max_bad_channel_frac"]
    )

    exclude_time = (
        bad_time_frac >
        cfg["exclusions"]["eeg_max_bad_time_frac"]
    )

    # Create a sample mask using the existing 1-second QC segments.
    good_mask = np.ones(cleaned.n_times, dtype=bool)
    segment_samples = int(round(sfreq))

    for segment_index in qc["bad_segments_1s"]:
        start = int(segment_index) * segment_samples
        stop = min(start + segment_samples, cleaned.n_times)
        good_mask[start:stop] = False

    # Extract features only from QC-passing recordings.
    feature_row = None

    if not (exclude_channels or exclude_time):
        if good_mask.sum() < 2 * sfreq:
            raise ValueError("Insufficient artifact-free EEG samples")

        eeg_data = cleaned.get_data(picks="eeg")

        extracted = features.eeg_features(
            data=eeg_data,
            ch_names=cleaned.copy().pick("eeg").ch_names,
            sfreq=sfreq,
            cfg_eeg=cfg["eeg"],
            good_mask=good_mask,
        )

        feature_row = {
            "experiment": 2,
            "subject": session_dir.parent.name,
            "video": base.split("_task-")[-1],
            "session": session_dir.name,
            "variant": cfg["eeg"]["variant"],
            "recording": base,
            "eeg_good_sample_frac": float(good_mask.mean()),
            **extracted,
        }

        feature_values = np.array(
            list(extracted.values()), dtype=float
        )

        if len(extracted) != 24 or not np.isfinite(feature_values).all():
            raise ValueError("Incomplete or non-finite EEG features")

    qc_row = {
        "recording": base,
        "subject": session_dir.parent.name,
        "session": session_dir.name,
        "status": "processed",
        "original_eeg_samples": original_samples,
        "aligned_samples": end_samples,
        "trimmed_samples": original_samples - end_samples,
        "sfreq": sfreq,
        "n_eeg": qc["n_eeg"],
        "n_eog": 6,
        "bad_channels": json.dumps(qc["bad_channels"]),
        "bad_channel_frac": bad_channel_frac,
        "bad_time_frac": bad_time_frac,
        "bad_segments_1s": json.dumps(qc["bad_segments_1s"]),
        "eye_artifact": qc["eye_artifact"],
        "exclude_bad_channels": bool(exclude_channels),
        "exclude_bad_time": bool(exclude_time),
        "exclude": bool(exclude_channels or exclude_time),
    }

    return qc_row, feature_row


def main():
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--limit", type=int, default=3,
        help="Number of EEG recordings to attempt",
    )

    parser.add_argument(
        "--out",
        default="/home/mml_07/MML_BBBD/04_results/eeg_diagnostic",
    )

    parser.add_argument(
        "--member",
        default="B",
        help="Who ran this, for the run registry",
    )

    parser.add_argument(
        "--no-runlog",
        action="store_true",
        help="Skip run registration; diagnostics only, results cannot be cited",
    )

    args = parser.parse_args()

    cfg = load_config(data_root="/home/mml_07/MML_BBBD")
    root = Path(cfg["paths"]["raw"])

    files = sorted(
        p for p in root.rglob("*_eeg.bdf")
        if "derivatives" not in p.parts
    )

    # This diagnostic covers matched EEG/EOG pairs only.
    matched = []

    for path in files:
        base = path.name.removesuffix("_eeg.bdf")
        eog_path = (
            path.parent.parent / "beh"
            / f"{base}_recording-eog_physio.tsv.gz"
        )

        if eog_path.exists():
            matched.append(path)

    if args.limit < 0:
        raise ValueError("--limit must be nonnegative")

    selected = matched[:args.limit] if args.limit else matched

    print(f"Total EEG files: {len(files)}", flush=True)
    print(f"Matched EEG/EOG files: {len(matched)}", flush=True)
    print(f"Selected for processing: {len(selected)}", flush=True)

    qc_rows = []
    feature_rows = []
    error_rows = []

    for index, path in enumerate(selected, 1):
        print(
            f"\n[{index}/{len(selected)}] {path.name}",
            flush=True,
        )

        try:
            result, feature_row = process_recording(path, cfg)
            qc_rows.append(result)

            if feature_row is not None:
                feature_rows.append(feature_row)

            print(
                "PASS",
                "bad_channel_frac=",
                result["bad_channel_frac"],
                "bad_time_frac=",
                result["bad_time_frac"],
                "exclude=",
                result["exclude"],
                flush=True,
            )

        except Exception as exc:
            error_rows.append({
                "recording": path.name.removesuffix("_eeg.bdf"),
                "error_type": type(exc).__name__,
                "error": str(exc),
            })

            print(
                f"ERROR: {type(exc).__name__}: {exc}",
                flush=True,
            )

    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)

    pd.DataFrame(qc_rows).to_csv(
        out / "eeg_qc.csv",
        index=False,
    )

    pd.DataFrame(feature_rows).to_csv(
        out / "eeg_features.csv",
        index=False,
    )

    pd.DataFrame(
        error_rows,
        columns=["recording", "error_type", "error"],
    ).to_csv(
        out / "eeg_errors.csv",
        index=False,
    )

    print("\n========== BATCH SUMMARY ==========")
    print("Attempted:", len(selected))
    print("Processed:", len(qc_rows))
    print("Feature rows:", len(feature_rows))
    print("Errors:", len(error_rows))

    if qc_rows:
        print(
            "QC exclusions:",
            sum(row["exclude"] for row in qc_rows),
        )

    print("Results:", out)

    # README rule 3: register through runlog so these numbers carry a run ID.
    if not args.no_runlog:
        qc_df = pd.DataFrame(qc_rows)
        summary = {
            "experiment": 2, "modality": "eeg", "variant": cfg["eeg"]["variant"],
            "attempted": int(len(selected)),
            "processed": int(len(qc_rows)),
            "feature_rows": int(len(feature_rows)),
            "errors": int(len(error_rows)),
            "eye_artifact": cfg["eeg"]["eye_artifact"],
            "highpass_hz": cfg["eeg"]["highpass_hz"],
            "max_bad_channel_frac": cfg["exclusions"]["eeg_max_bad_channel_frac"],
            "max_bad_time_frac": cfg["exclusions"]["eeg_max_bad_time_frac"],
        }
        if qc_rows:
            summary["qc_exclusions"] = int(sum(row["exclude"] for row in qc_rows))
        run_id = batch_runlog.register(
            cfg, name="eeg_exp2", notebook="eeg_batch", member=args.member,
            tables={"eeg_qc.csv": qc_df,
                    "eeg_features.csv": pd.DataFrame(feature_rows),
                    "eeg_errors.csv": pd.DataFrame(
                        error_rows, columns=["recording", "error_type", "error"])},
            summary=summary,
            note=f"EEG Exp 2, {cfg['eeg']['variant']}, {cfg['eeg']['eye_artifact']}.")
        print(f"registered as {run_id}; cite that id for any number above")


if __name__ == "__main__":
    main()
