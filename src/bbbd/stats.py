"""Inference: permutation tests, learner bootstrap, equivalence (TOST) and Holm correction.

Preregistration section 4: permutation p-values (1,000 shuffles of the target within video),
95% CIs by resampling learners, equivalence of eye vs EEG if the 90% CI of the difference
lies inside +/- margin, Holm correction within each research question.
"""
from __future__ import annotations

from typing import Callable

import numpy as np
from scipy.stats import spearmanr


def spearman(y, pred) -> float:
    y, pred = np.asarray(y, float), np.asarray(pred, float)
    ok = ~(np.isnan(y) | np.isnan(pred))
    return float(spearmanr(y[ok], pred[ok]).statistic)


def shuffle_within(y, strata, rng) -> np.ndarray:
    """Permute y separately inside each stratum (e.g. video), keeping video difficulty intact."""
    y = np.asarray(y).copy()
    strata = np.asarray(strata)
    for s in np.unique(strata):
        idx = np.where(strata == s)[0]
        y[idx] = y[rng.permutation(idx)]
    return y


def permutation_test(score_fn: Callable[[np.ndarray], float], y, strata,
                     n_perm: int = 1000, seed: int = 0) -> dict:
    """Permutation p-value for a full cross-validated pipeline.

    score_fn(y_used) must rerun the whole CV with the given target and return the score
    (e.g. Spearman of out-of-fold predictions). Refitting on shuffled targets is what makes
    the null honest; shuffling predictions alone would ignore the model fitting.
    p = (1 + #null >= observed) / (1 + n_perm).
    """
    rng = np.random.default_rng(seed)
    observed = score_fn(np.asarray(y))
    null = np.array([score_fn(shuffle_within(y, strata, rng)) for _ in range(n_perm)])
    p = (1 + np.sum(null >= observed)) / (1 + n_perm)
    return {"observed": float(observed), "p": float(p),
            "null_mean": float(np.mean(null)), "null_95": float(np.quantile(null, 0.95))}


def bootstrap_learners(metric: Callable[..., float], subjects, *arrays,
                       n_boot: int = 2000, seed: int = 0, ci: float = 0.95) -> dict:
    """CI of metric(*arrays) by resampling learners with replacement (all their rows together).

    Example: bootstrap_learners(spearman, df.subject, y, pred)
    """
    subjects = np.asarray(subjects)
    arrays = [np.asarray(a) for a in arrays]
    uniq = np.unique(subjects)
    rows_of = {s: np.where(subjects == s)[0] for s in uniq}
    rng = np.random.default_rng(seed)
    est = metric(*arrays)
    boots = np.empty(n_boot)
    for b in range(n_boot):
        idx = np.concatenate([rows_of[s] for s in rng.choice(uniq, size=len(uniq), replace=True)])
        boots[b] = metric(*[a[idx] for a in arrays])
    lo, hi = np.nanquantile(boots, [(1 - ci) / 2, 1 - (1 - ci) / 2])
    return {"estimate": float(est), "ci_low": float(lo), "ci_high": float(hi), "boot": boots}


def paired_difference(subjects, y, pred_a, pred_b, n_boot: int = 2000, seed: int = 0,
                      ci: float = 0.95) -> dict:
    """Bootstrap CI of spearman(y, pred_a) - spearman(y, pred_b), resampling learners.

    Both models must be scored on the same rows and the same folds (paired comparison).
    """
    def diff(yy, a, b):
        return spearman(yy, a) - spearman(yy, b)
    return bootstrap_learners(diff, subjects, y, pred_a, pred_b, n_boot=n_boot, seed=seed, ci=ci)


def equivalence_tost(subjects, y, pred_a, pred_b, margin: float = 0.10,
                     n_boot: int = 2000, seed: int = 0) -> dict:
    """Two one-sided tests via the bootstrap: equivalent if the 90% CI of the difference
    lies entirely inside (-margin, +margin). (H1b: eye vs EEG.)
    """
    r = paired_difference(subjects, y, pred_a, pred_b, n_boot=n_boot, seed=seed, ci=0.90)
    r["margin"] = margin
    r["equivalent"] = bool(-margin < r["ci_low"] and r["ci_high"] < margin)
    return r


def holm(pvals: dict[str, float], alpha: float = 0.05) -> dict[str, dict]:
    """Holm step-down correction. Returns adjusted p and reject flag per name."""
    names = sorted(pvals, key=pvals.get)
    m = len(names)
    out, running = {}, 0.0
    for i, n in enumerate(names):
        adj = min(1.0, max(running, (m - i) * pvals[n]))
        running = adj
        out[n] = {"p": pvals[n], "p_holm": adj, "reject": adj < alpha}
    return out
