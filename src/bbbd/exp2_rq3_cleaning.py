"""RQ3 on the Experiment 2 cohort: ICA against EOG regression (D-41 / DV-11).

RQ3 asks whether the modality ranking is stable when EEG is cleaned with ICA
instead of EOG regression. The R-016 cohort and its frozen folds are held
fixed and only the 24 EEG feature columns are swapped, so rows, targets, eye
features, ECG features and splits are identical between the two variants and
the cleaning method is the only difference.

Attentive Experiment 2 EEG is recomputed from raw twice, once per variant,
then the D-35 matched ridge is rerun unchanged for each.

This answers RQ3 on the exploratory Experiment 2 cohort, which is where a
modality ranking exists. It is not the preregistered confirmatory comparison.

    python -m bbbd.exp2_rq3_cleaning <experiment2.zip>
"""
import argparse
import copy
import tempfile
import zipfile
from collections import Counter
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.model_selection import GroupKFold
from threadpoolctl import threadpool_limits

from . import cv, eeg as eegmod, runlog, stats
from .config import REPO_ROOT, load_config
from .exp2_eeg_ocular_rerun import RAW, attach_eog, read_eog
from .exp2_matched_ridge import EYE, SINGLE, fit_outer

COHORT = REPO_ROOT / "results/R-016_exp2_common_cohort"
ATTENTIVE = "ses-01"
VARIANTS = ("eog_regression", "ica")


def regional_features(raw, cfg_eeg):
    """The 24-column regional schema the R-016 cohort uses."""
    picked = raw.copy().pick("eeg")
    data, sfreq, names = picked.get_data(), picked.info["sfreq"], picked.ch_names
    power = eegmod.band_power(data, sfreq, cfg_eeg["bands_hz"])
    slope = eegmod.aperiodic_slope(data, sfreq)
    row = {}
    for region, channels in cfg_eeg["regions"].items():
        idx = [names.index(c) for c in channels if c in names]
        if not idx:
            raise ValueError(f"No channels present for region {region}")
        means = {band: float(np.mean(values[idx])) for band, values in power.items()}
        for band, value in means.items():
            row[f"eeg_{region}_{band}_rel"] = value
        row[f"eeg_{region}_alpha_theta"] = means["alpha"] / means["theta"]
        row[f"eeg_{region}_slope"] = float(np.mean(slope[idx]))
    return row


def features_from_raw(archive, cfg_eeg, wanted, tmpdir):
    """Attentive EEG features for `wanted` (subject, video) keys, under both variants."""
    rows, failures = [], []
    names = sorted(n for n in archive.namelist()
                   if (m := RAW.match(n)) and m.group(2) == "01"
                   and (int(m.group(1)), int(m.group(3))) in wanted)
    print(f"[rq3] {len(names)} attentive recordings to process", flush=True)
    for i, name in enumerate(names, 1):
        sub, ses, stim = RAW.match(name).groups()
        try:
            target = Path(tmpdir) / "recording.bdf"
            with archive.open(name) as src, target.open("wb") as dst:
                dst.write(src.read())
            raw = eegmod.load_bdf(target)
            if "Afz" in raw.ch_names:
                raw.rename_channels({"Afz": "AFz"})
            eog, eog_names = read_eog(archive, sub, ses, stim)
            prepared, _ = attach_eog(raw, eog, eog_names)
            eegmod.set_biosemi64(prepared)
            eegmod.filter_raw(prepared, cfg_eeg["highpass_hz"], cfg_eeg["line_freq_hz"],
                              cfg_eeg["notch_16hz_if_detected"])
            bads = eegmod.find_bad_channels(prepared, cfg_eeg["bad_channel_z"])
            eegmod.interpolate_bads(prepared, bads)
            eegmod.average_reference(prepared)
            for variant in VARIANTS:
                clean = prepared.copy()
                if variant == "eog_regression":
                    eegmod.eog_regression(clean)
                else:
                    eegmod.ica_remove_eog(clean, seed=0)
                rows.append(dict(subject=int(sub), video=int(stim), variant=variant,
                                 **regional_features(clean, cfg_eeg)))
        except Exception as exc:                       # noqa: BLE001 - recorded, not swallowed
            failures.append({"recording": name, "error": f"{type(exc).__name__}: {exc}"})
        if i % 25 == 0:
            print(f"[rq3] {i}/{len(names)}  failures {len(failures)}", flush=True)
    return pd.DataFrame(rows), failures


def run_ridge(table, keys, schemes, cfg, eeg_columns):
    """The D-35 matched ridge, unchanged, on one feature set."""
    ecg = ["hr_mean", "hr_sd", "rmssd"]
    columns = dict(eye=EYE, ecg=ecg, eeg=eeg_columns, eye_ecg=EYE + ecg,
                   all_sensors=EYE + ecg + eeg_columns)
    data = {name: table[cols].to_numpy(float) for name, cols in columns.items()}
    y, groups = table.quiz_z.to_numpy(float), keys.subject.to_numpy()
    if not all(np.isfinite(a).all() for a in [y, *data.values()]):
        raise ValueError("Non-finite inputs")
    options = cfg["reconciliation"]
    alphas = np.logspace(options["ridge_alpha_log10_min"], options["ridge_alpha_log10_max"],
                         options["ridge_alpha_count"])
    names = [*data, "selected_single"]
    repeats = {name: [] for name in names}
    chosen = []
    with threadpool_limits(limits=1):
        for scheme, labels in schemes.items():
            cv.check_no_leakage(labels, groups)
            batch = {name: np.full(len(y), np.nan) for name in names}
            for fold in sorted(set(labels)):
                train, test = np.flatnonzero(labels != fold), np.flatnonzero(labels == fold)
                pred, best, _, _ = fit_outer(
                    data, y, groups, (train, test, GroupKFold(cfg["cv"]["inner_splits"])),
                    alphas, options["inner_scoring"])
                for name in names:
                    batch[name][test] = pred[name]
                chosen.append(best)
            for name in names:
                repeats[name].append(batch[name])
    prediction = {k: np.mean(v, axis=0) for k, v in repeats.items()}
    metrics = {k: cv.score(y, v) for k, v in prediction.items()}
    comparisons = {}
    for a, b, level in (("eeg", "eye", .90), ("eeg", "eye_ecg", .90),
                        ("all_sensors", "selected_single", .95)):
        result = stats.paired_difference(groups, y, prediction[a], prediction[b],
                                         n_boot=cfg["stats"]["n_bootstrap"],
                                         seed=cfg["seeds"]["global"], ci=level)
        result.pop("boot")
        result["ci_level"] = level
        comparisons[f"{a}_minus_{b}"] = result
    ranking = sorted(SINGLE, key=lambda m: -metrics[m]["spearman"])
    return dict(metrics=metrics, comparisons=comparisons, ranking=ranking,
                selected_single_counts=dict(Counter(chosen)))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("archive")
    args = parser.parse_args()
    cfg = load_config()

    base = pd.read_csv(COHORT / "exp2_common_cohort.csv")
    keys, schemes = cv.load_folds(COHORT / "folds_exp2.json")
    eeg_columns = [c for c in base.columns if c.startswith("eeg_")]
    if len(eeg_columns) != 24:
        raise ValueError("Unexpected R-016 EEG schema")
    wanted = set(zip(base.subject.astype(int), base.video.astype(int)))

    with zipfile.ZipFile(args.archive) as archive, tempfile.TemporaryDirectory() as tmp:
        features, failures = features_from_raw(archive, cfg["eeg"], wanted, tmp)
    if failures:
        raise ValueError(f"{len(failures)} recordings failed: {failures[:3]}")

    results = {}
    for variant in VARIANTS:
        subset = features[features.variant == variant].drop(columns="variant")
        merged = base.drop(columns=eeg_columns).merge(
            subset, on=["subject", "video"], how="left", validate="one_to_one")
        if merged[eeg_columns].isna().any().any() or len(merged) != len(base):
            raise ValueError(f"Incomplete EEG coverage for {variant}")
        results[variant] = run_ridge(merged, keys, schemes, cfg, eeg_columns)
        print(f"[rq3] {variant}: ranking {results[variant]['ranking']}", flush=True)

    eog, ica = (results[v] for v in VARIANTS)
    summary = dict(
        research_question="RQ3", decision="D-41 Proposed", deviation="DV-11",
        venue="exploratory Experiment 2 cohort (R-016 rows and frozen folds)",
        is_preregistered_confirmatory=False, raw_eeg_reprocessed=True,
        cohort_run="R-016", comparison_run="R-017",
        n_rows=len(base), n_learners=int(base.subject.nunique()),
        n_recordings_processed=int(len(features) // len(VARIANTS)),
        variants={v: results[v] for v in VARIANTS},
        ranking_stable=eog["ranking"] == ica["ranking"],
        ranking_eog=eog["ranking"], ranking_ica=ica["ranking"],
        spearman_shift={m: round(ica["metrics"][m]["spearman"]
                                 - eog["metrics"][m]["spearman"], 4)
                        for m in eog["metrics"]},
    )
    run = runlog.start_run(cfg, "exp2_rq3_cleaning", "exp2_rq3_cleaning", member="A")
    runlog.save_table(run, features, "eeg_features_by_cleaning_variant.csv")
    runlog.save_json(run, summary, "exp2_rq3_cleaning.json")
    runlog.finish_run(run, note="D-41/DV-11 RQ3 on the Experiment 2 cohort: ICA against EOG "
                                "regression, rows and folds fixed. Not the confirmatory version.")

    print(f"\n  rows {len(base)}  learners {summary['n_learners']}")
    print(f"  ranking stable: {summary['ranking_stable']}")
    for variant in VARIANTS:
        m = results[variant]["metrics"]
        print(f"  {variant:15s} " + "  ".join(
            f"{k} {m[k]['spearman']:+.3f}" for k in ("eye", "ecg", "eeg", "eye_ecg",
                                                     "all_sensors", "selected_single")))


if __name__ == "__main__":
    main()
