"""D-35/DV-06 exploratory matched Experiment 2 ridge comparisons."""
import hashlib
from collections import Counter

import numpy as np
import pandas as pd
from sklearn.linear_model import Ridge
from sklearn.model_selection import GridSearchCV, GroupKFold
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler
from threadpoolctl import threadpool_limits

from . import cv, runlog, stats
from .config import REPO_ROOT, load_config

SINGLE = ("eye", "ecg", "eeg")
EYE = ["eye_invalid_frac", "saccade_rate_min", "blink_rate_min", "fixation_rate_min",
       "fixation_dur_ms_mean", "pupil_mean_raw", "pupil_diff_sd_z", "gaze_dispersion_deg"]


def fit_outer(data, y, groups, splits, alphas, scoring):
    """Fit and select exclusively on the outer training rows."""
    train, test, inner = splits
    predictions, scores, penalties = {}, {}, {}
    for name, x in data.items():
        search = GridSearchCV(make_pipeline(StandardScaler(), Ridge()), {"ridge__alpha": alphas},
                              scoring=scoring, cv=inner, error_score="raise")
        search.fit(x[train], y[train], groups=groups[train])
        predictions[name] = search.predict(x[test])
        scores[name] = search.best_score_
        penalties[name] = float(search.best_params_["ridge__alpha"])
    best = max(SINGLE, key=scores.__getitem__)
    predictions["selected_single"] = predictions[best]
    return predictions, best, scores, penalties


def main():
    cfg = load_config()
    folder = REPO_ROOT / "results/R-016_exp2_common_cohort"
    table_path, fold_path = folder / "exp2_common_cohort.csv", folder / "folds_exp2.json"
    table = pd.read_csv(table_path, dtype={"subject": str, "video": str, "experiment": str})
    keys, schemes = cv.load_folds(fold_path)
    if not table[keys.columns].equals(keys) or not table.run_id.eq("R-016").all() or not keys.experiment.eq("2").all():
        raise ValueError("R-016 rows do not match the frozen Experiment 2 folds")
    eeg = [c for c in table if c.startswith("eeg_")]
    ecg = ["hr_mean", "hr_sd", "rmssd"]
    if len(eeg) != 24 or keys.duplicated().any():
        raise ValueError("Unexpected R-016 feature schema or duplicate keys")
    columns = dict(eye=EYE, ecg=ecg, eeg=eeg, eye_ecg=EYE+ecg, all_sensors=EYE+ecg+eeg)
    data = {name: table[cols].to_numpy(float) for name, cols in columns.items()}
    y, groups = table.quiz_z.to_numpy(float), keys.subject.to_numpy()
    if not all(np.isfinite(a).all() for a in [y, *data.values()]):
        raise ValueError("Non-finite inputs")
    options = cfg["reconciliation"]
    alphas = np.logspace(options["ridge_alpha_log10_min"], options["ridge_alpha_log10_max"],
                        options["ridge_alpha_count"])
    expected = {f"group{cfg['cv']['n_splits']}_seed{s}" for s in cfg["seeds"]["cv_repeats"]}
    if set(schemes) != expected:
        raise ValueError("Unexpected repeat schemes")
    names = [*data, "selected_single"]
    repeats = {name: [] for name in names}
    audits = []
    with threadpool_limits(limits=1):
        for scheme, labels in schemes.items():
            cv.check_no_leakage(labels, groups)
            if len(labels) != len(table) or len(set(labels)) != cfg["cv"]["n_splits"]:
                raise ValueError("Unexpected fold assignments")
            batch = {name: np.full(len(y), np.nan) for name in names}
            for fold in sorted(set(labels)):
                train, test = np.flatnonzero(labels != fold), np.flatnonzero(labels == fold)
                pred, best, scores, penalties = fit_outer(
                    data, y, groups, (train, test, GroupKFold(cfg["cv"]["inner_splits"])),
                    alphas, options["inner_scoring"])
                for name in names:
                    batch[name][test] = pred[name]
                audits.append(dict(scheme=scheme, fold=int(fold), selected_single=best,
                                   **{f"inner_mse_{k}": -v for k,v in scores.items()},
                                   **{f"alpha_{k}": v for k,v in penalties.items()}))
            for name in names:
                repeats[name].append(batch[name])
    prediction = {k: np.mean(v, axis=0) for k,v in repeats.items()}
    n_boot, seed = cfg["stats"]["n_bootstrap"], cfg["seeds"]["global"]
    comparisons = {}
    for a,b,level in (("eeg","eye",.90), ("eeg","eye_ecg",.90),
                      ("all_sensors","selected_single",.95)):
        result = stats.paired_difference(groups, y, prediction[a], prediction[b],
                                        n_boot=n_boot, seed=seed, ci=level)
        result.pop("boot")
        result["ci_level"] = level
        if level == .90:
            margin = cfg["stats"]["equivalence_margin_rho"]
            result.update(equivalence_margin=margin,
                          interval_within_margin=bool(-margin < result["ci_low"] and result["ci_high"] < margin))
        comparisons[f"{a}_minus_{b}"] = result
    run = runlog.start_run(cfg, "exp2_matched_ridge", "exp2_matched_ridge", member="A")
    runlog.save_table(run, keys.assign(quiz_z=y, **{f"pred_{k}":v for k,v in prediction.items()}), "oof_predictions.csv")
    runlog.save_table(run, pd.DataFrame(audits), "outer_fold_tuning.csv")
    summary = dict(cohort_run="R-016", decision="D-35 Proposed", deviation="DV-06",
                   exploratory=True, n_rows=len(y), n_learners=len(set(groups)),
                   metrics={k:cv.score(y,v) for k,v in prediction.items()},
                   comparisons=comparisons, n_bootstrap=n_boot,
                   selected_single_counts=dict(Counter(row["selected_single"] for row in audits)),
                   input_sha256={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in (table_path,fold_path)})
    runlog.save_json(run, summary, "exp2_matched_ridge.json")
    runlog.finish_run(run, note="D-35/DV-06 exploratory matched Experiment 2 sensor and early fusion comparison.")
    print(run.output_dir)


if __name__ == "__main__":
    main()
