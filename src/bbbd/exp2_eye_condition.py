"""Paired Experiment 2 eye event rates, attentive against distracted (D-37 / DV-08).

R-014 covered the attentive session only, because that is what prediction needed.
This covers both sessions so the condition contrast can be computed within learner,
which is the behavioural check on whether R-018's low-frequency EEG difference could
be ocular.

Blink rate is the metric to lead on: it comes from pupil dropout (D-25) and does not
depend on the D-26 px/deg scale. Saccade and fixation rates use one constant scale
for both sessions, so a wrong scale moves both equally and the within-learner
contrast survives it.

Reuses the V1 settings, the exclusion rule and the feature code from R-014 unchanged.
R-014 is not modified.

    python -m bbbd.exp2_eye_condition <experiment2.zip>
"""
import argparse
import re
from zipfile import ZipFile

import numpy as np
import pandas as pd
from scipy import stats

from bbbd import features, runlog
from bbbd.config import load_config
from bbbd.exp2_eye_features import read_eye as read_attentive_eye

GAZE = re.compile(
    r"sub-(\d+)/ses-(01|02)/eyetrack/"
    r"sub-\1_ses-\2_task-stim(\d+)_gaze_visualangle_eyetrack\.tsv\.gz"
)
# The sidecars state the condition outright for Experiment 2, so unlike D-29 for
# Experiment 1 this mapping is read from the data, not inferred.
CONDITION = {"01": "Attentive Condition", "02": "Distracted Condition"}
RATES = ["blink_rate_min", "saccade_rate_min", "fixation_rate_min",
         "fixation_dur_ms_mean", "eye_invalid_frac"]
# Blink first: it is the only one of these independent of the px/deg scale.
PRIMARY = "blink_rate_min"


def read_eye(archive, name, columns, session):
    """read_eye from R-014, with the sidecar condition checked per session."""
    expected = CONDITION[session]
    if expected == "Attentive Condition":
        return read_attentive_eye(archive, name, columns)
    # Same checks as R-014's reader, against the distracted label.
    import gzip
    import json
    sidecar = json.loads(archive.read(name.removesuffix(".tsv.gz") + ".json"))
    if (sidecar["Columns"] != columns or sidecar["SamplingFrequency"] != 128
            or sidecar["StartTime"] != 0
            or not sidecar["TaskName"].endswith(", " + expected)):
        raise ValueError(f"Unexpected metadata: {name}")
    if columns[0] == "x" and any(sidecar[c]["Units"] != "screen pixels" for c in ("x", "y")):
        raise ValueError(f"Unexpected gaze units: {name}")
    with archive.open(name) as member, gzip.GzipFile(fileobj=member) as raw:
        data = pd.read_csv(raw, sep="\t", header=None, dtype=float)
    if data.empty or data.shape[1] != len(columns):
        raise ValueError(f"Unexpected table shape: {name}")
    data.columns = columns
    return data


def extract(archive, cfg, scale):
    rows, keys = [], set()
    for name in sorted(archive.namelist()):
        match = GAZE.fullmatch(name)
        if not match:
            continue
        subject, session, video = match.groups()
        key = (int(subject), session, int(video))
        if key in keys:
            raise ValueError(f"Duplicate recording key: {key}")
        keys.add(key)
        gaze = read_eye(archive, name, ["x", "y", "vdx", "vdy"], session)
        pupil = read_eye(archive, name.replace("_gaze_visualangle_", "_pupil_"),
                         ["pupil_size"], session)
        if len(gaze) != len(pupil):
            raise ValueError(f"Unequal gaze and pupil lengths: {name}")
        row = features.eye_features(gaze.x.to_numpy() / scale, gaze.y.to_numpy() / scale,
                                    pupil.pupil_size.to_numpy(), 128, cfg["eye"])
        rows.append(dict(experiment=2, subject=f"sub-{subject}", video=int(video),
                         session=f"ses-{session}",
                         condition="attentive" if session == "01" else "distracted",
                         variant="V1",
                         excluded=row["eye_invalid_frac"] > cfg["exclusions"]["eye_max_invalid_frac"],
                         **row))
    if not rows:
        raise ValueError("No matching Experiment 2 recordings")
    return pd.DataFrame(rows)


def contrast(table, metric):
    """Paired attentive-vs-distracted test over learner means of `metric`."""
    means = (table.groupby(["subject", "condition"])[metric].mean()
             .unstack("condition"))
    pair = means[["attentive", "distracted"]].dropna()
    a, d = pair["attentive"].to_numpy(), pair["distracted"].to_numpy()
    diff = d - a
    sd = diff.std(ddof=1)
    t, p = stats.ttest_rel(d, a)
    return dict(metric=metric, n_learners=int(len(diff)),
                mean_attentive=float(a.mean()), mean_distracted=float(d.mean()),
                mean_diff=float(diff.mean()),
                pct_higher_when_distracted=float(100.0 * np.mean(diff > 0)),
                cohens_dz=float(diff.mean() / sd) if sd > 0 else float("nan"),
                t=float(t), p=float(p),
                p_wilcoxon=float(stats.wilcoxon(d, a).pvalue) if np.any(diff) else float("nan"),
                scale_dependent=metric != "blink_rate_min")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("archive")
    args = parser.parse_args()

    cfg = load_config()
    screen = cfg["eye"]["screen"]
    from bbbd import eye
    scale = screen["px_per_deg"] or eye.px_per_deg_from_screen(
        screen["width_px"], screen["width_cm"], screen["distance_cm"])

    with ZipFile(args.archive) as archive:
        table = extract(archive, cfg, scale)

    kept = table[~table["excluded"]]
    rows = [contrast(kept, m) for m in RATES]
    primary = next(r for r in rows if r["metric"] == PRIMARY)

    run = runlog.start_run(cfg, "exp2_eye_condition", "exp2_eye_condition", member="A")
    runlog.save_table(run, table, "eye_features_exp2_both_sessions.csv")
    runlog.save_table(run, pd.DataFrame(rows), "exp2_condition_contrasts.csv")
    summary = dict(
        experiment=2, decision="D-37 Proposed", deviation="DV-08",
        archive="experiment2.zip", px_per_deg=scale,
        calibration="D-26 assumption; blink rate does not depend on it",
        condition_labels_source="archive sidecar TaskName, not inferred",
        confirmatory=False,
        n_recordings=int(len(table)), n_excluded=int(table["excluded"].sum()),
        n_recordings_attentive=int((table["session"] == "ses-01").sum()),
        n_recordings_distracted=int((table["session"] == "ses-02").sum()),
        n_learners=int(table["subject"].nunique()),
        n_learners_paired=primary["n_learners"],
        primary_metric=PRIMARY, primary=primary,
        contrasts={r["metric"]: r for r in rows},
    )
    runlog.save_json(run, summary, "exp2_eye_condition.json")
    runlog.finish_run(run, note="D-37/DV-08 paired Experiment 2 eye condition rates; "
                                "ocular check for R-018. R-014 unchanged.")
    for r in rows:
        print(f"  {r['metric']:22s} att {r['mean_attentive']:9.3f}  dis {r['mean_distracted']:9.3f}"
              f"  d_z {r['cohens_dz']:+.2f}  p {r['p']:.4g}"
              f"{'' if r['metric'] == PRIMARY else '  (scale-dependent)'}")


if __name__ == "__main__":
    main()
