"""Cross-validation harness shared by every model (classical and deep).

Rules enforced here:
- Folds are grouped by learner: no learner is in both train and test (D-09).
- Fold assignments are made once, saved to results/folds.json, and reused by every model,
  so comparisons between modalities and models are paired.
- Anything learned from data (scaling, ISC reference, CorrCA weights, hyperparameters)
  is fitted on the training fold only. Fold-dependent features go through `feature_fn`.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Callable

import numpy as np
import pandas as pd
from scipy.stats import spearmanr
from sklearn.base import clone
from sklearn.linear_model import RidgeCV
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler


def make_group_folds(groups, n_splits: int = 5, seed: int = 0) -> np.ndarray:
    """Assign each row to a fold so that all rows of a group (learner) share one fold.

    Groups are shuffled with `seed`, then dealt to the fold with the fewest rows so far,
    which keeps fold sizes balanced when learners have different numbers of videos.
    Returns an int array of fold labels, one per row.
    """
    groups = np.asarray(groups)
    uniq, counts = np.unique(groups, return_counts=True)
    rng = np.random.default_rng(seed)
    order = rng.permutation(len(uniq))
    fold_of_group, fold_rows = {}, np.zeros(n_splits, dtype=int)
    for i in order:
        f = int(np.argmin(fold_rows))
        fold_of_group[uniq[i]] = f
        fold_rows[f] += counts[i]
    return np.array([fold_of_group[g] for g in groups])


def leave_one_out_folds(values) -> np.ndarray:
    """Fold label = index of the value, e.g. leave-one-video-out when values = video IDs."""
    values = np.asarray(values)
    uniq = {v: i for i, v in enumerate(pd.unique(values))}
    return np.array([uniq[v] for v in values])


def save_folds(path: str | Path, keys: pd.DataFrame, folds: dict[str, np.ndarray]) -> None:
    """Save fold schemes. `keys` has the row identifiers (experiment, subject, video).

    folds: e.g. {"group5_seed11": arr, "group5_seed22": arr, "lovo": arr}
    """
    out = {"keys": keys.astype(str).to_dict(orient="list"),
           "schemes": {k: np.asarray(v).tolist() for k, v in folds.items()}}
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(out, f)


def load_folds(path: str | Path) -> tuple[pd.DataFrame, dict[str, np.ndarray]]:
    with open(path, encoding="utf-8") as f:
        d = json.load(f)
    return pd.DataFrame(d["keys"]), {k: np.array(v) for k, v in d["schemes"].items()}


def check_no_leakage(folds: np.ndarray, groups) -> None:
    """Raise if any group appears in more than one fold."""
    df = pd.DataFrame({"fold": folds, "group": np.asarray(groups)})
    bad = df.groupby("group")["fold"].nunique()
    bad = bad[bad > 1]
    if len(bad):
        raise ValueError(f"Leakage: {len(bad)} learners appear in several folds, e.g. {list(bad.index[:5])}")


def default_model():
    """Primary confirmatory model: standardise, then ridge with alpha tuned by internal CV."""
    return make_pipeline(StandardScaler(), RidgeCV(alphas=np.logspace(-3, 4, 30)))


def cross_val_predict_grouped(
    X: np.ndarray | None,
    y: np.ndarray,
    folds: np.ndarray,
    model=None,
    feature_fn: Callable[[np.ndarray, np.ndarray], tuple[np.ndarray, np.ndarray]] | None = None,
) -> np.ndarray:
    """Out-of-fold predictions.

    Either pass X directly (fold-independent features), or pass `feature_fn(train_idx, test_idx)`
    returning (X_train, X_test) for features that must be computed per fold (ISC, CorrCA, DL
    embeddings). The model is cloned and refitted in every fold.
    """
    if (X is None) == (feature_fn is None):
        raise ValueError("Pass exactly one of X or feature_fn.")
    model = default_model() if model is None else model
    y = np.asarray(y, dtype=float)
    pred = np.full_like(y, np.nan)
    for f in np.unique(folds):
        te = np.where(folds == f)[0]
        tr = np.where(folds != f)[0]
        if feature_fn is None:
            Xtr, Xte = X[tr], X[te]
        else:
            Xtr, Xte = feature_fn(tr, te)
        keep = ~np.isnan(y[tr])
        # Clone the scaler and estimator together so fitted state cannot carry across folds.
        m = clone(model).fit(Xtr[keep], y[tr][keep])
        pred[te] = m.predict(Xte)
    return pred


def score(y, pred) -> dict:
    """Primary and secondary metrics (D-15). R2 is against predicting the mean of y."""
    y, pred = np.asarray(y, float), np.asarray(pred, float)
    ok = ~(np.isnan(y) | np.isnan(pred))
    y, pred = y[ok], pred[ok]
    rho = spearmanr(y, pred).statistic
    ss_res = np.sum((y - pred) ** 2)
    # This denominator uses the evaluated-target mean (conventional R²).
    ss_tot = np.sum((y - y.mean()) ** 2)
    return {"spearman": float(rho), "r2": float(1 - ss_res / ss_tot),
            "mae": float(np.mean(np.abs(y - pred))), "n": int(ok.sum())}
