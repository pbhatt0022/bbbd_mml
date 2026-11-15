"""Generate registered attentive Experiment 2 eye features directly from the raw ZIP."""
import argparse
import gzip
import json
import re
from zipfile import ZipFile

import pandas as pd

from bbbd import eye, features, runlog
from bbbd.config import load_config

GAZE = re.compile(
    r"sub-(\d+)/ses-01/eyetrack/sub-\1_ses-01_task-stim(\d+)_gaze_visualangle_eyetrack\.tsv\.gz"
)


def read_eye(archive, name, columns):
    sidecar = json.loads(archive.read(name.removesuffix(".tsv.gz") + ".json"))
    if (sidecar["Columns"] != columns or sidecar["SamplingFrequency"] != 128
            or sidecar["StartTime"] != 0
            or not sidecar["TaskName"].endswith(", Attentive Condition")):
        raise ValueError(f"Unexpected metadata: {name}")
    if columns[0] == "x" and any(sidecar[c]["Units"] != "screen pixels" for c in ("x", "y")):
        raise ValueError(f"Unexpected gaze units: {name}")
    with archive.open(name) as member, gzip.GzipFile(fileobj=member) as raw:
        data = pd.read_csv(raw, sep="\t", header=None, dtype=float)
    if data.empty or data.shape[1] != len(columns):
        raise ValueError(f"Unexpected table shape: {name}")
    data.columns = columns
    return data


def extract(archive, cfg):
    screen = cfg["eye"]["screen"]
    scale = screen["px_per_deg"] or eye.px_per_deg_from_screen(
        screen["width_px"], screen["width_cm"], screen["distance_cm"]
    )
    rows = []
    keys = set()
    for name in sorted(archive.namelist()):
        match = GAZE.fullmatch(name)
        if not match:
            continue
        subject, video = match.groups()
        key = (int(subject), int(video))
        if key in keys:
            raise ValueError(f"Duplicate recording key: {key}")
        keys.add(key)
        gaze = read_eye(archive, name, ["x", "y", "vdx", "vdy"])
        pupil = read_eye(archive, name.replace("_gaze_visualangle_", "_pupil_"), ["pupil_size"])
        if len(gaze) != len(pupil):
            raise ValueError(f"Unequal gaze and pupil lengths: {name}")
        row = features.eye_features(gaze.x.to_numpy()/scale, gaze.y.to_numpy()/scale,
                                    pupil.pupil_size.to_numpy(), 128, cfg["eye"])
        rows.append(dict(experiment=2, subject=f"sub-{subject}", video=int(video),
                         session="ses-01", variant="V1",
                         excluded=row["eye_invalid_frac"] > cfg["exclusions"]["eye_max_invalid_frac"],
                         **row))
    if not rows:
        raise ValueError("No matching attentive Experiment 2 recordings")
    return pd.DataFrame(rows), scale


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("archive")
    args = parser.parse_args()
    cfg = load_config()
    with ZipFile(args.archive) as archive:
        table, scale = extract(archive, cfg)
    run = runlog.start_run(cfg, "eye_features_exp2", "exp2_eye_features", member="A")
    runlog.save_table(run, table, "eye_features_exp2.csv")
    runlog.save_json(run, {"archive": "experiment2.zip", "px_per_deg": scale,
                          "calibration": "D-26 assumption applied under Proposed D-32",
                          "session": "ses-01", "n_rows": len(table),
                          "n_excluded": int(table.excluded.sum())}, "eye_features_exp2.json")
    runlog.finish_run(run, note="D-32/DV-03 Experiment 2 eye features; preprocessing only.")


if __name__ == "__main__":
    main()
