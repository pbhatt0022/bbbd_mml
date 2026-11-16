"""RQ4 Task C, eye only: do learned features beat hand-crafted ones? (D-43 / DV-13)

For each outer fold the eye encoder is pretrained from scratch on the
attend-versus-distract objective using **training-fold learners only**, then
frozen. Its 64-dimensional pooled embedding for each attentive cohort
recording goes into ridge against `quiz_z`, on the frozen R-016 rows and
folds. The hand-crafted eight-feature ridge is rerun on the same single
repeat so the two are paired.

Pretraining on all learners would shape the representation on test learners'
signals even without their quiz scores, so the encoder is refit per fold as
the methods plan requires.

**Tasks A and B are not attempted and RQ4 is not executed as specified.**

    python -m bbbd.exp2_rq4_taskc <experiment2.zip>
"""
import argparse
import zipfile
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.linear_model import Ridge
from sklearn.model_selection import GridSearchCV, GroupKFold
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

from . import cv, runlog, stats
from .config import REPO_ROOT, load_config
from .exp2_attention_cnn import (EYE_FEATURES, R019, SEEDS, VAL_FRACTION,
                                 fit_fold, load_windows, make_model)

COHORT = REPO_ROOT / "results/R-016_exp2_common_cohort"
EMBED_DIM = 64
ATTENTIVE = "ses-01"


def embed(torch, model, x, batch=512):
    """Pooled 64-d features: the encoder with its classifier head removed."""
    trunk = torch.nn.Sequential(*list(model.children())[:-2])   # drop Dropout+Linear
    trunk.eval()
    out = []
    with torch.no_grad():
        for start in range(0, len(x), batch):
            out.append(trunk(torch.from_numpy(x[start:start + batch])).numpy())
    return np.concatenate(out) if out else np.empty((0, EMBED_DIM), dtype=np.float32)


def ridge_cv(x, y, groups, labels, cfg):
    """Held-out predictions from grouped ridge with inner grouped tuning (D-31)."""
    options = cfg["reconciliation"]
    alphas = np.logspace(options["ridge_alpha_log10_min"], options["ridge_alpha_log10_max"],
                         options["ridge_alpha_count"])
    predicted = np.full(len(y), np.nan)
    for fold in sorted(set(labels)):
        train, test = labels != fold, labels == fold
        search = GridSearchCV(make_pipeline(StandardScaler(), Ridge()),
                              {"ridge__alpha": alphas},
                              scoring=options["inner_scoring"],
                              cv=GroupKFold(cfg["cv"]["inner_splits"]), error_score="raise")
        search.fit(x[train], y[train], groups=groups[train])
        predicted[test] = search.predict(x[test])
    return predicted


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("archive")
    args = parser.parse_args()
    import torch
    torch.set_num_threads(max(1, torch.get_num_threads() // 2))

    cfg = load_config()
    cohort = pd.read_csv(COHORT / "exp2_common_cohort.csv")
    keys, schemes = cv.load_folds(COHORT / "folds_exp2.json")
    scheme_name = sorted(schemes)[0]
    fold_of_row = np.asarray(schemes[scheme_name])
    print(f"[taskc] using the single repeat {scheme_name}", flush=True)

    r019 = pd.read_csv(R019)
    excluded = {(r.subject, r.session, int(r.video))
                for r in r019[r019.excluded].itertuples()}
    with zipfile.ZipFile(args.archive) as archive:
        x, y_cond, subject, recording_id, win_keys = load_windows(archive, cfg, excluded)
    print(f"[taskc] {len(x)} windows over {len(win_keys)} recordings", flush=True)

    # Map each cohort row to its attentive recording's windows.
    win_keys = win_keys.assign(recording=np.arange(len(win_keys)))
    win_keys["sub_int"] = win_keys.subject.str.replace("sub-", "").astype(int)
    attentive = win_keys[win_keys.session == ATTENTIVE]
    lookup = {(r.sub_int, r.video): r.recording for r in attentive.itertuples()}
    cohort_recording = np.array([lookup[(int(s), int(v))]
                                 for s, v in zip(cohort.subject, cohort.video)])

    y = cohort.quiz_z.to_numpy(float)
    groups = cohort.subject.to_numpy()

    deep_predictions = []
    for seed in SEEDS:
        per_fold = {}
        for fold in sorted(set(fold_of_row)):
            test_learners = set(groups[fold_of_row == fold])
            # Pretrain on windows from training-fold learners only, both sessions.
            in_test = np.isin(subject, list(test_learners))
            pool = np.flatnonzero(~in_test)
            learners = np.unique(subject[pool])
            rng = np.random.default_rng(seed)
            val_learners = set(rng.choice(
                learners, max(1, int(round(VAL_FRACTION * len(learners)))), replace=False))
            is_val = np.isin(subject[pool], list(val_learners))
            model = fit_fold(torch, x[pool[~is_val]], y_cond[pool[~is_val]],
                             x[pool[is_val]], y_cond[pool[is_val]], seed)
            # Embed every cohort recording with this fold's encoder, then pool.
            frame = pd.DataFrame(embed(torch, model, x))
            frame["recording"] = recording_id
            pooled = frame.groupby("recording").mean()
            embeddings = pooled.loc[cohort_recording].to_numpy(dtype=np.float32)
            # Only this fold's test rows take predictions from this fold's encoder.
            per_fold[fold] = (embeddings, fold_of_row == fold)
            print(f"[taskc] seed {seed} fold {fold} encoder done", flush=True)

        predicted = np.full(len(y), np.nan)
        options = cfg["reconciliation"]
        alphas = np.logspace(options["ridge_alpha_log10_min"],
                             options["ridge_alpha_log10_max"],
                             options["ridge_alpha_count"])
        for fold, (emb, fold_rows) in per_fold.items():
            train = ~fold_rows
            search = GridSearchCV(make_pipeline(StandardScaler(), Ridge()),
                                  {"ridge__alpha": alphas},
                                  scoring=options["inner_scoring"],
                                  cv=GroupKFold(cfg["cv"]["inner_splits"]),
                                  error_score="raise")
            search.fit(emb[train], y[train], groups=groups[train])
            predicted[fold_rows] = search.predict(emb[fold_rows])
        deep_predictions.append(predicted)
        print(f"[taskc] seed {seed}: deep rho "
              f"{cv.score(y, predicted)['spearman']:+.3f}", flush=True)

    deep = np.mean(deep_predictions, axis=0)
    hand = ridge_cv(cohort[EYE_FEATURES].to_numpy(float), y, groups, fold_of_row, cfg)

    contrast = stats.paired_difference(groups, y, deep, hand,
                                       n_boot=cfg["stats"]["n_bootstrap"],
                                       seed=cfg["seeds"]["global"], ci=0.95)
    contrast.pop("boot")

    run = runlog.start_run(cfg, "exp2_rq4_taskc", "exp2_rq4_taskc", member="A")
    runlog.save_table(run, keys.assign(quiz_z=y, pred_deep=deep, pred_handcrafted=hand),
                      "oof_predictions.csv")
    summary = dict(
        task="RQ4 Task C, eye only: deep encoder embeddings into ridge against quiz score",
        rq4_executed_as_specified=False, tasks_a_and_b_attempted=False,
        decision="D-43 Proposed", deviation="DV-13",
        cohort_run="R-016", repeat=scheme_name, n_repeats=1, seeds=list(SEEDS),
        embedding_dim=EMBED_DIM, n_rows=len(y), n_learners=int(len(set(groups))),
        encoder="R-023 eye CNN, pretrained per outer fold on training learners only",
        deep=cv.score(y, deep), handcrafted=cv.score(y, hand),
        deep_minus_handcrafted=contrast,
        deep_beats_handcrafted=bool(cv.score(y, deep)["spearman"]
                                    > cv.score(y, hand)["spearman"]))
    runlog.save_json(run, summary, "exp2_rq4_taskc.json")
    runlog.finish_run(run, note="D-43/DV-13 RQ4 Task C eye-only; Tasks A and B not "
                                "attempted and RQ4 not executed as specified.")
    print(f"\n  deep embeddings   rho {summary['deep']['spearman']:+.3f}")
    print(f"  hand-crafted      rho {summary['handcrafted']['spearman']:+.3f}")
    print(f"  difference        {contrast['estimate']:+.3f} "
          f"95% CI [{contrast['ci_low']:+.3f}, {contrast['ci_high']:+.3f}]")


if __name__ == "__main__":
    main()
