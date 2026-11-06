"""Inter-subject correlation (ISC), fold-safe.

ISC measures how closely one learner's signal time course follows the group watching the
same video (Madsen et al. 2021 for gaze/pupil; Perez et al. 2021 for heart rate; Cohen et al.
2018 for EEG via correlated components analysis, CorrCA; Parra et al. 2019 for the method).

Leakage rule (D-11): the reference group is ALWAYS training-fold learners only.
- A test learner is correlated with the mean of all training learners.
- A training learner is correlated with the mean of the OTHER training learners
  (leave-one-out), so it is never correlated with itself.

Signals for one video must be on a common time base (aligned to video start, same length).
"""
from __future__ import annotations

import numpy as np
from scipy.linalg import eigh


def _corr(a: np.ndarray, b: np.ndarray) -> float:
    ok = ~(np.isnan(a) | np.isnan(b))
    if ok.sum() < 3:
        return np.nan
    a, b = a[ok] - a[ok].mean(), b[ok] - b[ok].mean()
    den = np.sqrt((a @ a) * (b @ b))
    return float(a @ b / den) if den > 0 else np.nan


def isc_1d(signals: np.ndarray, train_mask: np.ndarray) -> np.ndarray:
    """ISC for a 1-D signal (pupil, HR, gaze x, ...), one video.

    signals: (n_subjects, n_times), NaN allowed for missing samples.
    train_mask: bool (n_subjects,), True for training-fold learners.
    Returns ISC per subject (n_subjects,).
    """
    signals = np.asarray(signals, float)
    train_mask = np.asarray(train_mask, bool)
    if train_mask.sum() < 2:
        raise ValueError("Need at least 2 training learners for a reference.")
    tr = signals[train_mask]
    n_tr = (~np.isnan(tr)).sum(0)
    sum_tr = np.nansum(tr, 0)
    out = np.empty(len(signals))
    for i, s in enumerate(signals):
        if train_mask[i]:
            # leave this learner out of its own reference
            own = np.nan_to_num(s)
            cnt = n_tr - (~np.isnan(s)).astype(int)
            with np.errstate(invalid="ignore", divide="ignore"):
                ref = np.where(cnt > 0, (sum_tr - own) / cnt, np.nan)
        else:
            with np.errstate(invalid="ignore", divide="ignore"):
                ref = np.where(n_tr > 0, sum_tr / n_tr, np.nan)
        out[i] = _corr(s, ref)
    return out


class CorrCA:
    """Correlated components analysis (Parra et al. 2019), fitted on training learners only.

    Finds spatial filters W maximising between-subject over within-subject covariance:
    Rb w = lambda Rw w. Shrinkage regularises Rw (EEG covariances are near-singular after
    channel interpolation and average referencing).

    data: (n_subjects, n_times, n_channels) for ONE video.
    """

    def __init__(self, n_components: int = 3, shrinkage: float = 0.1):
        self.n_components = n_components
        self.shrinkage = shrinkage

    def fit(self, data: np.ndarray) -> "CorrCA":
        X = np.asarray(data, float)
        X = X - np.nanmean(X, axis=1, keepdims=True)
        X = np.nan_to_num(X)
        n, _, d = X.shape
        Rw = sum(x.T @ x for x in X)
        Rt = (X.sum(0)).T @ X.sum(0)          # total = within + between
        Rb = (Rt - Rw) / (n - 1)
        Rw = Rw / n
        Rw_reg = (1 - self.shrinkage) * Rw + self.shrinkage * np.trace(Rw) / d * np.eye(d)
        evals, evecs = eigh(Rb, Rw_reg)
        order = np.argsort(evals)[::-1]
        self.eigenvalues_ = evals[order]
        self.W_ = evecs[:, order[: self.n_components]]
        return self

    def transform(self, data: np.ndarray) -> np.ndarray:
        """(n_subjects, n_times, n_channels) -> (n_subjects, n_times, n_components)."""
        return np.nan_to_num(np.asarray(data, float)) @ self.W_


def corrca_isc(data: np.ndarray, train_mask: np.ndarray, n_components: int = 3,
               shrinkage: float = 0.1) -> np.ndarray:
    """EEG ISC per subject and component, with CorrCA weights fitted on training learners.

    Returns (n_subjects, n_components). Sum over components for a single EEG-ISC score.
    """
    train_mask = np.asarray(train_mask, bool)
    cca = CorrCA(n_components, shrinkage).fit(data[train_mask])
    Y = cca.transform(data)                    # (subjects, times, comps)
    return np.stack([isc_1d(Y[:, :, c], train_mask) for c in range(n_components)], axis=1)
