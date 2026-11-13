"""D-31: protect the corrected statistic, nested grouping, and source artifacts."""
import copy

import numpy as np
import pandas as pd
import pytest
from sklearn.linear_model import Ridge
from sklearn.model_selection import GroupKFold
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

from bbbd import reconcile_eye as r
from bbbd.config import load_config


def synthetic():
    rng = np.random.default_rng(72)
    groups = np.repeat(np.arange(9), 2)
    X = rng.normal(size=(18, 3)) * [1, 10, 100]
    y = X[:, 0] + rng.normal(size=18)
    schemes = {"first": groups % 3, "second": (groups // 3) % 3}
    return X, y, groups, schemes


def test_nested_matches_manual_inner_grouped_search():
    X, y, groups, schemes = synthetic()
    alphas = [0.1, 10.0]
    predictions, baseline, chosen = r.nested_predictions(X, y, groups, schemes, alphas)
    folds = schemes["first"]
    tr, te = np.where(folds != 0)[0], np.where(folds == 0)[0]
    losses = []
    for alpha in alphas:
        loss = []
        for inner_tr, inner_va in GroupKFold(3).split(X[tr], y[tr], groups[tr]):
            assert not set(groups[tr][inner_tr]) & set(groups[tr][inner_va])
            model = make_pipeline(StandardScaler(), Ridge(alpha=alpha))
            model.fit(X[tr][inner_tr], y[tr][inner_tr])
            loss.append(np.mean((y[tr][inner_va] - model.predict(X[tr][inner_va])) ** 2))
        losses.append(np.mean(loss))
    alpha = alphas[np.argmin(losses)]
    model = make_pipeline(StandardScaler(), Ridge(alpha=alpha)).fit(X[tr], y[tr])
    np.testing.assert_allclose(predictions[0, te], model.predict(X[te]))
    np.testing.assert_allclose(baseline[0, te], y[tr].mean())
    assert chosen[0]["alpha"] == alpha
    # Changing this outer fold's test targets must not affect its fitted predictions.
    changed = y.copy()
    changed[te] += 1000
    other, _, _ = r.nested_predictions(X, changed, groups, schemes, alphas)
    np.testing.assert_allclose(predictions[0, te], other[0, te])


def test_permutation_statistic_averages_all_repeats(monkeypatch):
    seen = []
    predictions = np.array([[3, 1, 2, 0], [0, 1, 2, 3]])

    def fit(X, y, subjects, schemes, *args):
        seen.append((y.copy(), list(schemes)))
        return predictions, np.zeros_like(predictions), []

    monkeypatch.setattr(r, "nested_predictions", fit)
    y = np.array([1., 2., 4., 3.])
    score = r.fit_score(None, y, None, {"a": None, "b": None}, [1], 3, "neg_mean_squared_error")
    assert score == r.stats.spearman(y, predictions.mean(axis=0))
    assert seen[0][1] == ["a", "b"]
    np.testing.assert_array_equal(seen[0][0], y)


def test_resume_permutations_preserve_stream_and_video_strata():
    y = np.arange(20.)
    videos = np.tile(np.arange(4), 5)
    all_targets = list(r.permutation_targets(y, videos, 2026, 0, 8))
    resumed = list(r.permutation_targets(y, videos, 2026, 3, 5))
    np.testing.assert_array_equal(all_targets[3:], resumed)
    for target in all_targets:
        for video in np.unique(videos):
            np.testing.assert_array_equal(np.sort(target[videos == video]), y[videos == video])


def test_baseline_skill_is_separately_defined():
    y = np.array([1., 2., 3.])
    pred = np.array([1., 2., 2.])
    baseline = np.zeros(3)
    assert r.training_mean_skill(y, pred, baseline) == pytest.approx(1 - 1 / 14)
    assert r.training_mean_skill(y, pred, baseline) != r.cv.score(y, pred)["r2"]


def test_real_input_contract_and_frozen_fold_copy():
    df, names, schemes, hashes = r.load_inputs(load_config())
    assert len(df) == 120 and df.subject.nunique() == 25 and len(names) == 8
    assert len(schemes) == 10
    assert hashes["folds"] == hashes["archived_folds"]


def test_registration_completion_and_resume(tmp_path, monkeypatch):
    """Tiny synthetic execution exercises artifacts and refuses incompatible resumes."""
    cfg = copy.deepcopy(load_config())
    cfg["paths"]["results_repo"] = str(tmp_path / "results")
    cfg["paths"]["run_registry"] = str(tmp_path / "registry.csv")
    cfg["stats"].update(n_permutations=3, n_bootstrap=20)
    cfg["reconciliation"].update(ridge_alpha_count=2, permutation_workers=1, checkpoint_every=2)
    X, y, groups, schemes = synthetic()
    names = ["a", "b", "c"]
    df = pd.DataFrame(X, columns=names).assign(subject=groups, video=np.tile([1, 2], 9), quiz_z=y)
    monkeypatch.setattr(r, "load_config", lambda: cfg)
    monkeypatch.setattr(r, "load_inputs", lambda cfg: (df, names, schemes, {"test": "synthetic"}))
    monkeypatch.setattr(r, "REPO_ROOT", tmp_path)
    monkeypatch.setattr(r.runlog, "git_info", lambda: ("synthetic", False))
    out = r.execute()
    result = r.json.loads((out / "eye_reconciliation.json").read_text())
    progress = r.json.loads((out / "progress.json").read_text())
    assert result["run_id"] == "R-001" and result["confirmatory"] is False
    assert result["n_permutations"] == 3 and len(progress["null"]) == 3
    assert result["p_permutation_raw"] == (1 + np.sum(
        np.asarray(progress["null"]) >= result["metrics"]["spearman"])) / 4
    assert r.execute(str(out)) == out
    cfg["stats"]["n_permutations"] = 4
    with pytest.raises(ValueError, match="changed"):
        r.execute(str(out))
