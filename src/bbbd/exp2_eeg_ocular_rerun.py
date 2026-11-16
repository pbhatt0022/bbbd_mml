"""From-raw Experiment 2 EEG with and without EOG regression (D-40 / DV-10).

R-018 found a low-frequency increase in the distracted session on a pipeline
that applied no ocular correction. R-019 could not test the blink route and
R-020's topography argument is indirect. This reprocesses the raw recordings
and applies EOG regression (D-12), so the condition contrast can be compared
with and against the correction.

Each recording is filtered once, then `preprocess` runs twice from that copy:
once with the EOG channels attached, once without. The only difference between
the two outputs is the regression, so the comparison isolates it.

This is the project's first from-raw EEG run. It is **not** RQ3, which asks
whether the modality ranking is stable under ICA instead of EOG regression.

    python -m bbbd.exp2_eeg_ocular_rerun <experiment2.zip> [--limit N]
"""
import argparse
import gzip
import io
import json
import re
import tempfile
import zipfile
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats

from . import eeg as eegmod
from . import runlog
from .config import load_config

RAW = re.compile(r"^sub-(\d+)/ses-(01|02)/eeg/"
                 r"sub-\1_ses-\2_task-stim(\d+)_eeg\.bdf$")
EOG_TEMPLATE = ("sub-{sub}/ses-{ses}/beh/"
                "sub-{sub}_ses-{ses}_task-stim{stim}_recording-eog_physio")
ATTENTIVE, DISTRACTED = "ses-01", "ses-02"
PRIMARY_BAND = "delta"
FRONT, BACK = "frontal", "occipital"
N_BOOTSTRAP, SEED = 2000, 2026


def holm(pvalues):
    order = np.argsort(pvalues)
    n, adjusted, running = len(pvalues), np.empty(len(pvalues)), 0.0
    for rank, idx in enumerate(order):
        running = max(running, (n - rank) * pvalues[idx])
        adjusted[idx] = min(running, 1.0)
    return adjusted


def read_eog(archive, sub, ses, stim):
    """Six-channel EOG physio for one recording, with its sidecar checked."""
    base = EOG_TEMPLATE.format(sub=sub, ses=ses, stim=stim)
    sidecar = json.loads(archive.read(base + ".json"))
    if sidecar["SamplingFrequency"] != 128 or sidecar["StartTime"] != 0:
        raise ValueError(f"Unexpected EOG metadata: {base}")
    with archive.open(base + ".tsv.gz") as member, gzip.GzipFile(fileobj=member) as raw:
        data = pd.read_csv(raw, sep="\t", header=None, dtype=float)
    if data.empty:
        raise ValueError(f"Empty EOG table: {base}")
    return data.to_numpy().T, list(sidecar["Columns"])


def attach_eog(raw, eog_data, names):
    """Return a copy of `raw` with EOG channels appended, both truncated to a common length."""
    import mne
    n = min(raw.n_times, eog_data.shape[1])
    out = raw.copy().crop(tmax=(n - 1) / raw.info["sfreq"])
    info = mne.create_info([f"EOG{i+1}" for i in range(len(names))],
                           raw.info["sfreq"], ch_types="eog")
    # BDF is volts in MNE; the physio file is microvolts.
    extra = mne.io.RawArray(eog_data[:, :n] * 1e-6, info, verbose="error")
    out.add_channels([extra], force_update_info=True)
    return out, n


def regional_features(raw, cfg_eeg):
    """Relative band power and 1/f slope, averaged within each configured region."""
    picked = raw.copy().pick("eeg")
    data = picked.get_data()
    sfreq = picked.info["sfreq"]
    power = eegmod.band_power(data, sfreq, cfg_eeg["bands_hz"])
    slope = eegmod.aperiodic_slope(data, sfreq)
    names = picked.ch_names
    row = {}
    for region, channels in cfg_eeg["regions"].items():
        idx = [names.index(c) for c in channels if c in names]
        if not idx:
            continue
        for band, values in power.items():
            row[f"eeg_{region}_{band}_rel"] = float(np.mean(values[idx]))
        row[f"eeg_{region}_slope"] = float(np.mean(slope[idx]))
    return row


def process(archive, name, cfg_eeg, tmpdir):
    import mne
    sub, ses, stim = RAW.match(name).groups()
    target = Path(tmpdir) / "recording.bdf"
    with archive.open(name) as src, target.open("wb") as dst:
        dst.write(src.read())
    raw = eegmod.load_bdf(target)
    # The release spells one electrode 'Afz'. The biosemi64 montage and
    # config.yaml's frontal region both use 'AFz', so without this the channel
    # gets no position, spherical-spline interpolation fails, and the channel
    # is silently dropped from the frontal average.
    if "Afz" in raw.ch_names:
        raw.rename_channels({"Afz": "AFz"})
    eog_data, eog_names = read_eog(archive, sub, ses, stim)
    with_eog, n_common = attach_eog(raw, eog_data, eog_names)
    without_eog = with_eog.copy().pick("eeg")

    rows = {}
    for label, source in (("corrected", with_eog), ("uncorrected", without_eog)):
        clean, report = eegmod.preprocess(source.copy(), cfg_eeg)
        rows[label] = dict(
            subject=f"sub-{sub}", session=f"ses-{ses}", video=int(stim),
            variant=label, eye_artifact=report["eye_artifact"],
            n_bad_channels=len(report["bad_channels"]),
            bad_time_frac=report["bad_time_frac"],
            eeg_samples=raw.n_times, eog_samples=eog_data.shape[1],
            common_samples=n_common,
            **regional_features(clean, cfg_eeg))
    if rows["corrected"]["eye_artifact"] != "eog_regression":
        raise ValueError(f"EOG regression did not run for {name}")
    if rows["uncorrected"]["eye_artifact"] == "eog_regression":
        raise ValueError(f"Uncorrected variant was corrected for {name}")
    return [rows["corrected"], rows["uncorrected"]]


def learner_diffs(df, column):
    means = df.groupby(["subject", "session"])[column].mean().unstack("session")
    pair = means[[ATTENTIVE, DISTRACTED]].dropna()
    return (pair[DISTRACTED] - pair[ATTENTIVE]).to_numpy()


def describe(diff, name):
    sd = diff.std(ddof=1)
    t, p = stats.ttest_1samp(diff, 0.0)
    return dict(name=name, n_learners=int(len(diff)), mean_diff=float(diff.mean()),
                cohens_dz=float(diff.mean() / sd) if sd > 0 else float("nan"),
                t=float(t), p=float(p))


def bootstrap_ci(diff, level=0.95):
    rng = np.random.default_rng(SEED)
    means = diff[rng.integers(0, len(diff), size=(N_BOOTSTRAP, len(diff)))].mean(axis=1)
    return (float(np.percentile(means, (1 - level) / 2 * 100)),
            float(np.percentile(means, (1 + level) / 2 * 100)))


def analyse(table, regions):
    out = {}
    for variant in ("corrected", "uncorrected"):
        sub = table[table["variant"] == variant]
        rows = [describe(learner_diffs(sub, f"eeg_{r}_{PRIMARY_BAND}_rel"), r)
                for r in regions]
        for row, adj in zip(rows, holm([r["p"] for r in rows])):
            row["p_holm_region_family"] = float(adj)
        front = learner_diffs(sub, f"eeg_{FRONT}_{PRIMARY_BAND}_rel")
        back = learner_diffs(sub, f"eeg_{BACK}_{PRIMARY_BAND}_rel")
        gradient = describe(front - back, f"{FRONT} minus {BACK}")
        gradient["ci_low"], gradient["ci_high"] = bootstrap_ci(front - back)
        out[variant] = dict(delta_by_region={r["name"]: r for r in rows}, gradient=gradient)
    out["dz_change"] = {
        r: round(out["corrected"]["delta_by_region"][r]["cohens_dz"]
                 - out["uncorrected"]["delta_by_region"][r]["cohens_dz"], 4)
        for r in regions}
    out["survives_correction"] = {
        r: bool(out["corrected"]["delta_by_region"][r]["p_holm_region_family"] < 0.05)
        for r in regions}
    return out


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("archive")
    parser.add_argument("--limit", type=int, default=0, help="process only the first N (testing)")
    args = parser.parse_args()

    cfg = load_config()
    cfg_eeg = cfg["eeg"]
    rows, failures = [], []
    with zipfile.ZipFile(args.archive) as archive, tempfile.TemporaryDirectory() as tmp:
        names = sorted(n for n in archive.namelist() if RAW.match(n))
        if args.limit:
            names = names[:args.limit]
        print(f"[rerun] {len(names)} raw recordings", flush=True)
        for i, name in enumerate(names, 1):
            try:
                rows.extend(process(archive, name, cfg_eeg, tmp))
            except Exception as exc:                      # noqa: BLE001 - recorded, not swallowed
                failures.append({"recording": name, "error": f"{type(exc).__name__}: {exc}"})
            if i % 25 == 0:
                print(f"[rerun] {i}/{len(names)}  failures {len(failures)}", flush=True)

    table = pd.DataFrame(rows)
    if table.empty:
        raise ValueError("No recordings processed")
    result = analyse(table, list(cfg_eeg["regions"]))

    run = runlog.start_run(cfg, "exp2_eeg_ocular_rerun", "exp2_eeg_ocular_rerun", member="A")
    runlog.save_table(run, table, "regional_features_by_variant.csv")
    if failures:
        runlog.save_table(run, pd.DataFrame(failures), "failures.csv")
    summary = dict(
        experiment=2, decision="D-40 Proposed", deviation="DV-10",
        raw_eeg_reprocessed=True, source="raw sub-XX/ses-YY/eeg/*_eeg.bdf",
        ocular_correction="eog_regression (D-12)", confirmatory=False,
        is_rq3=False,
        n_recordings_attempted=len(names), n_failures=len(failures),
        n_recordings=int(table["variant"].eq("corrected").sum()),
        n_learners=int(table["subject"].nunique()),
        n_attentive=int(table[table.variant == "corrected"]["session"].eq(ATTENTIVE).sum()),
        n_distracted=int(table[table.variant == "corrected"]["session"].eq(DISTRACTED).sum()),
        n_bootstrap=N_BOOTSTRAP, seed=SEED, **result)
    runlog.save_json(run, summary, "exp2_eeg_ocular_rerun.json")
    runlog.finish_run(run, note="D-40/DV-10 from-raw Exp 2 EEG with and without EOG "
                                "regression; ocular control for R-018. Not RQ3.")

    print(f"\n  recordings {summary['n_recordings']}  learners {summary['n_learners']}"
          f"  failures {len(failures)}")
    for region in cfg_eeg["regions"]:
        c = result["corrected"]["delta_by_region"][region]
        u = result["uncorrected"]["delta_by_region"][region]
        print(f"  delta {region:10s} uncorrected d_z {u['cohens_dz']:+.2f}"
              f" -> corrected {c['cohens_dz']:+.2f}"
              f"  (Holm {c['p_holm_region_family']:.3g})"
              f"  survives={result['survives_correction'][region]}")
    g = result["corrected"]["gradient"]
    print(f"  corrected frontal-occipital gradient {g['mean_diff']:+.4f} "
          f"95% CI [{g['ci_low']:+.4f}, {g['ci_high']:+.4f}]")


if __name__ == "__main__":
    main()
