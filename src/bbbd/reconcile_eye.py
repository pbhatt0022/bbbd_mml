"""D-31 / DV-02: separately registered correction of R-012.

Run with python -m bbbd.reconcile_eye. No raw data or Drive is required.
Every permutation refits the complete nested ten-repeat pipeline.
"""
from __future__ import annotations

import argparse
import hashlib
import importlib.metadata
import json
import time
from pathlib import Path

import numpy as np
import pandas as pd
from joblib import Parallel, delayed
from sklearn.linear_model import Ridge
from sklearn.model_selection import GridSearchCV, GroupKFold
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler
from threadpoolctl import threadpool_limits

from . import cv, runlog, stats
from .config import REPO_ROOT, config_hash, load_config


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def load_inputs(cfg):
    """Pin source runs and reject changed folds, ambiguous joins or missing data."""
    settings = cfg["reconciliation"]
    paths = {k: REPO_ROOT / settings[k] for k in
             ("targets", "features", "original_summary", "folds", "archived_folds")}
    hashes = {k: digest(p) for k, p in paths.items()}
    if hashes["folds"] != hashes["archived_folds"]:
        raise ValueError("Canonical folds differ from R-011; do not rebuild them")
    original = json.loads(paths["original_summary"].read_text())
    if original["run_id"] != "R-012":
        raise ValueError("Expected the preserved R-012 summary")
    keys, schemes = cv.load_folds(paths["folds"])
    targets = pd.read_csv(paths["targets"], dtype={"subject": str})
    features = pd.read_csv(paths["features"], dtype={"subject": str})
    for table in (keys, targets, features):
        table["subject"] = table.subject.astype(str).str.replace("sub-", "", regex=False).str.zfill(2)
        table["video"] = pd.to_numeric(table.video, errors="raise").astype(int)
        if table.duplicated(["subject", "video"]).any():
            raise ValueError("Duplicate subject/video keys")
    if set(targets.run_id) != {"R-006"} or set(features.run_id) != {"R-010"}:
        raise ValueError("Input tables must come from R-006 and R-010")
    if set(keys.experiment.astype(str)) != {"1"}:
        raise ValueError("Only Experiment 1 is supported")
    if set(features.experiment.astype(str)) != {"1"} or set(features.variant) != {"V1"}:
        raise ValueError("Unexpected feature experiment or variant")
    if set(pd.to_numeric(features.session)) != {1}:
        raise ValueError("Expected the D-29 attend session only")
    names = original["features"]
    df = keys.merge(targets[["subject", "video", "quiz_z"]],
                    on=["subject", "video"], how="left", validate="one_to_one")
    df = df.merge(features[["subject", "video", "excluded", *names]],
                  on=["subject", "video"], how="left", validate="one_to_one")
    if len(df) != 120 or df.subject.nunique() != 25 or len(names) != 8:
        raise ValueError("Expected R-012's 120 rows, 25 learners and eight features")
    if df.excluded.isna().any() or not df.excluded.eq(False).all():
        raise ValueError("Missing or excluded feature rows in frozen folds")
    if not np.isfinite(df[["quiz_z", *names]].to_numpy(float)).all():
        raise ValueError("Non-finite target/features; no silent imputation")
    expected = [f"group{cfg['cv']['n_splits']}_seed{s}" for s in cfg["seeds"]["cv_repeats"]]
    if set(schemes) != {*expected, "lovo"}:
        raise ValueError("Unexpected frozen fold schemes")
    outer = {name: schemes[name] for name in expected}
    for labels in outer.values():
        if len(labels) != len(df) or len(np.unique(labels)) != cfg["cv"]["n_splits"]:
            raise ValueError("Malformed outer folds")
        cv.check_no_leakage(labels, df.subject)
    return df, names, outer, hashes


def nested_predictions(X, y, subjects, schemes, alphas, inner_splits=3,
                       scoring="neg_mean_squared_error"):
    """Same nested fit for observed and shuffled targets; no inner learner overlap."""
    X, y, subjects = np.asarray(X), np.asarray(y), np.asarray(subjects)
    predictions, baselines, chosen = [], [], []
    with threadpool_limits(limits=1):
        for scheme, folds in schemes.items():
            pred, base = np.full(len(y), np.nan), np.full(len(y), np.nan)
            cv.check_no_leakage(folds, subjects)
            for fold in np.unique(folds):
                train, test = np.where(folds != fold)[0], np.where(folds == fold)[0]
                search = GridSearchCV(
                    make_pipeline(StandardScaler(), Ridge()),
                    {"ridge__alpha": alphas},
                    cv=GroupKFold(n_splits=inner_splits), scoring=scoring,
                    n_jobs=1, error_score="raise", refit=True,
                )
                search.fit(X[train], y[train], groups=subjects[train])
                pred[test] = search.predict(X[test])
                base[test] = y[train].mean()
                chosen.append({"scheme": scheme, "fold": int(fold),
                               "alpha": float(search.best_params_["ridge__alpha"])})
            predictions.append(pred)
            baselines.append(base)
    return np.asarray(predictions), np.asarray(baselines), chosen


def fit_score(X, y, subjects, schemes, alphas, inner_splits, scoring):
    pred, _, _ = nested_predictions(X, y, subjects, schemes, alphas, inner_splits, scoring)
    return stats.spearman(y, pred.mean(axis=0))


def training_mean_skill(y, pred, baseline):
    denominator = np.sum((y - baseline) ** 2)
    if denominator <= 0:
        raise ValueError("Training-mean baseline has zero error")
    return float(1 - np.sum((y - pred) ** 2) / denominator)


def permutation_targets(y, videos, seed, completed, count):
    """Resume the identical RNG stream, regardless of worker/checkpoint count."""
    rng = np.random.default_rng(seed)
    for _ in range(completed):
        stats.shuffle_within(y, videos, rng)
    for _ in range(count):
        yield stats.shuffle_within(y, videos, rng)


def execute(resume=None):
    cfg = load_config()
    settings = cfg["reconciliation"]
    df, names, schemes, hashes = load_inputs(cfg)
    seed = cfg["seeds"]["global"]
    X, y, groups = df[names].to_numpy(float), df.quiz_z.to_numpy(float), df.subject.to_numpy()
    alphas = np.logspace(settings["ridge_alpha_log10_min"], settings["ridge_alpha_log10_max"],
                        settings["ridge_alpha_count"])
    fit_args = (groups, schemes, alphas, cfg["cv"]["inner_splits"], settings["inner_scoring"])
    versions = {p: importlib.metadata.version(p) for p in
                ("numpy", "scipy", "pandas", "scikit-learn", "joblib")}
    source_hashes = {p.name: digest(p) for p in Path(__file__).parent.glob("*.py")}
    n_perm = cfg["stats"]["n_permutations"]
    if resume:
        out = Path(resume).resolve()
        if out.parent != (REPO_ROOT / "results").resolve():
            raise ValueError("Resume must name a run directory in this checkout's results")
        meta = json.loads((out / "run_meta.json").read_text())
        progress = json.loads((out / "progress.json").read_text())
        if (meta["git_hash"] != runlog.git_info()[0] or meta["config_hash"] != config_hash(cfg)
                or progress["input_hashes"] != hashes or progress["versions"] != versions
                or progress["source_hashes"] != source_hashes):
            raise ValueError("Code, configuration, inputs or package versions changed; cannot resume")
        if progress["status"] == "complete":
            print(f"Already complete: {out}", flush=True)
            return out
        run = runlog.Run(meta["run_id"], meta["name"], meta["notebook"], meta["member"],
                         meta["seed"], cfg, out, meta["started_utc"], meta["git_hash"], meta["git_dirty"])
        null = list(progress["null"])
        if len(null) > n_perm or not np.isfinite(null).all():
            raise ValueError("Invalid checkpoint permutation scores")
    else:
        if runlog.git_info()[1]:
            raise ValueError("Start from a clean committed checkout so provenance is reproducible")
        run = runlog.start_run(cfg, name="eye_reconciliation", notebook="85_statistics",
                               member="A", seed=seed)
        null = []
    # Register at start to reserve the ID; the registry explicitly says incomplete.
    runlog.finish_run(run, note="D-31/DV-02 post-result correction IN PROGRESS; not reportable")

    def checkpoint(status):
        runlog.save_json(run, {"status": status, "input_hashes": hashes, "versions": versions,
                              "source_hashes": source_hashes,
                              "completed_permutations": len(null), "null": null}, "progress.tmp.json")
        (run.output_dir / "progress.tmp.json").replace(run.output_dir / "progress.json")

    checkpoint("in_progress")
    print(f"{run.run_id}: fitting observed nested CV; {len(null)}/{n_perm} permutations saved", flush=True)
    P, B, chosen = nested_predictions(X, y, *fit_args)
    prediction, baseline = P.mean(axis=0), B.mean(axis=0)
    observed = stats.spearman(y, prediction)
    runlog.save_table(run, df[["subject", "video", "quiz_z"]].assign(
        pred_ridge=prediction, pred_training_mean=baseline,
        **{f"pred_{name}": P[i] for i, name in enumerate(schemes)}), "oof_predictions.csv")
    runlog.save_table(run, pd.DataFrame(chosen), "selected_alphas.csv")
    start, initial = time.monotonic(), len(null)
    targets = permutation_targets(y, df.video.to_numpy(), seed, len(null), n_perm - len(null))
    while len(null) < n_perm:
        batch = [next(targets) for _ in range(min(settings["checkpoint_every"], n_perm - len(null)))]
        scores = Parallel(n_jobs=settings["permutation_workers"])(
            delayed(fit_score)(X, shuffled, *fit_args) for shuffled in batch)
        if not np.isfinite(scores).all():
            raise ValueError("Non-finite permutation score; do not silently discard")
        null.extend(scores)
        checkpoint("in_progress")
        elapsed = time.monotonic() - start
        eta = elapsed / (len(null) - initial) * (n_perm - len(null)) / 60
        print(f"{run.run_id}: {len(null)}/{n_perm} permutations saved; ETA {eta:.0f} min", flush=True)

    boot = stats.bootstrap_learners(stats.spearman, groups, y, prediction,
                                    n_boot=cfg["stats"]["n_bootstrap"], seed=seed)
    p = float((1 + np.sum(np.asarray(null) >= observed)) / (1 + n_perm))
    result = {
        "status": "complete", "analysis_status": "post_result_correction_DV-02",
        "decision": "D-31 Proposed; joint agreement outstanding", "original_run": "R-012",
        "confirmatory": False, "input_hashes": hashes, "versions": versions,
        "features": names, "n_learners": int(df.subject.nunique()),
        "scheme": "frozen learner-grouped 5-fold x10; averaged predictions",
        "inner_cv": "3-fold GroupKFold; scaling within inner fold; mean MSE tuning",
        "metrics": cv.score(y, prediction),
        "r2_definition": "conventional R2 against evaluated-target mean",
        "training_mean_skill": training_mean_skill(y, prediction, baseline),
        "training_mean_skill_definition": "1-SSE(model)/SSE(averaged outer-training-mean predictions)",
        "ci_low": boot["ci_low"], "ci_high": boot["ci_high"],
        "p_permutation_raw": p, "n_permutations": n_perm,
        "n_bootstrap": cfg["stats"]["n_bootstrap"],
        "per_repeat_rho": [stats.spearman(y, row) for row in P],
        "multiplicity": "pending across eye/cardiac/EEG; raw eye p is not a family-corrected claim",
    }
    runlog.save_table(run, pd.DataFrame({"permutation": np.arange(1, n_perm + 1),
                                       "spearman": null}), "permutation_null.csv")
    runlog.save_json(run, result, "eye_reconciliation.json")
    runlog.save_table(run, pd.DataFrame({"spearman": boot["boot"]}), "learner_bootstrap.csv")
    checkpoint("complete")
    runlog.finish_run(run, note="D-31/DV-02 post-result correction COMPLETE; Holm pending; original R-012 preserved")
    print(f"\n{run.run_id}: rho={observed:+.3f}, 95% CI [{boot['ci_low']:+.3f}, "
          f"{boot['ci_high']:+.3f}], raw p={p:.4f}. Across-modality inference pending.", flush=True)
    print(f"Saved: {run.output_dir}", flush=True)
    return run.output_dir


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--resume", help="Existing incomplete run directory; same code/config/environment")
    args = parser.parse_args()
    execute(args.resume)
