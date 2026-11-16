"""Eye-only attend-versus-distract decoding, learners held out (D-42 / DV-12).

This is the methods plan's `Aux` task and the Task A objective. It is **not
RQ4**: no quiz score is used anywhere, so nothing here bears on RQ1, RQ2 or
RQ4. Whether it satisfies the course's deep-learning requirement is a
decision for the team, not for this run.

Everything below was fixed in D-42 before any fitting: 4-second windows at
50% overlap (D-21), five folds grouped by learner with both sessions of a
learner in the same fold, early-stopping learners drawn from inside the
training fold, AdamW with lr 1e-3 and weight decay 1e-2, batch 256, three
seeds (methods plan §6b), recording-level balanced accuracy as the primary
metric, and a mandatory hand-crafted baseline on the same folds.

    python -m bbbd.exp2_attention_cnn <experiment2.zip>
"""
import argparse
import re
import zipfile
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import balanced_accuracy_score
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

from . import cv, runlog
from .config import REPO_ROOT, load_config
from .exp2_eye_condition import GAZE, read_eye

WINDOW_S, OVERLAP = 4.0, 0.5          # D-21
SFREQ = 128.0
N_SPLITS, SEEDS = 5, (0, 1, 2)        # methods plan 6b
LR, WEIGHT_DECAY, BATCH, MAX_EPOCHS, PATIENCE = 1e-3, 1e-2, 256, 40, 6
VAL_FRACTION = 0.2
EYE_FEATURES = ["eye_invalid_frac", "saccade_rate_min", "blink_rate_min",
                "fixation_rate_min", "fixation_dur_ms_mean", "pupil_mean_raw",
                "pupil_diff_sd_z", "gaze_dispersion_deg"]
R019 = REPO_ROOT / "results/R-019_exp2_eye_condition/eye_features_exp2_both_sessions.csv"


def standardize(x):
    """Within-recording z-score, so the model cannot key on a learner's offsets."""
    sd = x.std()
    return (x - x.mean()) / sd if sd > 0 else np.zeros_like(x)


def windows(gaze_x, gaze_y, pupil):
    """(n_windows, 3, n_samples) of within-recording standardized channels."""
    size = int(WINDOW_S * SFREQ)
    step = int(size * (1 - OVERLAP))
    stack = np.stack([standardize(gaze_x), standardize(gaze_y), standardize(pupil)])
    n = (stack.shape[1] - size) // step + 1
    if n <= 0:
        return np.empty((0, 3, size), dtype=np.float32)
    idx = np.arange(size)[None, :] + step * np.arange(n)[:, None]
    out = stack[:, idx].transpose(1, 0, 2)
    return np.ascontiguousarray(out, dtype=np.float32)


def load_windows(archive, cfg, excluded):
    """Windows, labels and keys for every usable Experiment 2 eye recording."""
    screen = cfg["eye"]["screen"]
    from . import eye as eyemod
    scale = screen["px_per_deg"] or eyemod.px_per_deg_from_screen(
        screen["width_px"], screen["width_cm"], screen["distance_cm"])
    chunks, labels, subjects, keys = [], [], [], []
    names = sorted(n for n in archive.namelist() if GAZE.fullmatch(n))
    for i, name in enumerate(names, 1):
        sub, ses, stim = GAZE.fullmatch(name).groups()
        if (f"sub-{sub}", f"ses-{ses}", int(stim)) in excluded:
            continue
        gaze = read_eye(archive, name, ["x", "y", "vdx", "vdy"], ses)
        pupil = read_eye(archive, name.replace("_gaze_visualangle_", "_pupil_"),
                         ["pupil_size"], ses)
        n = min(len(gaze), len(pupil))
        block = windows(gaze.x.to_numpy()[:n] / scale,
                        gaze.y.to_numpy()[:n] / scale,
                        pupil.pupil_size.to_numpy()[:n])
        if not len(block):
            continue
        chunks.append(block)
        labels.append(np.full(len(block), 0 if ses == "01" else 1, dtype=np.int64))
        subjects.append(np.full(len(block), int(sub)))
        keys.append((f"sub-{sub}", f"ses-{ses}", int(stim)))
        if i % 60 == 0:
            print(f"[cnn] read {i}/{len(names)}", flush=True)
    recording_id = np.concatenate([np.full(len(c), k) for k, c in enumerate(chunks)])
    return (np.concatenate(chunks), np.concatenate(labels),
            np.concatenate(subjects), recording_id,
            pd.DataFrame(keys, columns=["subject", "session", "video"]))


def make_model(torch):
    """A small 1D CNN. Deliberately modest: the sample is 31 learners."""
    nn = torch.nn
    return nn.Sequential(
        nn.Conv1d(3, 16, 7, stride=2, padding=3), nn.BatchNorm1d(16), nn.ReLU(),
        nn.Conv1d(16, 32, 5, stride=2, padding=2), nn.BatchNorm1d(32), nn.ReLU(),
        nn.Conv1d(32, 64, 3, stride=2, padding=1), nn.BatchNorm1d(64), nn.ReLU(),
        nn.AdaptiveAvgPool1d(1), nn.Flatten(), nn.Dropout(0.3), nn.Linear(64, 1))


def fit_fold(torch, x_train, y_train, x_val, y_val, seed):
    torch.manual_seed(seed)
    model = make_model(torch)
    opt = torch.optim.AdamW(model.parameters(), lr=LR, weight_decay=WEIGHT_DECAY)
    loss_fn = torch.nn.BCEWithLogitsLoss()
    xt = torch.from_numpy(x_train)
    yt = torch.from_numpy(y_train.astype(np.float32))
    xv = torch.from_numpy(x_val)
    yv = torch.from_numpy(y_val.astype(np.float32))
    best, best_state, waited = np.inf, None, 0
    for _ in range(MAX_EPOCHS):
        model.train()
        order = torch.randperm(len(xt))
        for start in range(0, len(xt), BATCH):
            batch = order[start:start + BATCH]
            opt.zero_grad()
            loss_fn(model(xt[batch]).squeeze(1), yt[batch]).backward()
            opt.step()
        model.eval()
        with torch.no_grad():
            val_loss = float(loss_fn(model(xv).squeeze(1), yv))
        if val_loss < best - 1e-4:
            best, waited = val_loss, 0
            best_state = {k: v.clone() for k, v in model.state_dict().items()}
        else:
            waited += 1
            if waited >= PATIENCE:
                break
    model.load_state_dict(best_state)
    model.eval()
    return model


def recording_scores(probabilities, recording_id, labels):
    """Mean window probability per recording, with that recording's label."""
    frame = pd.DataFrame({"recording": recording_id, "p": probabilities, "y": labels})
    grouped = frame.groupby("recording").agg(p=("p", "mean"), y=("y", "first"))
    return grouped.p.to_numpy(), grouped.y.to_numpy()


def baseline(features, folds, labels_by_recording):
    """Logistic regression on the eight hand-crafted eye features, same folds."""
    x = features[EYE_FEATURES].to_numpy(float)
    y = labels_by_recording
    predicted = np.full(len(y), np.nan)
    for fold in sorted(set(folds)):
        train, test = folds != fold, folds == fold
        model = make_pipeline(StandardScaler(), LogisticRegression(max_iter=1000))
        model.fit(x[train], y[train])
        predicted[test] = model.predict(x[test])
    return float(balanced_accuracy_score(y, predicted))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("archive")
    args = parser.parse_args()
    import torch
    torch.set_num_threads(max(1, torch.get_num_threads() // 2))

    cfg = load_config()
    r019 = pd.read_csv(R019)
    excluded = {(r.subject, r.session, int(r.video))
                for r in r019[r019.excluded].itertuples()}
    print(f"[cnn] {len(excluded)} recordings excluded by the D-32 pupil rule", flush=True)

    with zipfile.ZipFile(args.archive) as archive:
        x, y, subject, recording_id, keys = load_windows(archive, cfg, excluded)
    print(f"[cnn] {len(x)} windows, {len(set(recording_id))} recordings, "
          f"{len(set(subject))} learners", flush=True)

    # One fold label per window, grouped by learner: both sessions travel together.
    fold_of_window = cv.make_group_folds(subject, n_splits=N_SPLITS,
                                         seed=cfg["seeds"]["cv_repeats"][0])
    cv.check_no_leakage(fold_of_window, subject)

    per_seed, oof = [], {}
    for seed in SEEDS:
        probabilities = np.full(len(x), np.nan)
        for fold in sorted(set(fold_of_window)):
            test = fold_of_window == fold
            train_pool = np.flatnonzero(~test)
            learners = np.unique(subject[train_pool])
            rng = np.random.default_rng(seed)
            val_learners = set(rng.choice(
                learners, max(1, int(round(VAL_FRACTION * len(learners)))), replace=False))
            is_val = np.isin(subject[train_pool], list(val_learners))
            train, val = train_pool[~is_val], train_pool[is_val]
            model = fit_fold(torch, x[train], y[train], x[val], y[val], seed)
            with torch.no_grad():
                logits = model(torch.from_numpy(x[test])).squeeze(1)
                probabilities[test] = torch.sigmoid(logits).numpy()
            print(f"[cnn] seed {seed} fold {fold} done", flush=True)
        window_accuracy = balanced_accuracy_score(y, probabilities > 0.5)
        p_rec, y_rec = recording_scores(probabilities, recording_id, y)
        per_seed.append(dict(seed=seed,
                             window_balanced_accuracy=float(window_accuracy),
                             recording_balanced_accuracy=float(
                                 balanced_accuracy_score(y_rec, p_rec > 0.5))))
        oof[seed] = probabilities
        print(f"[cnn] seed {seed}: recording bAcc "
              f"{per_seed[-1]['recording_balanced_accuracy']:.3f}", flush=True)

    mean_probabilities = np.mean([oof[s] for s in SEEDS], axis=0)
    p_rec, y_rec = recording_scores(mean_probabilities, recording_id, y)
    cnn_recording = float(balanced_accuracy_score(y_rec, p_rec > 0.5))

    # Baseline on the same learner folds, at recording level. Features are
    # joined on the recording keys carried through, not on row order.
    order = pd.DataFrame({"recording": recording_id, "subject": subject,
                          "fold": fold_of_window}).groupby("recording").first()
    features = keys.merge(r019[["subject", "session", "video", *EYE_FEATURES]],
                          on=["subject", "session", "video"], how="left",
                          validate="one_to_one")
    if len(features) != len(y_rec) or features[EYE_FEATURES].isna().any().any():
        raise ValueError("Baseline features do not cover every recording")
    baseline_accuracy = baseline(features, order.fold.to_numpy(), y_rec)

    run = runlog.start_run(cfg, "exp2_attention_cnn", "exp2_attention_cnn", member="A")
    runlog.save_table(run, pd.DataFrame(per_seed), "per_seed_scores.csv")
    runlog.save_table(run, pd.DataFrame({"recording": order.index, "subject": order.subject,
                                         "fold": order.fold, "label": y_rec,
                                         "cnn_probability": p_rec}),
                      "recording_predictions.csv")
    summary = dict(
        task="attend vs distract decoding, eye only (methods plan Aux / Task A)",
        is_rq4=False, quiz_scores_used=False,
        decision="D-42 Proposed", deviation="DV-12",
        window_s=WINDOW_S, overlap=OVERLAP, window_decision="D-21",
        n_windows=int(len(x)), n_recordings=int(len(y_rec)),
        n_learners=int(len(set(subject))), n_splits=N_SPLITS, seeds=list(SEEDS),
        grouping="learner; both sessions of a learner in the same fold",
        cnn_recording_balanced_accuracy=cnn_recording,
        cnn_per_seed=per_seed,
        baseline="logistic regression on 8 hand-crafted eye features, same folds",
        baseline_recording_balanced_accuracy=baseline_accuracy,
        cnn_minus_baseline=round(cnn_recording - baseline_accuracy, 4),
        cnn_beats_baseline=bool(cnn_recording > baseline_accuracy))
    runlog.save_json(run, summary, "exp2_attention_cnn.json")
    runlog.finish_run(run, note="D-42/DV-12 eye-only attention decoding (Aux task). "
                                "Not RQ4; no quiz scores used.")
    print(f"\n  CNN recording balanced accuracy  {cnn_recording:.3f}")
    print(f"  hand-crafted baseline            {baseline_accuracy:.3f}")
    print(f"  difference                       {summary['cnn_minus_baseline']:+.3f}")


if __name__ == "__main__":
    main()
